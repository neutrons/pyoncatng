# Widgets

Reusable NiceGUI widgets provided by `pyoncatng`. Each widget can be dropped into
any NiceGUI page; see the [Tutorials](tutorials.md) for runnable examples.

## OncatLogin

### Using the widget

```{figure} media/login-widget-overview.png
:alt: ONCat login widget in row and column orientations, disconnected and connected states, plus sign-in dialog
:width: 100%

The login widget with its buttons side by side or stacked, in the disconnected
(empty circle) and connected (green circle) states, and the sign-in dialog.
```

The login card signs you in to ONCat through your browser; it has no username
or password fields.

1. Click **Connect**. A dialog shows a link and a one-time code.
2. Open the link, sign in with your ONCat credentials, and approve the request.
   Enter the code if you are asked for it.
3. The circle turns green when you are connected. Hover over the circle to see
   the connection status in words.

Click **Log out** to end the session; the circle becomes an empty ring again. A
yellow circle means that a sign-in, status check, or log-out is in progress.
Errors appear as short messages at the edge of the page. Your session is
remembered by the browser, so you usually stay signed in when you open the page
again.

### Implementation Details

`OncatLogin` drives the OAuth 2.0 Device Authorization Grant. Supply either an
explicit `client_id` or a `key`, which looks up the client ID as `<key>_id` in
the `[login.oncat]` section of the configuration file. Arrange the
**Connect** and **Log out** buttons with `orientation="row"` (side by side, the
default) or `orientation="column"` (stacked).

