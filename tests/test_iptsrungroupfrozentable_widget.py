"""Tests for the IPTSRunGroupFrozenTable widget.

Unit tests on the construction validation, which need no UI context. The
widget tests that use NiceGUI's ``user`` simulation are added with the test page.
"""

import pytest

from pyoncatng.widgets.iptsrungroupfrozentable import _validate_construction
from pyoncatng.widgets.iptstable import DEFAULT_PROCESSING_VARIABLES

TITLE = ("Title", "datafiles.raw.metadata.entry.title")
START = ("Start Time", "datafiles.raw.metadata.entry.start_time")


def test_valid_construction_returns_pairs() -> None:
    assert _validate_construction([TITLE, [" Start Time ", " datafiles.raw.metadata.entry.start_time "]], "Title") == [
        TITLE,
        START,
    ]


def test_default_processing_variables_accept_title() -> None:
    assert _validate_construction(DEFAULT_PROCESSING_VARIABLES, "Title") == list(DEFAULT_PROCESSING_VARIABLES)


def test_group_by_must_be_a_label() -> None:
    with pytest.raises(ValueError, match="must be one of the processing_variables labels"):
        _validate_construction([TITLE, START], "Sample")


def test_group_by_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be one of the processing_variables labels"):
        _validate_construction([TITLE], "ID")


def test_id_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="'ID' is reserved"):
        _validate_construction([TITLE, ("ID", "datafiles.raw.metadata.entry.id")], "Title")


def test_duplicate_labels_are_rejected() -> None:
    with pytest.raises(ValueError, match="labels must be unique"):
        _validate_construction([TITLE, ("Title", "other.path")], "Title")


@pytest.mark.parametrize("value", [("Title",), ("Title", ""), ("Title", 1), "ab", None])
def test_malformed_pair_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="must be a .label, path. pair"):
        _validate_construction([value], "Title")
