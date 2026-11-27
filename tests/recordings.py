"""Recordings of ONCat responses: how they are named and how they are stored.

A recording holds the runs of one experiment (one facility, instrument, and IPTS) as returned by ONCat. It is a
gzip-compressed JSON file. The file name is the truncated SHA-256 digest of the canonical request text, so that the
experiment is not obvious from a directory listing. This is obfuscation, not encryption: the name cannot be decoded,
but anyone can compute it for a candidate IPTS.
"""

import copy
import gzip
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import pyoncat

# Where the recordings of real ONCat responses are kept.
RECORDINGS_DIRECTORY = Path(__file__).parent / "data" / "oncat"
RECORDING_FORMAT = 2
_NAME_DIGEST_LENGTH = 32
_IPTS_PREFIX = re.compile(r"^IPTS[-_]?", re.IGNORECASE)
# The only experiment form that ONCat matches.
_EXPERIMENT = re.compile(r"IPTS-[0-9]+")
# Top-level keys that ONCat returns for every run, whatever the projection.
_ALWAYS_PROJECTED = ("id", "object", "type")
_SORT_DIRECTIONS = ("ASCENDING", "DESCENDING")


def _canonical_part(value: str, what: str) -> str:
    text = (value or "").strip().upper()
    if not text:
        raise ValueError(f"{what} must be a non-empty string, got {value!r}.")
    return text


def _canonical_experiment(experiment: str) -> str:
    number = _IPTS_PREFIX.sub("", (experiment or "").strip()).strip()
    if not number:
        raise ValueError(f"experiment must name an IPTS, got {experiment!r}.")
    return f"IPTS_{number.upper()}"


def recording_name(facility: str, instrument: str, experiment: str) -> str:
    """The file name of the recording of one experiment.

    ``experiment`` may be a bare number (``"24703"``) or carry the prefix (``"IPTS-24703"``, ``"ipts_24703"``).
    """
    text = "_".join(
        (
            _canonical_part(facility, "facility"),
            _canonical_part(instrument, "instrument"),
            _canonical_experiment(experiment),
        )
    )
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{digest[:_NAME_DIGEST_LENGTH]}.json.gz"


def write_recording(
    path: Union[str, Path],
    runs: List[Dict[str, Any]],
    *,
    projection: Sequence[str],
    pyoncat_version: str,
    recorded_at: str,
) -> None:
    """Write ``runs`` (a list of run dictionaries) to ``path``.

    ``projection`` is the list of paths that the runs were requested with. The store uses it to refuse a request for
    a path that was not recorded. The output is deterministic: the gzip header carries neither a time stamp nor a file
    name.
    """
    document = {
        "format": RECORDING_FORMAT,
        "recorded_at": recorded_at,
        "pyoncat_version": pyoncat_version,
        "projection": list(projection),
        "runs": runs,
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    # Write next to the destination, then replace it in one step, so that an interrupted write cannot leave a
    # truncated recording in place of a good one.
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".partial")
    try:
        with os.fdopen(descriptor, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as packed:
            packed.write(payload)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def read_recording(path: Union[str, Path]) -> Dict[str, Any]:
    """Read a recording written by :func:`write_recording`.

    Raises
    ------
    ValueError
        If the file does not have the supported ``format``.
    """
    with gzip.open(path, "rb") as packed:
        document = json.loads(packed.read().decode("utf-8"))
    if document.get("format") != RECORDING_FORMAT:
        raise ValueError(f"Unsupported recording format {document.get('format')!r} in {path}.")
    return document


class RecordingNotFoundError(pyoncat.NotFoundError):
    """Raised when there is no recording for the requested facility, instrument, and experiment."""


def _uncovered_paths(requested: Sequence[str], recorded: Sequence[str]) -> List[str]:
    """The requested paths that are neither one of the recorded paths nor below one of them."""
    return [
        path
        for path in requested
        if path not in _ALWAYS_PROJECTED
        and not any(path == prefix or path.startswith(prefix + ".") for prefix in recorded)
    ]


def project(content: Dict[str, Any], paths: Sequence[str]) -> Dict[str, Any]:
    """The part of a run that ONCat returns for a projection.

    The result always holds ``id``, ``object``, and ``type``, plus every dot-delimited path of ``paths`` that exists
    in ``content``, either a leaf or a whole branch, nested as in the source. Missing paths are left out. The result
    shares no data with ``content``.
    """
    result = {key: copy.deepcopy(content[key]) for key in _ALWAYS_PROJECTED if key in content}
    for path in paths:
        parts = path.split(".")
        value = content
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                break
            value = value[part]
        else:
            target = result
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = copy.deepcopy(value)
    return result


class RecordingStore:
    """The recordings in one directory, queried like ``agent.Run.list``."""

    def __init__(self, directory: Union[str, Path]) -> None:
        self._directory = Path(directory)

    def list_runs(
        self,
        *,
        facility: str,
        instrument: str,
        experiment: str,
        projection: Optional[Sequence[str]] = None,
        sort_direction: str = "ASCENDING",
    ) -> List[pyoncat.ONCatObject]:
        """The recorded runs of one experiment, sorted by ``id``, as ``ONCatObject`` instances.

        Without a ``projection`` the runs are returned as recorded. Only the arguments above are supported; any other
        argument of the real ``Run.list`` (``sort_by``, ``page_size``, ``since_id``) raises ``TypeError``.

        Raises
        ------
        RecordingNotFoundError
            If there is no recording for the request, or if ``experiment`` is not written as ``IPTS-<number>``.
        ValueError
            If ``sort_direction`` is neither ``"ASCENDING"`` nor ``"DESCENDING"``, or if ``projection`` asks for a path
            that the recording does not hold (one that is not equal to, or below, a path of its projection).
        """
        if sort_direction not in _SORT_DIRECTIONS:
            raise ValueError(f"sort_direction must be one of {_SORT_DIRECTIONS}, got {sort_direction!r}.")
        # ONCat matches only the exact IPTS-<number> form. Refusing any other form here makes a test fail when the
        # code under test sends, for example, the bare number that a user typed.
        if not isinstance(experiment, str) or _EXPERIMENT.fullmatch(experiment) is None:
            raise RecordingNotFoundError(
                f"ONCat would find no runs for experiment={experiment!r}: the experiment must be written as "
                "IPTS-<number>, for example IPTS-24703."
            )
        path = self._directory / recording_name(facility, instrument, experiment)
        if not path.is_file():
            raise RecordingNotFoundError(
                f"No recording for facility={facility!r}, instrument={instrument!r}, experiment={experiment!r}. "
                "Create it with `pixi run record-oncat <facility> <instrument> IPTS-<number>`."
            )
        document = read_recording(path)
        if projection is not None:
            # Without this check a path that was not recorded would give None, as if the runs did not have it.
            uncovered = _uncovered_paths(projection, document["projection"])
            if uncovered:
                raise ValueError(
                    f"The recording of {facility}/{instrument}/{experiment} does not hold {uncovered}: it was "
                    f"recorded with the projection {document['projection']}. Record it again with a --projection "
                    "that covers these paths."
                )
        runs = sorted(document["runs"], key=lambda run: run["id"], reverse=sort_direction == "DESCENDING")
        if projection is not None:
            runs = [project(run, projection) for run in runs]
        return [pyoncat.ONCatObject(content=run) for run in runs]
