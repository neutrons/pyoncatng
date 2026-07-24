=========
pyoncatng
=========

``pyoncatng`` is a Python package that handles **login to** and **data fetching
from** `ONCAT <https://oncat.ornl.gov/>`_ (the ONCat data catalog), built on top
of the `pyoncat <https://oncat.ornl.gov/>`_ library.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   widgets
   tutorials

Getting Started
===============

This project is managed entirely with `Pixi <https://pixi.sh/>`_, a reproducible
and declarative environment manager. All build and packaging metadata lives in a
single ``pyproject.toml``.

1. Install Pixi
---------------

.. code-block:: bash

   curl -fsSL https://pixi.sh/install.sh | bash

2. Set up the environment
-------------------------

.. code-block:: bash

   pixi install

3. Explore available tasks
---------------------------

.. code-block:: bash

   pixi run

4. Development workflow
-----------------------

.. code-block:: bash

   pixi shell            # activate the environment
   pixi run test         # run the test suite
   ruff check .          # lint
   pip install --no-deps -e .   # editable install

Optional direnv integration
----------------------------

If a checkout has a local ``.envrc``, developers using
`direnv <https://direnv.net/>`_ can have the Pixi environment activated
automatically when entering the repository. The local ``.envrc`` used in this
checkout watches ``pixi.lock`` and evaluates Pixi's shell hook:

.. code-block:: bash

   watch_file pixi.lock
   eval "$(pixi shell-hook --frozen --change-ps1 false)"

This is only a local convenience. ``.envrc`` is ignored by Git, is not required
for normal development, and may differ between developers. Without ``direnv``,
use ``pixi shell`` or ``pixi run ...`` directly.

Testing
=======

.. code-block:: bash

   pixi run test

Documentation
=============

.. code-block:: bash

   pixi run build-docs

Build & Publish Packages
========================

Both PyPI and Conda packages are supported; all build and publishing steps are
defined as Pixi tasks (``pixi run pypi-build``, ``pixi run pypi-publish``,
``pixi run conda-build``, ``pixi run conda-publish``). Conda packages are
published to the `anaconda.org/neutrons <https://anaconda.org/neutrons>`_
organization.

License
=======

``pyoncatng`` is distributed under the terms of the
`GPL-3.0 <https://github.com/neutrons/pyoncatng/blob/main/LICENSE>`_ license.

=========================================
Indices and tables
=========================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
