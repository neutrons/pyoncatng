"""Tests for the recorder command (no NiceGUI and no ONCat needed)."""

import argparse

import pyoncat
import pytest
from fakes import FakeAgent, RecordedAgent
from record_oncat import DEFAULT_PROJECTION, _experiment, main, record
from recordings import RecordingStore, read_recording, recording_name

REQUEST = {"facility": "SNS", "instrument": "USANS", "experiment": "IPTS-24703"}
CONTENT = [
    {"id": i, "object": "run", "type": "run", "datafiles": {"raw": {"metadata": {"entry": {"title": t}}}}}
    for i, t in ((2, "B"), (1, "A"))
]


@pytest.fixture
def source() -> FakeAgent:
    agent = FakeAgent()
    agent.run_result = [pyoncat.ONCatObject(content=content) for content in CONTENT]
    return agent


def test_record_writes_a_recording_that_the_store_reads_back(source, tmp_path) -> None:
    report = record(source, **REQUEST, directory=tmp_path)
    assert report["path"] == tmp_path / recording_name("SNS", "USANS", "IPTS-24703")
    runs = RecordingStore(tmp_path).list_runs(**REQUEST)
    assert [run.to_dict() for run in runs] == sorted(CONTENT, key=lambda content: content["id"])


def test_record_requests_all_pvs_in_ascending_order_by_default(source, tmp_path) -> None:
    record(source, **REQUEST, directory=tmp_path)
    assert source.run_kwargs == {**REQUEST, "projection": DEFAULT_PROJECTION, "sort_direction": "ASCENDING"}


def test_record_forwards_the_projection(source, tmp_path) -> None:
    record(source, **REQUEST, projection=["datafiles.raw.metadata.entry.title"], directory=tmp_path)
    assert source.run_kwargs["projection"] == ["datafiles.raw.metadata.entry.title"]


def test_record_header_holds_the_pyoncat_version_and_a_time(source, tmp_path) -> None:
    path = record(source, **REQUEST, directory=tmp_path)["path"]
    document = read_recording(path)
    assert document["pyoncat_version"]
    assert document["recorded_at"].endswith("+00:00")


def test_record_reports_run_count_and_sizes(source, tmp_path) -> None:
    report = record(source, **REQUEST, directory=tmp_path)
    assert report["runs"] == 2
    assert report["compressed_bytes"] == report["path"].stat().st_size
    assert report["raw_bytes"] > 0


def test_record_reports_a_replacement(source, tmp_path) -> None:
    assert record(source, **REQUEST, directory=tmp_path)["replaced"] is False
    assert record(source, **REQUEST, directory=tmp_path)["replaced"] is True


def test_record_creates_the_directory(source, tmp_path) -> None:
    record(source, **REQUEST, directory=tmp_path / "new" / "directory")
    assert (tmp_path / "new" / "directory" / recording_name("SNS", "USANS", "IPTS-24703")).is_file()


def test_record_refuses_an_experiment_without_runs(tmp_path) -> None:
    with pytest.raises(ValueError, match="no runs"):
        record(FakeAgent(), **REQUEST, directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_record_allows_an_empty_experiment_on_request(tmp_path) -> None:
    report = record(FakeAgent(), **REQUEST, directory=tmp_path, allow_empty=True)
    assert report["runs"] == 0
    assert RecordingStore(tmp_path).list_runs(**REQUEST) == []


def test_recorded_agent_can_replay_what_was_recorded(source, tmp_path) -> None:
    record(source, **REQUEST, directory=tmp_path)
    assert len(RecordedAgent(tmp_path).Run.list(**REQUEST)) == 2


def test_main_records_and_prints_the_report(source, tmp_path, capsys) -> None:
    assert main(["SNS", "USANS", "IPTS-24703", "--directory", str(tmp_path)], agent=source) == 0
    assert (tmp_path / recording_name("SNS", "USANS", "IPTS-24703")).is_file()
    output = capsys.readouterr().out
    assert "Wrote" in output
    assert "2 runs" in output
    assert "bytes compressed" in output


def test_main_passes_the_options_to_record(source, tmp_path) -> None:
    main(["SNS", "USANS", "IPTS-24703", "--projection", "a.b", "c.d", "--directory", str(tmp_path)], agent=source)
    assert source.run_kwargs["projection"] == ["a.b", "c.d"]
    assert source.run_kwargs["experiment"] == "IPTS-24703"


def test_main_allow_empty(tmp_path) -> None:
    assert main(["SNS", "USANS", "IPTS-1", "--directory", str(tmp_path), "--allow-empty"], agent=FakeAgent()) == 0


def test_main_refuses_a_bare_number_and_writes_nothing(source, tmp_path, capsys) -> None:
    with pytest.raises(SystemExit):
        main(["SNS", "USANS", "24703", "--directory", str(tmp_path)], agent=source)
    assert "must be written as IPTS-<number>" in capsys.readouterr().err
    assert source.run_calls == 0
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("text", ["IPTS-24703", "ipts-24703", "  IPTS-24703  "])
def test_experiment_argument_is_normalized(text: str) -> None:
    assert _experiment(text) == "IPTS-24703"


@pytest.mark.parametrize("text", ["", "  ", "24703", "IPTS-", "ipts_24703", "IPTS24703", "IPTS-24 703"])
def test_experiment_argument_must_be_an_ipts_with_its_prefix(text: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="IPTS-<number>"):
        _experiment(text)
