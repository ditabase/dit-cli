"""Runs code in any language, given correct configs"""

import os
import subprocess

from dit_cli import CONFIG
from dit_cli.tree import Node, Tree
from dit_cli.parser import parse_variable, find_name
from dit_cli.exceptions import ValidationError, CodeError


def validate_object(obj: Node, tree: Tree):
    """Run all relevant validators for this object.
    First everything it contains, then all extended validators,
    then the validator of this object itself"""

    # Note: the evaler system is highly recursive.
    # Almost everything here calls itself and/or things which call
    # higher, back up the recursive tree
    # which results in circular/indirect recursion.
    # Base case methods which have no recursion whatsoever are
    # _ser_string and _run_code.

    # Recurse anything this object contains first
    for contain in obj.contains:
        if contain['id_'] != -1:
            for list_item in _traverse(contain['data']):  # In case it's a list
                validate_object(list_item, tree)

    # Then deal with this object itself
    _run_validator(obj, tree.nodes[obj.extends[0]], tree)


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


def _run_validator(obj: Node, class_: Node, tree: Tree):
    # Recurse to the highest inherited class validator first
    for extend in class_.extends:
        _run_validator(obj, tree.nodes[extend], tree)

    # Then run this validator
    if class_.validator:
        lang = CONFIG[class_.validator['lang']]
        code = _prep_code(obj, tree, class_.validator['code'], lang)
        result = _run_code(class_, 'Validator', code, lang)
        if result.casefold() != 'true':
            raise ValidationError(result, obj.name)


def _run_print(obj: Node, class_: Node, caller_lang: dict, tree: Tree) -> str:
    # If a validator needed a print, find out how to print that object
    if class_.print is None:
        return _ser_obj(obj, caller_lang, tree, False)
    elif class_.print['variable'] is not None:
        if class_.print['id_'] is not None:
            return _run_print(obj, tree.nodes[class_.print['id_']],
                              caller_lang, tree)
        else:
            contain = tree.get_contain(class_.print['variable'],
                                       class_=class_, obj=obj)
            return _ser_contain(contain, caller_lang, tree, True)
    else:
        # Run code, similar structure to running code in the validator,
        # which means we indirectly recurse _prep_code.
        print_lang = CONFIG[class_.print['lang']]
        code = _prep_code(obj, tree, class_.print['code'], print_lang)
        print_value = _run_code(class_, 'Print', code, print_lang)
        return _ser_str(print_value, caller_lang)


def _prep_code(obj: Node, tree: Tree, code: str, lang: dict) -> str:
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
            raw_var = code[escape + 2:code.find(')') + 1]
        else:
            raw_var = find_name(code[escape + 2:])

        # Starts the serialization recursion chain
        value = serialize(raw_var, tree, class_=tree.nodes[obj.extends[0]],
                          obj=obj, lang=lang)
        start = escape + len(value)

        code = code[:escape] + value + code[escape + 2 + len(raw_var):]

    return code


def serialize(var: str, tree: Tree, class_: Node = None, obj: Node = None,
              lang: dict = CONFIG[CONFIG['general']['serializer']]) -> str:
    """Convert a variable sequence into a
    string representation of that variable"""
    print_ = False
    if var[:6] == 'print(':
        print_ = True
        var = var[6:-1]

    variable = parse_variable(var)
    result = tree.get_contain(variable, class_=class_, obj=obj)
    if isinstance(result, Node):
        if print_:
            class_ = tree.nodes[result.extends[0]]
            return _run_print(result, class_, lang, tree)
        else:
            return _ser_obj(result, lang, tree, print_)
    else:
        return _ser_contain(result, lang, tree, print_)


def _ser_contain(contain, lang: dict, tree: Tree, print_: bool) -> str:
    if contain is None:
        return lang['null_type']
    elif contain['list_']:
        return _ser_list(contain['id_'], contain['data'], lang, tree, print_)
    elif contain['id_'] == -1:
        return _ser_str(contain['data'], lang)
    elif print_:
        obj = contain['data']
        class_ = tree.nodes[obj.extends[0]]
        return _run_print(obj, class_, lang, tree)
    else:
        return _ser_obj(contain['data'], lang, tree, print_)


def _ser_str(str_: str, lang: dict):
    # The only base case in the entire serialization system
    if lang['str_open'] in str_:
        str_ = str_.replace(
            lang['str_open'], lang['str_escape'] + lang['str_open'])

    if lang['str_open'] != lang['str_close'] and lang['str_close'] in str_:
        str_ = str_.replace(
            lang['str_close'], lang['str_escape'] + lang['str_close'])

    return lang['str_open'] + str_ + lang['str_close']


def _ser_list(id_: int, item, lang: dict, tree: Tree, print_: bool) -> str:
    if isinstance(item, list):
        value = lang['list_open']
        for i in item:
            # Serialize any depth of list by recursing
            value += _ser_list(id_, i, lang, tree, print_)
            value += lang['list_delimiter']
        # Replace last comma with ]
        value = value[:-1] + lang['list_close']
        return value
    else:
        if id_ == -1:
            return _ser_str(item, lang)
        elif print_:
            obj = item
            class_ = tree.nodes[obj.extends[0]]
            return _run_print(obj, class_, lang, tree)
        else:
            return _ser_obj(item, lang, tree, print_)


def _ser_obj(obj: Node, lang: dict, tree: Tree, print_: bool) -> str:
    # Basically serialize like JSON, which works in javascript and python,
    # and could be made to work anywhere, although more customization in
    # the future is likely.
    value = lang['obj_open']
    class_ = tree.nodes[obj.extends[0]]

    def field(identifier: str, value: str) -> str:
        return lang['str_open'] + identifier + lang['str_close'] + \
            lang['obj_colon'] + value + lang['obj_delimiter']

    # This information is redundant.
    # It could be added back conditionally, but removed entirely for now.
    # value += field('name', _ser_str(obj.name, lang))
    value += field('class', _ser_str(tree.nodes[obj.extends[0]].name, lang))
    if class_.print is not None:
        value += field('print', _run_print(obj, class_, lang, tree))
    for con in obj.contains:
        value += field(con['name'], _ser_contain(con, lang, tree, print_))

    # Replace last comma with }
    value = value[:-1] + lang['obj_close']
    return value


def _run_code(class_: Node, purpose: str, code: str, lang: dict) -> str:
    # Use subprocess to actually run the given code.
    path = _get_file_path(class_.name, purpose, lang['file_extension'])
    file_string = lang['function_string'] + lang['call_string']
    file_string = file_string.replace(r'\n', '\n')
    file_string = file_string.replace('@@CODE', code)

    with open(path, 'w') as code_file:
        code_file.write(file_string)

    cmd = [lang['path'], path]
    try:
        # TODO: Subprocess is the slowest part of the project.
        # Fix this before anything else
        output = subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        raise CodeError(error, class_, purpose, lang)

    raw = str(output.stdout)
    begin = 'begin--'
    end = '--end'
    return raw[raw.find(begin) + len(begin):raw.find(end)]


def _get_file_path(name: str, purpose: str, ext: str) -> str:
    """Generate file name and path to file"""
    file_name = name + '-' + purpose + '.' + ext
    return os.path.join(CONFIG['general']['tmp_dir'], file_name)