Once connected, the authenticated `pyoncat.ONCat` agent is available as
`agent`, for example to pass to [`IPTSTable`](#ipts-run-table). Check the state
with `is_connected`, or register a callback with `on_connection_change`, which
receives `True` or `False`. The token is stored per browser in
`app.storage.user`, so set a `storage_secret` in `ui.run` to keep sessions
across restarts; without one the widget still works but does not persist the
token. See the [login tutorial](tutorials.md) for a runnable example.

```{eval-rst}
.. autoclass:: pyoncatng.widgets.login.OncatLogin
   :members:
```

## Run table

### Using the table

```{figure} media/runtable.png
:alt: RunTable widget showing one row per run and one column per processing variable
:width: 100%

The run table, with one row per run and one column per processing variable
(here `run_number`, `run_title`, `start_time`, `duration`, `counts`, and
`LambdaRequest`).
```

The run table lists runs, one per row, with one column per run property.

Select runs by clicking: click a row to select it, `Ctrl`/`Cmd` + click to add
or remove individual rows, and `Shift` + click to select a contiguous range. The
application then uses the selected runs.

Columns can be reordered by dragging their headers, except the leftmost column
(the run number, by default), which stays in place. The table's contents are
fixed: cells cannot be edited, clicking a header does not sort the rows, and
rows cannot be dragged, so the runs keep the order the application gave them.

### Implementation Details

`RunTable` is a `ui.aggrid` subclass. Fetching the data from ONCat is out of
scope for the widget: a caller builds the ordered list of column names and the
rows (a list of per-run dicts keyed by processing-variable name) and passes
them to the constructor. The column name, header label, and row-dict key are
all the same string. The `key_column` (`run_number` by default) is locked to
the leftmost position and must be one of the columns. `set_rows` replaces the
displayed rows, keeping their order.

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

### Using the table

```{figure} media/iptstable.png
:alt: IPTSTable widget showing an IPTS input, a Load button, and a run table with ID, Title, Start Time, and Total Counts columns
:width: 100%

The IPTS run table showing the runs of IPTS-24703 on SNS / USANS, one row per
run.
```

The IPTS run table lists the runs of one experiment. Type the experiment's IPTS
number, either as a bare number such as `24703` or as `IPTS-24703`, and click
**Load** or press `Enter`. The table then shows one row per run, most recent
first, with the run `ID` in the leftmost column.

You must be signed in to ONCat first, usually with the [login card](#oncatlogin)
on the same page. If the runs cannot be loaded, for example because you are not
signed in or the IPTS number does not exist, a message appears below the table.

Select, reorder, and browse the rows as in the [run table](#run-table).

### Implementation Details

`IPTSTable` is a `ui.card` that composes an IPTS input and a **Load** button
over a [`RunTable`](#run-table). It fetches the experiment's runs from ONCat for
a fixed facility and instrument (`"SNS"` and `"USANS"` by default) and normalizes
a bare number such as `24703` to `IPTS-24703`. The default columns are `ID`,
`Title`, `Start Time`, and `Total Counts`. The `ID` column is always first. Pass
ordered `(display label, ONCat metadata path)` pairs through
`processing_variables` to choose the remaining columns; for example:

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

## Grouped run table

### Using the table

```{figure} media/runGroupFrozenTable.png
:alt: RunGroupFrozenTable widget with Title, First, Last, and Size columns and the Sample A 25C group selected, above a table listing that group's four runs
:width: 100%

The grouped run table from the tutorial, with runs grouped by title. The
selected group, `Sample A 25C`, holds four runs; the table below it lists them.
```

The grouped run table summarizes a list of runs by showing **one row per group**
of related runs, for example all runs that share the same title. Each row has
these columns:

- The grouping value, such as the run title. This column is always the leftmost
  one.
- `First` and `Last` — the smallest and largest run numbers in the group. The
  runs in a group are not necessarily consecutive, so the group does not
  contain every run number between `First` and `Last`.
- `Size` — the number of runs in the group.

Select groups to work with their runs: click a row to select it, `Ctrl`/`Cmd` +
click to add or remove individual rows, and `Shift` + click to select a
contiguous range. The application then uses the runs of the selected groups;
the [RunGroupFrozenTable tutorial](tutorials.md), for example, lists them in a
second table.

Columns other than the leftmost one can be reordered by dragging their headers.
The table's contents are fixed: cells cannot be edited, clicking a header does
not sort the rows, and rows cannot be dragged.

### Implementation Details

`RunGroupFrozenTable` groups run dictionaries by a key and shows one row per
group, where [`RunTable`](#run-table) shows one row per run. Unlike `RunTable`,
it cannot be changed after it is created: it is a `ui.card` that wraps a private
`RunTable`, and it does not expose the methods that replace the table's data
(such as `set_rows()`, `options`, or `run_grid_method()`). The wrapped table
keeps every `RunTable` interaction rule: read-only cells, a locked first column,
movable remaining columns, no row sorting, no row dragging, and multi-row
selection.

```python
rows = [
    {"ID": 123, "Title": "A"},
    {"ID": 124, "Title": "A"},
    {"ID": "125", "Title": "B"},
    {"ID": 129, "Title": "A"},
]
table = RunGroupFrozenTable(rows=rows, group_by="Title")
table.groups  # ((0, 1, 3), (2,))
```

Constructor arguments:

- `rows` — a non-empty sequence of run dictionaries. Each must contain
  `group_by` and `run_idkey`.
- `group_by` — the run-dict key used to group rows. Rows whose values are equal
  form one group; comparison is exact, with no whitespace or case
  normalization. Values must be hashable.
- `run_idkey` — the run-dict key holding the run ID, used for the `First` and
  `Last` columns. Defaults to `"ID"`. Values must be `int`, or `str` values that
  `int()` accepts; `str` values are cast to `int`.

The constructor raises `ValueError` if `rows` is empty, a row is missing
`group_by`, a `group_by` value is not hashable, or a run ID is missing or cannot
be converted to `int`.

The widget stores **read-only deep copies** of the input rows in `rows`. Each
row is a read-only mapping (`types.MappingProxyType`), nested dicts are
read-only mappings, and nested lists are stored as tuples. Changing the caller's
list or dicts afterwards has no effect, and the caller's run dictionaries are
never mutated or enriched. `groups` is a `tuple[tuple[int, ...], ...]`: one
tuple of ascending indexes into `rows` per group, ordered by the first
occurrence of the group's value. `rows`, `groups`, `group_by`, and `run_idkey`
are read-only properties.

The visible columns are `[group_by, "First", "Last", "Size"]`. Each grid row
also carries an internal `"_group_index"` field, the index of its group in
`groups`. It is hidden and is not a column.

Register a callback with `on_selection_change` and read the selection with the
async accessors `selected_group_indexes()`, `selected_groups()`, and
`selected_source_rows()`; `rows_for_group(group_index)` returns the rows of any
one group (see the [RunGroupFrozenTable tutorial](tutorials.md) for a runnable
version):

```python
async def on_change() -> None:
    print("selected groups:", await table.selected_group_indexes())
    print("selected run IDs:", [row["ID"] for row in await table.selected_source_rows()])

table.on_selection_change(on_change)
```

```{eval-rst}
.. autoclass:: pyoncatng.widgets.rungroupfrozentable.RunGroupFrozenTable
   :members:
```
