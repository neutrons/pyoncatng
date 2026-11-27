"""Recordings of ONCat responses: how they are named and how they are stored.

A recording holds the runs of one experiment (one facility, instrument, and IPTS) as returned by ONCat. It is a
gzip-compressed JSON file. The file name is the truncated SHA-256 digest of the canonical request text, so that the
experiment is not obvious from a directory listing. This is obfuscation, not encryption: the name cannot be decoded,
but anyone can compute it for a candidate IPTS.
"""

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union

RECORDING_FORMAT = 1
_NAME_DIGEST_LENGTH = 32
_IPTS_PREFIX = re.compile(r"^IPTS[-_]?", re.IGNORECASE)


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
    path: Union[str, Path], runs: List[Dict[str, Any]], *, pyoncat_version: str, recorded_at: str
) -> None:
    """Write ``runs`` (a list of run dictionaries) to ``path``.

    The output is deterministic: the gzip header carries neither a time stamp nor a file name.
    """
    document = {
        "format": RECORDING_FORMAT,
        "recorded_at": recorded_at,
        "pyoncat_version": pyoncat_version,
        "runs": runs,
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    with Path(path).open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as packed:
        packed.write(payload)


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
