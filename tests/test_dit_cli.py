"""Pytest unit tests"""


import os
import pytest

from dit_cli.cli import validate_dit
VALID_STR = 'dit is valid, no errors found'


@pytest.mark.short
@pytest.mark.parametrize("file_name,expected", [
    ('dits/conflicts1.dit', VALID_STR),
    ('dits/conflicts2.dit', VALID_STR),
    ('dits/escape1.dit', VALID_STR),
    ('dits/eval1.dit', VALID_STR),
    ('dits/inheritance1.dit', VALID_STR),
    ('dits/list1.dit', VALID_STR),
    ('dits/misc1.dit', VALID_STR),
    ('dits/query1.dit', VALID_STR),
    ('dits/space3.dit', VALID_STR),
])
def test_validate(file_name, expected):
    result = validate_dit(get_file(file_name))
    assert result == expected


@pytest.mark.short
@pytest.mark.parametrize("file_name,expected", [
    ('fail/assign1.dit', 'AssignError: Assigner "a" expected 1 args, got 2'),
    ('fail/assign2.dit', 'AssignError: Undefined arg "garbage" for Assigner a'),
])
def test_raise(file_name, expected):
    result = validate_dit(get_file(file_name)).args[0]
    assert result == expected


@pytest.mark.long
@pytest.mark.parametrize("file_name,query,expected,", [
    ('dits/escape1.dit', 'print(e.escape1)', '''"Let's"'''),
    ('dits/query1.dit', 'print(name)', '"Jane Emily Marie Doe"'),
    ('dits/query1.dit', 'name',
     '''{"class":"FullName","print":"Jane Emily Marie Doe","givenName":{"class":"Name","print":"Jane","value":"Jane"},"middleNames":[{"class":"Name","print":"Emily","value":"Emily"},{"class":"Name","print":"Marie","value":"Marie"}],"familyName":{"class":"Name","print":"Doe","value":"Doe"}}'''),
])
def test_query(file_name, query, expected):
    result = validate_dit(get_file(file_name), query_string=query)
    assert result == expected


@pytest.mark.long
@pytest.mark.parametrize("file_name,expected", [
    ('../examples/fruit.dit', VALID_STR),
    ('../examples/import.dit', VALID_STR),
    ('../examples/length.dit', VALID_STR),
    ('../examples/name.dit', VALID_STR),
    ('../examples/school.dit', VALID_STR),
])
def test_examples(file_name, expected):
    result = validate_dit(get_file(file_name))
    assert result == expected


def get_file(file_name):
    """Helper to turn a test file name into the file"""
    with open(os.path.join(os.path.dirname(__file__), file_name)) as file_object:
        return file_object.read()
