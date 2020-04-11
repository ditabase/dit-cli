"""Runs code in any language, given correct configs"""

import os
import subprocess
from typing import Any
from copy import copy

from dit_cli import CONFIG
from dit_cli.node import Node
from dit_cli.parser import parse_expr, find_name
from dit_cli.dataclasses import Expression, Attribute, EvalContext
from dit_cli.exceptions import ValidationError, CodeError


def validate_object(obj: Node):
    """Run all relevant validators for this object.
    First all of its attributes, then all extended validators,
    then the validator of this object itself"""

    # Note: the evaler system is highly recursive.
    # Almost everything here calls itself and/or things which call
    # higher, back up the recursive tree
    # which results in circular/indirect recursion.
    # Base case methods which have no recursion whatsoever are
    # _ser_string and _run_code.

    # Recurse anything this object's attributes first
    for attr in obj.attrs:
        if attr.class_ != 'String':
            for list_item in _traverse(attr.data):  # In case it's a list
                validate_object(list_item)

    # Then deal with this object itself
    eva = EvalContext(obj, obj.extends[0], obj.namespace)
    _run_validator(eva)


def _traverse(item):
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    try:
        if isinstance(item, str):
            yield item
        else:
            for i in iter(item):
                for j in _traverse(i):
                    yield j
    except TypeError:
        yield item


def _run_validator(eva: EvalContext):
    # Recurse to the highest inherited class validator first
    for extend in eva.class_.extends:
        new_eva = copy(eva)
        new_eva.class_ = extend
        _run_validator(new_eva)

    # Then run this validator
    if eva.class_.validator:
        eva.lang = CONFIG[eva.class_.validator['lang']]
        base_code = eva.class_.validator['code']
        # Skip validator if the is no actual code
        if base_code.isspace() or not base_code:
            return
        code = _prep_code(eva, base_code)
        result = _run_code(eva.class_.name, 'Validator', code, eva.lang)
        if result.casefold() != 'true':
            raise ValidationError(result, eva.obj.name)


def _run_print(eva: EvalContext) -> str:
    # If a validator needed a print, find out how to print that object

    if eva.class_.print is None:
        return _ser_obj(eva)
    elif eva.class_.print['class_']:
        eva.class_ = eva.class_.print['class_']
        return _run_print(eva)
    elif eva.class_.print['expr']:
        expr = Expression(eva.namespace, eva.class_,
                          eva.obj, eva.class_.print['expr'])
        attr = eva.class_.namespace.read(expr)
        return _ser_attribute(eva, attr)
    else:
        # Run code, similar structure to running code in the validator,
        # which means we indirectly recurse _prep_code.
        # We also need to make a new eva, to avoid making
        # mutable changes to the old one.
        print_eva = copy(eva)
        print_eva.lang = CONFIG[eva.class_.print['lang']]
        base_code = eva.class_.print['code']
        # Skip validator if the is no actual code
        if base_code.isspace() or not base_code:
            return eva.lang['null_type']
        code = _prep_code(print_eva, base_code)
        value = _run_code(print_eva.class_.name, 'Print', code, print_eva.lang)
        return _ser_str(value, eva.lang)


def _prep_code(eva: EvalContext, code: str) -> str:
    # Replace all @@ dit escape sequences with variables
    start = 0
    while True:
        escape = code.find('@@', start)
        if escape == -1:
            break
        if code[escape:escape + 4] == '@@@@':
            code = code[:escape] + code[escape + 2:]  # Keep only one @@
            start = escape + 2
            continue
        if code[escape:escape + 3] == '@@@':  # Leave the first @
            escape += 1

        if code[escape + 2:escape + 8] == 'print(':
            query = code[escape + 2:code.find(')') + 1]
        else:
            query = find_name(code[escape + 2:])

        # Starts the serialization recursion chain
        value = serialize(eva, query)
        start = escape + len(value)

        code = code[:escape] + value + code[escape + 2 + len(query):]

    return code


def serialize(eva: EvalContext, query: str) -> str:
    """Convert a query sequence into a
    string representation of that variable"""
    if eva.lang is None:
        eva.lang = CONFIG[CONFIG['general']['serializer']]

    if query[:6] == 'print(':
        eva.print_ = True
        query = query[6:-1]
    else:
        # Always set to False in case mutable changes to this eva
        # have set it to True. Could also create new eva's at
        # the correct places. This seems simplier.
        eva.print_ = False

    expr = Expression(eva.namespace, eva.class_, eva.obj, parse_expr(query))
    result = eva.namespace.read(expr)
    if isinstance(result, Node):
        return _handle_new_obj(eva, result)
    else:
        # The only other possible return is an attribute
        return _ser_attribute(eva, result)


