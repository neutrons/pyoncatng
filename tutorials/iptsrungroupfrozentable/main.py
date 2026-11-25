"""ONCat IPTS grouped-run tutorial: load the runs of an IPTS grouped by title.

Run it with ``pixi run tutorial-iptsrungroupfrozentable`` or
``python tutorials/iptsrungroupfrozentable/main.py``. Like the IPTSTable
tutorial, it fetches live data, so an ONCat sign-in is required:

1. Click **Connect** on the login card and approve the sign-in in your browser.
2. Type an IPTS number (e.g. ``24703``) in the field and click **Load**.
3. The top table shows **one row per group** of runs sharing a ``Title``, with
   the group's smallest (``First``) and largest (``Last``) run ID and its ``Size``.
4. Select groups with a click, **Ctrl/Cmd + click**, **Shift + click**, or the
   **Space** key. The caption lists the selected group indexes, and the bottom
   table shows the source runs of the selected groups.
5. Every **Load**, including a reload of the same IPTS, clears the selection.

The selection is read out via ``IPTSRunGroupFrozenTable.on_selection_change``
(register a callback) and the async ``selected_group_indexes`` and
``selected_source_rows`` accessors. The callback also runs after every **Load**.
"""

import argparse

import argcomplete
from nicegui import ui

from pyoncatng.configuration import Configuration, get_data
from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable
from pyoncatng.widgets.login import OncatLogin
from pyoncatng.widgets.runtable import RunTable

# Columns of the source-run table below the grouped table. ID is the locked key.
SOURCE_COLUMNS = ["ID", "Title", "Start Time", "Total Counts"]

# Dev-only secret so ``app.storage.user`` (per-browser token persistence) works
# out of the box. For any real deployment pass your own via --storage-secret.
_DEFAULT_STORAGE_SECRET = "pyoncatng-dev-secret-change-me"  # noqa: S105


@ui.page("/")
def index() -> None:
    """The single tutorial page: a login card, the grouped runs, and the selected source runs."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("pyoncatng IPTSRunGroupFrozenTable demo").classes("text-h5")
        ui.markdown(
            "Sign in, then enter an IPTS number (e.g. **24703**) and click **Load**. Runs "
            "sharing a **Title** are grouped into one row. The source runs of the selected "
            "groups appear in the table below."
        )
        login = OncatLogin(client_id=get_data("login.oncat", "client_id"), orientation="row")
        # The agent is created once and reused; passing it now is fine even though
        # it starts disconnected -- it becomes usable after the sign-in above.
        groups = IPTSRunGroupFrozenTable(agent=login.agent, group_by="Title").style("height: 400px")

        selection_label = ui.label("No groups selected.").classes("text-caption")
        sources = RunTable(columns=SOURCE_COLUMNS, rows=[], key_column="ID").style("height: 300px")

        # Read the selection through the widget's public API: register a callback
        # with on_selection_change, then await the accessors. The callback also
        # runs after every Load, when the selection is cleared.
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
        prog="tutorial-iptsrungroupfrozentable",
        description="Run the pyoncatng IPTSRunGroupFrozenTable tutorial.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080).")
    parser.add_argument(
        "--storage-secret",
        default=_DEFAULT_STORAGE_SECRET,
        help="Secret used to sign per-user storage cookies.",
    )
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
    # Ensure ~/.pyoncatng/configuration.ini exists and carries the latest
    # [login.oncat] defaults (created/backfilled from the bundled template).
    Configuration()
    ui.run(
        host=args.host,
        port=args.port,
        storage_secret=args.storage_secret,
        native=args.native,
        reload=False,
        title="pyoncatng IPTSRunGroupFrozenTable",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
