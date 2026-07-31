"""A composite NiceGUI widget: fetch and display ONCat runs for an IPTS number.

``IPTSTable`` wires an IPTS input and a **Load** button to a :class:`RunTable`.
The user types an IPTS number, clicks **Load**, and the widget fetches that
experiment's runs from ONCat (via :func:`pyoncatng.core.runs.list_runs`) for a
fixed facility/instrument and renders one row per run.

The authenticated agent is supplied by the caller (typically
``OncatLogin.agent``); the widget does not create or manage the connection. Any
problem -- no live session, a non-existent IPTS number, or a request failure --
is reported in an inline message area below the table rather than as a toast.

Blocking ONCat I/O is run off the event loop with ``asyncio.to_thread``, as in
:class:`~pyoncatng.core.service.LoginService`.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pyoncat
from nicegui import ui

from ..core.runs import list_runs
from .runtable import RunTable

# Ordered ``(display column, run path)`` pairs backing the table. A ``None`` path
# means the run's own ``id`` (the run number). The other columns read the raw
# datafile metadata a run aggregates, under ``datafiles.raw.metadata.entry.*``
# (verified against SNS/USANS runs; a run's own ``metadata`` is not populated).
ColumnSpec = Sequence[Tuple[str, Optional[str]]]
ProcessingVariable = Tuple[str, str]

# ``ID`` is always added by ``IPTSTable`` as the leftmost column. Callers can
# replace these path-backed processing variables through the constructor.
DEFAULT_PROCESSING_VARIABLES: Tuple[ProcessingVariable, ...] = (
    ("Title", "datafiles.raw.metadata.entry.title"),
    ("Start Time", "datafiles.raw.metadata.entry.start_time"),
    ("Total Counts", "datafiles.raw.metadata.entry.total_counts"),
)

COLUMN_SPEC: List[Tuple[str, Optional[str]]] = [
    ("ID", None),
    *DEFAULT_PROCESSING_VARIABLES,
]

# The column pinned leftmost in the RunTable (the run number).
KEY_COLUMN = "ID"

Row = Dict[str, Any]


class IPTSTable(ui.card):
    """IPTS input + Load button over a read-only :class:`RunTable`.

    Params
    ------
    agent : pyoncat.ONCat
        The authenticated ONCat agent to query, e.g. ``OncatLogin.agent``. It
        may be disconnected when passed; a failed **Load** simply reports the
        problem in the message area.
    facility : str, optional
        Facility passed to ``Run.list``. Defaults to ``"SNS"``.
    instrument : str, optional
        Instrument passed to ``Run.list``. Defaults to ``"USANS"``.
    processing_variables : sequence of (str, str), optional
        Ordered ``(display label, ONCat metadata path)`` pairs to show and
        query. ``ID`` is always added as the first column and must not be
        included here. Defaults to Title, Start Time, and Total Counts.

    Example
    -------
    To show only ``Title`` and ``Start Time``:

    .. code-block:: python

        IPTSTable(
            agent=login.agent,
            processing_variables=[
                ("Title", "datafiles.raw.metadata.entry.title"),
                ("Start Time", "datafiles.raw.metadata.entry.start_time"),
            ],
        )
    """

    def __init__(
        self,
        agent: pyoncat.ONCat,
        *,
        facility: str = "SNS",
        instrument: str = "USANS",
        processing_variables: Sequence[ProcessingVariable] = DEFAULT_PROCESSING_VARIABLES,
    ) -> None:
        super().__init__()
        self._agent = agent
        self._facility = facility
        self._instrument = instrument
        self._processing_variables = list(processing_variables)
        self._column_spec: List[Tuple[str, Optional[str]]] = [
            (KEY_COLUMN, None),
            *self._processing_variables,
        ]
        self._busy = False
        self._build_ui()

    # -- pure helpers (unit-testable without a UI context) ------------------

    @staticmethod
    def normalize_ipts(text: Optional[str]) -> Optional[str]:
        """Normalize field input to an ``IPTS-<n>`` identifier.

        A bare number (``"24703"``) gains the ``IPTS-`` prefix; an already
        prefixed value (any case) is preserved. Returns ``None`` when ``text``
        has no usable content.
        """
        value = (text or "").strip()
        if not value:
            return None
        if value.upper().startswith("IPTS-"):
            suffix = value.split("-", 1)[1].strip()
            return f"IPTS-{suffix}" if suffix else None
        return f"IPTS-{value}"

    @staticmethod
    def column_names(spec: ColumnSpec = COLUMN_SPEC) -> List[str]:
        """The ordered display column names (RunTable columns)."""
        return [name for name, _ in spec]

    @staticmethod
    def build_projection(spec: ColumnSpec = COLUMN_SPEC) -> List[str]:
        """The ONCat metadata paths to project (columns backed by a path)."""
        return [path for _, path in spec if path is not None]

    @staticmethod
    def rows_from_runs(runs: Sequence[Any], spec: ColumnSpec = COLUMN_SPEC) -> List[Row]:
        """Map fetched runs to RunTable rows keyed by display column name.

        The key column (``path is None``) takes the run's ``id``; every other
        column reads its dot-path via ``run.get(path)`` (missing -> ``None``).
        """
        rows: List[Row] = []
        for run in runs:
            row: Row = {}
            for name, path in spec:
                row[name] = run["id"] if path is None else run.get(path)
            rows.append(row)
        return rows

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        # Fill the available width and lay children out in a column so the table
        # grows to whatever height the caller gives the widget (e.g. via
        # ``.style("height: 600px")``); AG Grid needs a concrete height to fill.
        self.classes("w-full column")
        with self:
            with ui.row().classes("items-center w-full"):
                ui.label("IPTS:")
                self._input = ui.input(placeholder="e.g. 24703").props("dense")
                # Load on click, and also on Enter for convenience.
                self._input.on("keydown.enter", self._on_load)
                self._load_button = ui.button("Load", on_click=self._on_load)
            self._table = (
                RunTable(
                    columns=self.column_names(self._column_spec),
                    rows=[],
                    key_column=KEY_COLUMN,
                )
                .classes("w-full")
                .style("flex: 1 1 auto; min-height: 300px")
            )
            self._message = ui.label("").classes("text-negative")
            self._message.set_visibility(False)

    def _set_message(self, text: str) -> None:
        """Show (or clear, when ``text`` is empty) the inline message area."""
        self._message.set_text(text)
        self._message.set_visibility(bool(text))

    # -- data loading -------------------------------------------------------

    async def _on_load(self, _event: Any = None) -> None:
        """Fetch runs for the entered IPTS and repopulate the table."""
        # Guard against overlapping loads: the button is disabled while busy, but
        # the Enter key handler stays live and could otherwise re-enter here.
        if self._busy:
            return
        self._set_message("")
        experiment = self.normalize_ipts(self._input.value)
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
                projection=self.build_projection(self._column_spec),
            )
            rows = self.rows_from_runs(runs, self._column_spec)
            self._table.set_rows(rows)
            if not rows:
                self._set_message(f"No runs found for {experiment}.")
        except Exception as error:  # noqa: BLE001 - surface any failure to the user
            self._table.set_rows([])
            self._set_message(f"Could not load runs for {experiment}: {error}")
        finally:
            self._busy = False
            self._load_button.set_enabled(True)

    # -- selection ----------------------------------------------------------

    async def selected_rows(self) -> List[Row]:
        """Return the rows the user has selected in the table (may be empty)."""
        return await self._table.get_selected_rows()

    def on_selection_change(self, callback: Callable[..., Any]) -> "IPTSTable":
        """Register ``callback`` to run when the table selection changes.

        Read the selection with :meth:`selected_rows`. Returns ``self`` for
        chaining.
        """
        self._table.on_selection_change(callback)
        return self
