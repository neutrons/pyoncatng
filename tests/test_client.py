"""Unit tests for the pure pyoncat layer: agent construction and probing."""

import pyoncat
import requests
from fakes import FakeAgent

from pyoncatng.core.client import (
    ONCAT_SCOPES,
    SESSION_CONNECTED,
    SESSION_NEEDS_LOGIN,
    SESSION_UNREACHABLE,
    build_agent,
    classify_session,
)


def test_build_agent_passes_device_flow_configuration(monkeypatch):
    recorded = {}

    def _recorder(url, **kwargs):
        recorded["url"] = url
        recorded.update(kwargs)
        return "sentinel-agent"

    monkeypatch.setattr(pyoncat, "ONCat", _recorder)

    getter, setter, handler = object(), object(), object()
    agent = build_agent(
        "https://oncat.ornl.gov",
        "client-123",
        token_getter=getter,
        token_setter=setter,
        verification_handler=handler,
        timeout=7.0,
    )

    assert agent == "sentinel-agent"
    assert recorded["url"] == "https://oncat.ornl.gov"
    assert recorded["client_id"] == "client-123"
    assert recorded["flow"] == pyoncat.DEVICE_AUTHORIZATION_FLOW
    assert recorded["scopes"] == ONCAT_SCOPES
    assert recorded["reauth_on_expired"] == pyoncat.REAUTH_INTERACTION_REQUIRED
    assert recorded["token_getter"] is getter
    assert recorded["token_setter"] is setter
    assert recorded["verification_handler"] is handler
    assert recorded["timeout"] == 7.0


def test_classify_session_without_token_needs_login_without_network():
    agent = FakeAgent()
    agent.tokened = False
    assert classify_session(agent) == SESSION_NEEDS_LOGIN
    # No probe request is made when there is no token.
    assert agent.facility_calls == 0


def test_classify_session_connected():
    agent = FakeAgent()
    agent.tokened = True
    agent.facility_error = None
    assert classify_session(agent) == SESSION_CONNECTED
    assert agent.facility_calls == 1


def test_classify_session_dead_token_needs_login():
    for error in (
        pyoncat.InvalidRefreshTokenError("dead"),
        pyoncat.InteractionRequiredError("interact"),
        pyoncat.LoginRequiredError("login"),
    ):
        agent = FakeAgent()
        agent.tokened = True
        agent.facility_error = error
        assert classify_session(agent) == SESSION_NEEDS_LOGIN


def test_classify_session_outage_is_unreachable():
    for error in (
        pyoncat.DeviceAuthorizationNetworkError("net"),
        requests.exceptions.ConnectionError("refused"),
        RuntimeError("unclassified"),
    ):
        agent = FakeAgent()
        agent.tokened = True
        agent.facility_error = error
        assert classify_session(agent) == SESSION_UNREACHABLE
