"""Helpers for grouping run rows, free of NiceGUI imports.

A grouping function receives one row (the read-only mapping of one run) and returns the key of the group that the run
belongs to.
"""

from typing import Any, Callable, Mapping

Row = Mapping[str, Any]


def _as_group_key(value: Any) -> str:
    """Convert the result of a grouping function to a group key: ``None`` becomes ``""``, otherwise ``str(value)``."""
    return "" if value is None else str(value)


def by_pv(pv: str) -> Callable[[Row], str]:
    """Return a grouping function that groups runs by the value of one processing variable.

    Runs without a value for the processing variable (``None``) and runs whose value is the empty string share the
    group whose key is ``""``. Whitespace is not stripped.

    Parameters
    ----------
    pv
        Key of the row that holds the processing variable.

    Raises
    ------
    ValueError
        If ``pv`` is not a non-empty string. The error is raised when ``by_pv`` is called, not when the returned
        function is called. The returned function raises ``KeyError`` for a row without the key.
    """
    if not isinstance(pv, str) or not pv:
        raise ValueError(f"pv must be a non-empty string, got {pv!r}.")

    def grouping_function(row: Row) -> str:
        return _as_group_key(row[pv])

    grouping_function.__qualname__ = f"by_pv({pv!r})"
    return grouping_function
