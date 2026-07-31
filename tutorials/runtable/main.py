"""ONCat run-table tutorial: browse run data with the RunTable widget.

Run it with ``pixi run tutorial-runtable`` or ``python tutorials/runtable/main.py``.
No ONCat sign-in is needed -- the page generates sample run data locally so you
can try the widget's interactions:

* **Select rows** -- click a row to select it, **Ctrl/Cmd + click** to toggle
  individual rows, and **Shift + click** to select a contiguous range. The
  caption under the table lists the selected run numbers live.
* **Drag a column header** left/right to reorder columns...
* ...except **run_number**, which is locked to the leftmost position.
* **Clicking a header does nothing** -- rows are never sorted, so the run order
  is fixed.
* **Cells are read-only** -- double-clicking a cell will not edit it.
* **Rows cannot be dragged.**

The selection is read out via ``RunTable.on_selection_change`` (register a
callback) and the inherited async ``get_selected_rows``.
"""

import argparse

import argcomplete
from nicegui import ui

from pyoncatng.widgets.runtable import RunTable

# The processing-variable columns to display, in their initial order. run_number
# is the locked key column; the rest are draggable.
COLUMNS = ["run_number", "run_title", "start_time", "duration", "counts", "LambdaRequest"]

# Sample run data standing in for what would otherwise be fetched from ONCat.
_TITLES = [
    "Bohemian Rhapsody",
    "Stairway to Heaven",
    "Hotel California",
    "Sweet Child o' Mine",
    "Smells Like Teen Spirit",
    "Billie Jean",
    "Like a Rolling Stone",
    "Imagine",
    "One",
    "Hallelujah",
    "Wonderwall",
    "Livin' on a Prayer",
]
_DURATIONS = [5400, 5400, 6300, 4500, 2700, 5400, 5400, 6300, 5400, 3600, 5400, 7200]


def _sample_rows() -> list[dict]:
    """Build sample run rows keyed by the RunTable columns."""
    rows = []
    for i, (title, duration) in enumerate(zip(_TITLES, _DURATIONS, strict=True)):
        rows.append(
            {
                "run_number": 47775 + i,
                "run_title": title,
                "start_time": f"2023-01-01 {7 + i:02d}:00",
                "duration": duration,
                "counts": duration * 100,
                "LambdaRequest": round(3.0 + 0.1 * i, 1),
            }
        )
    return rows


@ui.page("/")
def index() -> None:
    """The single tutorial page: an explanatory header and the RunTable."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("pyoncatng RunTable demo").classes("text-h5")
        ui.markdown(
            "**Click** a row to select it, **Ctrl/Cmd + click** to toggle rows, and "
            "**Shift + click** to select a range. Drag column headers to reorder them "
            "&mdash; but **run_number** stays leftmost. Header clicks never sort, cells "
            "are read-only, and rows cannot be dragged, so the run order is fixed."
        )
        table = RunTable(columns=COLUMNS, rows=_sample_rows()).style("height: 460px")

        # Read the live selection out through the widget's public API: register a
        # callback with on_selection_change, then pull the rows with the inherited
        # async get_selected_rows.
        selection_label = ui.label("No rows selected.").classes("text-caption")

        async def _show_selection() -> None:
            rows = await table.get_selected_rows()
            selection_label.set_text(
                "Selected run(s): " + ", ".join(str(row["run_number"]) for row in rows) if rows else "No rows selected."
            )

        table.on_selection_change(_show_selection)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tutorial-runtable", description="Run the pyoncatng RunTable tutorial.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080).")
    parser.add_argument(
        "--native",
        action="store_true",
        help="Open in a native desktop window instead of a browser tab.",
    )
    return parser


def main() -> None:
    """Parse arguments (with shell completion) and start the NiceGUI server."""
    parser = _build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ui.run(
        host=args.host,
        port=args.port,
        native=args.native,
        reload=False,
        title="pyoncatng RunTable",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
