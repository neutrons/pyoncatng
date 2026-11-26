=================
Build & Publish
=================

All the steps below are defined as Pixi tasks in ``pyproject.toml``.

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

Building Packages
=================

Conda packages are supported. Build one with:

.. code-block:: bash

   pixi run conda-build

The task takes the version from the Git tags and builds the package into the
``local-channel`` directory. It restores ``pyproject.toml`` afterwards.

Publishing Packages
===================

Conda packages are published to the `anaconda.org/neutrons
<https://anaconda.org/neutrons>`_ organization. To publish a package from your
machine, which requires permission to upload to the organization, run:

.. code-block:: bash

   pixi run conda-publish

The task builds the package and then uploads the ``.conda`` files of the repository
root. The GitHub workflow
``.github/workflows/test_and_deploy.yaml`` builds and verifies the package for
every pull request, and it uploads the package after the tests pass when a commit
is pushed to the ``next`` branch or a tag that starts with ``v`` is pushed.
