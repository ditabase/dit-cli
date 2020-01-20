"""Pytest unit tests"""

import os
from dit_cli.dit import validate_dit

DIT_DIR = os.path.join(os.path.dirname(__file__), 'dits/')
VALID_STR = 'dit is valid, no errors found'


def test_lengths():
    """Check that lengths.dit is valid"""
    assert is_file_valid('lengths.dit')


def test_basic():
    """Check that test.dit is valid"""
    assert is_file_valid('basic.dit')


def test_error_doc():
    """Test that the missing doc type error is correct"""
    assert is_error_valid(
        'error-doctype.dit', 'Found Header reads: <!DOCTYE dit xml>')


def test_error_json():
    """Test that a json parser type error is correct"""
    assert is_error_valid(
        'error-json.dit', '"json" is not currently supported.')


def get_file(file_name):
    """Helper to turn a test file name into the file"""
    with open(os.path.join(DIT_DIR, file_name)) as file_object:
        return file_object.read()


def is_file_valid(file_name: str) -> bool:
    """Helper to test the validation of a test file"""
    return validate_dit(get_file(file_name)) == VALID_STR


def is_error_valid(file_name: str, error: str) -> bool:
    """Helper to test the error returned by a dit"""
    return str(validate_dit(get_file(file_name))).find(error) != -1
