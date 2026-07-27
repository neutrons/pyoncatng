# Tutorials

Runnable, self-contained examples of the `pyoncatng` NiceGUI widgets. Each
tutorial is a subfolder containing:

- `README.md`
- the code needed to run it (typically a `main.py` NiceGUI app).

Tutorials live outside the `pyoncatng` package and import the installed library just like any downstream app would.

## Running a tutorial

Each tutorial has a dedicated pixi task named `tutorial-<name>`:

```console
pixi run tutorial-login
```

Or run the script directly:

```console
python tutorials/login/main.py
```

## Available tutorials

| Tutorial | Description |
|----------| --- |
| `login`    | Sign in to ONCat with the `OncatLogin` widget (OAuth device-authorization flow). |
| `runtable` | Browse run data with the read-only `RunTable` widget (draggable columns, locked `run_number`). |
| `iptstable` | Fetch and browse an experiment's runs by IPTS number with the `IPTSTable` widget (requires sign-in). |

As new widgets are added (table, search, …), add a new subfolder here plus a
matching `tutorial-<name>` task in `pyproject.toml`.
