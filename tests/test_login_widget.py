"""Widget tests for OncatLogin using NiceGUI's in-process `user` simulation."""

from nicegui import ui
from nicegui.testing import User


async def test_disconnected_without_token(fake_agent, user: User) -> None:
    fake_agent.tokened = False
    await user.open("/key")
    await user.should_see("state: disconnected")


async def test_resolves_client_id_from_key(fake_agent, user: User) -> None:
    fake_agent.tokened = False
    await user.open("/key")
    assert fake_agent.built["client_id"] == "0123456489"
    assert fake_agent.built["oncat_url"] == "https://oncat.ornl.gov"


async def test_resolves_explicit_client_id(fake_agent, user: User) -> None:
    fake_agent.tokened = False
    await user.open("/client")
    assert fake_agent.built["client_id"] == "0123456489"


async def test_requires_client_id_or_key(user: User) -> None:
    await user.open("/noargs")
    await user.should_see("error:")


async def test_connect_shows_verification_then_cancel(fake_agent, user: User) -> None:
    fake_agent.tokened = False
    fake_agent.login_mode = "cancel"
    await user.open("/key")
    await user.should_see("state: disconnected")

    user.find("Connect").click()
    # The verification link and one-time code are surfaced in the dialog.
    await user.should_see("https://oncat.example/verify?user_code=WXYZ-1234")
    await user.should_see("WXYZ-1234")

    user.find("Cancel").click()
    # Cancelling is silent and returns to the disconnected state.
    await user.should_see("state: disconnected")
    assert fake_agent.login_calls == 1


async def test_connected_with_valid_token(fake_agent, user: User) -> None:
    fake_agent.tokened = True
    fake_agent.facility_error = None
    await user.open("/key")
    # The stored session is probed on mount and reported as connected.
    await user.should_see("state: connected")
    assert fake_agent.login_calls == 0


async def test_logout(fake_agent, user: User) -> None:
    fake_agent.tokened = True
    fake_agent.facility_error = None
    await user.open("/key")
    await user.should_see("state: connected")

    user.find("Log out").click()
    await user.should_see("state: disconnected")
    assert fake_agent.logout_calls == 1


async def test_column_orientation_renders(fake_agent, user: User) -> None:
    fake_agent.tokened = False
    await user.open("/column")
    # The column branch builds and both buttons render.
    await user.should_see(kind=ui.button, content="Connect")
    await user.should_see(kind=ui.button, content="Log out")


async def test_invalid_orientation(user: User) -> None:
    await user.open("/badorientation")
    await user.should_see("error:")
