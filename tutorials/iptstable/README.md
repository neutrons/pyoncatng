# IPTSTable tutorial

Demonstrates the [`IPTSTable`](../../src/pyoncatng/widgets/iptstable.py) widget:
an IPTS input and a **Load** button over a read-only
[`RunTable`](../../src/pyoncatng/widgets/runtable.py). Enter an IPTS number and
the widget fetches that experiment's runs from ONCat (for SNS / USANS) and shows
one **row per run** with columns `ID`, `Title`, `Start Time`, and `Total Counts`.

Unlike the RunTable tutorial, this one fetches **live data**, so an ONCat
sign-in is required.

## Prerequisites

- The project's pixi environment (`pixi install`).
- An ONCat account (you sign in interactively via the login card on the page).

## Run it

```console
pixi run tutorial-iptstable
```

or directly, with options:

```console
python tutorials/iptstable/main.py --port 8080   # change the port
python tutorials/iptstable/main.py --native      # native desktop window
```

Then open the printed URL (default <http://127.0.0.1:8080>).

## What to try

1. **Sign in** — click **Connect** on the login card and approve the sign-in in
   your browser; the status indicator turns green.
2. **Load an experiment** — type an IPTS number (e.g. `24703`) and click
   **Load**. The table fills with that experiment's runs, most recent first.
3. **A bare number is enough** — `24703` is normalized to `IPTS-24703`.
4. **Errors show inline** — a non-existent IPTS number, or loading while
   disconnected, shows a message below the table instead of runs.

## Notes

- The widget receives the authenticated agent from the login card
  (`IPTSTable(agent=login.agent)`). It does not manage the connection itself.
- The displayed columns map to `run["id"]` and the raw-datafile metadata a run
  aggregates, under `datafiles.raw.metadata.entry.*` (`title`, `start_time`,
  `total_counts`). Adjust `COLUMN_SPEC` in `pyoncatng.widgets.iptstable` to show
  different metadata.
