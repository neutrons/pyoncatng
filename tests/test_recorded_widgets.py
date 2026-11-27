"""Integration tests of the IPTS widgets against the recording of SNS/USANS IPTS-24703.

The pages use a ``RecordedAgent``, so the widgets load real ONCat responses without signing in.
"""

import pytest
from nicegui.testing import User
from recordings import RECORDINGS_DIRECTORY, read_recording, recording_name

from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable
from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.rungroupfrozentable import RunGroupFrozenTable
from pyoncatng.widgets.runtable import RunTable


def _recorded_runs() -> list:
    """The (id, title) pairs of the recording, newest first, as the widgets request them."""
    document = read_recording(RECORDINGS_DIRECTORY / recording_name("SNS", "USANS", "IPTS-24703"))
    runs = sorted(document["runs"], key=lambda run: run["id"], reverse=True)
    return [(run["id"], run["datafiles"]["raw"]["metadata"]["entry"]["title"]) for run in runs]


def _element(user: User, kind: type):
    return next(iter(user.find(kind).elements))


@pytest.mark.parametrize("typed", ["24703", "IPTS-24703", "ipts-24703"])
async def test_iptstable_loads_the_recorded_runs(user: User, typed: str) -> None:
    await user.open("/iptstable-recorded")
    widget = _element(user, IPTSTable)
    # A bare number is accepted in the field. The recorded agent finds runs only for "IPTS-24703", so this also
    # checks that the widget adds the prefix before it calls ONCat.
    widget._input.value = typed

    await widget._on_load()

    rows = _element(user, RunTable).options["rowData"]
    expected = _recorded_runs()
    assert len(rows) == len(expected) > 0
    assert [(row["ID"], row["Title"]) for row in rows] == expected
    assert all(row["Start Time"] and row["Total Counts"] is not None for row in rows)


async def test_iptstable_reports_an_experiment_without_a_recording(user: User) -> None:
    await user.open("/iptstable-recorded")
    widget = _element(user, IPTSTable)
    widget._input.value = "1"

    await widget._on_load()

    await user.should_see("Could not load runs for IPTS-1: No recording for")
    assert _element(user, RunTable).options["rowData"] == []


async def test_iptsrungroupfrozentable_groups_the_recorded_runs_by_title(user: User) -> None:
    await user.open("/iptsrungroupfrozentable-recorded")
    widget = _element(user, IPTSRunGroupFrozenTable)
    widget._input.value = "24703"

    await widget._on_load()

    expected = _recorded_runs()
    positions = {}
    for index, (_, title) in enumerate(expected):
        positions.setdefault(title, []).append(index)
    inner = _element(user, RunGroupFrozenTable)
    assert [row["ID"] for row in inner.rows] == [run_id for run_id, _ in expected]
    assert inner.group_keys == tuple(positions)
    assert inner.groups == tuple(tuple(indexes) for indexes in positions.values())
    grid = inner._table.options["rowData"]
    assert [row["Title"] for row in grid] == list(positions)
    assert sum(row["Size"] for row in grid) == len(expected)


async def test_iptsrungroupfrozentable_reports_an_experiment_without_a_recording(user: User) -> None:
    await user.open("/iptsrungroupfrozentable-recorded")
    widget = _element(user, IPTSRunGroupFrozenTable)
    widget._input.value = "1"

    await widget._on_load()

    await user.should_see("Could not load runs for IPTS-1: No recording for")
    assert _element(user, RunGroupFrozenTable).groups == ()
