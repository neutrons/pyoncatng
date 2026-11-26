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

## Run Table

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
all the same string. Each row is a flat dict, so a column name that contains a
dot, such as `motor.readX`, is a plain key of the row, not a path into nested
data. The `key_column` (`run_number` by default) is locked to
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

## IPTS Run Table

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

## Grouped Run Table

### Using the table

```{figure} media/runGroupFrozenTable.png
:alt: RunGroupFrozenTable widget with Title, First, Last, and Size columns and the Sample A 25C group selected, above a table listing that group's four runs
:width: 100%

The grouped run table from the tutorial, with runs grouped by title. The
selected group, `Sample A 25C`, holds four runs; the table below it lists them.
```

The grouped run table summarizes a list of runs by showing **one row per group**
of related runs, for example all runs that share the same title. How the runs are
grouped is described in {doc}`Grouping Runs <grouping>`. Each row has these
columns:

- The group key, such as the run title. This column is always the leftmost one.
  A blank cell means that the runs of the group have no value.
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

`RunGroupFrozenTable` groups run dictionaries with a grouping function and shows
one row per group, where [`RunTable`](#run-table) shows one row per run. Unlike `RunTable`,
it cannot be changed after it is created: it is a `ui.card` that wraps a private
`RunTable`, and it does not expose the methods that replace the table's data
(such as `set_rows()`, `options`, or `run_grid_method()`). The wrapped table
keeps every `RunTable` interaction rule: read-only cells, a locked first column,
movable remaining columns, no row sorting, no row dragging, and multi-row
selection.

```python
from pyoncatng import by_pv

rows = [
    {"ID": 123, "Title": "A"},
    {"ID": 124, "Title": "A"},
    {"ID": "125", "Title": "B"},
    {"ID": 129, "Title": "A"},
]
table = RunGroupFrozenTable(rows=rows, grouping_function=by_pv("Title"), group_column="Title")
table.groups  # ((0, 1, 3), (2,))
table.group_keys  # ("A", "B")
```

Constructor arguments:

- `rows` — a non-empty sequence of run dictionaries. Each must contain
  `run_idkey`.
- `grouping_function` — a function that receives the read-only mapping of one
  run and returns the key of its group. It is called once per run. Rows with
  equal keys form one group; comparison is exact, with no whitespace or case
  normalization. A key that is not a string is converted: `None` becomes the
  empty string and any other value goes through `str()`. `by_pv(name)` builds
  the function that groups by the value of one key.
- `group_column` — the name of the leftmost column, which shows the key of each
  group. It must be a non-empty string other than `First`, `Last`, `Size`, and
  `_group_index`.
- `run_idkey` — the run-dict key holding the run ID, used for the `First` and
  `Last` columns. Defaults to `"ID"`. Values must be `int`, or `str` values that
  `int()` accepts; `str` values are cast to `int`.

The constructor raises `ValueError` if `rows` is empty, `grouping_function` is not
callable or fails for a run (the message names the run), `group_column` is
invalid, or a run ID is missing or cannot be converted to `int`.

The widget stores **read-only deep copies** of the input rows in `rows`. Each
row is a read-only mapping (`types.MappingProxyType`), nested dicts are
read-only mappings, and nested lists are stored as tuples. Changing the caller's
list or dicts afterwards has no effect, and the caller's run dictionaries are
never mutated or enriched. `groups` is a `tuple[tuple[int, ...], ...]`: one
tuple of ascending indexes into `rows` per group, ordered by the first
occurrence of the group's key. `group_keys` is a `tuple[str, ...]` with the key
of each group, aligned with `groups`: it is the text in the first cell of the
group's row. `rows`, `groups`, `group_keys`, `grouping_function`, `group_column`,
and `run_idkey` are read-only properties.

The visible columns are `[group_column, "First", "Last", "Size"]`. Each grid row
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

## IPTS Grouped Run Table

### Using the table

```{figure} media/iptsRunGroupFrozenTable.png
:alt: IPTSRunGroupFrozenTable widget with an IPTS input, a Load button, and a table of run groups with Title, First, Last, and Size columns, with the first group selected, above a table listing that group's runs
:width: 100%

The IPTS grouped run table from the tutorial, showing the runs of IPTS-24703
on SNS / USANS grouped by title. The selected group, `Align:0 stop rheometer`,
holds eight runs; the table below it lists them.
```

The IPTS grouped run table loads the runs of one experiment and shows them
grouped, one row per group. Type the experiment's IPTS number, either as a bare
number such as `24703` or as `IPTS-24703`, and click **Load** or press `Enter`.
Runs that have the same group key, for example the same title, form one group.
The application chooses the grouping when it creates the widget, either by the
value of one variable or by a value computed from the run; see
{doc}`Grouping Runs <grouping>`. Runs that have no value for the variable form
one group whose leftmost cell is blank. The groups are ordered by their most
recent run.

The columns are those of the [grouped run table](#grouped-run-table): the
group key in the leftmost column, then `First`, `Last`, and `Size`. Select
groups by clicking a row, `Ctrl`/`Cmd` + click to add or remove individual rows,
`Shift` + click to select a contiguous range, or `Space` to add or remove the row
that has the keyboard focus. Move the focus with the arrow keys.

Every **Load** of an IPTS number replaces the table and clears the selection,
including a reload of the same IPTS. The application is told that the selection
changed, so what it shows for the selected groups is cleared too. If the IPTS
field is empty, **Load** only shows a message and leaves the table and the
selection as they are.

You must be signed in to ONCat first, usually with the [login card](#oncatlogin)
on the same page. If the runs cannot be loaded, for example because you are not
signed in or the IPTS number does not exist, a message appears below an empty
table. The same happens if the IPTS has no runs.

### Implementation Details

`IPTSRunGroupFrozenTable` is a `ui.card` that composes an IPTS input and a
**Load** button with a [`RunGroupFrozenTable`](#grouped-run-table), as
[`IPTSTable`](#ipts-run-table) composes them with a `RunTable`. Each **Load**
fetches the complete run list of the experiment and replaces the inner
`RunGroupFrozenTable` with a new instance. The inner table is never changed, and
it is not public. The helpers of `IPTSTable` (`normalize_ipts`,
`build_projection`, and `rows_from_runs`) are reused as they are, so the facility,
the instrument, the sort order, and the messages match `IPTSTable`.

Constructor arguments:

- `agent` — the authenticated ONCat agent, typically `OncatLogin.agent`. It may
  be disconnected when passed.
- `grouping_function` — a function that receives the read-only mapping of one
  run, with `ID` and the labels of `processing_variables` as keys, and returns
  the key of its group; for example `by_pv("Title")`. See
  [`RunGroupFrozenTable`](#grouped-run-table) for how the results are converted.
- `group_column` — the name of the leftmost column, which shows the key of each
  group. `ID`, `First`, `Last`, and `Size` are reserved and cannot be used,
  because the first is the run identifier and the others are columns of the
  grouped table.
- `facility` and `instrument` — default to `"SNS"` and `"USANS"`.
- `processing_variables` — ordered `(display label, ONCat metadata path)` pairs,
  as in `IPTSTable`. The default labels are `Title`, `Start Time`, and
  `Total Counts`.

The constructor raises `ValueError` if `processing_variables` is malformed,
contains the label `ID` or a repeated label, `grouping_function` is not callable,
or `group_column` is empty or a reserved name. An error in the function, such as a
mistyped label in `by_pv`, is not detected at construction: the first **Load**
reports it in the message area, naming the row that failed. All
arguments are fixed for the lifetime of the widget.

The widget stores only what must outlive one inner table: the callbacks
registered with `on_selection_change`. It registers them again on each new inner
table, and the live selection stays in the grid. After every **Load** of an IPTS
number, it also calls each callback with a selection-changed event, because the
new table has no selection. A callback that takes no arguments is called without
them. Otherwise it receives an event whose `sender` is the widget. This holds for
every event, whether the user changed the selection or a **Load** cleared it, so
the inner table is never passed to a callback. After a **Load**, `args` is empty;
for a change made by the user, `args` holds the arguments that the grid sent.

The members that read the table always use the current inner table. They have the
names and meanings of `RunGroupFrozenTable`: the properties `rows`, `groups`,
`group_keys`, `grouping_function`, and `group_column`, the async methods `selected_group_indexes()`, `selected_groups()`, and
`selected_source_rows()`, and the method `rows_for_group()`. Here `rows` holds one
read-only row per run, keyed by the display labels and `ID`.

Group indexes and row indexes are valid only until the next **Load**, because new
runs move existing rows and groups.

```python
from pyoncatng import by_pv

table = IPTSRunGroupFrozenTable(agent=login.agent, grouping_function=by_pv("Title"), group_column="Title")

async def on_change() -> None:
    print("selected groups:", await table.selected_group_indexes())
    print("selected run IDs:", [row["ID"] for row in await table.selected_source_rows()])

table.on_selection_change(on_change)
```

See the [IPTSRunGroupFrozenTable tutorial](tutorials.md) for a runnable version.

```{eval-rst}
.. autoclass:: pyoncatng.widgets.iptsrungroupfrozentable.IPTSRunGroupFrozenTable
   :members:
```
