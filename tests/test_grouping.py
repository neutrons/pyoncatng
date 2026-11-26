import subprocess
import sys

import pytest

from pyoncatng import by_pv
from pyoncatng.core.grouping import _as_group_key


def test_as_group_key_returns_a_string_as_is():
    assert _as_group_key("Sample A") == "Sample A"


@pytest.mark.parametrize("value", [None, ""])
def test_as_group_key_gives_the_empty_string_for_none_and_empty(value):
    assert _as_group_key(value) == ""


@pytest.mark.parametrize(("value", "expected"), [(1, "1"), (2.5, "2.5"), ((1, 2), "(1, 2)")])
def test_as_group_key_applies_str_to_other_values(value, expected):
    assert _as_group_key(value) == expected


def test_by_pv_returns_the_value_as_a_string():
    assert by_pv("Title")({"Title": "Sample A"}) == "Sample A"
    assert by_pv("Temperature")({"Temperature": 300}) == "300"


def test_by_pv_does_not_strip_whitespace():
    assert by_pv("Title")({"Title": " Sample A "}) == " Sample A "


def test_by_pv_gives_the_empty_string_for_none_and_empty():
    grouping_function = by_pv("Title")
    assert grouping_function({"Title": None}) == ""
    assert grouping_function({"Title": ""}) == ""


@pytest.mark.parametrize("pv", ["", 3, None])
def test_by_pv_rejects_an_invalid_name_when_called(pv):
    with pytest.raises(ValueError, match="pv must be a non-empty string"):
        by_pv(pv)


def test_by_pv_raises_key_error_for_a_missing_key():
    with pytest.raises(KeyError):
        by_pv("Title")({"ID": 1})


def test_by_pv_names_the_returned_function():
    assert by_pv("Title").__qualname__ == "by_pv('Title')"


def test_importing_the_package_does_not_load_nicegui_or_the_widgets():
    code = (
        "import sys, pyoncatng; from pyoncatng import by_pv; "
        "sys.exit('nicegui' in sys.modules or 'pyoncatng.widgets' in sys.modules)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