def _ser_attribute(eva: EvalContext, attr: Attribute) -> str:
    if attr is None:
        return eva.lang['null_type']
    elif attr.list_:
        new_eva = copy(eva)
        new_eva.class_ = attr.class_
        return _ser_list(new_eva, attr.data)
    elif attr.class_ == 'String':
        return _ser_str(attr.data, eva.lang)
    else:
        return _handle_new_obj(eva, attr.data)


def _ser_str(str_: str, lang: dict) -> str:
    # The only base case in the entire serialization system
    if lang['str_escape'] in str_:
        str_ = str_.replace(
            lang['str_escape'], lang['str_escape'] + lang['str_escape'])

    if lang['str_open'] in str_:
        str_ = str_.replace(
            lang['str_open'], lang['str_escape'] + lang['str_open'])

    if lang['str_open'] != lang['str_close'] and lang['str_close'] in str_:
        str_ = str_.replace(
            lang['str_close'], lang['str_escape'] + lang['str_close'])

    if '\n' in str_:
        str_ = str_.replace('\n', lang['str_newline'])

    if '\t' in str_:
        str_ = str_.replace('\t', lang['str_tab'])

    return lang['str_open'] + str_ + lang['str_close']


def _ser_list(eva: EvalContext, item: Any) -> str:
    if isinstance(item, list):
        if len(item) == 0:
            return eva.lang['list_open'] + eva.lang['list_close']
        value = eva.lang['list_open']
        for i in item:
            # Serialize any depth of list by recursing
            value += _ser_list(eva, i)
            value += eva.lang['list_delimiter']
        # Replace last comma with ]
        value = value[:-1] + eva.lang['list_close']
        return value
    else:
        if eva.class_ == 'String':
            return _ser_str(item, eva.lang)
        else:
            return _handle_new_obj(eva, item)


def _ser_obj(eva: EvalContext) -> str:
    # Basically serialize like JSON, which works in javascript and python,
    # and could be made to work anywhere, although more customization in
    # the future is likely.
    value = eva.lang['obj_open']

    def field(identifier: str, value: str) -> str:
        return eva.lang['str_open'] + identifier + eva.lang['str_close'] + \
            eva.lang['obj_colon'] + value + eva.lang['obj_delimiter']

    # This information is redundant.
    # It could be added back conditionally, but removed entirely for now.
    # value += field('name', _ser_str(obj.name, lang))
    value += field('class', _ser_str(eva.class_.name, eva.lang))
    if eva.class_.print is not None:
        value += field('print', _run_print(eva))
    for attr in eva.obj.attrs:
        value += field(attr.name, _ser_attribute(eva, attr))

    # Replace last comma with }
    value = value[:-1] + eva.lang['obj_close']
    return value


def _run_code(name: str, purpose: str, code: str, lang: dict) -> str:
    """Write the code to a file based on the specified language.
    Then run code and get result using the subprocess.run command."""
    path = _get_file_path(name, purpose, lang['file_extension'])
    file_string = lang['function_string'] + lang['call_string']
    file_string = file_string.replace(r'\n', '\n')
    file_string = file_string.replace(r'\t', '\t')
    file_string = file_string.replace('@@CODE', code)

    with open(path, 'w') as code_file:
        code_file.write(file_string)

    cmd = [lang['path'], path]
    try:
        # TODO: Subprocess is the slowest part of the project.
        # Fix this before anything else
        output = subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        raise CodeError(error, name, purpose, lang)

    raw = output.stdout.decode()
    begin = 'begin--'
    end = '--end'
    return raw[raw.find(begin) + len(begin):raw.find(end)]


def _handle_new_obj(eva: EvalContext, obj: Node) -> str:
    new_eva = copy(eva)
    new_eva.obj = obj
    new_eva.class_ = new_eva.obj.extends[0]
    new_eva.namespace = new_eva.obj.namespace

    if new_eva.print_:
        return _run_print(new_eva)
    else:
        return _ser_obj(new_eva)


def _get_file_path(name: str, purpose: str, ext: str) -> str:
    """Generate file name and path to file"""
    file_name = name + '-' + purpose + '.' + ext
    return os.path.join(CONFIG['general']['tmp_dir'], file_name)
