"""Tests for the core ``list_runs`` helper (no NiceGUI needed)."""

import pytest
from fakes import FakeAgent

from pyoncatng.core.runs import list_runs


def test_list_runs_passes_arguments_and_returns_result() -> None:
    agent = FakeAgent()
    agent.run_result = [{"id": 1}, {"id": 2}]
    out = list_runs(
        agent,
        facility="SNS",
        instrument="USANS",
        experiment="IPTS-24703",
        projection=["metadata.entry.title"],
    )
    assert out == [{"id": 1}, {"id": 2}]
    assert agent.run_calls == 1
    assert agent.run_kwargs["facility"] == "SNS"
    assert agent.run_kwargs["instrument"] == "USANS"
    assert agent.run_kwargs["experiment"] == "IPTS-24703"
    assert agent.run_kwargs["projection"] == ["metadata.entry.title"]
    # Highest run numbers first by default, matching the website table.
    assert agent.run_kwargs["sort_direction"] == "DESCENDING"


def test_list_runs_forwards_sort_direction() -> None:
    agent = FakeAgent()
    list_runs(
        agent,
        facility="SNS",
        instrument="USANS",
        experiment="IPTS-1",
        projection=[],
        sort_direction="ASCENDING",
    )
    assert agent.run_kwargs["sort_direction"] == "ASCENDING"


def test_list_runs_propagates_errors() -> None:
    agent = FakeAgent()
    agent.run_error = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        list_runs(agent, facility="SNS", instrument="USANS", experiment="IPTS-1", projection=[])
