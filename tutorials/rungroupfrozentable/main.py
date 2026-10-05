"""ONCat grouped-run tutorial: browse runs grouped by title with RunGroupFrozenTable.

Run it with ``pixi run tutorial-rungroupfrozentable`` or
``python tutorials/rungroupfrozentable/main.py``. No ONCat sign-in is needed --
the page generates sample run data locally so you can try the widget:

* The top table shows **one row per group** of runs sharing a ``Title``, with
  the group's smallest (``First``) and largest (``Last``) run ID and its ``Size``.
* **Select groups** -- click a row to select it, **Ctrl/Cmd + click** to toggle
  individual rows, and **Shift + click** to select a contiguous range.
* The caption lists the selected group indexes, and the bottom table shows the
  source runs of the selected groups.
* **Drag a column header** left/right to reorder columns, except ``Title``,
  which is locked to the leftmost position.

The selection is read out via ``RunGroupFrozenTable.on_selection_change``
(register a callback) and the async ``selected_group_indexes`` and
``selected_source_rows`` accessors.
"""

import argparse

import argcomplete
from nicegui import ui

from pyoncatng.widgets.rungroupfrozentable import RunGroupFrozenTable
from pyoncatng.widgets.runtable import RunTable

# Columns of the source-run table below the grouped table. ID is the locked key.
SOURCE_COLUMNS = ["ID", "Title", "Start Time", "Total Counts"]

# Sample run titles, in acquisition order. Repeated titles form groups whose run
# IDs are not consecutive, because other measurements were taken in between.
_TITLES = [
    "Empty cell",
    "Sample A 25C",
    "Sample A 25C",
    "Sample B 25C",
    "Sample A 25C",
    "Sample B 25C",
    "Empty cell",
    "Sample B 40C",
    "Sample B 40C",
    "Sample A 25C",
]


def _sample_rows() -> list[dict]:
    """Build sample run rows standing in for what would be fetched from ONCat."""
    return [
        {
            "ID": 33200 + i,
            "Title": title,
            "Start Time": f"2023-01-01 {7 + i:02d}:00",
            "Total Counts": 250000 + 1000 * i,
        }
        for i, title in enumerate(_TITLES)
    ]


@ui.page("/")
def index() -> None:
    """The single tutorial page: the grouped table and the selected source runs."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("pyoncatng RunGroupFrozenTable demo").classes("text-h5")
        ui.markdown(
            "Runs sharing a **Title** are grouped into one row. **Click** a row to select "
            "it, **Ctrl/Cmd + click** to toggle rows, and **Shift + click** to select a "
            "range. The source runs of the selected groups appear in the table below."
        )
        groups = RunGroupFrozenTable(rows=_sample_rows(), group_by="Title").style("height: 320px")

        selection_label = ui.label("No groups selected.").classes("text-caption")
        sources = RunTable(columns=SOURCE_COLUMNS, rows=[], key_column="ID").style("height: 300px")

        # Read the selection through the widget's public API: register a callback
        # with on_selection_change, then await the group accessors.
        async def _show_selection() -> None:
            indexes = await groups.selected_group_indexes()
            selection_label.set_text(
                "Selected group index(es): " + ", ".join(str(index) for index in indexes)
                if indexes
                else "No groups selected."
            )
            sources.set_rows(await groups.selected_source_rows())

        groups.on_selection_change(_show_selection)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tutorial-rungroupfrozentable",
        description="Run the pyoncatng RunGroupFrozenTable tutorial.",
    )
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
        title="pyoncatng RunGroupFrozenTable",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
