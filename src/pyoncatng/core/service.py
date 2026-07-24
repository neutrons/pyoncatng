"""Async login/probe/logout workflows around a :class:`pyoncat.ONCat` agent.

``pyoncat``'s ``login()``, ``logout()`` and the liveness probe all block while
they do network I/O, so each is run off the event loop with
:func:`asyncio.to_thread`. This module holds the live token in memory (the
``token_getter``/``token_setter`` the agent calls run on the worker thread,
where request-scoped stores such as ``app.storage.user`` are not safely
reachable); the widget layer is responsible for loading/flushing that token to
whatever per-session persistence it uses.

Kept free of any NiceGUI import so it can be unit-tested without a browser.
(``asyncio.to_thread`` uses the loop's default executor; swap in
``nicegui.run.io_bound`` at the call sites if executor contention ever matters.)
"""

import asyncio
import threading
from typing import Callable, Optional

import pyoncat

from .client import (
    SESSION_CONNECTED,
    SESSION_NEEDS_LOGIN,
    build_agent,
    classify_session,
)


class LoginService:
    """Own a per-session ONCat agent and drive its sign-in lifecycle.

    Params
    ------
    oncat_url : str
        Base URL of the ONCat API.
    client_id : str
        Public OAuth client ID for the Device Authorization Grant.
    verification_handler : Callable[[DeviceAuthorizationChallenge], None]
        Called (on the login worker thread) with the verification challenge.
    initial_token : dict, optional
        A previously persisted token to seed the session with, or ``None``.
    scopes : list, optional
        OAuth scopes to request; defaults to the agent's default scopes.
    timeout : float, optional
        Request timeout, in seconds, for ordinary API calls. Defaults to 10.0.
    """

    def __init__(
        self,
        oncat_url: str,
        client_id: str,
        *,
        verification_handler: Callable[["pyoncat.DeviceAuthorizationChallenge"], None],
        initial_token: Optional[dict] = None,
        scopes: Optional[list] = None,
        timeout: float = 10.0,
    ) -> None:
        self._token: Optional[dict] = initial_token
        self._agent = build_agent(
            oncat_url,
            client_id,
            token_getter=self._get_token,
            token_setter=self._set_token,
            verification_handler=verification_handler,
            scopes=scopes,
            timeout=timeout,
        )

    # -- token plumbing -----------------------------------------------------

    def _get_token(self) -> Optional[dict]:
        """``token_getter`` passed to pyoncat (may run on a worker thread)."""
        return self._token

    def _set_token(self, token: Optional[dict]) -> None:
        """``token_setter`` passed to pyoncat (may run on a worker thread)."""
        self._token = token

    @property
    def token(self) -> Optional[dict]:
        """The current in-memory token, for the widget to persist."""
        return self._token

    @property
    def agent(self) -> pyoncat.ONCat:
        """The underlying authenticated agent, for consumers to query."""
        return self._agent

    def has_stored_token(self) -> bool:
        """Whether a token is present without any network round trip."""
        return self._agent.has_stored_token()

    # -- workflows ----------------------------------------------------------

    async def probe(self) -> str:
        """Classify the stored session off the event loop.

        Returns one of the ``SESSION_*`` constants from :mod:`.client`.
        """
        return await asyncio.to_thread(classify_session, self._agent)

    async def connect(self, cancel_event: threading.Event) -> str:
        """Ensure a live session, signing in interactively if needed.

        Probes the stored session first. A still-valid session returns
        immediately; a transient outage is reported without touching the token;
        otherwise the stale token is cleared (the Device Authorization Grant's
        ``login()`` returns at once when any token -- even an expired one -- is
        stored, so the browser challenge would never appear) and an interactive
        sign-in is run off the event loop.

        Params
        ------
        cancel_event : threading.Event
            Set by the caller to abort the sign-in poll loop; pyoncat then
            raises :class:`pyoncat.DeviceAuthorizationCancelled`.

        Returns
        -------
        str
            :data:`~.client.SESSION_CONNECTED` when a sign-in completed or the
            existing session was already live, or
            :data:`~.client.SESSION_UNREACHABLE` on a transient outage.

        Raises
        ------
        pyoncat.PyONCatError
            Propagated from ``login()`` on sign-in failure or cancellation.
        """
        status = await self.probe()
        if status == SESSION_CONNECTED:
            return SESSION_CONNECTED
        if status != SESSION_NEEDS_LOGIN:
            # SESSION_UNREACHABLE: preserve the token and let the caller decide.
            return status

        # Token is genuinely invalid/expired: discard it so login() re-prompts.
        self._set_token(None)
        await asyncio.to_thread(self._agent.login, cancel_event=cancel_event)
        return SESSION_CONNECTED

    async def logout(self) -> None:
        """Revoke the session server-side and clear the local token.

        ``logout()`` revokes the refresh token at the IdP (network I/O), so it
        runs off the event loop. The local token is cleared regardless of
        whether server-side revocation succeeded; on failure the exception
        propagates so the caller can report it.
        """
        try:
            await asyncio.to_thread(self._agent.logout)
        finally:
            self._set_token(None)
