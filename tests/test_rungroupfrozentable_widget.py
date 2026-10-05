"""Tests for the RunGroupFrozenTable widget.

Two layers (mirroring ``test_runtable_widget.py``):

* **Unit tests** on the pure helpers (``freeze``, ``run_id``, ``validate_rows``,
  ``build_groups``, ``build_group_rows``, ``column_names``), which need no UI
  context.
* **Widget tests** via NiceGUI's in-process ``user`` simulation. AG Grid cells
  are rendered client-side, so the data is verified through the inner
  RunTable's ``options``. Tests that need their own input rows build the widget
  inside the page's client context (``with user:``).
"""

import copy
from types import MappingProxyType

import pytest
from nicegui.testing import User

from pyoncatng.widgets.rungroupfrozentable import (
    GROUP_INDEX_KEY,
    RunGroupFrozenTable,
    build_group_rows,
    build_groups,
    column_names,
    freeze,
    run_id,
    validate_rows,
)
from pyoncatng.widgets.runtable import RunTable

# Title "A" at indexes 0, 1, 3 (IDs out of order and non-consecutive); Title "B"
# at index 2 with a str ID.
ROWS = [
    {"ID": 124, "Title": "A", "Run": "r124"},
    {"ID": 129, "Title": "A", "Run": "r129"},
    {"ID": "125", "Title": "B", "Run": "r125"},
    {"ID": 123, "Title": "A", "Run": "r123"},
]

# -- unit tests: grouping -----------------------------------------------------


def test_build_groups_by_matching_values() -> None:
    assert build_groups(ROWS, "Title") == ((0, 1, 3), (2,))


def test_build_groups_is_tuple_of_int_tuples() -> None:
    groups = build_groups(ROWS, "Title")
    assert isinstance(groups, tuple)
    assert all(isinstance(group, tuple) for group in groups)
    assert all(isinstance(index, int) for group in groups for index in group)


def test_build_groups_key_is_configurable() -> None:
    rows = [
        {"ID": 1, "Title": "A", "Sample": "S2"},
        {"ID": 2, "Title": "A", "Sample": "S1"},
        {"ID": 3, "Title": "B", "Sample": "S2"},
    ]
    assert build_groups(rows, "Sample") == ((0, 2), (1,))


def test_build_groups_follow_first_occurrence() -> None:
    rows = [{"ID": 1, "Title": "Z"}, {"ID": 2, "Title": "A"}, {"ID": 3, "Title": "Z"}]
    assert build_groups(rows, "Title") == ((0, 2), (1,))


def test_build_groups_use_exact_equality() -> None:
    rows = [{"ID": 1, "Title": "A"}, {"ID": 2, "Title": "A "}, {"ID": 3, "Title": "a"}]
    assert build_groups(rows, "Title") == ((0,), (1,), (2,))


def test_build_groups_store_indexes_not_rows() -> None:
    groups = build_groups(ROWS, "Title")
    assert not any(isinstance(item, dict) for group in groups for item in group)


# -- unit tests: visible rows and columns -------------------------------------


def test_group_rows_size_first_last() -> None:
    groups = build_groups(ROWS, "Title")
    assert build_group_rows(ROWS, groups, "Title") == [
        {"Title": "A", "First": 123, "Last": 129, "Size": 3, GROUP_INDEX_KEY: 0},
        {"Title": "B", "First": 125, "Last": 125, "Size": 1, GROUP_INDEX_KEY: 1},
    ]


def test_group_rows_first_last_independent_of_order() -> None:
    rows = [{"ID": 9, "Title": "A"}, {"ID": 2, "Title": "A"}, {"ID": 5, "Title": "A"}]
    (row,) = build_group_rows(rows, build_groups(rows, "Title"), "Title")
    assert (row["First"], row["Last"]) == (2, 9)


def test_group_rows_cast_str_ids_to_int() -> None:
    rows = [{"ID": "10", "Title": "A"}, {"ID": "9", "Title": "A"}]
    (row,) = build_group_rows(rows, build_groups(rows, "Title"), "Title")
    # Compared as ints (9 < 10), not as strings ("10" < "9").
    assert (row["First"], row["Last"]) == (9, 10)


def test_group_rows_run_idkey_is_configurable() -> None:
    rows = [{"run_number": 7, "Title": "A"}, {"run_number": 3, "Title": "A"}]
    (row,) = build_group_rows(rows, build_groups(rows, "Title"), "Title", run_idkey="run_number")
    assert (row["First"], row["Last"]) == (3, 7)


