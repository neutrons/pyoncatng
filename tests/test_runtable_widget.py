"""Tests for the RunTable widget.

Two layers:

* **Unit tests** on the pure option builders (``build_column_defs`` /
  ``build_options``), which need no UI context and assert every locked-down
  behavior (read-only, no sort, no row drag, key column first & locked).
* **Widget tests** via NiceGUI's in-process ``user`` simulation, asserting the
  page renders and the live element carries the expected options. AG Grid cell
  content is rendered client-side and is not visible to the simulation, so the
  data is verified through the element's ``options`` rather than ``should_see``.
"""

import pytest
from nicegui.testing import User

from pyoncatng.widgets.runtable import DEFAULT_COL_DEF, RunTable

# -- unit tests: build_column_defs --------------------------------------------


def test_column_defs_key_column_first_and_locked() -> None:
    defs = RunTable.build_column_defs(["run_title", "run_number", "start_time"])
    # run_number is forced first regardless of its position in the input...
    assert [d["field"] for d in defs] == ["run_number", "run_title", "start_time"]
    # ...and locked to the left edge so nothing can be dragged ahead of it.
    assert defs[0]["lockPosition"] == "left"
    assert defs[0]["suppressMovable"] is True


def test_column_defs_other_columns_are_movable() -> None:
    defs = RunTable.build_column_defs(["run_number", "run_title", "start_time"])
    for definition in defs[1:]:
        assert "lockPosition" not in definition
        assert "suppressMovable" not in definition


def test_column_defs_header_equals_field() -> None:
    defs = RunTable.build_column_defs(["run_number", "LambdaRequest"])
    for definition in defs:
        assert definition["headerName"] == definition["field"]


def test_column_defs_requires_key_column() -> None:
    with pytest.raises(ValueError):
        RunTable.build_column_defs(["run_title", "start_time"])


def test_column_defs_rejects_duplicate_columns() -> None:
    with pytest.raises(ValueError):
        RunTable.build_column_defs(["run_number", "run_title", "run_title"])


def test_column_defs_custom_key_column() -> None:
    defs = RunTable.build_column_defs(["a", "b", "c"], key_column="b")
    assert defs[0]["field"] == "b"
    assert defs[0]["suppressMovable"] is True


# -- unit tests: build_options ------------------------------------------------


def test_options_cells_read_only() -> None:
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["defaultColDef"]["editable"] is False


def test_options_no_row_sorting() -> None:
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["defaultColDef"]["sortable"] is False


def test_options_no_row_dragging() -> None:
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["suppressRowDrag"] is True


def test_options_multiple_row_selection() -> None:
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["rowSelection"] == "multiple"


def test_options_selection_does_not_relax_lockdowns() -> None:
    # Enabling selection must leave read-only / no-sort / no-drag intact.
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["rowSelection"] == "multiple"
    assert opts["defaultColDef"]["editable"] is False
    assert opts["defaultColDef"]["sortable"] is False
    assert opts["suppressRowDrag"] is True


def test_options_row_order_preserved() -> None:
    rows = [{"run_number": 3}, {"run_number": 1}, {"run_number": 2}]
    opts = RunTable.build_options(["run_number"], rows=rows)
    assert [r["run_number"] for r in opts["rowData"]] == [3, 1, 2]


def test_options_copies_rows_defensively() -> None:
    rows = [{"run_number": 1}]
    opts = RunTable.build_options(["run_number"], rows=rows)
    opts["rowData"][0]["run_number"] = 99
    assert rows[0]["run_number"] == 1  # caller's list is untouched


def test_options_empty_rows_default() -> None:
    opts = RunTable.build_options(["run_number"], rows=None)
    assert opts["rowData"] == []


def test_default_col_def_constant_is_locked_down() -> None:
    assert DEFAULT_COL_DEF["editable"] is False
    assert DEFAULT_COL_DEF["sortable"] is False


# -- widget tests: live element via the user simulation -----------------------


async def test_runtable_renders(user: User) -> None:
    await user.open("/runtable")
    await user.should_see(kind=RunTable)


async def test_runtable_element_options_wired(user: User) -> None:
    await user.open("/runtable")
    grid = next(iter(user.find(RunTable).elements))
    opts = grid.options
    assert opts["defaultColDef"]["editable"] is False
    assert opts["defaultColDef"]["sortable"] is False
    assert opts["suppressRowDrag"] is True
    assert opts["rowSelection"] == "multiple"
    assert opts["columnDefs"][0]["field"] == "run_number"
    assert opts["columnDefs"][0]["lockPosition"] == "left"
    assert len(opts["rowData"]) == 3


async def test_runtable_forces_key_column_first(user: User) -> None:
    await user.open("/runtable-keylast")
    grid = next(iter(user.find(RunTable).elements))
    assert grid.options["columnDefs"][0]["field"] == "run_number"


async def test_runtable_empty_renders(user: User) -> None:
    await user.open("/runtable-empty")
    grid = next(iter(user.find(RunTable).elements))
    assert grid.options["rowData"] == []


async def test_runtable_set_rows_preserves_order(user: User) -> None:
    await user.open("/runtable")
    grid = next(iter(user.find(RunTable).elements))
    grid.set_rows([{"run_number": 9}, {"run_number": 7}, {"run_number": 8}])
    assert [r["run_number"] for r in grid.options["rowData"]] == [9, 7, 8]


async def test_runtable_on_selection_change_registers_and_chains(user: User) -> None:
    await user.open("/runtable")
    grid = next(iter(user.find(RunTable).elements))

    def handler() -> None:  # pragma: no cover - never invoked in the sim
        pass

    # Registration returns the grid (chainable) and records a listener for the
    # AG Grid selectionChanged event.
    assert grid.on_selection_change(handler) is grid
    assert any("selectionChanged" in listener.type for listener in grid._event_listeners.values())


async def test_runtable_bad_key_column_reports_error(user: User) -> None:
    await user.open("/runtable-badkey")
    await user.should_see("error:")
