"""pyoncatng: NiceGUI widgets for ONCAT login and data fetching."""

from pyoncatng.core.grouping import by_pv

try:
    from pyoncatng._version import __version__  # noqa: F401
except (ModuleNotFoundError, ImportError):
    __version__ = "0.0.1"

__all__ = ["__version__", "by_pv"]
