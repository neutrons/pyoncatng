"""Shared fixtures: test configuration path, a scriptable fake ONCat agent, and one backed by recordings."""

import os

import pytest
from fakes import FakeAgent, RecordedAgent

import pyoncatng.configuration as configuration

TEST_CONFIG = os.path.join(os.path.dirname(__file__), "data", "configuration.ini")


@pytest.fixture(autouse=True)
def _config_path(monkeypatch):
    """Point the configuration loader at the bundled test INI for every test."""
    monkeypatch.setattr(configuration, "CONFIG_PATH_FILE", TEST_CONFIG)


def _patch_build_agent(monkeypatch, agent):
    """Patch ``build_agent`` so the service/widget use ``agent``.

    ``agent`` records the arguments ``build_agent`` was called with (``built``) and captures the token
    getter/setter and verification handler the caller wired in.
    """

    def _build(oncat_url, client_id, *, token_getter, token_setter, verification_handler, scopes=None, timeout=10.0):
        agent.built = {
            "oncat_url": oncat_url,
            "client_id": client_id,
            "scopes": scopes,
            "timeout": timeout,
        }
        agent.token_getter = token_getter
        agent.token_setter = token_setter
        agent.verification_handler = verification_handler
        return agent

    monkeypatch.setattr("pyoncatng.core.service.build_agent", _build)
    return agent


@pytest.fixture
def fake_agent(monkeypatch):
    """A scriptable :class:`FakeAgent` wired in place of the real agent."""
    return _patch_build_agent(monkeypatch, FakeAgent())


@pytest.fixture
def recorded_agent(monkeypatch):
    """A :class:`RecordedAgent` wired in place of the real agent; ``Run.list`` answers from the recordings."""
    return _patch_build_agent(monkeypatch, RecordedAgent())
