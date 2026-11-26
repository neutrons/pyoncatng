=================
Build & Publish
=================

The documentation steps below are defined as Pixi tasks in ``pyproject.toml``.

Building the Documentation Locally
==================================

Build the HTML pages and open ``docs/_build/index.html`` in a browser:

.. code-block:: bash

   pixi run build-docs

Run the examples of the documentation, which are the ``testcode`` blocks, with:

.. code-block:: bash

   pixi run test-docs

Remove the build output with ``pixi run clean-docs``.

How Read the Docs Builds the Documentation
==========================================

The published documentation at `pyoncatng.readthedocs.io
<https://pyoncatng.readthedocs.io/>`_ is built by `Read the Docs
<https://readthedocs.org/>`_ with the configuration in ``.readthedocs.yaml``. It
installs Pixi, runs ``pixi install``, and then builds the HTML pages with
``sphinx-build -T -b html docs``. This is the command behind ``pixi run
build-docs``, so a local build previews what is published.

Building and Publishing Packages
================================

Conda packages are built and published by the GitHub workflow
``.github/workflows/test_and_deploy.yaml``, so there is no need to build or
publish them by hand. For every pull request, the workflow builds the package
and verifies that it installs and imports. When a commit is pushed to the
``next`` branch, or a tag that starts with ``v`` is pushed, and the tests pass,
the workflow uploads the package to the `anaconda.org/neutrons
<https://anaconda.org/neutrons>`_ organization. The version of the package comes
from the Git tags.
