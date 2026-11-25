"""Tests for the IPTSRunGroupFrozenTable widget.

Two layers (mirroring ``test_iptstable_widget.py``):

* **Unit tests** on the construction validation, which need no UI context.
* **Widget tests** via NiceGUI's in-process ``user`` simulation. The test page
  builds the widget with a scriptable fake agent, which a test reaches through
  ``widget._agent`` before calling ``widget._on_load()``.
"""

import pytest
from nicegui.events import GenericEventArguments
from nicegui.testing import User

from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable, _validate_construction
from pyoncatng.widgets.iptstable import DEFAULT_PROCESSING_VARIABLES, IPTSTable
from pyoncatng.widgets.rungroupfrozentable import GROUP_INDEX_KEY, RunGroupFrozenTable
from pyoncatng.widgets.runtable import RunTable

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


async def _load(widget: IPTSRunGroupFrozenTable, runs=RUNS) -> None:
    widget._agent.run_result = runs
    widget._input.value = "24703"
    await widget._on_load()


async def test_callbacks_fire_after_a_load(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    calls: list = []

    def without_arguments() -> None:
        calls.append("no arguments")

    def with_event(event: GenericEventArguments) -> None:
        calls.append(event)

    assert widget.on_selection_change(without_arguments) is widget
    widget.on_selection_change(with_event)

    await _load(widget)

    assert calls[0] == "no arguments"
    assert isinstance(calls[1], GenericEventArguments)
    assert calls[1].sender is widget
    assert calls[1].args == {}
    assert len(calls) == 2


async def test_callbacks_are_registered_on_every_new_table(user: User, monkeypatch) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    registered: list = []

    def record(self, callback):
        registered.append((self, callback))
        return self

    monkeypatch.setattr(RunGroupFrozenTable, "on_selection_change", record)

    def first() -> None:
        pass

    def second() -> None:
        pass

    widget.on_selection_change(first).on_selection_change(second)
    assert registered == [(_inner(user), first), (_inner(user), second)]

    for _ in range(3):
        registered.clear()
        await _load(widget)
        assert registered == [(_inner(user), first), (_inner(user), second)]


async def test_empty_input_sends_no_event(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    calls: list = []
    widget.on_selection_change(lambda: calls.append("event"))
    await _load(widget)
    assert calls == ["event"]

    widget._input.value = "   "
    await widget._on_load()

    assert calls == ["event"]


async def test_reload_clears_the_selection(user: User, monkeypatch) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    await _load(widget)

    # The browser keeps the selection of each grid; model it with an attribute.
    async def fake_get_selected_rows(grid):
        return getattr(grid, "fake_selection", [])

    monkeypatch.setattr(RunTable, "get_selected_rows", fake_get_selected_rows)
    _inner(user)._table.fake_selection = [{GROUP_INDEX_KEY: 0}]
    assert await widget.selected_group_indexes() == (0,)
    assert [row["ID"] for row in await widget.selected_source_rows()] == [130, 128, 127]

    await _load(widget)

    assert await widget.selected_group_indexes() == ()
    assert await widget.selected_groups() == ()
    assert await widget.selected_source_rows() == ()


async def test_accessors_reflect_the_latest_load(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    await _load(widget)
    assert widget.groups == ((0, 1, 3), (2,))

    await _load(widget, RUNS[:3])

    assert [row["ID"] for row in widget.rows] == [130, 128, 129]
    assert widget.groups == ((0, 1), (2,))
    assert [row["ID"] for row in widget.rows_for_group(1)] == [129]
    assert widget.group_by == "Title"
