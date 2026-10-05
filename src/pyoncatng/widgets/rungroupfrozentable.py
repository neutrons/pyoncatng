"""A read-only NiceGUI table that shows one row per group of ONCat runs.

``RunGroupFrozenTable`` groups run dictionaries by a configurable key and
displays one summary row per group, with the columns ``[group_by, "First",
"Last", "Size"]``. It is a :class:`nicegui.ui.card` that holds a private
:class:`~pyoncatng.widgets.runtable.RunTable` (composition, as in
``IPTSTable``), so the grid keeps every ``RunTable`` interaction rule (read-only
cells, locked first column, movable remaining columns, no row sorting, no row
dragging, multi-row selection) while the widget exposes none of the methods that
replace the grid's data.

The widget cannot be changed after it is created:

* ``rows`` holds deep copies of the input rows, each stored as a read-only
  mapping (:class:`types.MappingProxyType`). Nested dicts become read-only
  mappings and nested lists become tuples.
* ``groups`` is a tuple of tuples of indexes into ``rows``.
* ``rows``, ``groups``, ``group_by``, and ``run_idkey`` are read-only properties.

The selection accessors read ``"_group_index"`` from the selected grid rows and
then return values from ``groups`` and ``rows``, never from the grid's row data.
"""

import copy
from types import MappingProxyType
from typing import Any, Callable, Dict, Hashable, List, Mapping, Sequence, Tuple

from nicegui import ui

from .runtable import RunTable

# Default run-dict key holding the run ID, used for the First and Last columns.
DEFAULT_RUN_IDKEY = "ID"

# Summary columns that follow the group_by column, in display order.
SUMMARY_COLUMNS = ["First", "Last", "Size"]

# Hidden row-data field holding the index of a visible row's group in `groups`.
GROUP_INDEX_KEY = "_group_index"

Row = Mapping[str, Any]
Group = Tuple[int, ...]


# -- pure helpers (unit-testable without a UI context) -----------------------


def freeze(value: Any) -> Any:
    """Return a read-only version of ``value``.

    Mappings become :class:`types.MappingProxyType` views over new dicts, and
    lists and tuples become tuples, recursively. Other values are returned as
    they are. Call this on a deep copy so that no other reference to the
    underlying containers exists.

    Parameters
    ----------
    value : Any
        The value to convert.

    Returns
    -------
    Any
        A read-only mapping if ``value`` is a mapping, a tuple if it is a list
        or tuple, and ``value`` itself otherwise.
    """
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def run_id(row: Row, run_idkey: str) -> int:
    """Return the run ID of ``row`` as an ``int``.

    Parameters
    ----------
    row : Mapping[str, Any]
        A run dictionary.
    run_idkey : str
        Key of ``row`` holding the run ID.

    Returns
    -------
    int
        ``row[run_idkey]``, cast to ``int`` if it is a ``str``.

    Raises
    ------
    ValueError
        If the key is missing, or the value is neither an ``int`` nor a ``str``
        that ``int()`` accepts. ``bool`` values are rejected.
    """
    if run_idkey not in row:
        raise ValueError(f"row is missing the run_idkey {run_idkey!r}: {dict(row)!r}.")
    value = row[run_idkey]
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    raise ValueError(f"run ID {run_idkey!r} must be an int or a str that int() accepts, got {value!r}.")


def validate_rows(rows: Sequence[Row], group_by: str, run_idkey: str = DEFAULT_RUN_IDKEY) -> None:
    """Check ``rows`` against the construction rules.

    Parameters
    ----------
    rows : Sequence[Mapping[str, Any]]
        The run dictionaries to check.
    group_by : str
        Key every row must contain, with a hashable value.
    run_idkey : str, optional
        Key every row must contain, with a valid run ID. Defaults to ``"ID"``.

    Raises
    ------
    ValueError
        If ``rows`` is empty, a row is missing ``group_by``, a ``group_by``
        value is not hashable, or a run ID is missing or not convertible to
        ``int``.
    """
    if len(rows) == 0:
        raise ValueError("rows must not be empty.")
    for index, row in enumerate(rows):
        if group_by not in row:
            raise ValueError(f"rows[{index}] is missing the group_by key {group_by!r}.")
        value = row[group_by]
        try:
            hash(value)
        except TypeError as error:
            raise ValueError(f"rows[{index}][{group_by!r}] must be hashable, got {value!r}.") from error
        run_id(row, run_idkey)


