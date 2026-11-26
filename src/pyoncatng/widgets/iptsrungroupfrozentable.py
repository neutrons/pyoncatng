"""An IPTS run loader that shows the runs grouped, one row per group.

``IPTSRunGroupFrozenTable`` combines the IPTS input and **Load** button of
:class:`~pyoncatng.widgets.iptstable.IPTSTable` with the grouped display of
:class:`~pyoncatng.widgets.rungroupfrozentable.RunGroupFrozenTable`. Each
**Load** fetches the complete run list of the IPTS and replaces the inner
``RunGroupFrozenTable`` with a new instance. The inner table is never changed,
and it is not public.

The helpers of ``IPTSTable`` (``normalize_ipts``, ``build_projection``, and
``rows_from_runs``) are reused as they are. Before the first **Load**, for an IPTS
without runs, and after a failed **Load**, the inner table is created with
:meth:`~pyoncatng.widgets.rungroupfrozentable.RunGroupFrozenTable.empty`, so it
always is a ``RunGroupFrozenTable``.

The widget keeps the selection callbacks of the caller and registers them again on
each new inner table. After every **Load** of an IPTS number it sends each
callback a selection-changed event, because the new table has no selection. The
selection accessors always read the current inner table.
"""

import asyncio
from typing import Any, Callable, List, Optional, Sequence, Tuple

import pyoncat
from nicegui import ui
from nicegui.events import GenericEventArguments, handle_event

from pyoncatng.core.runs import list_runs
from pyoncatng.widgets.iptstable import (
    DEFAULT_PROCESSING_VARIABLES,
    KEY_COLUMN,
    IPTSTable,
    ProcessingVariable,
    validate_processing_variables,
)
from pyoncatng.widgets.rungroupfrozentable import RESERVED_GROUP_KEYS, Group, Row, RunGroupFrozenTable

# -- pure helpers (unit-testable without a UI context) -----------------------


def _validate_construction(
    processing_variables: Sequence[ProcessingVariable],
    group_by: str,
) -> List[ProcessingVariable]:
    """Validate the constructor arguments and return the processing variables.

    Parameters
    ----------
    processing_variables : sequence of (str, str)
        Ordered ``(display label, ONCat metadata path)`` pairs.
    group_by : str
        Label of the processing variable that defines the groups. It must not
        be a name that ``RunGroupFrozenTable`` reserves.

    Returns
    -------
    list of (str, str)
        The validated pairs, with surrounding whitespace removed.

    Raises
    ------
    ValueError
        If a pair is malformed, a label is ``"ID"`` or is repeated,
        ``group_by`` is one of the names that ``RunGroupFrozenTable`` reserves
        (``"First"``, ``"Last"``, ``"Size"``, and ``"_group_index"``), or
        ``group_by`` is not one of the labels. The last rule also excludes
        ``"ID"`` as ``group_by``.
    """
    validated = validate_processing_variables(processing_variables)
    labels = [label for label, _ in validated]
    if group_by in RESERVED_GROUP_KEYS:
        raise ValueError(f"group_by {group_by!r} is reserved and cannot be used.")
    if group_by not in labels:
        raise ValueError(f"group_by {group_by!r} must be one of the processing_variables labels {labels!r}.")
    return validated


# -- widget ------------------------------------------------------------------


