"""Tests for the IPTSRunGroupFrozenTable widget.

Two layers (mirroring ``test_iptstable_widget.py``):

* **Unit tests** on the construction validation, which need no UI context.
* **Widget tests** via NiceGUI's in-process ``user`` simulation. The test page
  builds the widget with a scriptable fake agent, which a test reaches through
  ``widget._agent`` before calling ``widget._on_load()``.
"""

import pytest
from nicegui.testing import User

from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable, _validate_construction
from pyoncatng.widgets.iptstable import DEFAULT_PROCESSING_VARIABLES, IPTSTable
from pyoncatng.widgets.rungroupfrozentable import RunGroupFrozenTable

TITLE = ("Title", "datafiles.raw.metadata.entry.title")
START = ("Start Time", "datafiles.raw.metadata.entry.start_time")

# Runs as ONCat returns them (newest first) with a flat, dot-path projection.
# Title "A" is repeated at indexes 0, 1, and 3, and is not adjacent.
RUNS = [
    {"id": 130, "datafiles.raw.metadata.entry.title": "A"},
    {"id": 128, "datafiles.raw.metadata.entry.title": "A"},
    {"id": 129, "datafiles.raw.metadata.entry.title": "B"},
    {"id": 127, "datafiles.raw.metadata.entry.title": "A"},
]


def test_valid_construction_returns_pairs() -> None:
    assert _validate_construction([TITLE, [" Start Time ", " datafiles.raw.metadata.entry.start_time "]], "Title") == [
        TITLE,
        START,
    ]


def test_default_processing_variables_accept_title() -> None:
    assert _validate_construction(DEFAULT_PROCESSING_VARIABLES, "Title") == list(DEFAULT_PROCESSING_VARIABLES)


def test_group_by_must_be_a_label() -> None:
    with pytest.raises(ValueError, match="must be one of the processing_variables labels"):
        _validate_construction([TITLE, START], "Sample")


def test_group_by_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be one of the processing_variables labels"):
        _validate_construction([TITLE], "ID")


def test_id_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="'ID' is reserved"):
        _validate_construction([TITLE, ("ID", "datafiles.raw.metadata.entry.id")], "Title")


def test_duplicate_labels_are_rejected() -> None:
    with pytest.raises(ValueError, match="labels must be unique"):
        _validate_construction([TITLE, ("Title", "other.path")], "Title")


@pytest.mark.parametrize("value", [("Title",), ("Title", ""), ("Title", 1), "ab", None])
def test_malformed_pair_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="must be a .label, path. pair"):
        _validate_construction([value], "Title")


# -- widget tests: live element via the user simulation -----------------------


def _widget(user: User) -> IPTSRunGroupFrozenTable:
    return next(iter(user.find(IPTSRunGroupFrozenTable).elements))


def _inner(user: User) -> RunGroupFrozenTable:
    return next(iter(user.find(RunGroupFrozenTable).elements))


async def test_renders_with_an_empty_table(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    await user.should_see(kind=IPTSRunGroupFrozenTable)
    await user.should_see("IPTS:")
    await user.should_see("Load")
    assert _inner(user).rows == ()
    assert _inner(user).groups == ()


async def test_load_groups_the_runs(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._agent.run_result = RUNS
    widget._input.value = "24703"

    await widget._on_load()

    kwargs = widget._agent.run_kwargs
    assert kwargs["experiment"] == "IPTS-24703"
    assert kwargs["facility"] == "SNS"
    assert kwargs["instrument"] == "USANS"
    assert kwargs["projection"] == IPTSTable.build_projection(widget._column_spec)
    assert kwargs["sort_direction"] == "DESCENDING"
    inner = _inner(user)
    assert inner.groups == ((0, 1, 3), (2,))
    assert [row["ID"] for row in inner.rows] == [130, 128, 129, 127]
    assert inner._table.options["rowData"] == [
        {"Title": "A", "First": 127, "Last": 130, "Size": 3, "_group_index": 0},
        {"Title": "B", "First": 129, "Last": 129, "Size": 1, "_group_index": 1},
    ]


async def test_load_button_triggers_fetch(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._input.value = "24703"  # run_result defaults to empty

    user.find("Load").click()

    await user.should_see("No runs found for IPTS-24703.")
    assert widget._agent.run_calls == 1


async def test_no_runs_shows_an_empty_table_and_a_message(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._input.value = "24703"

    await widget._on_load()

    assert _inner(user).groups == ()
    assert _inner(user)._table.options["rowData"] == []
    await user.should_see("No runs found for IPTS-24703.")


async def test_failed_load_shows_an_empty_table_and_a_message(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._agent.run_error = RuntimeError("no session")
    widget._input.value = "24703"

    await widget._on_load()

    assert _inner(user).groups == ()
    await user.should_see("Could not load runs for IPTS-24703: no session")


async def test_failed_load_clears_the_previous_groups(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._agent.run_result = RUNS
    widget._input.value = "24703"
    await widget._on_load()
    assert _inner(user).groups == ((0, 1, 3), (2,))

    widget._agent.run_error = RuntimeError("no session")
    await widget._on_load()

    assert _inner(user).groups == ()
    assert _inner(user).rows == ()


async def test_empty_input_leaves_the_table_unchanged(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._agent.run_result = RUNS
    widget._input.value = "24703"
    await widget._on_load()
    before = _inner(user)
    calls = widget._agent.run_calls

    widget._input.value = "   "
    await widget._on_load()

    assert widget._agent.run_calls == calls
    assert _inner(user) is before
    await user.should_see("Please enter an IPTS number.")


async def test_reload_replaces_the_inner_table(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._agent.run_result = RUNS
    widget._input.value = "24703"
    await widget._on_load()
    first = _inner(user)

    widget._agent.run_result = RUNS[:2]
    await widget._on_load()

    second = _inner(user)
    assert second is not first
    assert second.groups == ((0, 1),)
    assert list(widget._container.default_slot.children) == [second]