def build_groups(rows: Sequence[Row], group_by: str) -> Tuple[Group, ...]:
    """Group the indexes of ``rows`` by exact equality of ``row[group_by]``.

    Parameters
    ----------
    rows : Sequence[Mapping[str, Any]]
        The run dictionaries to group. Each must contain ``group_by`` with a
        hashable value.
    group_by : str
        Key whose values define the groups.

    Returns
    -------
    tuple of tuple of int
        One tuple of ascending indexes into ``rows`` per group. Groups are
        ordered by the first occurrence of their value in ``rows``.
    """
    indexes: Dict[Hashable, List[int]] = {}
    for index, row in enumerate(rows):
        indexes.setdefault(row[group_by], []).append(index)
    return tuple(tuple(members) for members in indexes.values())


def build_group_rows(
    rows: Sequence[Row],
    groups: Sequence[Group],
    group_by: str,
    run_idkey: str = DEFAULT_RUN_IDKEY,
) -> List[Dict[str, Any]]:
    """Build one visible grid row per group.

    Parameters
    ----------
    rows : Sequence[Mapping[str, Any]]
        The run dictionaries that ``groups`` indexes into.
    groups : Sequence[tuple of int]
        Groups of indexes into ``rows``, as returned by :func:`build_groups`.
    group_by : str
        Key whose value is shown in the first column.
    run_idkey : str, optional
        Key holding the run ID. Defaults to ``"ID"``.

    Returns
    -------
    list of dict
        One dict per group, in the order of ``groups``, holding the group's
        ``group_by`` value, ``"First"`` and ``"Last"`` (the smallest and largest
        run IDs, cast to ``int``), ``"Size"`` (the number of rows in the
        group), and the hidden ``"_group_index"``.
    """
    group_rows: List[Dict[str, Any]] = []
    for group_index, members in enumerate(groups):
        ids = [run_id(rows[index], run_idkey) for index in members]
        group_rows.append(
            {
                group_by: rows[members[0]][group_by],
                "First": min(ids),
                "Last": max(ids),
                "Size": len(members),
                GROUP_INDEX_KEY: group_index,
            }
        )
    return group_rows


def column_names(group_by: str) -> List[str]:
    """Return the visible column names.

    Parameters
    ----------
    group_by : str
        Key shown in the first column.

    Returns
    -------
    list of str
        ``[group_by, "First", "Last", "Size"]``.
    """
    return [group_by, *SUMMARY_COLUMNS]


# -- widget ------------------------------------------------------------------


