"""ONCat IPTS run-table tutorial: fetch and browse runs for an IPTS number.

Run it with ``pixi run tutorial-iptstable`` or ``python tutorials/iptstable/main.py``.
Unlike the RunTable tutorial (which uses local sample data), this one fetches
live data, so an ONCat sign-in is required:

1. Click **Connect** on the login card and approve the sign-in in your browser.
2. Type an IPTS number (e.g. ``24703``) in the field and click **Load**.
3. The table fills with that experiment's runs (ID, Title, Start Time, Total
   Counts) for SNS / USANS, most recent first.

A bad or non-existent IPTS number, or being disconnected, shows a message below
the table instead of runs.
"""

import argparse

import argcomplete
from nicegui import ui

from pyoncatng.configuration import Configuration, get_data
from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.login import OncatLogin

# Dev-only secret so ``app.storage.user`` (per-browser token persistence) works
# out of the box. For any real deployment pass your own via --storage-secret.
_DEFAULT_STORAGE_SECRET = "pyoncatng-dev-secret-change-me"  # noqa: S105


@ui.page("/")
def index() -> None:
    """The single tutorial page: a login card above an IPTSTable."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("pyoncatng IPTSTable demo").classes("text-h5")
        ui.markdown(
            "Sign in, then enter an IPTS number (e.g. **24703**) and click **Load** to fetch its runs for SNS / USANS."
        )
        login = OncatLogin(client_id=get_data("login.oncat", "client_id"), orientation="row")
        # The agent is created once and reused; passing it now is fine even though
        # it starts disconnected -- it becomes usable after the sign-in above.
        # Size the widget here; the table fills the given height and width.
        IPTSTable(agent=login.agent, facility="SNS", instrument="USANS").classes("w-full").style("height: 600px")
        # A short note on the underlying RunTable's interactions.
        ui.markdown(
            "**Tip:** click a row to select it (**Ctrl/Cmd + click** to toggle rows, "
            "**Shift + click** to select a range). Drag a column header left or right "
            "to reorder the columns &mdash; except **ID**, which stays pinned as the "
            "first column. Header clicks do not sort, cells are read-only, and rows "
            "cannot be dragged, so the run order is fixed."
        ).classes("text-caption")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tutorial-iptstable", description="Run the pyoncatng IPTSTable tutorial.")
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
        title="pyoncatng IPTSTable",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
