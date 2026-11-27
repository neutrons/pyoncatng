"""Tests for ``RecordedAgent`` and the ``recorded_agent`` fixture (no NiceGUI needed)."""

import pyoncat
import pytest
from fakes import FakeAgent, RecordedAgent
from recordings import RecordingNotFoundError, recording_name, write_recording

import pyoncatng.core.service as service

TITLE = "datafiles.raw.metadata.entry.title"
REQUEST = {"facility": "SNS", "instrument": "USANS", "experiment": "IPTS-24703"}
RUNS = [
    {"id": i, "object": "run", "type": "run", "datafiles": {"raw": {"metadata": {"entry": {"title": t}}}}}
    for i, t in ((2, "B"), (1, "A"))
]


@pytest.fixture
def directory(tmp_path):
    write_recording(
        tmp_path / recording_name("SNS", "USANS", "IPTS-24703"),
        RUNS,
        pyoncat_version="2.6",
        recorded_at="2026-11-27T00:00:00",
    )
    return tmp_path


def test_run_list_answers_from_the_recording(directory) -> None:
    agent = RecordedAgent(directory)
    runs = agent.Run.list(**REQUEST, projection=[TITLE], sort_direction="DESCENDING")
    assert [(run["id"], run.get(TITLE)) for run in runs] == [(2, "B"), (1, "A")]


def test_run_list_records_the_call(directory) -> None:
    agent = RecordedAgent(directory)
    agent.Run.list(**REQUEST, projection=[TITLE])
    assert agent.run_calls == 1
    assert agent.run_kwargs == {**REQUEST, "projection": [TITLE]}


def test_run_error_takes_precedence(directory) -> None:
    agent = RecordedAgent(directory)
    agent.run_error = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        agent.Run.list(**REQUEST)


def test_missing_recording_raises_by_default(directory) -> None:
    with pytest.raises(RecordingNotFoundError) as excinfo:
        RecordedAgent(directory).Run.list(facility="SNS", instrument="USANS", experiment="IPTS-1")
    assert isinstance(excinfo.value, pyoncat.NotFoundError)


def test_missing_recording_returns_empty_list_when_requested(directory) -> None:
    agent = RecordedAgent(directory, on_missing="empty")
    assert agent.Run.list(facility="SNS", instrument="USANS", experiment="IPTS-1") == []
    assert len(agent.Run.list(**REQUEST)) == 2


def test_invalid_on_missing_is_rejected(directory) -> None:
    with pytest.raises(ValueError, match="on_missing"):
        RecordedAgent(directory, on_missing="ignore")


def test_unsupported_argument_raises_through_the_agent(directory) -> None:
    with pytest.raises(TypeError):
        RecordedAgent(directory).Run.list(**REQUEST, page_size=10)


def test_fake_agent_still_returns_run_result() -> None:
    agent = FakeAgent()
    agent.run_result = [{"id": 1}]
    assert agent.Run.list(**REQUEST) == [{"id": 1}]


def test_recorded_agent_keeps_the_login_scripting() -> None:
    agent = RecordedAgent()
    assert agent.has_stored_token() is False
    agent.login()
    assert agent.has_stored_token() is True
    assert agent.Facility.list() == []


def test_recorded_agent_fixture_is_wired_in_place_of_the_real_agent(recorded_agent) -> None:
    assert isinstance(recorded_agent, RecordedAgent)
    login_service = service.LoginService("https://oncat.example", "client", verification_handler=lambda _: None)
    assert login_service.agent is recorded_agent
    assert recorded_agent.built["oncat_url"] == "https://oncat.example"