class RunGroupFrozenTable(ui.card):
    """Read-only table with one row per group of runs; fixed after creation.

    Parameters
    ----------
    rows : Sequence[Mapping[str, Any]]
        Non-empty sequence of run dictionaries. Each must contain ``group_by``
        and ``run_idkey``. The widget stores read-only deep copies, so later
        changes to the caller's list or dicts have no effect, and the caller's
        dicts are never mutated or enriched.
    group_by : str
        Run-dict key used to group rows. Rows whose values are equal (exact
        equality, no whitespace or case normalization) form one group. Values
        must be hashable.
    run_idkey : str, optional
        Run-dict key holding the run ID, used to compute ``"First"`` and
        ``"Last"``. Values must be ``int``, or ``str`` values that ``int()``
        accepts. Defaults to ``"ID"``.

    Raises
    ------
    ValueError
        If ``rows`` is empty, a row is missing ``group_by``, a ``group_by``
        value is not hashable, or a run ID is missing or not convertible to
        ``int``.

    Examples
    --------
    .. code-block:: python

        rows = [
            {"ID": 123, "Title": "A"},
            {"ID": 124, "Title": "A"},
            {"ID": "125", "Title": "B"},
            {"ID": 129, "Title": "A"},
        ]
        table = RunGroupFrozenTable(rows=rows, group_by="Title")
        table.groups  # ((0, 1, 3), (2,))
    """

    def __init__(
        self,
        *,
        rows: Sequence[Row],
        group_by: str,
        run_idkey: str = DEFAULT_RUN_IDKEY,
    ) -> None:
        validate_rows(rows, group_by, run_idkey)
        super().__init__()
        self._group_by = group_by
        self._run_idkey = run_idkey
        self._rows: Tuple[Row, ...] = tuple(freeze(copy.deepcopy(dict(row))) for row in rows)
        self._groups = build_groups(self._rows, group_by)
        self._build_ui()

    def _build_ui(self) -> None:
        # Fill the available width and lay the table out in a column so it grows
        # to whatever height the caller gives the widget (e.g. via
        # ``.style("height: 400px")``); AG Grid needs a concrete height to fill.
        # The minimum height is set on the card rather than the grid, so the
        # grid never extends past the card's border.
        self.classes("w-full column").style("min-height: 300px")
        with self:
            self._table = (
                RunTable(
                    columns=column_names(self._group_by),
                    rows=build_group_rows(self._rows, self._groups, self._group_by, self._run_idkey),
                    key_column=self._group_by,
                )
                .classes("w-full")
                .style("flex: 1 1 auto; min-height: 0")
            )

    # -- read-only properties -----------------------------------------------

    @property
    def rows(self) -> Tuple[Row, ...]:
        """Read-only deep copies of the input rows, in input order."""
        return self._rows

    @property
    def groups(self) -> Tuple[Group, ...]:
        """One tuple of ascending indexes into :attr:`rows` per group, in first-occurrence order."""
        return self._groups

    @property
    def group_by(self) -> str:
        """The run-dict key used to group rows."""
        return self._group_by

    @property
    def run_idkey(self) -> str:
        """The run-dict key holding the run ID."""
        return self._run_idkey

    # -- selection ----------------------------------------------------------

    def on_selection_change(self, callback: Callable[..., Any]) -> "RunGroupFrozenTable":
        """Register ``callback`` to run when the table selection changes.

        Read the selection with :meth:`selected_group_indexes`,
        :meth:`selected_groups`, or :meth:`selected_source_rows`.

        Parameters
        ----------
        callback : Callable[..., Any]
            Function called on each selection change.

        Returns
        -------
        RunGroupFrozenTable
            ``self``, for chaining.
        """
        self._table.on_selection_change(callback)
        return self

    async def selected_group_indexes(self) -> Tuple[int, ...]:
        """Return the indexes into :attr:`groups` of the selected rows.

        Returns
        -------
        tuple of int
            The selected group indexes, ascending. Empty when nothing is
            selected.
        """
        selected = await self._table.get_selected_rows()
        return tuple(sorted({int(row[GROUP_INDEX_KEY]) for row in selected}))

    async def selected_groups(self) -> Tuple[Group, ...]:
        """Return the :attr:`groups` entries of the selected rows.

        Returns
        -------
        tuple of tuple of int
            The selected groups, in ascending group-index order. Empty when
            nothing is selected.
        """
        return tuple(self._groups[index] for index in await self.selected_group_indexes())

    async def selected_source_rows(self) -> Tuple[Row, ...]:
        """Return the :attr:`rows` of the selected groups.

        Returns
        -------
        tuple of Mapping[str, Any]
            The read-only rows of the selected groups, ordered by group and then
            by index within the group. Empty when nothing is selected.
        """
        return tuple(
            self._rows[row_index]
            for group_index in await self.selected_group_indexes()
            for row_index in self._groups[group_index]
        )

    def rows_for_group(self, group_index: int) -> Tuple[Row, ...]:
        """Return the :attr:`rows` of one group.

        Parameters
        ----------
        group_index : int
            Index into :attr:`groups`.

        Returns
        -------
        tuple of Mapping[str, Any]
            The read-only rows of the group, in ascending index order.

        Raises
        ------
        IndexError
            If ``group_index`` is outside ``0 .. len(groups) - 1``.
        """
        if not 0 <= group_index < len(self._groups):
            raise IndexError(f"group_index must be in 0 .. {len(self._groups) - 1}, got {group_index}.")
        return tuple(self._rows[row_index] for row_index in self._groups[group_index])
