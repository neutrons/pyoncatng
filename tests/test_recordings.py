"""Tests for the naming and file format of ONCat recordings (no NiceGUI needed)."""

import gzip
import json
import re

import pytest
from recordings import RECORDING_FORMAT, read_recording, recording_name, write_recording

# -- recording_name ------------------------------------------------------------


def test_recording_name_is_truncated_hexadecimal_digest() -> None:
    assert re.fullmatch(r"[0-9a-f]{32}\.json\.gz", recording_name("SNS", "USANS", "IPTS-24703"))


@pytest.mark.parametrize("experiment", ["24703", "IPTS-24703", "ipts-24703", "ipts_24703", "  24703  ", "IPTS24703"])
def test_recording_name_accepts_equivalent_experiments(experiment: str) -> None:
    assert recording_name("SNS", "USANS", experiment) == recording_name("SNS", "USANS", "IPTS-24703")


def test_recording_name_ignores_case_and_whitespace_of_facility_and_instrument() -> None:
    assert recording_name(" sns ", "usans", "24703") == recording_name("SNS", "USANS", "24703")


def test_recording_name_differs_for_different_requests() -> None:
    names = {
        recording_name("SNS", "USANS", "24703"),
        recording_name("SNS", "USANS", "24704"),
        recording_name("SNS", "BL-6", "24703"),
        recording_name("HFIR", "USANS", "24703"),
    }
    assert len(names) == 4


def test_recording_name_does_not_reveal_the_request() -> None:
    name = recording_name("SNS", "USANS", "24703")
    assert "24703" not in name
    assert "usans" not in name.lower()


@pytest.mark.parametrize(
    ("facility", "instrument", "experiment"),
    [
        ("", "USANS", "24703"),
        ("SNS", "  ", "24703"),
        ("SNS", "USANS", ""),
        ("SNS", "USANS", "IPTS-"),
        ("SNS", "USANS", "ipts_"),
    ],
)
def test_recording_name_rejects_empty_parts(facility: str, instrument: str, experiment: str) -> None:
    with pytest.raises(ValueError, match="must"):
        recording_name(facility, instrument, experiment)


# -- write_recording / read_recording -----------------------------------------


RUNS = [{"id": 1, "datafiles": {"raw": {"metadata": {"entry": {"title": "A", "total_counts": None}}}}}, {"id": 2}]


def test_write_then_read_round_trip(tmp_path) -> None:
    path = tmp_path / "recording.json.gz"
    write_recording(path, RUNS, pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00")
    document = read_recording(path)
    assert document == {
        "format": RECORDING_FORMAT,
        "recorded_at": "2026-11-27T00:00:00",
        "pyoncat_version": "2.6",
        "runs": RUNS,
    }


def test_write_recording_is_deterministic_and_does_not_embed_the_file_name(tmp_path) -> None:
    first, second = tmp_path / "first_name.json.gz", tmp_path / "second_name.json.gz"
    for path in (first, second):
        write_recording(path, RUNS, pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00")
    assert first.read_bytes() == second.read_bytes()
    assert b"first_name" not in first.read_bytes()


def test_recording_holds_no_plain_instrument_or_experiment(tmp_path) -> None:
    path = tmp_path / "recording.json.gz"
    write_recording(path, RUNS, pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00")
    assert set(read_recording(path)) == {"format", "recorded_at", "pyoncat_version", "runs"}


def test_read_recording_rejects_unknown_format(tmp_path) -> None:
    path = tmp_path / "recording.json.gz"
    path.write_bytes(gzip.compress(json.dumps({"format": 99, "runs": []}).encode("utf-8")))
    with pytest.raises(ValueError, match="Unsupported recording format 99"):
        read_recording(path)
