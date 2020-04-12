"""Pytest unit tests"""


import os
import pytest

from dit_cli.cli import validate_dit
VALID_STR = 'dit is valid, no errors found'


@pytest.mark.short
@pytest.mark.parametrize("file_name,expected", [
    ('dits/comments1.dit', VALID_STR),
    ('dits/conflicts1.dit', VALID_STR),
    ('dits/conflicts2.dit', VALID_STR),
    ('dits/empty.dit', 'file is empty'),
    ('dits/escape1.dit', VALID_STR),
    ('dits/eval1.dit', VALID_STR),
    ('dits/eval2.dit', VALID_STR),
    ('dits/inheritance1.dit', VALID_STR),
    ('dits/list1.dit', VALID_STR),
    ('dits/list2.dit', VALID_STR),
    ('dits/misc1.dit', VALID_STR),
    ('dits/no-objects.dit', 'dit is valid, no objects to check'),
    ('dits/query1.dit', VALID_STR),
    ('dits/scripts1.dit', VALID_STR),
    ('dits/space3.dit', VALID_STR),
])
def test_validate(file_name, expected):
    result = validate_dit(get_file(file_name))
    assert result == expected


@pytest.mark.short
@pytest.mark.parametrize("file_name,expected", [
    ('fail/assigner1.dit', 'AssignError: Assigner "a" expected 1 args, got 2'),
    ('fail/assigner2.dit', 'AssignError: Undefined arg "garbage" for Assigner a'),
    ('fail/evaler1.dit', 'ValidationError<a>: This is a test error'),
    ('fail/namespace-att1.dit', 'VarError: Expected string "A.value", got "B"'),
    ('fail/namespace-att2.dit', 'VarError: Expected class "A", got string'),
    ('fail/namespace-att3.dit', 'VarError: Expected "A", got "C"'),
    ('fail/namespace-att4.dit', 'VarError: "A.value" expected a list'),
    ('fail/namespace-att5.dit', 'VarError: Expected string "A.value", got list'),
    ('fail/namespace-att6.dit', 'VarError: Expected class "A", got list'),
    ('fail/namespace-def1.dit', 'VarError: "A" is already defined (class)'),
    ('fail/namespace-def2.dit', 'VarError: "A" is already defined (object)'),
    ('fail/namespace-def3.dit', 'VarError: "A" is already defined (namespace)'),
    ('fail/namespace-def4.dit', 'VarError: "A" is already defined (assigner)'),
    ('fail/namespace-obj1.dit', 'VarError: Expected class "A", got string'),
    ('fail/namespace-obj2.dit', 'VarError: Expected class "A", got list'),
    ('fail/namespace-obj3.dit', 'VarError: Expected "A", got "B"'),
    ('fail/namespace-var1.dit', 'VarError: Undefined variable "does" in "does.not.exist"'),
    ('fail/node-ext1.dit', 'NodeError: Cannot extend String'),
    ('fail/node-ext2.dit', 'NodeError: Top level objects cannot be String'),
    ('fail/node-ext3.dit', 'NodeError: "B" already extends "A"'),
    ('fail/node-att1.dit', 'NodeError: "A" already has attribute "value"'),
    ('fail/node-print1.dit',
     'NodeError: "HopefullyThisWillNeverBeALanguage" does not exist in .dit-languages'),
    ('fail/node-val1.dit',
     'NodeError: "HopefullyThisWillNeverBeALanguage" does not exist in .dit-languages'),
    ('fail/node-recur1.dit', 'NodeError: Illegal recursive extension in class "A"'),
    ('fail/node-recur2.dit', 'NodeError: Illegal recursive attribution in class "A"'),
    ('fail/parser-class1.dit', 'ParseError: "extends" must come first, or not at all'),
    ('fail/parser-class2.dit', 'ParseError: Unexpected EOF while parsing class.'),
    ('fail/parser-class3.dit', 'ParseError: Unexpected EOF while parsing class.'),
    ('fail/parser-assign0.dit', 'ParseError: Unexpected EOF while parsing assignment.'),
    ('fail/parser-assign1.dit', 'ParseError: Closing "]" but no opening "["'),
    ('fail/parser-assign2.dit', 'ParseError: ")" expected, found instead "]"'),
    ('fail/parser-assign3.dit', 'ParseError: Closing ")" but no opening "("'),
    ('fail/parser-assign4.dit', 'ParseError: "]" expected, found instead ")"'),
    ('fail/parser-assign5.dit', 'ParseError: Expected ";" after assignment'),
    ('fail/parser-assign6.dit', 'ParseError: Expected ";" after assignment'),
    ('fail/parser-assign7.dit', 'ParseError: Expected "]"'),
    ('fail/parser-assign8.dit', 'ParseError: Expected ")"'),
    ('fail/parser-escape1.dit', 'ParseError: Missing closing sequence: }}'),
    ('fail/parser-escape2.dit', 'ParseError: Missing closing sequence: }}'),
    ('fail/parser-escape3.dit', 'ParseError: Missing closing sequence: \''),
    ('fail/parser-escape4.dit', 'ParseError: Missing closing sequence: "'),
    ('fail/parser-escape5.dit', 'ParseError: Missing closing sequence: \''),
    ('fail/parser-escape6.dit', 'ParseError: Missing closing sequence: "'),
    ('fail/parser-escape7.dit', 'ParseError: Unrecognized escape character: "\\q"'),
    ('fail/parser-comment1.dit', 'ParseError: Comment must end with newline'),
    ('fail/parser-import1.dit', 'ParseError: Expected ";" after import'),
    ('fail/parser-import2.dit', '''ParseError: Import failed, file not found
Path: "/not/a/real/link"'''),
    ('fail/parser-import3.dit', '''ParseError: Import failed, permission denied
Path: "/root/"'''),
    ('fail/parser-import4.dit', '''ParseError: Import failed, HTTP Error 500: Domain Not Found
URL: "https://notadomain.githubusercontent.com/"'''),
    ('fail/parser-import5.dit', '''ParseError: Import failed, HTTP Error 404: Not Found
URL: "https://raw.githubusercontent.com/isaiahshiner/dits/master/dits/ClearlyNotADit.dit"'''),
    ('fail/parser-import6.dit', '''ParseError: Import failed, file is <!DOCTYPE html>.
Load raw text, not webpage.'''),
    ('fail/parser-tokens1.dit',
     "ParseError: Found no tokens: ['{', '(', ';', '=', '//', 'import']"),
])
def test_raise(file_name, expected):
    result = validate_dit(get_file(file_name)).args[0]
    assert result == expected


@pytest.mark.short
def test_code_error():
    result = validate_dit(get_file('fail/evaler2.dit')).args[0]
    assert result.startswith('''CodeError: A Javascript Validator
Error message follows:

/tmp/dit/A-Validator.js:3
        const a = 2;
              ^

SyntaxError: Identifier 'a' has already been declared''')


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
])
def test_examples(file_name, expected):
    result = validate_dit(get_file(file_name))
    assert result == expected


def get_file(file_name):
    """Helper to turn a test file name into the file"""
    with open(os.path.join(os.path.dirname(__file__), file_name)) as file_object:
        return file_object.read()
