"""A reusable NiceGUI table widget for ONCat run data.

Displays one **row per run** and one **column per processing variable** (PV),
backed by AG Grid (:class:`nicegui.ui.aggrid`). The grid is deliberately locked
down for read-only browsing of a fixed run ordering:

* **Read-only cells** -- no inline editing, so the user cannot change a value.
* **No row sorting** -- header clicks do not reorder the rows, so the rows stay
  in exactly the order of the ``rows`` passed in.
* **No row dragging** -- the row order is fixed.
* **Draggable columns** -- columns can be reordered by dragging their headers
  left/right, *except* the key column (``run_number`` by default), which is
  locked to the leftmost position so no column can be dragged ahead of it.

Fetching the data from ONCat is intentionally out of scope: a caller builds the
ordered list of PV column names and the ``rows`` (a list of per-run dicts keyed
by PV name) and hands them to the constructor. Column name, header label, and
row-dict key are all the same PV string (``name == label == field``).
"""

from typing import Any, Dict, List, Optional, Sequence

from nicegui import ui

# Applied to every column. Cells are read-only and header clicks never sort, so
# neither the values nor the row order can be changed by the user. Columns stay
# resizable and (by default) movable.
DEFAULT_COL_DEF: Dict[str, Any] = {
    "editable": False,
    "sortable": False,
    "resizable": True,
}

# Default PV pinned to the leftmost, non-draggable column.
DEFAULT_KEY_COLUMN = "run_number"

Row = Dict[str, Any]


class RunTable(ui.aggrid):
    """Read-only AG Grid of runs (rows) by processing variables (columns).

    Params
    ------
    columns : sequence of str
        Ordered PV names, one per column. Must include ``key_column``. Each PV
        name is used as the column field, the header label, and the row-dict key.
    rows : sequence of dict, optional
        One dict per run, keyed by PV name; a missing key renders as an empty
        cell. Defaults to no rows. Rows render in the given order and stay put.
    key_column : str, optional
        The PV pinned to the leftmost, non-draggable column. Defaults to
        ``"run_number"``.
    """

    def __init__(
        self,
        *,
        columns: Sequence[str],
        rows: Optional[Sequence[Row]] = None,
        key_column: str = DEFAULT_KEY_COLUMN,
    ) -> None:
        self._columns = list(columns)
        self._key_column = key_column
        super().__init__(self.build_options(self._columns, rows, key_column))

    # -- option construction (pure; unit-testable without a UI context) -----

    @staticmethod
    def build_column_defs(
        columns: Sequence[str],
        key_column: str = DEFAULT_KEY_COLUMN,
    ) -> List[Dict[str, Any]]:
        """Build the AG Grid ``columnDefs`` for ``columns``.

        The key column is emitted **first** and locked to the left edge
        (``lockPosition`` + ``suppressMovable``), so it cannot be dragged and no
        other column can be dragged ahead of it. The remaining columns keep the
        order given in ``columns`` and stay draggable.

        Raises
        ------
        ValueError
            If ``key_column`` is not present in ``columns``, or if ``columns``
            contains duplicate names.
        """
        columns = list(columns)
        if key_column not in columns:
            raise ValueError(f"key_column {key_column!r} must be one of the columns: {columns}.")
        if len(set(columns)) != len(columns):
            # Duplicate fields would bind several columns to the same value.
            raise ValueError(f"columns must be unique, got: {columns}.")

        # Key column first and locked left, regardless of its slot in `columns`.
        defs: List[Dict[str, Any]] = [
            {
                "field": key_column,
                "headerName": key_column,
                "lockPosition": "left",
                "suppressMovable": True,
            }
        ]
        # Remaining columns in their given order; movable, read-only by default.
        defs.extend({"field": field, "headerName": field} for field in columns if field != key_column)
        return defs

    @classmethod
    def build_options(
        cls,
        columns: Sequence[str],
        rows: Optional[Sequence[Row]],
        key_column: str = DEFAULT_KEY_COLUMN,
    ) -> Dict[str, Any]:
        """Assemble the full AG Grid options dict backing the widget.

        Rows are shallow-copied so later external mutation of the caller's list
        does not silently change the grid (and vice versa).
        """
        return {
            "columnDefs": cls.build_column_defs(columns, key_column),
            "rowData": [dict(row) for row in (rows or [])],
            "defaultColDef": dict(DEFAULT_COL_DEF),
            # No column opts into rowDrag, but forbid row dragging explicitly so
            # the row order stays fixed even if a column later enables it.
            "suppressRowDrag": True,
        }

    # -- data updates -------------------------------------------------------

    def set_rows(self, rows: Sequence[Row]) -> None:
        """Replace the displayed rows (order preserved) and refresh the grid."""
        self.options["rowData"] = [dict(row) for row in rows]
        self.update()
