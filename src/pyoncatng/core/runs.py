"""Blocking ONCat run-listing helper, free of any NiceGUI import.

Wraps :meth:`pyoncat.ONCat.Run.list` so the widget layer can call it off the
event loop (via ``asyncio.to_thread``) and translate any failure into UI. Kept
NiceGUI-agnostic so it can be unit-tested without a browser, mirroring the
core/widget split used elsewhere (see :mod:`.client`).
"""

from typing import Any, List, Sequence

import pyoncat


def list_runs(
    agent: pyoncat.ONCat,
    *,
    facility: str,
    instrument: str,
    experiment: str,
    projection: Sequence[str],
    sort_direction: str = "DESCENDING",
) -> List[Any]:
    """List the runs of one experiment, most recent first.

    This performs blocking network I/O; run it off the event loop.

    Params
    ------
    agent : pyoncat.ONCat
        An authenticated ONCat agent.
    facility : str
        Facility identifier, e.g. ``"SNS"``.
    instrument : str
        Instrument identifier, e.g. ``"USANS"``.
    experiment : str
        IPTS identifier, e.g. ``"IPTS-24703"``.
    projection : sequence of str
        Metadata paths to fetch for each run (dot-delimited), e.g.
        ``["metadata.entry.title"]``.
    sort_direction : str, optional
        ``"ASCENDING"`` or ``"DESCENDING"``. Defaults to ``"DESCENDING"`` so the
        highest run numbers come first.

    Returns
    -------
    list
        The run objects returned by ONCat (each supports ``run["id"]`` and
        dot-path ``run.get("...")``).

    Raises
    ------
    pyoncat.PyONCatError
        Propagated from the underlying request (e.g. no live session).
    """
    return agent.Run.list(
        facility=facility,
        instrument=instrument,
        experiment=experiment,
        projection=list(projection),
        sort_direction=sort_direction,
    )
