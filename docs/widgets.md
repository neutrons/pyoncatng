# Widgets

Reusable NiceGUI widgets provided by `pyoncatng`. Each widget can be dropped into
any NiceGUI page; see the [Tutorials](tutorials.md) for runnable examples.

## OncatLogin

```{figure} media/login-widget-overview.png
:alt: ONCat login widget in row and column orientations, disconnected and connected states, plus sign-in dialog
:width: 100%

The login widget supports arranging the "connect" and "log out" buttons as
`orientation="row"` or `orientation="column"`.
The status indicator shows disconnected (empty circle) and connected states (green circle),
and the sign-in dialog provides the browser approval link and device code.
```

```{eval-rst}
.. autoclass:: pyoncatng.widgets.login.OncatLogin
   :members:
```

## Run table

```{figure} media/runtable.png
:alt: RunTable widget showing one row per run and one column per processing variable
:width: 100%

The run table renders one row per run and one column per processing variable
(here `run_number`, `run_title`, `start_time`, `duration`, `counts`, and
`LambdaRequest`). Rows are selectable — click to select one, `Ctrl`/`Cmd` +
click to toggle individual rows, and `Shift` + click to select a contiguous
range. Otherwise the grid is locked down: cells are read-only, header clicks do
not sort the rows (so the supplied run order is preserved), and rows cannot be
dragged. Columns can be reordered by dragging their headers, except the key
column (`run_number` by default), which is locked to the leftmost position.
```

Fetching the data from ONCat is out of scope for the widget: a caller builds the
ordered list of column names and the rows (a list of per-run dicts keyed by
processing-variable name) and passes them to the constructor.

React to the selection by registering a callback with `on_selection_change` and
reading the selected rows with the inherited async `get_selected_rows` (see the
[RunTable tutorial](tutorials.md) for a runnable version):

```python
table = RunTable(columns=columns, rows=rows)

async def on_change() -> None:
    selected = await table.get_selected_rows()
    print("selected run numbers:", [row["run_number"] for row in selected])

table.on_selection_change(on_change)
```

```{eval-rst}
.. autoclass:: pyoncatng.widgets.runtable.RunTable
   :members:
```

## IPTS run table

```{figure} media/iptstable.png
:alt: IPTSTable widget showing an IPTS input, a Load button, and a run table with ID, Title, Start Time, and Total Counts columns
:width: 100%

The IPTS run table: enter an IPTS number and click **Load** to fetch that
experiment's runs (here IPTS-24703 on SNS / USANS), one row per run.
```

`IPTSTable` composes an IPTS input and a **Load** button over a
[`RunTable`](#run-table). The user types an IPTS number (a bare number such as
`24703`, which is normalized to `IPTS-24703`) and clicks **Load**; the widget
fetches that experiment's runs from ONCat for a fixed facility/instrument
(`"SNS"`/`"USANS"` by default) and renders one row per run with the columns
`ID`, `Title`, `Start Time`, and `Total Counts` (most recent run first).
The `ID` column is always first. Pass ordered `(display label, ONCat metadata
path)` pairs through `processing_variables` to choose the remaining columns;
for example:

```python
IPTSTable(
    agent=login.agent,
    processing_variables=[("Title", "datafiles.raw.metadata.entry.title")],
)
```

The authenticated agent is supplied by the caller — typically
`OncatLogin.agent` — so the widget does not create or manage the connection. The
agent may be disconnected when passed; problems (no live session, a non-existent
IPTS number, or a request failure) are reported in an inline message area below
the table. Blocking ONCat I/O runs off the event loop.

Rows are selectable just as in [`RunTable`](#run-table); `IPTSTable` exposes the
selection through its own `selected_rows()` (async) and `on_selection_change()`
methods, which delegate to the underlying table.

```{eval-rst}
.. autoclass:: pyoncatng.widgets.iptstable.IPTSTable
   :members:
```
