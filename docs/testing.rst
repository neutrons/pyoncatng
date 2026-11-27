Testing
=======

Running the Tests
-----------------

.. code-block:: bash

   pixi run test

Testing Without Signing In to ONCat
-----------------------------------

The tests never contact ONCat. Two fake agents stand in for ``pyoncat.ONCat``, and each has a fixture that wires it
in place of the real agent:

* ``FakeAgent`` (fixture ``fake_agent``) is scripted by the test: set ``run_result`` to the runs that ``Run.list``
  returns, or ``run_error`` to make it fail.
* ``RecordedAgent`` (fixture ``recorded_agent``) answers ``Run.list`` from recordings of real ONCat responses, kept
  in ``tests/data/oncat``.

A test that needs realistic runs asks for the runs of an instrument and IPTS, as the widgets do:

.. code-block:: python

   from fakes import RecordedAgent

   agent = RecordedAgent()
   runs = agent.Run.list(
       facility="SNS",
       instrument="USANS",
       experiment="IPTS-24703",
       projection=["datafiles.raw.metadata.entry.title"],
       sort_direction="DESCENDING",
   )
   runs[0]["id"]  # the highest run number
   runs[0].get("datafiles.raw.metadata.entry.title")

The runs are ``pyoncat.ONCatObject`` instances. Each holds only the projected paths, plus ``id``, ``object``, and
``type``, as the real service returns them. A path that a run does not have gives ``None`` from ``get``. A path
that the recording does not hold raises ``ValueError``: a recording stores the projection it was made with, and only
those paths and the paths below them can be requested. The runs
are sorted by ``id`` according to ``sort_direction``. The arguments ``sort_by``, ``page_size``, and ``since_id`` are
not supported and raise ``TypeError``.

Missing Recordings
------------------

A request for an experiment without a recording raises an error that names the facility, instrument, and
experiment. The error is a ``pyoncat.NotFoundError``, so a mistyped IPTS fails the test instead of looking like an
experiment without runs. The same error is raised when the experiment is not written exactly as ``IPTS-<number>``,
for example the bare number ``24703``, because ONCat finds no runs for it. A widget that accepts a bare number must
add the prefix before it calls ``Run.list``.

The real service answers an unknown experiment with an empty list, and an unknown instrument or facility with
``pyoncat.NotFoundError``. To test how a widget handles an experiment without runs, create the agent with
``RecordedAgent(on_missing="empty")``: a missing recording then returns an empty list.

Recording an Experiment
-----------------------

To add an experiment, sign in to ONCat and record it:

.. code-block:: bash

   pixi run record-oncat SNS USANS IPTS-24703

Write the experiment with its ``IPTS-`` prefix. A bare number such as ``24703`` is refused, so that it cannot be
taken for a run number.

The command prints a URL and a code for the sign-in, then fetches the metadata of each run, but no neutron event
data. It reports the number of runs and the size of the file. Recording an experiment again replaces its file. An
experiment without runs is refused, because ONCat also answers an unknown experiment with an empty list; add
``--allow-empty`` to record it anyway.

By default the command records ``datafiles.raw.metadata``, which holds every processing variable of a run. Use
``--projection`` to record other paths, for example a top-level field such as ``location`` that a widget requests.

A recording is a compressed JSON file in ``tests/data/oncat`` (about 1.2 MB for the 278 runs of IPTS-24703). Its
name is a hash of the facility, instrument, and IPTS, so that the experiment is not obvious from a directory
listing. This hides the name only; it is not encryption. The name of a recording is computed with:

.. code-block:: python

   from recordings import recording_name

   recording_name("SNS", "USANS", "IPTS-24703")

A recording holds the metadata of the experiment but leaves out the neutron event data and
leaves out the ``user1``, ``user2``, ... metadata entries.
Record only experiments whose metadata may be published.

What the Fake Does Not Simulate
-------------------------------

The recorded agent does not simulate authentication or token refresh, pagination, or sorting by anything other than
the run number. Use ``FakeAgent`` to script a failure such as an expired session.

Trying the Widgets Offline
--------------------------

The test application serves pages that use the recordings, so the widgets can be tried without signing in. Start it:

.. code-block:: bash

   pixi run python tests/nicegui_main.py

The application has no page at its root address, so the message ``http://127.0.0.1:8080/ not found`` in the output
(and a "not found" page if a browser opens there) is expected. Open one of these pages in a browser instead:

* ``http://localhost:8080/iptstable-recorded`` shows the runs of an experiment in a table.
* ``http://localhost:8080/iptsrungroupfrozentable-recorded`` shows the same runs grouped by title.

Enter ``IPTS-24703`` in the ``IPTS:`` field and press Load. The widgets also accept the bare number ``24703``. An
IPTS without a recording shows the message "Could not load runs for IPTS-...: No recording for ...".
