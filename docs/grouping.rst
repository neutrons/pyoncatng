=============
Grouping Runs
=============

Purpose
=======

An experiment often has runs the user wants to group according to one (or more) processing variables (PV).
The :doc:`grouped run tables <widgets>` show **one row per group** of related runs
instead of one row per run. Each row shows the key of the group, the smallest and
largest run number in the group (``First`` and ``Last``), and the number of runs
(``Size``). You select groups, and the application then works with all the runs
of the selected groups.

The application decides which runs belong together when it creates the table.
Two arguments describe the grouping:

``grouping_function``
   A function that receives one run and returns the key of its group. Runs with
   the same key form one group.

``group_column``
   The name of the leftmost column, which shows the key of each group.

Grouping by a Processing Variable
=================================

To group the runs by the value of one processing variable, such as the title,
use ``by_pv``. It builds the grouping function for you.
In the example below, the table groups the runs by the value of the ``Title`` PV.

.. code-block:: python

   from pyoncatng import by_pv
   from pyoncatng.widgets.iptsrungroupfrozentable import IPTSRunGroupFrozenTable

   IPTSRunGroupFrozenTable(agent=login.agent, grouping_function=by_pv("Title"), group_column="Title")

The text of the variable is the key, exactly as it is: capital letters and
spaces make a difference. This is what ``by_pv`` returns for a run:

.. testcode::

   from pyoncatng import by_pv

   group_key = by_pv("Title")
   print(repr(group_key({"ID": 1, "Title": "Sample A 25C"})))
   print(repr(group_key({"ID": 2, "Title": None})))

.. testoutput::

   'Sample A 25C'
   ''

If the name does not match a column of the table, for example ``by_pv("Subject")``
for a table that has no ``Subject`` column, the table cannot group the runs.
The IPTS table reports this in a message area just
below the table widget, the first time you click **Load**, and names the row that failed.

Grouping by a Computed Value
============================

A grouping function can compute the key from the run in any way. It receives the
run as a read-only mapping, with one entry per column of the table, and returns
the key. This function groups the runs by the first word of the title, so that
``Sample X 25C`` and ``Sample X 50C`` fall in one group called ``Sample``:

.. code-block:: python

   IPTSRunGroupFrozenTable(
       agent=login.agent,
       grouping_function=lambda row: (row["Title"] or "").split(" ")[0],
       group_column="Sample",
   )

A run can have no value for a variable. The title is then ``None``, and the
function above handles it with ``or ""``. The same function written as a regular
function can be tried without a table:

.. testcode::

   def first_word(row):
       return (row["Title"] or "").split(" ")[0]

   print(repr(first_word({"ID": 1, "Title": "Sample X 25C"})))
   print(repr(first_word({"ID": 2, "Title": None})))

.. testoutput::

   'Sample'
   ''

The Group Column and Group Keys
===============================

``group_column`` represents the value returned by the grouping function, for instance, ``"Title"``.
It can be any text, and it does not have to match the variable that
the function reads. For instance, ``by_pv("Title")`` with ``group_column="Sample"`` is accepted,
and the column storing the titles is then headed ``Sample``. It cannot be ``First``, ``Last``,
``Size``, or ``_group_index``, which the reserved names that table uses itself. The IPTS table does
not accept ``ID`` either.

The table also offers ``group_keys``, the key of each group in the order of the
rows. ``group_keys[i]`` is the text in the first cell of row ``i``, so you can
name the selected groups without calling the function again:

.. code-block:: python

   names = [table.group_keys[index] for index in await table.selected_group_indexes()]

Blank Groups
============

A blank cell in the leftmost column means that the runs of that group have **no
value**. All such runs form one group. The grouping function should return text.
A key that is not text is converted: ``None`` becomes blank and any other value
becomes its text. Two runs whose keys have the same text therefore share a group,
for example the number ``1`` and the text ``"1"``, or ``None`` and the empty text.
