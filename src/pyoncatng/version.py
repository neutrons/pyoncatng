"""Module to load the version created by versioningit

Will fall back to a default if pyoncatng is not installed."""


def get_version() -> None:
    """Get the version of the package"""
    try:
        from ._version import __version__
    except ModuleNotFoundError:
        __version__ = "0.0.1"
    print(f"pyoncatng version: {__version__}")
