"""Tests for the naming, file format, and store of ONCat recordings (no NiceGUI needed)."""

import gzip
import json
import re

import pyoncat
import pytest
from recordings import (
    RECORDING_FORMAT,
    RecordingNotFoundError,
    RecordingStore,
    project,
    read_recording,
    recording_name,
    write_recording,
)

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
    write_recording(
        path, RUNS, projection=["datafiles.raw.metadata"], pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00"
    )
    document = read_recording(path)
    assert document == {
        "format": RECORDING_FORMAT,
        "recorded_at": "2026-11-27T00:00:00",
        "pyoncat_version": "2.6",
        "projection": ["datafiles.raw.metadata"],
        "runs": RUNS,
    }


def test_write_recording_is_deterministic_and_does_not_embed_the_file_name(tmp_path) -> None:
    first, second = tmp_path / "first_name.json.gz", tmp_path / "second_name.json.gz"
    for path in (first, second):
        write_recording(
            path, RUNS, projection=["datafiles.raw.metadata"], pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00"
        )
    assert first.read_bytes() == second.read_bytes()
    assert b"first_name" not in first.read_bytes()


def test_interrupted_write_keeps_the_previous_recording(tmp_path, monkeypatch) -> None:
    path = tmp_path / "recording.json.gz"
    write_recording(path, RUNS, projection=["datafiles.raw.metadata"], pyoncat_version="2.6", recorded_at="first")
    before = path.read_bytes()

    def interrupt(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr(gzip.GzipFile, "write", interrupt)
    with pytest.raises(KeyboardInterrupt):
        write_recording(path, RUNS, projection=["datafiles.raw.metadata"], pyoncat_version="2.6", recorded_at="second")
    assert path.read_bytes() == before
    assert [entry.name for entry in tmp_path.iterdir()] == ["recording.json.gz"]


def test_recording_header_has_only_the_expected_keys(tmp_path) -> None:
    path = tmp_path / "recording.json.gz"
    write_recording(
        path, RUNS, projection=["datafiles.raw.metadata"], pyoncat_version="2.6", recorded_at="2026-11-27T00:00:00"
    )
    assert set(read_recording(path)) == {"format", "recorded_at", "pyoncat_version", "projection", "runs"}


def test_read_recording_rejects_unknown_format(tmp_path) -> None:
    path = tmp_path / "recording.json.gz"
    path.write_bytes(gzip.compress(json.dumps({"format": 99, "runs": []}).encode("utf-8")))
    with pytest.raises(ValueError, match="Unsupported recording format 99"):
        read_recording(path)


# -- project ------------------------------------------------------------------

RUN = {
    "id": 7,
    "object": "run",
    "type": "run",
    "facility": "SNS",
    "datafiles": {"raw": {"metadata": {"entry": {"title": "A", "total_counts": 5}, "run_number": 7}}},
}


def test_project_keeps_requested_leaf_with_nested_structure() -> None:
    assert project(RUN, ["datafiles.raw.metadata.entry.title"]) == {
        "id": 7,
        "object": "run",
        "type": "run",
        "datafiles": {"raw": {"metadata": {"entry": {"title": "A"}}}},
    }


def test_project_keeps_a_whole_branch() -> None:
    assert project(RUN, ["datafiles.raw.metadata"])["datafiles"] == RUN["datafiles"]


def test_project_merges_paths_that_share_a_branch() -> None:
    result = project(RUN, ["datafiles.raw.metadata.entry.title", "datafiles.raw.metadata.run_number"])
    assert result["datafiles"]["raw"]["metadata"] == {"entry": {"title": "A"}, "run_number": 7}


def test_project_always_keeps_id_object_and_type_and_drops_the_rest() -> None:
    assert project(RUN, []) == {"id": 7, "object": "run", "type": "run"}


def test_project_omits_missing_paths() -> None:
    assert project(RUN, ["datafiles.raw.metadata.entry.nothing", "nothing.at.all", "id.deeper"]) == {
        "id": 7,
        "object": "run",
        "type": "run",
    }


def test_project_does_not_share_data_with_the_source() -> None:
    result = project(RUN, ["datafiles"])
    result["datafiles"]["raw"]["metadata"]["entry"]["title"] = "changed"
    assert RUN["datafiles"]["raw"]["metadata"]["entry"]["title"] == "A"


# -- RecordingStore -----------------------------------------------------------

STORE_RUNS = [
    {"id": i, "object": "run", "type": "run", "datafiles": {"raw": {"metadata": {"entry": {"title": t}}}}}
    for i, t in ((2, "B"), (3, "C"), (1, "A"))
]
REQUEST = {"facility": "SNS", "instrument": "USANS", "experiment": "IPTS-24703"}
TITLE = "datafiles.raw.metadata.entry.title"


@pytest.fixture
def store(tmp_path) -> RecordingStore:
    write_recording(
        tmp_path / recording_name("SNS", "USANS", "IPTS-24703"),
        STORE_RUNS,
        projection=["datafiles.raw.metadata"],
        pyoncat_version="2.6",
        recorded_at="2026-11-27T00:00:00",
    )
    return RecordingStore(tmp_path)


def test_store_returns_oncat_objects_sorted_ascending_by_default(store) -> None:
    runs = store.list_runs(**REQUEST, projection=[TITLE])
    assert all(isinstance(run, pyoncat.ONCatObject) for run in runs)
    assert [run["id"] for run in runs] == [1, 2, 3]


def test_store_sorts_descending(store) -> None:
    runs = store.list_runs(**REQUEST, projection=[TITLE], sort_direction="DESCENDING")
    assert [run["id"] for run in runs] == [3, 2, 1]


def test_store_rejects_an_invalid_sort_direction(store) -> None:
    with pytest.raises(ValueError, match="sort_direction"):
        store.list_runs(**REQUEST, sort_direction="UP")


def test_store_results_support_dot_path_get(store) -> None:
    run = store.list_runs(**REQUEST, projection=[TITLE])[0]
    assert run.get(TITLE) == "A"
    assert run.get("datafiles.raw.metadata.entry.total_counts") is None
    assert run.get("datafiles.raw.metadata.entry.total_counts", "default") == "default"


def test_store_without_projection_returns_runs_as_recorded(store) -> None:
    runs = store.list_runs(**REQUEST)
    assert [run.to_dict() for run in runs] == sorted(STORE_RUNS, key=lambda run: run["id"])


@pytest.mark.parametrize("path", [TITLE, "datafiles.raw.metadata", "id"])
def test_store_accepts_a_projection_covered_by_the_recording(store, path: str) -> None:
    assert len(store.list_runs(**REQUEST, projection=[path])) == 3


@pytest.mark.parametrize("path", ["location", "datafiles.raw", "datafiles.raw.metadataX"])
def test_store_refuses_a_projection_outside_the_recording(store, path: str) -> None:
    with pytest.raises(ValueError, match=r"does not hold \['" + path + r"'\].*datafiles\.raw\.metadata.*--projection"):
        store.list_runs(**REQUEST, projection=[TITLE, path])


def test_store_ignores_the_case_of_facility_and_instrument(store) -> None:
    assert len(store.list_runs(facility="sns", instrument="usans", experiment="IPTS-24703")) == 3


@pytest.mark.parametrize("experiment", ["24703", "ipts-24703", "IPTS24703", "IPTS_24703", " IPTS-24703", "IPTS-"])
def test_store_refuses_an_experiment_not_written_as_ipts_dash_number(store, experiment: str) -> None:
    with pytest.raises(RecordingNotFoundError, match="IPTS-<number>"):
        store.list_runs(facility="SNS", instrument="USANS", experiment=experiment)


def test_store_missing_recording_raises_an_explicit_not_found_error(store) -> None:
    with pytest.raises(RecordingNotFoundError, match=r"experiment='IPTS-1'.*record-oncat") as excinfo:
        store.list_runs(facility="SNS", instrument="USANS", experiment="IPTS-1")
    assert isinstance(excinfo.value, pyoncat.NotFoundError)
    assert recording_name("SNS", "USANS", "IPTS-1") not in str(excinfo.value)


def test_store_empty_recording_returns_an_empty_list(tmp_path) -> None:
    write_recording(
        tmp_path / recording_name("SNS", "USANS", "IPTS-2"),
        [],
        projection=["datafiles.raw.metadata"],
        pyoncat_version="2.6",
        recorded_at="2026-11-27T00:00:00",
    )
    assert RecordingStore(tmp_path).list_runs(facility="SNS", instrument="USANS", experiment="IPTS-2") == []


@pytest.mark.parametrize("argument", ["sort_by", "page_size", "since_id"])
def test_store_rejects_unsupported_arguments(store, argument: str) -> None:
    with pytest.raises(TypeError):
        store.list_runs(**REQUEST, **{argument: 1})


def test_store_calls_do_not_affect_each_other(store) -> None:
    store.list_runs(**REQUEST)[0].to_dict()["datafiles"]["raw"]["metadata"]["entry"]["title"] = "changed"
    assert store.list_runs(**REQUEST, projection=[TITLE])[0].get(TITLE) == "A"
