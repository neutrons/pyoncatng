"""Unit tests for the async LoginService workflows."""

import threading

import pyoncat
import pytest
import requests

from pyoncatng.core.client import SESSION_CONNECTED, SESSION_UNREACHABLE
from pyoncatng.core.service import LoginService


def _make_service(**kwargs) -> LoginService:
    return LoginService(
        "https://oncat.ornl.gov",
        "client-123",
        verification_handler=lambda *_: None,
        **kwargs,
    )


async def test_connect_clears_stale_token_before_login(fake_agent):
    """A dead stored token is discarded so login() re-prompts from scratch."""
    fake_agent.tokened = True
    fake_agent.facility_error = pyoncat.InvalidRefreshTokenError("dead")
    fake_agent.emit_challenge = False
    fake_agent.login_mode = "success"

    service = _make_service(initial_token={"old": 1})
    result = await service.connect(threading.Event())

    assert result == SESSION_CONNECTED
    assert fake_agent.login_calls == 1
    # The stale token was cleared before login ran.
    assert fake_agent.login_seen_token is None
    # login() persisted a fresh token through the setter.
    assert service.token == {"access_token": "fake"}


async def test_connect_already_connected_skips_login(fake_agent):
    fake_agent.tokened = True
    fake_agent.facility_error = None

    service = _make_service(initial_token={"live": 1})
    result = await service.connect(threading.Event())

    assert result == SESSION_CONNECTED
    assert fake_agent.login_calls == 0


async def test_connect_unreachable_preserves_token(fake_agent):
    fake_agent.tokened = True
    fake_agent.facility_error = requests.exceptions.ConnectionError("refused")

    service = _make_service(initial_token={"keep": 1})
    result = await service.connect(threading.Event())

    assert result == SESSION_UNREACHABLE
    assert fake_agent.login_calls == 0
    assert service.token == {"keep": 1}


async def test_connect_propagates_login_error(fake_agent):
    fake_agent.tokened = False
    fake_agent.emit_challenge = False
    fake_agent.login_mode = "error"

    service = _make_service()
    with pytest.raises(pyoncat.DeviceAuthorizationExpired):
        await service.connect(threading.Event())


async def test_logout_clears_token(fake_agent):
    fake_agent.tokened = True
    fake_agent.facility_error = None
    service = _make_service(initial_token={"live": 1})
    await service.connect(threading.Event())

    await service.logout()

    assert fake_agent.logout_calls == 1
    assert service.token is None


async def test_logout_error_still_clears_token(fake_agent):
    fake_agent.logout_error = pyoncat.PyONCatError("revocation failed")
    service = _make_service(initial_token={"live": 1})

    with pytest.raises(pyoncat.PyONCatError):
        await service.logout()
    # Cleared locally regardless of the server-side revocation failure.
    assert service.token is None
