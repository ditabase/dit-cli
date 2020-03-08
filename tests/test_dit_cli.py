"""Pytest unit tests"""

import os
from dit_cli.cli import validate_dit

DIT_DIR = os.path.join(os.path.dirname(__file__), 'dits/')
VALID_STR = 'dit is valid, no errors found'


def test_classroom():
    result = validate_dit(get_file('classroom.dit'))
    assert result == VALID_STR


def test_extension():
    result = validate_dit(get_file('extension.dit'))
    assert result == VALID_STR


def test_fruits():
    result = validate_dit(get_file('fruits.dit'), 'fav.value')
    assert result == '"kiwi"'


def test_lengths():
    result = validate_dit(get_file('lengths.dit'))
    assert result == VALID_STR


def test_multiple_inheritance():
    result = validate_dit(get_file('multiple_inheritance.dit'))
    assert result == VALID_STR


def test_name():
    result = validate_dit(get_file('name.dit'), 'print(myName)')
    assert result == '"Hi! My name is Isaiah Leopold Koser Shiner"'


def test_syntax_enums():
    result = validate_dit(get_file('syntax_enums.dit'))
    assert result == VALID_STR


def test_validator():
    result = validate_dit(get_file('syntax_enums.dit'))
    assert result == VALID_STR


def get_file(file_name):
    """Helper to turn a test file name into the file"""
    with open(os.path.join(DIT_DIR, file_name)) as file_object:
        return file_object.read()