class IPTSRunGroupFrozenTable(ui.card):
    """IPTS input + Load button over a read-only table of grouped runs.

    Parameters
    ----------
    agent : pyoncat.ONCat
        The authenticated ONCat agent to query, e.g. ``OncatLogin.agent``. It
        may be disconnected when passed; a failed **Load** reports the problem
        in the message area.
    group_by : str
        Label of the processing variable that defines the groups. It must be
        one of the labels in ``processing_variables``. ``"ID"``, ``"First"``,
        ``"Last"``, and ``"Size"`` are reserved and cannot be used. Runs without
        a value for the variable form one group.
    facility : str, optional
        Facility passed to ``Run.list``. Defaults to ``"SNS"``.
    instrument : str, optional
        Instrument passed to ``Run.list``. Defaults to ``"USANS"``.
    processing_variables : sequence of (str, str), optional
        Ordered ``(display label, ONCat metadata path)`` pairs to query, as in
        :class:`~pyoncatng.widgets.iptstable.IPTSTable`. ``ID`` is always added
        as the run identifier and must not be included. Defaults to Title,
        Start Time, and Total Counts.

    Raises
    ------
    ValueError
        If ``processing_variables`` is malformed, contains the label ``"ID"``
        or a repeated label, ``group_by`` is a reserved name, or ``group_by``
        is not one of its labels.

    Notes
    -----
    Every **Load** of an IPTS number replaces the inner table, clears the
    selection, and sends each callback registered with :meth:`on_selection_change`
    a selection-changed event with empty ``args``. A **Load** with an empty IPTS
    field only shows a message and changes nothing else. A callback also receives
    an event when the user changes the selection. Every event has this widget as
    its ``sender``, and the inner table is never passed to a callback. Group
    indexes and row indexes are valid only until the next **Load**, because new
    runs move existing rows and groups.

    Example
    -------
    .. code-block:: python

        IPTSRunGroupFrozenTable(agent=login.agent, group_by="Title")
    """

    def __init__(
        self,
        agent: pyoncat.ONCat,
        *,
        group_by: str,
        facility: str = "SNS",
        instrument: str = "USANS",
        processing_variables: Sequence[ProcessingVariable] = DEFAULT_PROCESSING_VARIABLES,
    ) -> None:
        processing_variables = _validate_construction(processing_variables, group_by)

        super().__init__()
        self._agent = agent
        self._group_by = group_by
        self._facility = facility
        self._instrument = instrument
        self._processing_variables = processing_variables
        self._column_spec: List[Tuple[str, Optional[str]]] = [(KEY_COLUMN, None), *processing_variables]
        self._busy = False
        self._callbacks: List[Callable[..., Any]] = []
        self._build_ui()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        # Fill the available width and lay children out in a column, as IPTSTable does.
        # The container and the inner table grow to the height that the caller
        # gives the widget (e.g. via ``.style("height: 600px")``).
        self.classes("w-full column")
        with self:
            with ui.row().classes("items-center w-full"):
                ui.label("IPTS:")
                self._input = ui.input(placeholder="e.g. 24703").props("dense")
                # Load on click, and also on Enter for convenience.
                self._input.on("keydown.enter", self._on_load)
                self._load_button = ui.button("Load", on_click=self._on_load)
            self._container = ui.column().classes("w-full").style("flex: 1 1 auto; min-height: 0")
            self._message = ui.label("").classes("text-negative")
            self._message.set_visibility(False)
        self._replace_table([])

    def _set_message(self, text: str) -> None:
        """Show (or clear, when ``text`` is empty) the inline message area."""
        self._message.set_text(text)
        self._message.set_visibility(bool(text))

    def _notify(self, callback: Callable[..., Any], args: Any) -> None:
        """Call ``callback`` with an event whose sender is this widget, as NiceGUI does."""
        handle_event(callback, GenericEventArguments(sender=self, client=self.client, args=args))

    def _forward(self, callback: Callable[..., Any]) -> Callable[[GenericEventArguments], None]:
        """Return a handler for the inner table that passes its events to ``callback`` as events of this widget.

        This keeps the private inner table out of the event, and gives the callback
        the same sender and UI context for every event.
        """

        def forward(event: GenericEventArguments) -> None:
            self._notify(callback, event.args)

        return forward

    def _replace_table(self, rows: Sequence[Any]) -> None:
        """Replace the inner table with a new one that shows ``rows``.

        An empty ``rows`` creates the table with
        :meth:`RunGroupFrozenTable.empty`. The stored selection callbacks are
        registered on the new table and each receives a selection-changed event.
        """
        self._container.clear()
        with self._container:
            if rows:
                self._table = RunGroupFrozenTable(rows=rows, group_by=self._group_by, run_idkey=KEY_COLUMN)
            else:
                self._table = RunGroupFrozenTable.empty(group_by=self._group_by, run_idkey=KEY_COLUMN)
            self._table.style("flex: 1 1 auto")
        for callback in self._callbacks:
            self._table.on_selection_change(self._forward(callback))
        for callback in self._callbacks:
            self._notify(callback, {})

    # -- data loading -------------------------------------------------------

    async def _on_load(self, _event: Any = None) -> None:
        """Fetch runs for the entered IPTS and replace the inner table."""
        # Guard against overlapping loads: the button is disabled while busy, but
        # the Enter key handler stays live and could otherwise re-enter here.
        if self._busy:
            return
        self._set_message("")
        experiment = IPTSTable.normalize_ipts(self._input.value)
        if experiment is None:
            self._set_message("Please enter an IPTS number.")
            return

        self._busy = True
        self._load_button.set_enabled(False)
        try:
            runs = await asyncio.to_thread(
                list_runs,
                self._agent,
                facility=self._facility,
                instrument=self._instrument,
                experiment=experiment,
                projection=IPTSTable.build_projection(self._column_spec),
            )
            rows = IPTSTable.rows_from_runs(runs, self._column_spec)
            self._replace_table(rows)
            if not rows:
                self._set_message(f"No runs found for {experiment}.")
        except Exception as error:  # noqa: BLE001 - surface any failure to the user
            self._replace_table([])
            self._set_message(f"Could not load runs for {experiment}: {error}")
        finally:
            self._busy = False
            self._load_button.set_enabled(True)

    # -- selection ----------------------------------------------------------

    def on_selection_change(self, callback: Callable[..., Any]) -> "IPTSRunGroupFrozenTable":
        """Register ``callback`` to run when the selection changes.

        The callback also runs after every **Load** of an IPTS number, which clears
        the selection.
        Read the selection with :meth:`selected_group_indexes`,
        :meth:`selected_groups`, or :meth:`selected_source_rows`.

        Parameters
        ----------
        callback : Callable[..., Any]
            Function called on each selection change, with no arguments or with
            the event. The event's ``sender`` is this widget. Its ``args`` are
            empty after a **Load**, and hold the arguments that the grid sent for
            a change made by the user.

        Returns
        -------
        IPTSRunGroupFrozenTable
            ``self``, for chaining.
        """
        self._callbacks.append(callback)
        self._table.on_selection_change(self._forward(callback))
        return self

    async def selected_group_indexes(self) -> Tuple[int, ...]:
        """Return the indexes into :attr:`groups` of the selected rows."""
        return await self._table.selected_group_indexes()

    async def selected_groups(self) -> Tuple[Group, ...]:
        """Return the :attr:`groups` entries of the selected rows."""
        return await self._table.selected_groups()

    async def selected_source_rows(self) -> Tuple[Row, ...]:
        """Return the :attr:`rows` of the selected groups."""
        return await self._table.selected_source_rows()

    def rows_for_group(self, group_index: int) -> Tuple[Row, ...]:
        """Return the :attr:`rows` of one group.

        Raises
        ------
        IndexError
            If the table has no groups, or ``group_index`` is out of range.
        """
        return self._table.rows_for_group(group_index)

    # -- read-only properties -----------------------------------------------

    @property
    def rows(self) -> Tuple[Row, ...]:
        """Read-only rows of the last **Load**, one per run, newest first."""
        return self._table.rows

    @property
    def groups(self) -> Tuple[Group, ...]:
        """One tuple of ascending indexes into :attr:`rows` per group."""
        return self._table.groups

    @property
    def group_by(self) -> str:
        """The label of the processing variable that defines the groups."""
        return self._group_by
