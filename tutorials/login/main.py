"""ONCat login tutorial: sign in to ONCat with the OncatLogin widget.

Run it with ``pixi run tutorial-login`` or ``python tutorials/login/main.py``.
Open the page, click **Connect to ONCat**, approve the sign-in in your browser,
and watch the status flip to *Connected*.
"""

import argparse

import argcomplete
from nicegui import ui

from pyoncatng.configuration import Configuration, get_data
from pyoncatng.widgets.login import OncatLogin

# Dev-only secret so ``app.storage.user`` (per-browser token persistence) works
# out of the box. For any real deployment pass your own via --storage-secret.
_DEFAULT_STORAGE_SECRET = "pyoncatng-dev-secret-change-me"  # noqa: S105


@ui.page("/")
def index() -> None:
    """The single tutorial page: an ONCat login card and a live status readout."""
    with ui.column().classes("q-pa-md"):
        ui.label("pyoncatng demo").classes("text-h5")
        login = OncatLogin(client_id=get_data("login.oncat", "client_id"), orientation="column")
        status = ui.label("Not connected")
        login.on_connection_change(
            lambda connected: status.set_text("Connected to ONCat" if connected else "Not connected")
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tutorial-login", description="Run the pyoncatng ONCat login tutorial.")
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
        title="pyoncatng",
    )


# ``ui.run`` must be reached at import time for NiceGUI's launcher; guard so the
# module can still be imported without starting a server.
if __name__ in {"__main__", "__mp_main__"}:
    main()