def test_group_rows_have_no_sequence_or_range() -> None:
    for row in build_group_rows(ROWS, build_groups(ROWS, "Title"), "Title"):
        assert set(row) == {"Title", "First", "Last", "Size", GROUP_INDEX_KEY}
        assert not any(isinstance(value, str) and "-" in value for value in row.values())


def test_column_names_exclude_group_index() -> None:
    assert column_names("Title") == ["Title", "First", "Last", "Size"]
    assert GROUP_INDEX_KEY not in column_names("Title")


# -- unit tests: validation ---------------------------------------------------


def test_validate_rejects_empty_rows() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_rows([], "Title")


def test_validate_rejects_missing_group_by() -> None:
    with pytest.raises(ValueError, match="missing the group_by key"):
        validate_rows([{"ID": 1, "Title": "A"}, {"ID": 2}], "Title")


def test_validate_rejects_unhashable_group_value() -> None:
    with pytest.raises(ValueError, match="must be hashable"):
        validate_rows([{"ID": 1, "Title": ["A"]}], "Title")


@pytest.mark.parametrize("value", [None, 1.0, "12a", "", True, [1]])
def test_validate_rejects_bad_run_id(value) -> None:
    with pytest.raises(ValueError, match="run ID"):
        validate_rows([{"ID": value, "Title": "A"}], "Title")


def test_validate_rejects_missing_run_id() -> None:
    with pytest.raises(ValueError, match="missing the run_idkey"):
        validate_rows([{"Title": "A"}], "Title")


def test_run_id_defaults_and_casts() -> None:
    assert run_id({"ID": 5}, "ID") == 5
    assert run_id({"ID": " 42 "}, "ID") == 42


# -- unit tests: freezing -----------------------------------------------------


def test_freeze_makes_nested_values_read_only() -> None:
    frozen = freeze({"ID": 1, "tags": [1, [2]], "meta": {"a": {"b": 1}}})
    assert isinstance(frozen, MappingProxyType)
    assert frozen["tags"] == (1, (2,))
    assert isinstance(frozen["meta"], MappingProxyType)
    assert isinstance(frozen["meta"]["a"], MappingProxyType)
    with pytest.raises(TypeError):
        frozen["ID"] = 2
    with pytest.raises(TypeError):
        frozen["meta"]["a"]["b"] = 2


# -- widget tests: live element via the user simulation -----------------------


def _widget(user: User) -> RunGroupFrozenTable:
    return next(iter(user.find(RunGroupFrozenTable).elements))


def _table(user: User) -> RunTable:
    return next(iter(user.find(RunTable).elements))


def _stub_selection(monkeypatch, widget: RunGroupFrozenTable, selected: list) -> None:
    async def fake_get_selected_rows():
        return selected

    monkeypatch.setattr(widget._table, "get_selected_rows", fake_get_selected_rows)


async def test_renders_one_row_per_group(user: User) -> None:
    await user.open("/rungroupfrozentable")
    await user.should_see(kind=RunGroupFrozenTable)
    assert _table(user).options["rowData"] == [
        {"Title": "A", "First": 123, "Last": 129, "Size": 3, GROUP_INDEX_KEY: 0},
        {"Title": "B", "First": 125, "Last": 125, "Size": 1, GROUP_INDEX_KEY: 1},
    ]


async def test_contains_but_is_not_a_runtable(user: User) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    assert not isinstance(widget, RunTable)
    assert isinstance(widget._table, RunTable)
    assert widget._table.parent_slot.parent is widget


async def test_does_not_expose_data_changing_methods(user: User) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    for name in (
        "set_rows",
        "options",
        "load_client_data",
        "run_grid_method",
        "run_row_method",
        "get_selected_rows",
    ):
        assert not hasattr(widget, name), name


@pytest.mark.parametrize("name", ["rows", "groups", "group_by", "run_idkey"])
async def test_properties_are_read_only(user: User, name: str) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    with pytest.raises(AttributeError):
        setattr(widget, name, None)


async def test_properties_values(user: User) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    assert widget.groups == ((0, 1, 3), (2,))
    assert widget.group_by == "Title"
    assert widget.run_idkey == "ID"
    assert [row["ID"] for row in widget.rows] == [124, 129, "125", 123]


