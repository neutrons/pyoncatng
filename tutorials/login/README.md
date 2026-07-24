# ONCat login tutorial

Demonstrates the [`OncatLogin`](../../src/pyoncatng/widgets/login.py) widget: a
NiceGUI card that signs in to ONCat using the OAuth 2.0 **Device Authorization
Grant** (browser-based sign-in — no username/password field). Once connected,
the authenticated `pyoncat.ONCat` agent is available for data queries and the
widget emits connection-state changes to the rest of the page.

## Prerequisites

- An ORNL / ONCat account (you approve the sign-in in your browser).
- Network access to `https://oncat.ornl.gov`.
- The project's pixi environment (`pixi install`).

## Run it

```console
pixi run tutorial-login
```

or directly, with options:

```console
python tutorials/login/main.py --port 8080          # change the port
python tutorials/login/main.py --native             # native desktop window
python tutorials/login/main.py --storage-secret ... # your own cookie secret
```

Then open the printed URL (default <http://127.0.0.1:8080>).

## What to expect

1. The page shows an **ONCat** card with a status line ("ONCat: Disconnected")
   and **Connect to ONCat** / **Log out of ONCat** buttons.
2. Click **Connect to ONCat**. A dialog appears with a verification link and a
   one-time user code.
3. Open the link, sign in with your ORNL credentials, and approve the request.
4. The status flips to a green **ONCat: Connected**, and the page's readout
   shows "Connected to ONCat".
5. Click **Log out of ONCat** to revoke the session; the status returns to red
   **ONCat: Disconnected**.

## Notes

- The token is persisted per browser via NiceGUI's `app.storage.user`, so a
  valid session is detected on the next launch without re-authenticating.
- On first run the tutorial creates `~/.pyoncatng/configuration.ini` from the
  bundled template (holding the ONCat URL and the public client ID).
