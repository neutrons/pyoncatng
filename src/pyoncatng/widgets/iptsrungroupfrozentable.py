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
"""

import asyncio
from typing import Any, List, Optional, Sequence, Tuple

import pyoncat
from nicegui import ui

from ..core.runs import list_runs
from .iptstable import (
    DEFAULT_PROCESSING_VARIABLES,
    KEY_COLUMN,
    IPTSTable,
    ProcessingVariable,
    _validate_processing_variables,
)
from .rungroupfrozentable import RunGroupFrozenTable

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
        Label of the processing variable that defines the groups.

    Returns
    -------
    list of (str, str)
        The validated pairs, with surrounding whitespace removed.

    Raises
    ------
    ValueError
        If a pair is malformed, a label is ``"ID"`` or is repeated, or
        ``group_by`` is not one of the labels. The last rule also excludes
        ``"ID"`` as ``group_by``.
    """
    validated = _validate_processing_variables(processing_variables)
    labels = [label for label, _ in validated]
    if KEY_COLUMN in labels:
        raise ValueError(f"{KEY_COLUMN!r} is reserved")
    if len(labels) != len(set(labels)):
        raise ValueError("processing_variables labels must be unique")
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
        one of the labels in ``processing_variables``. ``"ID"`` is reserved
        and cannot be used. Runs without a value for the variable form one
        group.
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
        or a repeated label, or ``group_by`` is not one of its labels.

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
        self._build_ui()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        # Fill the available width and lay children out in a column, as IPTSTable does.
        self.classes("w-full column")
        with self:
            with ui.row().classes("items-center w-full"):
                ui.label("IPTS:")
                self._input = ui.input(placeholder="e.g. 24703").props("dense")
                # Load on click, and also on Enter for convenience.
                self._input.on("keydown.enter", self._on_load)
                self._load_button = ui.button("Load", on_click=self._on_load)
            self._container = ui.column().classes("w-full")
            self._message = ui.label("").classes("text-negative")
            self._message.set_visibility(False)
        self._replace_table([])

    def _set_message(self, text: str) -> None:
        """Show (or clear, when ``text`` is empty) the inline message area."""
        self._message.set_text(text)
        self._message.set_visibility(bool(text))

    def _replace_table(self, rows: Sequence[Any]) -> None:
        """Replace the inner table with a new one that shows ``rows``.

        An empty ``rows`` creates the table with
        :meth:`RunGroupFrozenTable.empty`.
        """
        self._container.clear()
        with self._container:
            if rows:
                self._table = RunGroupFrozenTable(rows=rows, group_by=self._group_by, run_idkey=KEY_COLUMN)
            else:
                self._table = RunGroupFrozenTable.empty(group_by=self._group_by, run_idkey=KEY_COLUMN)

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
