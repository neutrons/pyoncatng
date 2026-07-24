"""NiceGUI main file executed by the `user` fixture to register test pages.

``nicegui.testing`` runs this module via ``runpy`` under the name ``__main__``,
so ``ui.run`` is reached (a ``storage_secret`` is supplied so ``app.storage.user``
works during the simulation). The page bodies build the widget lazily, at
request time, so a test can patch the agent before opening a page.
"""

from nicegui import ui

from pyoncatng.widgets.login import OncatLogin


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


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(storage_secret="test secret")