async def test_locks_group_by_column_and_keeps_runtable_options(user: User) -> None:
    await user.open("/rungroupfrozentable")
    opts = _table(user).options
    assert [column["field"] for column in opts["columnDefs"]] == ["Title", "First", "Last", "Size"]
    assert opts["columnDefs"][0]["lockPosition"] == "left"
    assert opts["columnDefs"][0]["suppressMovable"] is True
    assert opts["defaultColDef"]["editable"] is False
    assert opts["defaultColDef"]["sortable"] is False
    assert opts["suppressRowDrag"] is True
    assert opts["rowSelection"]["mode"] == "multiRow"
    assert opts["rowSelection"]["enableClickSelection"] is True


async def test_rows_are_read_only_copies(user: User) -> None:
    await user.open("/rungroupfrozentable")
    rows = [{"ID": 1, "Title": "A", "tags": ["x"], "meta": {"k": 1}}]
    original = copy.deepcopy(rows)
    with user:
        widget = RunGroupFrozenTable(rows=rows, group_by="Title")
    stored = widget.rows[0]
    assert stored is not rows[0]
    assert dict(stored) == {"ID": 1, "Title": "A", "tags": ("x",), "meta": MappingProxyType({"k": 1})}
    with pytest.raises(TypeError):
        stored["ID"] = 2
    with pytest.raises(TypeError):
        stored["meta"]["k"] = 2
    # The caller's dicts are not mutated or enriched.
    assert rows == original
    assert GROUP_INDEX_KEY not in stored


async def test_caller_changes_have_no_effect(user: User) -> None:
    await user.open("/rungroupfrozentable")
    rows = [{"ID": 1, "Title": "A", "tags": ["x"]}, {"ID": 2, "Title": "B", "tags": []}]
    with user:
        widget = RunGroupFrozenTable(rows=rows, group_by="Title")
    row_data = copy.deepcopy(widget._table.options["rowData"])

    rows[0]["Title"] = "B"
    rows[0]["tags"].append("y")
    rows.append({"ID": 3, "Title": "C", "tags": []})

    assert widget.groups == ((0,), (1,))
    assert widget.rows[0]["Title"] == "A"
    assert widget.rows[0]["tags"] == ("x",)
    assert len(widget.rows) == 2
    assert widget._table.options["rowData"] == row_data


async def test_constructor_validates(user: User) -> None:
    await user.open("/rungroupfrozentable-empty")
    await user.should_see("error: rows must not be empty.")
    with user, pytest.raises(ValueError, match="missing the group_by key"):
        RunGroupFrozenTable(rows=[{"ID": 1}], group_by="Title")


async def test_selected_group_indexes(user: User, monkeypatch) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    _stub_selection(monkeypatch, widget, [{"Title": "B", GROUP_INDEX_KEY: 1}, {"Title": "A", GROUP_INDEX_KEY: 0}])
    assert await widget.selected_group_indexes() == (0, 1)


async def test_selected_group_indexes_empty(user: User, monkeypatch) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    _stub_selection(monkeypatch, widget, [])
    assert await widget.selected_group_indexes() == ()
    assert await widget.selected_groups() == ()
    assert await widget.selected_source_rows() == ()


async def test_selected_groups(user: User, monkeypatch) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    _stub_selection(monkeypatch, widget, [{GROUP_INDEX_KEY: 0}])
    assert await widget.selected_groups() == ((0, 1, 3),)


async def test_selected_source_rows(user: User, monkeypatch) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    _stub_selection(monkeypatch, widget, [{GROUP_INDEX_KEY: 1}, {GROUP_INDEX_KEY: 0}])
    selected = await widget.selected_source_rows()
    # Ordered by group, then by index within the group.
    assert [row["ID"] for row in selected] == [124, 129, 123, "125"]
    assert all(row is widget.rows[index] for row, index in zip(selected, (0, 1, 3, 2), strict=True))


async def test_rows_for_group(user: User) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    assert [row["ID"] for row in widget.rows_for_group(0)] == [124, 129, 123]
    assert [row["ID"] for row in widget.rows_for_group(1)] == ["125"]
    for index in (-1, 2):
        with pytest.raises(IndexError):
            widget.rows_for_group(index)


async def test_on_selection_change_delegates(user: User, monkeypatch) -> None:
    await user.open("/rungroupfrozentable")
    widget = _widget(user)
    captured: dict[str, object] = {}

    def fake_on_selection_change(callback):
        captured["callback"] = callback
        return widget._table

    monkeypatch.setattr(widget._table, "on_selection_change", fake_on_selection_change)

    def handler() -> None:
        pass

    assert widget.on_selection_change(handler) is widget
    assert captured["callback"] is handler
