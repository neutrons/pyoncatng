"""Tests for the IPTSRunGroupFrozenTable widget.

Two layers (mirroring ``test_iptstable_widget.py``):

* **Unit tests** on the construction validation, which need no UI context.
* **Widget tests** via NiceGUI's in-process ``user`` simulation. The test page
  builds the widget with a scriptable fake agent, which a test reaches through
  ``widget._agent`` before calling ``widget._on_load()``.
"""

import asyncio

import pytest
from nicegui import context
from nicegui.events import GenericEventArguments
from nicegui.testing import User

from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable, _validate_construction
from pyoncatng.widgets.iptstable import DEFAULT_PROCESSING_VARIABLES, IPTSTable
from pyoncatng.widgets.rungroupfrozentable import GROUP_INDEX_KEY, RESERVED_GROUP_KEYS, RunGroupFrozenTable
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

# Runs of a second IPTS, with other titles and run IDs.
RUNS_OTHER = [
    {"id": 140, "datafiles.raw.metadata.entry.title": "C"},
    {"id": 139, "datafiles.raw.metadata.entry.title": "C"},
    {"id": 138, "datafiles.raw.metadata.entry.title": "D"},
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


@pytest.mark.parametrize("group_by", sorted(RESERVED_GROUP_KEYS))
def test_reserved_group_by_is_rejected(group_by: str) -> None:
    with pytest.raises(ValueError, match="is reserved"):
        _validate_construction([TITLE, (group_by, "datafiles.raw.metadata.entry.other")], group_by)


def test_reserved_label_is_accepted_when_it_is_not_group_by() -> None:
    assert _validate_construction([TITLE, ("Size", "datafiles.raw.metadata.entry.size")], "Title")[1][0] == "Size"


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
    called: list = []

    def record(self, handler):
        registered.append((self, handler))
        return self

    monkeypatch.setattr(RunGroupFrozenTable, "on_selection_change", record)

    def first() -> None:
        called.append("first")

    def second() -> None:
        called.append("second")

    def forwarded() -> list:
        """Call every registered handler with an event of the inner grid; return the callbacks that ran."""
        called.clear()
        for table, handler in registered:
            handler(GenericEventArguments(sender=table._table, client=widget.client, args={}))
        return list(called)

    widget.on_selection_change(first).on_selection_change(second)
    assert [table for table, _ in registered] == [_inner(user)] * 2
    assert forwarded() == ["first", "second"]

    for _ in range(3):
        registered.clear()
        await _load(widget)
        assert [table for table, _ in registered] == [_inner(user)] * 2
        assert forwarded() == ["first", "second"]


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


def _model_grid_selection(monkeypatch) -> list:
    """Model the browser, where each grid keeps its own selection.

    ``get_selected_rows`` returns the ``fake_selection`` attribute of the grid it
    is called on. Calls to ``run_grid_method`` are recorded and returned, so that
    a test can check that the widget never asks a grid to restore a selection.
    """
    grid_calls: list = []

    async def get_selected_rows(grid):
        return getattr(grid, "fake_selection", [])

    def run_grid_method(grid, name, *args, **kwargs):
        grid_calls.append((grid, name, args, kwargs))
        return asyncio.sleep(0)

    monkeypatch.setattr(RunTable, "get_selected_rows", get_selected_rows)
    monkeypatch.setattr(RunTable, "run_grid_method", run_grid_method)
    return grid_calls


def _select(user: User, group_indexes: list[int]) -> None:
    """Simulate the user selecting groups: the grid holds them and emits ``selectionChanged``."""
    grid = _inner(user)._table
    grid.fake_selection = [{GROUP_INDEX_KEY: index} for index in group_indexes]
    user.find(RunTable).trigger("selectionChanged")


async def _next(queue: asyncio.Queue):
    """Return the next item that an async callback put on ``queue``, which the event loop runs as a task."""
    async with asyncio.timeout(2):
        return await queue.get()


async def test_loading_another_ipts_clears_the_selection(user: User, monkeypatch) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    grid_calls = _model_grid_selection(monkeypatch)
    seen: asyncio.Queue = asyncio.Queue()

    async def on_change(event: GenericEventArguments) -> None:
        await seen.put(
            {
                "sender": event.sender,
                "args": event.args,
                "indexes": await widget.selected_group_indexes(),
                "ids": [row["ID"] for row in await widget.selected_source_rows()],
            }
        )

    widget.on_selection_change(on_change)

    # IPTS 24703: the Load event arrives with an empty selection.
    await _load(widget)
    assert (await _next(seen))["indexes"] == ()

    # The user selects the first group; a real selectionChanged event reaches the callback.
    first_table = _inner(user)
    _select(user, [0])
    selected = await _next(seen)
    assert selected["sender"] is widget
    assert selected["indexes"] == (0,)
    assert selected["ids"] == [130, 128, 127]

    # IPTS 24704: the callback is called again, and it reads an empty selection.
    widget._agent.run_result = RUNS_OTHER
    widget._input.value = "24704"
    await widget._on_load()
    cleared = await _next(seen)
    assert widget._agent.run_kwargs["experiment"] == "IPTS-24704"
    assert cleared["sender"] is widget
    assert cleared["args"] == {}
    assert cleared["indexes"] == ()
    assert cleared["ids"] == []
    assert seen.empty()

    # The accessors read the new table. The first grid still holds its selection,
    # and the widget did not ask the new grid to restore one.
    assert _inner(user) is not first_table
    assert first_table._table.fake_selection == [{GROUP_INDEX_KEY: 0}]
    assert await widget.selected_group_indexes() == ()
    assert await widget.selected_groups() == ()
    assert await widget.selected_source_rows() == ()
    assert [row["ID"] for row in widget.rows] == [140, 139, 138]
    assert widget.groups == ((0, 1), (2,))
    assert all(grid is not _inner(user)._table for grid, *_ in grid_calls)


async def test_callbacks_fire_after_every_load_and_on_real_events(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    calls: list = []
    widget.on_selection_change(lambda: calls.append("event"))

    for expected in (1, 2, 3):
        await _load(widget)
        assert len(calls) == expected

    user.find(RunTable).trigger("selectionChanged")
    assert len(calls) == 4


async def test_each_new_grid_listens_once_per_callback(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    calls: list = []
    widget.on_selection_change(lambda: calls.append("first")).on_selection_change(lambda: calls.append("second"))

    def listeners() -> list:
        grid = _inner(user)._table
        return [listener for listener in grid._event_listeners.values() if listener.type == "selectionChanged"]

    assert len(listeners()) == 2
    for _ in range(3):
        await _load(widget)
        assert len(listeners()) == 2
        calls.clear()
        user.find(RunTable).trigger("selectionChanged")
        assert calls == ["first", "second"]


async def test_every_event_has_the_widget_as_sender_and_the_same_context(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    seen: list = []

    def on_change(event: GenericEventArguments) -> None:
        seen.append((event, context.slot))

    widget.on_selection_change(on_change)
    payload = {"source": "grid"}

    user.find(RunTable).trigger("selectionChanged", args=payload)  # a change made by the user
    await _load(widget)  # a Load clears the selection

    (real, real_slot), (loaded, loaded_slot) = seen
    for event in (real, loaded):
        assert event.sender is widget
        assert event.client is widget.client
    assert real.args == payload
    assert loaded.args == {}
    # Callbacks run next to the widget for both events, not inside the private inner table.
    assert real_slot is widget.parent_slot
    assert loaded_slot is widget.parent_slot


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


async def test_reserved_group_by_leaves_no_partial_widget(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    before = len(user.find(IPTSRunGroupFrozenTable).elements)

    with user, pytest.raises(ValueError, match="is reserved"):
        IPTSRunGroupFrozenTable(
            agent=widget._agent, group_by="Size", processing_variables=[("Size", "datafiles.raw.metadata.entry.size")]
        )

    assert len(user.find(IPTSRunGroupFrozenTable).elements) == before


async def test_container_and_inner_table_grow_with_the_widget(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    # A height set by the caller reaches the grid only if every level of the layout grows.
    assert widget._container._style["flex"] == "1 1 auto"
    assert widget._container._style["min-height"] == "0"
    assert _inner(user)._style["flex"] == "1 1 auto"

    await _load(widget)

    assert _inner(user)._style["flex"] == "1 1 auto"


async def test_no_message_is_shown_before_the_first_load(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    assert widget._message.text == ""
    assert widget._message.visible is False


async def test_load_is_ignored_while_another_load_runs(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    widget._input.value = "24703"
    widget._set_message("kept")
    before = _inner(user)

    widget._busy = True
    await widget._on_load()

    assert widget._agent.run_calls == 0
    assert _inner(user) is before
    assert widget._message.text == "kept"

    widget._busy = False
    await widget._on_load()

    assert widget._agent.run_calls == 1
    assert widget._busy is False
    assert widget._load_button.enabled


async def test_callbacks_fire_after_a_failed_load_and_a_load_without_runs(user: User) -> None:
    await user.open("/iptsrungroupfrozentable")
    widget = _widget(user)
    events: list = []
    widget.on_selection_change(lambda event: events.append(event))
    widget._input.value = "24703"

    widget._agent.run_error = RuntimeError("no session")
    await widget._on_load()
    assert len(events) == 1

    widget._agent.run_error = None
    widget._agent.run_result = []
    await widget._on_load()

    assert len(events) == 2
    assert all(event.sender is widget and event.args == {} for event in events)
