"""Record the runs of one ONCat experiment, so that tests can replay them offline.

Usage (signs in with the device flow, so a browser is needed)::

    pixi run record-oncat SNS USANS IPTS-24703

The recording is written to ``tests/data/oncat`` under an obfuscated name (see :mod:`recordings`). Recording an
experiment again replaces its file.
"""

import argparse
import gzip
import re
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from recordings import RECORDINGS_DIRECTORY, recording_name, write_recording

# The projection that returns every processing variable of a run.
DEFAULT_PROJECTION = ["datafiles.raw.metadata"]


def record(
    agent,
    *,
    facility: str,
    instrument: str,
    experiment: str,
    projection: Sequence[str] = DEFAULT_PROJECTION,
    directory: Path = RECORDINGS_DIRECTORY,
    allow_empty: bool = False,
) -> Dict[str, Any]:
    """Fetch the runs of one experiment through ``agent`` and write their recording.

    The real service returns an empty list for an experiment that does not exist, so an empty result is refused
    (nothing is written) unless ``allow_empty`` is set.

    Returns
    -------
    dict
        ``path`` of the recording, ``replaced`` (whether it overwrote a file), ``runs``, ``raw_bytes`` (size of the
        JSON text), and ``compressed_bytes`` (size of the file).
    """
    runs = agent.Run.list(
        facility=facility,
        instrument=instrument,
        experiment=experiment,
        projection=list(projection),
        sort_direction="ASCENDING",
    )
    if not runs and not allow_empty:
        raise ValueError(
            f"ONCat returned no runs for {facility}/{instrument}/{experiment}: the experiment may not exist or "
            "may not be readable. Nothing was written; use --allow-empty to record it anyway."
        )
    path = Path(directory) / recording_name(facility, instrument, experiment)
    replaced = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_recording(
        path,
        [run.to_dict() for run in runs],
        pyoncat_version=version("pyoncat"),
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return {
        "path": path,
        "replaced": replaced,
        "runs": len(runs),
        "raw_bytes": len(gzip.decompress(path.read_bytes())),
        "compressed_bytes": path.stat().st_size,
    }


def _experiment(text: str) -> str:
    """The experiment as ``IPTS-<number>``. A bare number is refused: it could be taken for a run number."""
    match = re.fullmatch(r"IPTS-([0-9]+)", text.strip(), flags=re.IGNORECASE)
    if match is None:
        raise argparse.ArgumentTypeError(
            f"{text!r} must be written as IPTS-<number>, for example IPTS-24703, to make clear that it is an IPTS "
            "number and not a run number."
        )
    return f"IPTS-{match.group(1)}"


def _build_signed_in_agent():
    from pyoncatng.configuration import Configuration
    from pyoncatng.core.client import build_agent

    def show_challenge(challenge) -> None:
        print(f"\nOpen {challenge.verification_uri_complete}\nand confirm the code {challenge.user_code}\n", flush=True)

    settings = Configuration().config["login.oncat"]
    token = {}
    agent = build_agent(
        settings["oncat_url"],
        settings["client_id"],
        token_getter=lambda: token.get("value"),
        token_setter=lambda value: token.update(value=value),
        verification_handler=show_challenge,
    )
    agent.login()
    return agent


def main(argv: Optional[Sequence[str]] = None, *, agent=None) -> int:
    """Run the command; ``agent`` replaces the signed-in agent (used by the tests)."""
    parser = argparse.ArgumentParser(description="Record the runs of one ONCat experiment for the tests.")
    parser.add_argument("facility", help="for example SNS")
    parser.add_argument("instrument", help="for example USANS")
    parser.add_argument("ipts", type=_experiment, metavar="IPTS-<number>", help="for example IPTS-24703")
    parser.add_argument("--projection", nargs="+", default=DEFAULT_PROJECTION, help="metadata paths to record")
    parser.add_argument("--directory", type=Path, default=RECORDINGS_DIRECTORY, help="where to write the recording")
    parser.add_argument("--allow-empty", action="store_true", help="record an experiment that has no runs")
    args = parser.parse_args(argv)

    report = record(
        agent if agent is not None else _build_signed_in_agent(),
        facility=args.facility,
        instrument=args.instrument,
        experiment=args.ipts,
        projection=args.projection,
        directory=args.directory,
        allow_empty=args.allow_empty,
    )
    print(f"{'Replaced' if report['replaced'] else 'Wrote'} {report['path']}")
    print(
        f"  {report['runs']} runs, {report['raw_bytes']:,} bytes of JSON, "
        f"{report['compressed_bytes']:,} bytes compressed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
