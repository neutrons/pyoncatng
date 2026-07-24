"""A reusable NiceGUI login component for ONCat.

The NiceGUI counterpart of ``pyoncatqt``'s ``ONCatLogin``. It drives the OAuth
2.0 Device Authorization Grant: the user clicks **Connect**, a dialog surfaces a
verification link and one-time code to approve in a browser, and the widget
reflects the connection state and exposes the authenticated agent to consumers.

Threading model
---------------
``pyoncat``'s ``login()`` blocks while it polls the identity provider and, from
that worker thread, calls back into ``verification_handler`` with the challenge.
The blocking work is run off the event loop by :class:`LoginService`
(``asyncio.to_thread``); the challenge is relayed back to the event loop with
``loop.call_soon_threadsafe`` and the verification dialog is always built inside
the ``connect_to_oncat`` coroutine, where the NiceGUI client/slot context is
intact -- never from the cross-thread callback.

Token persistence
------------------
The live token is held in memory by the service. The widget seeds it from, and
flushes it to, ``app.storage.user`` -- per-browser storage that survives
restarts. Persistence is best-effort: if no ``storage_secret`` is configured
(e.g. in minimal tests) the widget still works, just without persistence.
"""

import asyncio
import logging
import threading
from typing import Callable, List, Optional

import pyoncat
from nicegui import app, ui

from ..configuration import get_data
from ..core.client import SESSION_CONNECTED, SESSION_UNREACHABLE
from ..core.service import LoginService

logger = logging.getLogger("PYONCATNG")


