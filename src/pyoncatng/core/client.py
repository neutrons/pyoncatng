"""Construct and probe a :class:`pyoncat.ONCat` agent.

This module is deliberately free of any NiceGUI import: it only knows about
``pyoncat`` and ``requests``, so it can be unit-tested without a browser or an
event loop. The interactive, browser-based Device Authorization Grant is the
only authentication flow used here -- there is no username/password.
"""

from typing import Callable, Optional

import pyoncat
import requests

# Scopes requested for the interactive human-user session. Matches pyoncatqt.
# Widen (e.g. add "openid") only if the identity of the signed-in user is needed
# via ``agent.User.retrieve("me")``.
ONCAT_SCOPES = ["api:read"]

# Outcomes of probing the stored session. A genuinely dead/expired token
# (NEEDS_LOGIN) must be cleared to trigger a fresh authorization; a transient
# connectivity failure (UNREACHABLE) must leave the token intact so the session
# survives the outage.
SESSION_CONNECTED = "connected"
SESSION_NEEDS_LOGIN = "needs_login"
SESSION_UNREACHABLE = "unreachable"


def build_agent(
    oncat_url: str,
    client_id: str,
    *,
    token_getter: Callable[[], Optional[dict]],
    token_setter: Callable[[Optional[dict]], None],
    verification_handler: Callable[["pyoncat.DeviceAuthorizationChallenge"], None],
    scopes: Optional[list] = None,
    timeout: float = 10.0,
) -> pyoncat.ONCat:
    """Create a :class:`pyoncat.ONCat` agent for interactive sign-in.

    Params
    ------
    oncat_url : str
        Base URL of the ONCat API (e.g. ``https://oncat.ornl.gov``).
    client_id : str
        Public OAuth client ID for the Device Authorization Grant.
    token_getter : Callable[[], Optional[dict]]
        Called by pyoncat to load the current token, or ``None`` if unset.
    token_setter : Callable[[Optional[dict]], None]
        Called by pyoncat to persist the token (including on refresh).
    verification_handler : Callable[[DeviceAuthorizationChallenge], None]
        Called by pyoncat, on the thread running ``login()``, with the
        verification URL and one-time user code to surface to the user.
    scopes : list, optional
        OAuth scopes to request. Defaults to :data:`ONCAT_SCOPES`.
    timeout : float, optional
        Request timeout, in seconds, for ordinary API calls. Defaults to 10.0.

    Returns
    -------
    pyoncat.ONCat
        A configured agent. No network call is made until the first data
        request or an explicit ``login()``.
    """
    return pyoncat.ONCat(
        oncat_url,
        client_id=client_id,
        flow=pyoncat.DEVICE_AUTHORIZATION_FLOW,
        scopes=scopes if scopes is not None else ONCAT_SCOPES,
        token_getter=token_getter,
        token_setter=token_setter,
        # Raise InteractionRequiredError on a dead session instead of silently
        # re-prompting from inside a data call.
        reauth_on_expired=pyoncat.REAUTH_INTERACTION_REQUIRED,
        verification_handler=verification_handler,
        timeout=timeout,
    )


def classify_session(agent: pyoncat.ONCat) -> str:
    """Probe the stored session and classify the outcome.

    Distinguishes a genuinely invalid or expired token -- which must be cleared
    to trigger a fresh authorization -- from a transient connectivity failure,
    during which the token is preserved so the session survives the outage
    rather than forcing a needless re-login.

    This performs a blocking network round trip (``agent.Facility.list()``) and
    so must be run off the event loop by the caller.

    Returns
    -------
    str
        One of :data:`SESSION_CONNECTED`, :data:`SESSION_NEEDS_LOGIN`, or
        :data:`SESSION_UNREACHABLE`.
    """
    # Without a stored token there is no session to probe, and calling a data
    # method would drive login() into a blocking, interactive Device
    # Authorization Grant. Report "needs login" without any network round trip.
    if not agent.has_stored_token():
        return SESSION_NEEDS_LOGIN

    try:
        agent.Facility.list()
        return SESSION_CONNECTED
    except (
        pyoncat.InvalidRefreshTokenError,
        pyoncat.InteractionRequiredError,
        pyoncat.LoginRequiredError,
    ):
        # The token is dead or a fresh interactive sign-in is required.
        return SESSION_NEEDS_LOGIN
    except (
        pyoncat.DeviceAuthorizationNetworkError,
        requests.exceptions.RequestException,
    ):
        # A transport-layer failure (timeout, DNS, connection refused) is not
        # evidence the token is dead, so keep it and report the outage.
        return SESSION_UNREACHABLE
    except Exception:  # noqa: BLE001
        # An unclassified failure is likewise no proof the token is dead; err on
        # the side of preserving it.
        return SESSION_UNREACHABLE
