# RunGroupFrozenTable tutorial

Demonstrates the [`RunGroupFrozenTable`](../../src/pyoncatng/widgets/rungroupfrozentable.py)
widget: a read-only NiceGUI table that groups run dictionaries by a key (here
`Title`) and shows **one row per group**, with the columns `Title`, `First`,
`Last`, and `Size`. No ONCat sign-in is required — the page generates sample
run data locally so you can focus on the widget's behavior.

## Prerequisites
- The project's pixi environment (`pixi install`).

## Run it

```console
pixi run tutorial-rungroupfrozentable
```

or directly, with options:

```console
python tutorials/rungroupfrozentable/main.py --port 8080   # change the port
python tutorials/rungroupfrozentable/main.py --native      # native desktop window
```

Then open the printed URL (default <http://127.0.0.1:8080>).

## What to try

1. **Read the summary columns** — `First` and `Last` are the smallest and
   largest run IDs in a group, and `Size` is the number of runs in the group.
   Runs with the same title are not consecutive, so `First`–`Last` is not a
   range of the group's runs.
2. **Select groups** — click a row to select it, **Ctrl/Cmd + click** to toggle
   individual rows, and **Shift + click** to select a contiguous range. The
   caption lists the selected group indexes (from `selected_group_indexes`), and
   the table below shows the source runs of those groups (from
   `selected_source_rows`).
3. **Reorder columns** — drag a column header left or right. `Title` is locked
   to the leftmost position.
4. **Header clicks do not sort**, **cells are read-only**, and **rows cannot be
   dragged**, as in `RunTable`.

## Notes

- The widget cannot be changed after it is created: it stores read-only deep
  copies of the input rows, and it does not expose methods that replace the
  table's data.
- Fetching data from ONCat is intentionally out of scope here. In a real
  application you would build the `rows` (a list of per-run dicts) from an
  ONCat query and pass them to `RunGroupFrozenTable(...)`.