class OncatLogin(ui.card):
    """ONCat login card: a circle status indicator plus Connect / Log out buttons.

    The circle reflects the connection state -- an empty ring when disconnected,
    a green disc when connected, and an amber disc while a sign-in/probe/logout
    is in progress. The exact status text is shown as a tooltip on the circle;
    connection failures are surfaced as ``ui.notify`` toasts.

    Params
    ------
    client_id : str, optional
        Explicit ONCat client ID. Either ``client_id`` or ``key`` is required.
    key : str, optional
        Config key used to look up the client ID as ``<key>_id`` in the
        ``[login.oncat]`` configuration section.
    timeout : float, optional
        Request timeout, in seconds, for the ONCat agent. Defaults to 10.0.
    login_title : str, optional
        Heading shown on the verification dialog. Defaults to
        ``"Sign in to ONCat"``.
    orientation : str, optional
        Arrangement of the Connect / Log out buttons: ``"row"`` (side by side,
        the default) or ``"column"`` (stacked).
    """

    # Circle status indicator styles, keyed by state. All three set the same CSS
    # properties, so switching state fully repaints the ring (via style replace).
    _INDICATOR_BASE = "width:22px;height:22px;border-radius:50%;box-sizing:border-box;"
    _INDICATOR_STYLE = {
        "empty": _INDICATOR_BASE + "border:2px solid #9e9e9e;background:transparent;",
        "connected": _INDICATOR_BASE + "border:2px solid #21ba45;background:#21ba45;",
        "busy": _INDICATOR_BASE + "border:2px solid #f2c037;background:#f2c037;",
    }

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        key: Optional[str] = None,
        timeout: float = 10.0,
        login_title: str = "Sign in to ONCat",
        orientation: str = "row",
    ) -> None:
        super().__init__()
        self._login_title = login_title
        if orientation not in ("row", "column"):
            raise ValueError(f"orientation must be 'row' or 'column', got {orientation!r}.")
        self._orientation = orientation

        oncat_url = get_data("login.oncat", "oncat_url")
        if client_id is not None:
            self._client_id = client_id
        elif key is not None:
            self._client_id = get_data("login.oncat", f"{key}_id")
        else:
            raise ValueError("Either 'client_id' or 'key' is required to build the ONCat login widget.")
        if not self._client_id:
            raise ValueError(f"No ONCat client ID found for key '{key}'.")

        # Per-session storage key: keep the token isolated per app (by key) or
        # per client ID prefix, mirroring pyoncatqt's token file naming.
        self._storage_key = f"oncat_token_{key or self._client_id[:8]}"

        # Cross-thread sign-in plumbing, populated per connect attempt.
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._challenge_ready: Optional[asyncio.Event] = None
        self._challenge: Optional["pyoncat.DeviceAuthorizationChallenge"] = None
        self._cancel_event: Optional[threading.Event] = None
        self._login_dialog: Optional[ui.dialog] = None

        self._busy = False
        self._connected = False
        self._on_change: List[Callable[[bool], None]] = []

        self._service = LoginService(
            oncat_url,
            self._client_id,
            verification_handler=self._verification_handler,
            initial_token=self._load_persisted_token(),
            timeout=timeout,
        )

        self._build_ui()

        # Render the initial (disconnected) state, then probe any stored session
        # in the background so a still-valid session shows without blocking.
        self._update_connection_status()
        ui.timer(0.1, self._refresh_connection_status, once=True)
        # Capture token refreshes that happen during direct consumer agent
        # calls, which the service updates in memory but does not persist.
        ui.timer(3.0, self._flush_token)

    # -- public integration surface ----------------------------------------

    @property
    def agent(self) -> pyoncat.ONCat:
        """The authenticated ONCat agent, for consumers to query."""
        return self._service.agent

    @property
    def is_connected(self) -> bool:
        """Cached connection state (no network round trip)."""
        return self._connected

    def on_connection_change(self, callback: Callable[[bool], None]) -> None:
        """Register a callback invoked with the connected bool on every change.

        The NiceGUI analogue of pyoncatqt's ``connection_updated`` signal;
        consumers use it to (re)populate instrument lists once connected.
        """
        self._on_change.append(callback)

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        button_container = ui.row if self._orientation == "row" else ui.column
        with self, ui.row().classes("items-center"):
            self._indicator = ui.element("div")
            with self._indicator:
                self._tooltip = ui.tooltip("")
            with button_container():
                self.oncat_button = ui.button("Connect", on_click=self.connect_to_oncat)
                self.oncat_button.tooltip("Connect to ONCat")
                self.logout_button = ui.button("Log out", on_click=self.disconnect_from_oncat)
                self.logout_button.tooltip("Log out of ONCat")

    def _set_indicator(self, state: str, text: str) -> None:
        """Repaint the circle for ``state`` and set its hover tooltip text."""
        self._indicator.style(replace=self._INDICATOR_STYLE[state])
        self._tooltip.set_text(text)

    def _update_connection_status(self) -> None:
        """Render the cached connection state and toggle the buttons."""
        connected = self._connected
        if connected:
            self._set_indicator("connected", "ONCat: Connected")
        else:
            self._set_indicator("empty", "ONCat: Disconnected")
        # Connect only while disconnected; log out while there is a live session
        # or a stored token to revoke. Both are disabled while a job is running.
        self.oncat_button.set_enabled(not connected and not self._busy)
        self.logout_button.set_enabled((connected or self._service.has_stored_token()) and not self._busy)
        for callback in self._on_change:
            callback(connected)

    def _set_status(self, text: str) -> None:
        """Show a transient (busy) status and disable both buttons."""
        self._set_indicator("busy", text)
        self.oncat_button.set_enabled(False)
        self.logout_button.set_enabled(False)

    # -- connection lifecycle ----------------------------------------------

    async def _refresh_connection_status(self) -> None:
        """Probe any stored session on a worker thread and refresh the status."""
        if not self._service.has_stored_token():
            self._connected = False
            self._update_connection_status()
            return
        if self._busy:
            return
        self._busy = True
        self._set_status("ONCat: Checking session...")
        try:
            self._connected = await self._service.probe() == SESSION_CONNECTED
        except Exception:  # noqa: BLE001
            self._connected = False
        finally:
            self._busy = False
            self._update_connection_status()

    async def connect_to_oncat(self) -> None:
        """Start an interactive, browser-based sign-in to ONCat."""
        if self._busy:
            return
        self._busy = True
        self._loop = asyncio.get_running_loop()
        self._challenge = None
        self._challenge_ready = asyncio.Event()
        self._cancel_event = threading.Event()
        self._set_status("ONCat: Starting sign-in...")

        login_task = asyncio.create_task(self._service.connect(self._cancel_event))
        waiter = asyncio.create_task(self._challenge_ready.wait())
        try:
            await asyncio.wait({login_task, waiter}, return_when=asyncio.FIRST_COMPLETED)
            # A challenge means the browser step is required: surface it here,
            # in the coroutine's UI context, then wait for sign-in to resolve.
            if self._challenge_ready.is_set() and not login_task.done():
                self._set_indicator("busy", "ONCat: Waiting for browser approval...")
                self._show_verification(self._challenge)
            status = await login_task
        except pyoncat.DeviceAuthorizationCancelled:
            # User cancelled: stay silent, just fall back to disconnected.
            self._connected = False
        except Exception as error:  # noqa: BLE001
            self._connected = False
            ui.notify(str(error), type="negative")
        else:
            if status == SESSION_UNREACHABLE:
                ui.notify(
                    "Could not reach ONCat to verify the session. Your sign-in has "
                    "been kept; please check your connection and try again.",
                    type="warning",
                )
            else:
                self._connected = True
        finally:
            waiter.cancel()
            self._close_dialog()
            self._cancel_event = None
            self._challenge_ready = None
            self._busy = False
            self._update_connection_status()
            self._flush_token()

    async def disconnect_from_oncat(self) -> None:
        """Log out of ONCat, revoking the current session server-side."""
        if self._busy:
            return
        self._busy = True
        self._set_status("ONCat: Logging out...")
        try:
            await self._service.logout()
        except Exception as error:  # noqa: BLE001
            # The local token is cleared regardless, so the session is unusable
            # here; surface the server-side revocation failure honestly.
            ui.notify(
                f"Logged out on this device, but ONCat could not revoke the session server-side:\n{error}",
                type="warning",
            )
        finally:
            self._connected = False
            self._busy = False
            self._update_connection_status()
            self._flush_token()

    # -- verification dialog ------------------------------------------------

    def _verification_handler(self, challenge: "pyoncat.DeviceAuthorizationChallenge") -> None:
        """Relay the device-authorization challenge to the event loop.

        Called by pyoncat on the login worker thread; must not touch UI here.
        """
        self._challenge = challenge
        loop = self._loop
        event = self._challenge_ready
        if loop is not None and event is not None:
            loop.call_soon_threadsafe(event.set)

    def _show_verification(self, challenge: "pyoncat.DeviceAuthorizationChallenge") -> None:
        """Build and open the verification dialog (must run in UI context)."""
        link = challenge.verification_uri_complete or challenge.verification_uri
        with ui.dialog() as dialog, ui.card():
            ui.label(self._login_title).classes("text-h6")
            ui.label("Open this link in your browser to approve the sign-in:")
            ui.link(link, link, new_tab=True)
            ui.label(f"If asked for a code, enter:  {challenge.user_code}")
            ui.button("Cancel", on_click=self._on_cancel_requested)
        self._login_dialog = dialog
        dialog.open()

    def _on_cancel_requested(self) -> None:
        """Signal the worker to abort the poll loop."""
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._set_indicator("busy", "ONCat: Cancelling sign-in...")

    def _close_dialog(self) -> None:
        """Close the verification dialog if one is open."""
        if self._login_dialog is not None:
            self._login_dialog.close()
            self._login_dialog = None

    # -- token persistence (best-effort) ------------------------------------

    def _load_persisted_token(self) -> Optional[dict]:
        """Load a previously persisted token from per-user storage, if any."""
        try:
            return app.storage.user.get(self._storage_key)
        except Exception as error:  # noqa: BLE001
            logger.debug("ONCat token storage unavailable on load: %s", error)
            return None

    def _flush_token(self) -> None:
        """Persist (or clear) the current in-memory token in per-user storage."""
        try:
            store = app.storage.user
        except Exception as error:  # noqa: BLE001
            logger.debug("ONCat token storage unavailable on flush: %s", error)
            return
        token = self._service.token
        if token is None:
            store.pop(self._storage_key, None)
        else:
            store[self._storage_key] = token
