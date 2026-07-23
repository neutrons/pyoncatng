# pyoncatng

/ _Under construction_ /

## Project Overview

`pyoncatng` is a Python package that handles **login to** and **data fetching from
[ONCAT](https://oncat.ornl.gov/)** (the ONCat data catalog), built on top of the
[`pyoncat`](https://oncat.ornl.gov/) library.

It provides **[NiceGUI](https://nicegui.io/) widgets** for building web UIs against ONCAT, including:

- a **login widget** that drives the ONCAT authentication flow, and
- a **table widget** to be populated with data fetched from ONCAT.

It is the NiceGUI-based sibling of [`pyoncatqt`](https://github.com/neutrons/pyoncatqt/),
which offers the same capabilities as Qt widgets.

## Getting Started

This project is managed entirely with [Pixi](https://pixi.sh/), a reproducible and declarative
environment manager. All build and packaging metadata lives in a single `pyproject.toml`.

### 1. Install Pixi

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

### 2. Set up the environment

```bash
pixi install
```

### 3. Explore available tasks

```bash
pixi run
```

### 4. Development workflow

```bash
pixi shell            # activate the environment
pixi run test         # run the test suite
ruff check .          # lint
pip install --no-deps -e .   # editable install
```

### Optional direnv integration

If a checkout has a local `.envrc`, developers using [`direnv`](https://direnv.net/) can
have the Pixi environment activated automatically when entering the repository. The local
`.envrc` used in this checkout watches `pixi.lock` and evaluates Pixi's shell hook:

```bash
watch_file pixi.lock
eval "$(pixi shell-hook --frozen --change-ps1 false)"
```

This is only a local convenience. `.envrc` is ignored by Git, is not required for normal
development, and may differ between developers. Without `direnv`, use `pixi shell` or
`pixi run ...` directly.

## Testing

```bash
pixi run test
```

## Documentation

```bash
pixi run build-docs
```

## Build & Publish Packages

Both PyPI and Conda packages are supported; all build and publishing steps are defined as Pixi tasks
(`pixi run pypi-build`, `pixi run pypi-publish`, `pixi run conda-build`, `pixi run conda-publish`).
Conda packages are published to the [anaconda.org/neutrons](https://anaconda.org/neutrons) organization.

## License

`pyoncatng` is distributed under the terms of the
[GPL-3.0](https://github.com/neutrons/pyoncatng/blob/main/LICENSE) license.
