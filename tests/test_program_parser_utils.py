from algodisco.toolkit.program_parser.utils import (
    extract_code_by_bottom_up,
    extract_code_from_response,
)


def test_extract_code_by_bottom_up_returns_none_when_no_code_found():
    assert extract_code_by_bottom_up("This is just some explanation.", "python") is None


def test_extract_code_by_bottom_up_returns_none_when_truncation_exhausts_code():
    response = """
Here is some broken code:

def f(
"""

    assert extract_code_by_bottom_up(response, "python") is None


def test_extract_code_by_bottom_up_returns_code_when_extraction_succeeds():
    response = """
Here is some code:

import os

def f():
    return 1

Extra explanation.
"""

    assert (
        extract_code_by_bottom_up(response, "python")
        == "import os\n\ndef f():\n    return 1\n"
    )


def test_extract_code_from_response_returns_none_when_no_code_found():
    assert extract_code_from_response("This is just some explanation.", "python") is None
