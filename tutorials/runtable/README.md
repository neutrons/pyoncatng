# RunTable tutorial

Demonstrates the [`RunTable`](../../src/pyoncatng/widgets/runtable.py) widget: a
selectable, otherwise read-only NiceGUI table (built on AG Grid) that shows one
**row per run** and one **column per processing variable**. No ONCat sign-in is
required — the page generates sample run data locally so you can focus on the
widget's behavior.

## Prerequisites

- The project's pixi environment (`pixi install`).

## Run it

```console
pixi run tutorial-runtable
```

or directly, with options:

```console
python tutorials/runtable/main.py --port 8080   # change the port
python tutorials/runtable/main.py --native      # native desktop window
```

Then open the printed URL (default <http://127.0.0.1:8080>).

## What to try

1. **Select rows** — click a row to select it, **Ctrl/Cmd + click** to toggle
   individual rows, and **Shift + click** to select a contiguous range. The
   caption under the table lists the selected run numbers, updated live via
   `RunTable.on_selection_change` + the inherited async `get_selected_rows`.
2. **Reorder columns** — grab a column header and drag it left or right.
3. **run_number stays first** — it is locked to the leftmost position, so no
   other column can be dragged ahead of it and it cannot itself be moved.
4. **Header clicks do not sort** — the run order is fixed to the order the rows
   were supplied in.
5. **Cells are read-only** — double-clicking a cell will not edit its value.
6. **Rows cannot be dragged.**

## Notes

- Fetching data from ONCat is intentionally out of scope here. In a real
  application you would build the `rows` (a list of per-run dicts keyed by
  processing-variable name) from an ONCat query and pass them, along with the
  ordered list of column names, to `RunTable(...)`.
