"""NiceGUI main file executed by the `user` fixture to register test pages.

``nicegui.testing`` runs this module via ``runpy`` under the name ``__main__``,
so ``ui.run`` is reached (a ``storage_secret`` is supplied so ``app.storage.user``
works during the simulation). The page bodies build the widget lazily, at
request time, so a test can patch the agent before opening a page.
"""

from fakes import FakeAgent
from nicegui import ui

from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.login import OncatLogin
from pyoncatng.widgets.runtable import RunTable

# Column set and generated rows for the RunTable pages. Fetching from ONCat is
# out of scope, so the tests supply the data directly.
RUNTABLE_COLUMNS = ["run_number", "run_title", "start_time", "LambdaRequest"]


def _sample_rows(count: int = 3) -> list[dict]:
    """Generate `count` run rows keyed by the RunTable columns."""
    return [
        {
            "run_number": 47775 + i,
            "run_title": f"Title {i}",
            "start_time": f"2023-01-01 0{i}:00",
            "LambdaRequest": 5400 + i,
        }
        for i in range(count)
    ]


def _with_readout(login: OncatLogin) -> None:
    """Mirror the widget's connection state into a visible label for tests.

    The widget itself shows status only via a hover tooltip (not visible to the
    `user` simulation), so exercise the public `on_connection_change` contract.
    """
    readout = ui.label("state: disconnected")
    login.on_connection_change(
        lambda connected: readout.set_text(f"state: {'connected' if connected else 'disconnected'}")
    )


@ui.page("/key")
def key_page() -> None:
    _with_readout(OncatLogin(key="test"))


@ui.page("/client")
def client_page() -> None:
    _with_readout(OncatLogin(client_id="0123456489"))


@ui.page("/column")
def column_page() -> None:
    _with_readout(OncatLogin(key="test", orientation="column"))


@ui.page("/badorientation")
def badorientation_page() -> None:
    try:
        OncatLogin(key="test", orientation="diagonal")
    except ValueError as err:
        ui.label(f"error: {err}")


@ui.page("/noargs")
def noargs_page() -> None:
    try:
        OncatLogin()
    except ValueError as err:
        ui.label(f"error: {err}")


@ui.page("/runtable")
def runtable_page() -> None:
    RunTable(columns=RUNTABLE_COLUMNS, rows=_sample_rows())


@ui.page("/runtable-empty")
def runtable_empty_page() -> None:
    RunTable(columns=RUNTABLE_COLUMNS)


@ui.page("/runtable-keylast")
def runtable_keylast_page() -> None:
    # run_number listed last on purpose: the widget must still put it first.
    RunTable(columns=["run_title", "start_time", "run_number"], rows=_sample_rows())


@ui.page("/runtable-badkey")
def runtable_badkey_page() -> None:
    try:
        RunTable(columns=["run_title", "start_time"])  # no run_number
    except ValueError as err:
        ui.label(f"error: {err}")


@ui.page("/iptstable")
def iptstable_page() -> None:
    # Build with a fresh fake agent; tests reach it via the widget element
    # (``IPTSTable._agent``) to script its ``Run.list`` before clicking Load.
    IPTSTable(agent=FakeAgent(), facility="SNS", instrument="USANS")


@ui.page("/iptstable-custom")
def iptstable_custom_page() -> None:
    IPTSTable(
        agent=FakeAgent(),
        facility="SNS",
        instrument="USANS",
        processing_variables=[
            (" Title ", " datafiles.raw.metadata.entry.title "),
            (" Total Counts ", " datafiles.raw.metadata.entry.total_counts "),
        ],
    )


@ui.page("/iptstable-reserved-label")
def iptstable_reserved_label_page() -> None:
    try:
        IPTSTable(
            agent=FakeAgent(),
            processing_variables=[(" ID ", "datafiles.raw.metadata.entry.title")],
        )
    except ValueError as error:
        ui.label(f"error: {error}")


@ui.page("/iptstable-duplicate-label")
def iptstable_duplicate_label_page() -> None:
    try:
        IPTSTable(
            agent=FakeAgent(),
            processing_variables=[
                ("Title", "datafiles.raw.metadata.entry.title"),
                ("Title", "datafiles.raw.metadata.entry.start_time"),
            ],
        )
    except ValueError as error:
        ui.label(f"error: {error}")


@ui.page("/iptstable-invalid-processing-variables")
def iptstable_invalid_processing_variables_page() -> None:
    cases = [
        ("shape", [("Title",)]),
        ("type", [("Title", None)]),
        ("empty-label", [(" ", "datafiles.raw.metadata.entry.title")]),
        ("empty-path", [("Title", "\t")]),
        ("non-iterable", 42),
    ]
    for name, processing_variables in cases:
        try:
            IPTSTable(agent=FakeAgent(), processing_variables=processing_variables)
        except ValueError as error:
            ui.label(f"{name}: {error}")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(storage_secret="test secret")
