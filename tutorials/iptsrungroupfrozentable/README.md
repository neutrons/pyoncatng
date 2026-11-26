# IPTSRunGroupFrozenTable tutorial

Demonstrates the [`IPTSRunGroupFrozenTable`](../../src/pyoncatng/widgets/iptsrungroupfrozentable.py)
widget: an IPTS input and a **Load** button over a read-only table that shows
**one row per group** of runs. Enter an IPTS number and the widget fetches that
experiment's runs from ONCat (for SNS / USANS), groups the runs that share a
`Title`, and shows the group's `Title`, `First` and `Last` run IDs, and `Size`.
Below the table, the page lists the runs of the selected groups.

Unlike the RunGroupFrozenTable tutorial, this one fetches **live data**, so an
ONCat sign-in is required.

## Prerequisites

- The project's pixi environment (`pixi install`).
- An ONCat account (you sign in interactively via the login card on the page).

## Run it

```console
pixi run tutorial-iptsrungroupfrozentable
```

or directly, with options:

```console
python tutorials/iptsrungroupfrozentable/main.py --port 8080   # change the port
python tutorials/iptsrungroupfrozentable/main.py --native      # native desktop window
```

Then open the printed URL (default <http://127.0.0.1:8080>).

## What to try

1. **Sign in** — click **Connect** on the login card and approve the sign-in in
   your browser; the status indicator turns green.
2. **Load an experiment** — type an IPTS number (e.g. `24703`) and click
   **Load**. The table fills with one row per `Title`.
3. **Check the groups** — a group with `Size` greater than 1 holds several runs
   with the same title. `First` and `Last` are its smallest and largest run IDs.
4. **Select groups** — click a row to select it, **Ctrl/Cmd + click** to toggle
   individual rows, **Shift + click** to select a contiguous range, and press
   **Space** to toggle the focused row.
5. **See the source runs** — the caption lists the selected group indexes, and
   the bottom table lists the runs of the selected groups.
6. **Reload** — click **Load** again, even for the same IPTS. The selection is
   cleared, and the caption and the bottom table are emptied.
7. **Errors show inline** — a non-existent IPTS number, or loading while
   disconnected, shows a message below the table and an empty table.

## Notes

- The widget receives the authenticated agent from the login card
  (`IPTSRunGroupFrozenTable(agent=login.agent, group_by="Title")`). It does not
  manage the connection itself.
- `group_by` must be one of the processing-variable labels (`Title`,
  `Start Time`, or `Total Counts` by default). `ID` cannot be used.
- The page reads the selection through `on_selection_change` and the async
  `selected_group_indexes` and `selected_source_rows` accessors. The callback
  also runs after every **Load** of an IPTS number, when the selection is cleared.
- Group and row indexes are valid only until the next **Load**, because new
  runs move existing rows and groups.
