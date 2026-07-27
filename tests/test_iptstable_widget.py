"""Tests for the IPTSTable widget.

Two layers (mirroring ``test_runtable_widget.py``):

* **Unit tests** on the pure helpers (``normalize_ipts``, ``build_projection``,
  ``column_names``, ``rows_from_runs``), which need no UI context.
* **Widget tests** via NiceGUI's in-process ``user`` simulation. The page builds
  the widget with a scriptable ``FakeAgent``; a test reaches it through the live
  element (``IPTSTable._agent``) to script ``Run.list`` before loading, then
  asserts the child RunTable's ``options`` (AG Grid cells are client-side and not
  visible to the simulation) or the inline message text.
"""

from nicegui.testing import User

from pyoncatng.widgets.iptstable import COLUMN_SPEC, IPTSTable
from pyoncatng.widgets.runtable import RunTable

# A sample run as returned by ONCat with a flat, dot-path projection (which is
# what ``run.get("datafiles.raw.metadata.entry.title")`` resolves to for the real
# client too). USANS runs expose metadata under datafiles.raw.metadata.entry.*.
SAMPLE_RUN = {
    "id": 33221,
    "datafiles.raw.metadata.entry.title": "Align:0 stop rheometer",
    "datafiles.raw.metadata.entry.start_time": "2020-11-24T06:33:53.879457667-05:00",
    "datafiles.raw.metadata.entry.total_counts": 258881,
}

# -- unit tests: pure helpers -------------------------------------------------


def test_normalize_ipts_prefixes_bare_number() -> None:
    assert IPTSTable.normalize_ipts("24703") == "IPTS-24703"


def test_normalize_ipts_strips_whitespace() -> None:
    assert IPTSTable.normalize_ipts("  24703  ") == "IPTS-24703"


def test_normalize_ipts_preserves_prefixed_value() -> None:
    assert IPTSTable.normalize_ipts("IPTS-24703") == "IPTS-24703"
    assert IPTSTable.normalize_ipts("ipts-24703") == "IPTS-24703"


def test_normalize_ipts_blank_is_none() -> None:
    assert IPTSTable.normalize_ipts("") is None
    assert IPTSTable.normalize_ipts("   ") is None
    assert IPTSTable.normalize_ipts(None) is None


def test_normalize_ipts_prefix_only_is_none() -> None:
    # Only the prefix (no number) is effectively blank, not "IPTS-".
    assert IPTSTable.normalize_ipts("IPTS-") is None
    assert IPTSTable.normalize_ipts("ipts-   ") is None


def test_column_names_match_spec() -> None:
    assert IPTSTable.column_names() == ["ID", "Title", "Start Time", "Total Counts"]


def test_build_projection_is_the_path_backed_columns() -> None:
    assert IPTSTable.build_projection() == [
        "datafiles.raw.metadata.entry.title",
        "datafiles.raw.metadata.entry.start_time",
        "datafiles.raw.metadata.entry.total_counts",
    ]


def test_rows_from_runs_maps_id_and_paths() -> None:
    rows = IPTSTable.rows_from_runs([SAMPLE_RUN])
    assert rows == [
        {
            "ID": 33221,
            "Title": "Align:0 stop rheometer",
            "Start Time": "2020-11-24T06:33:53.879457667-05:00",
            "Total Counts": 258881,
        }
    ]


def test_rows_from_runs_missing_path_is_none() -> None:
    rows = IPTSTable.rows_from_runs([{"id": 7}])
    assert rows == [{"ID": 7, "Title": None, "Start Time": None, "Total Counts": None}]


def test_key_column_is_first_in_spec() -> None:
    # The key column (path None -> run id) must be the leftmost RunTable column.
    assert COLUMN_SPEC[0][0] == "ID"
    assert COLUMN_SPEC[0][1] is None


# -- widget tests: live element via the user simulation -----------------------


def _widget(user: User) -> IPTSTable:
    return next(iter(user.find(IPTSTable).elements))


def _table(user: User) -> RunTable:
    return next(iter(user.find(RunTable).elements))


async def test_iptstable_renders(user: User) -> None:
    await user.open("/iptstable")
    await user.should_see(kind=IPTSTable)
    await user.should_see("IPTS:")
    await user.should_see("Load")


async def test_iptstable_load_populates_table(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._agent.run_result = [SAMPLE_RUN]
    widget._input.value = "24703"

    await widget._on_load()

    # The IPTS number was normalized and the fixed projection/sort were sent.
    assert widget._agent.run_kwargs["experiment"] == "IPTS-24703"
    assert widget._agent.run_kwargs["facility"] == "SNS"
    assert widget._agent.run_kwargs["instrument"] == "USANS"
    assert widget._agent.run_kwargs["projection"] == IPTSTable.build_projection()
    assert widget._agent.run_kwargs["sort_direction"] == "DESCENDING"
    # The child RunTable carries the mapped row.
    row_data = _table(user).options["rowData"]
    assert row_data == [
        {
            "ID": 33221,
            "Title": "Align:0 stop rheometer",
            "Start Time": "2020-11-24T06:33:53.879457667-05:00",
            "Total Counts": 258881,
        }
    ]


async def test_iptstable_empty_result_shows_message(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._agent.run_result = []
    widget._input.value = "24703"

    await widget._on_load()

    assert _table(user).options["rowData"] == []
    await user.should_see("No runs found for IPTS-24703.")


async def test_iptstable_blank_input_shows_message(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._input.value = "   "

    await widget._on_load()

    assert widget._agent.run_calls == 0
    await user.should_see("Please enter an IPTS number.")


async def test_iptstable_error_shows_message(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._agent.run_error = RuntimeError("no session")
    widget._input.value = "24703"

    await widget._on_load()

    assert _table(user).options["rowData"] == []
    await user.should_see("Could not load runs for IPTS-24703:")


async def test_iptstable_load_button_triggers_fetch(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._input.value = "24703"  # run_result defaults to empty

    user.find("Load").click()

    # Clicking Load runs the async handler end to end.
    await user.should_see("No runs found for IPTS-24703.")
    assert widget._agent.run_calls == 1


async def test_iptstable_load_is_guarded_while_busy(user: User) -> None:
    await user.open("/iptstable")
    widget = _widget(user)
    widget._input.value = "24703"
    widget._busy = True  # simulate a load already in flight

    await widget._on_load()

    # The guard short-circuits, so no overlapping fetch is issued.
    assert widget._agent.run_calls == 0
