"""Fill a namespace by parsing through the dit string.
Runs entirely functionally from parse(), assigning to namespace.

Indirectly recursive via import, which calls parse on the new file"""


from __future__ import annotations
from typing import List

import re
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from dit_cli.exceptions import ParseError
from dit_cli.namespace import Namespace
from dit_cli.node import Node
from dit_cli.assigner import Assigner


def parse(dit: str) -> Namespace:
    """Parse the given dit file, and return a valid namespace"""
    namespace = Namespace()

    while len(dit) > 0:
        token = _nearest_token(dit, ['{', '(', ';', '=', '//', 'import'])
        if token == '{':
            dit = _parse_class(dit, namespace)
        elif token == '(':
            dit = _parse_assigner(dit, namespace)
        elif token == ';':
            dit = _parse_object(dit, namespace)
        elif token == '=':
            dit = _parse_assign(dit, namespace)
        elif token == '//':
            dit = _parse_comment(dit)
        elif token == 'import':
            dit = _parse_import(dit, namespace)

    return namespace


def _parse_class(dit: str, namespace: Namespace) -> str:
    # Some_Class {
    #   extends Some_Other_Class, more_classes;
    #   Some_Class some_attribute;
    #   list Some_Class some_object;
    #   print some_attribute; // could be this or
    #   print some_language {{ A code block }}
    #   validator some_language {{ A code block }}
    # }
    line = dit[:dit.find('{') + 1]
    _regex_helper(line, r'^name\s*{$', 'class')
    class_ = Node(namespace, find_name(dit), 'class')
    namespace.nodes.append(class_)
    dit = _rep_strip(dit, line)

    # remove leading comments
    while dit.startswith('//'):
        dit = _parse_comment(dit)

    # extends must come first
    if dit.startswith('extends'):
        # 'extends some_class, second_class;'
        line = dit[:dit.find(';') + 1]
        _regex_helper(line, r'^extends \s*expr(,\s*expr)*;$', 'extends')
        ext = line[len('extends') + 1: line.find(';')]
        ext = ''.join(ext.split())  # Remove all whitespace
        for extend in ext.split(','):
            expr = parse_expr(extend)
            class_.add_extend(expr)
        dit = _rep_strip(dit, line)

    if len(dit) == 0:
        raise ParseError('Unexpected EOF while parsing class.')

    while dit[0] != '}':
        if dit[:2] == '//':
            dit = _parse_comment(dit)
            continue

        end = _nearest_token(dit, [';', '{{'])
        line = dit[:dit.find(end) + len(end)]
        token = _nearest_token(
            line, ['extends', ';', 'print', 'validator', 'list'])
        if token == 'extends':
            raise ParseError('"extends" must come first, or not at all')
        elif token == ';':
            # 'some_class some_object_name;'
            (type_expr, var_name) = _parse_declaration(line)
            class_.add_attribute(type_expr, var_name)
        elif token == 'print':
            if end == ';':
                # 'print some_expression'
                _regex_helper(line, r'^print \s*expr;$', 'print')
                expr = parse_expr(_rep_strip(line, 'print'))
                class_.set_print(expr)
            elif end == '{{':
                # 'print language {{ console.log('some custom code'); }}
                _regex_helper(line, r'^print name\s*\{\{$', 'print')
                lang = find_name(_rep_strip(dit, 'print'))
                (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
                class_.set_print(code=code, lang=lang)
        elif token == 'validator':
            # 'validator language {{ return 'Some custom validation code'; }}
            _regex_helper(line, r'^validator name\s*\{\{$', 'validator')
            lang = find_name(_rep_strip(dit, 'validator'))
            (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
            class_.set_validator(code, lang)
        elif token == 'list':
            # 'list some_class some_object_name;'
            _regex_helper(line, r'^list \s*expr \s*name;$', 'list')
            res = _parse_declaration(_rep_strip(line, 'list'))
            (type_expr, var_name) = res
            class_.add_attribute(type_expr, var_name, list_=True)

        if end == ';':
            dit = _rep_strip(dit, line)
        if len(dit) == 0:
            raise ParseError('Unexpected EOF while parsing class.')

    return _rep_strip(dit, '}')


def _parse_assigner(dit: str, namespace: Namespace) -> str:
    # Some_Class some_assigner(param1, param2) {
    #   some_field_of_Class = param1;
    #   other_field_of_Class = param2;
    # }
    line = dit[:dit.index('{') + 1]
    _regex_helper(
        line, r'^expr \s*name\(name(,\s*name)*\)\s*{$', 'assigner')
    dit = _rep_strip(dit, line)

    # Get Type and Function names 'type_name assigner_name()'
    type_name = find_name(line)
    line = _rep_strip(line, type_name)
    assigner_name = find_name(line)
    line = _rep_strip(line, assigner_name)
    type_expr = parse_expr(type_name)
    assigner = Assigner(namespace, assigner_name, type_expr)

    # Get args '(each, arg, here)'
    line = ''.join(line.split())
    line = line.replace('(', '').replace(')', '').replace('{', '')
    args = line.split(',')

    # Get Assignments 'some_left_assign = some_arg'
    # Since everything is in order, we just get everything until the }
    # and split up the assignments on ;

    # replace comments with nothing
    dit = re.sub(r'\s*\/\/[^\n]*\n', '', dit).lstrip()
    line = dit[:dit.index('}') + 1]
    _regex_helper(line, r'^(expr\s*=\s*name;\s*)+\s*}$', 'arg assign')
    dit = _rep_strip(dit, line)
    line = ''.join(line.split())  # clear white space
    line = line.replace('}', '')
    statements = line.split(';')
    assignments = []
    for statement in statements:
        if statement:  # Ignore first and last blank statements
            split_state = statement.split('=')
            expr = split_state[0].split('.')
            assign = {'expr': expr, 'arg': split_state[1]}
            assignments.append(assign)

    assigner.set_assign(assignments, args)

    return dit


def _parse_object(dit: str, namespace: Namespace) -> str:
    # Some_Class some_object;
    line = dit[:dit.find(';') + 1]
    (type_expr, var_name) = _parse_declaration(line)
    obj = Node(namespace, var_name, 'object')
    namespace.nodes.append(obj)
    obj.add_extend(type_expr)
    return _rep_strip(dit, line)


def _parse_assign(dit: str, namespace: Namespace) -> str:
    # Rather complicated, more like a typical parser.
    # Each step can be anything.
    left = dit[:dit.find('=') + 1]
    _regex_helper(left, r'^expr\s*=$', 'assignment')
    left_expr = parse_expr(left)
    namespace.raise_if_undefined(left_expr)
    dit = _rep_strip(dit, left)
    if len(dit) == 0:
        raise ParseError('Unexpected EOF while parsing assignment.')

    memory = []  # For opened lists and assigners
    data = []  # For all previously added values
    while dit[0] != ';':
        token = dit[0]
        if token == "'" or token == '"':
            (dit, string) = _parse_escape(dit, token, token, '\\')
            data.append(string)
        elif token == '[':
            memory.append((']', None))
            data.append(None)  # Used as a unique placeholder
            dit = _rep_strip(dit, token)
        elif token == ']':
            if len(memory) == 0:
                raise ParseError(f'Closing "]" but no opening "["')
            mem = memory.pop()
            if mem[0] != ']':
                raise ParseError(f'"{mem[0]}" expected, found instead "]"')
            # Check for empty list
            if data[-1] is None:
                data[-1] = []
            else:
                # Compress items into list and put it back into data.
                data[-1] = _list_from_data(data)
            dit = _rep_strip(dit, token)
        elif token == ')':
            if len(memory) == 0:
                raise ParseError(f'Closing ")" but no opening "("')
            mem = memory.pop()
            if mem[0] != ')':
                raise ParseError(f'"{mem[0]}" expected, found instead ")"')
            args = _list_from_data(data)
            assigner: Assigner = mem[1]
            data[-1] = assigner.get_object(args)
            dit = _rep_strip(dit, token)
        elif re.match(r'^[A-Za-z_]$', token):
            name = find_name(dit)
            dit = _rep_strip(dit, name)
            expr = parse_expr(name)
            if dit[0] == '(':
                memory.append((')', namespace.read(expr)))
                data.append(None)  # Used as a unique placeholder
                dit = _rep_strip(dit, '(')
            else:
                data.append(namespace.read_data(expr))
        else:
            raise ParseError('Expected ";" after assignment')

        if len(dit) == 0:
            raise ParseError('Expected ";" after assignment')
        if dit[0] == ',':
            dit = _rep_strip(dit, ',')

    if memory:
        raise ParseError(f'Expected "{memory[0][0]}"')

    # After the loop, len(data) will always be 1
    namespace.write(left_expr, data[0])
    return _rep_strip(dit, ';')


def _list_from_data(data):
    """Get a new list of all the items in the list since the last
    special token, either an assigner or a list.
    Special token denoted by None, which cannot appear otherwise."""
    for index, item in enumerate(reversed(data)):
        if item is None:
            list_ = data[-index: len(data)]
            del data[-index: len(data)]
            return list_


def _parse_declaration(dit: str) -> (List[str], str):
    """Parse a 'Some_Class some_object;' style object declaration,
    which appears in classes, assigners, and at top level."""
    _regex_helper(dit, r'^expr \s*name\s*;$', 'declaration')
    type_name = find_name(dit)
    var_name = find_name(_rep_strip(dit, type_name))
    type_expr = parse_expr(type_name)
    return (type_expr, var_name)


def _parse_escape(dit: str, left: str, right: str, esc: str) -> (str, str):
    r"""Parse a sequence with escaped ending tokens, like "3\""
    Also processes escape sequences. \\ are converted to \, @@}} to }}, etc.
    @@variable sequences are processed during eval time, in _prep_code()

    Dit must start at the very beginning of the sequence.
    Will return a tuple with the replaced dit and the sequence"""
    fnd_right = len(left)
    fnd_esc = len(left)

    # Find the right-side closing sequence, then break
    while True:
        fnd_right = dit.find(right, fnd_right)
        fnd_esc = dit.find(esc, fnd_esc)
        if fnd_right == -1:
            raise ParseError(f'Missing closing sequence: {right}')
        if fnd_esc == -1 or fnd_right < fnd_esc:
            break  # Found it!

        # There is an escape to process
        if esc == '@@':
            if dit[fnd_esc: fnd_esc + 4] == r'@@}}':
                dit = dit[:fnd_esc] + dit[fnd_right:]

            # Special case for @@ right next to the actual closing braces.
            # We recognize the escape, but don't consume it.
            elif dit[fnd_esc: fnd_esc + 6] == r'@@@@}}':
                break

        elif esc == '\\':
            # Literal \ in dit strings.
            char = dit[fnd_esc + 1: fnd_esc + 2]
            if char in ["'", '"', '\\']:
                dit = dit[:fnd_esc] + dit[fnd_esc + 1:]
            elif char == 't':
                dit = dit[:fnd_esc] + '\t' + dit[fnd_esc + 2:]
            elif char == 'n':
                dit = dit[:fnd_esc] + '\n' + dit[fnd_esc + 2:]
            else:
                raise ParseError(
                    f'Unrecognized escape character: "\\{char}"')

        fnd_esc += len(esc)
        fnd_right = fnd_esc

    sequence = dit[dit.find(left) + len(left): fnd_right]
    dit = dit[fnd_right + len(right):].lstrip()
    return (dit, sequence)


def parse_expr(dit: str) -> List[str]:
    """Turn a string into it's components, seperated by '.'"""
    dit = ''.join(dit.split())  # Remove all whitespace
    dit = dit.replace(';', '').replace('=', '')  # Remove line endings
    return dit.split('.')


def _parse_comment(dit: str) -> str:
    new_line = dit.find('\n')
    if new_line == -1:
        raise ParseError('Comment must end with newline')
    return _rep_strip(dit, dit[:new_line])


def _parse_import(dit: str, namespace: Namespace) -> str:
    # import someNamespace from 'https://www.example.com/someClasses.dit';
    # import someNamespace from '/home/isaiah/someClasses.dit'
    # Parse the path, load this file, then recursively
    # call parse to get the new namespace.
    # Reference this namespace by the name given in the import statement.
    line = dit[:dit.find(_nearest_token(dit, ['"', "'"]))]
    _regex_helper(line, r'^import \s*name \s*from \s*$', 'import')

    dit = _rep_strip(dit, 'import')
    name = find_name(dit)
    dit = _rep_strip(dit, name)
    dit = _rep_strip(dit, 'from')
    token = dit[0]
    (dit, path) = _parse_escape(dit, token, token, '\\')
    if dit[0] != ';':
        raise ParseError(f'Expected ";" after import')
    dit = _rep_strip(dit, ';')

    if path.startswith('https://') or path.startswith('http://'):
        try:
            imported_dit = urlopen(path).read().decode()
        except (HTTPError, URLError) as error:
            raise ParseError(f'Import failed, {error}\nURL: "{path}"')
    else:
        try:
            with open(path) as file_object:
                imported_dit = file_object.read()
        except FileNotFoundError:
            raise ParseError(f'Import failed, file not found\nPath: "{path}"')
        except PermissionError:
            raise ParseError(
                f'Import failed, permission denied\nPath: "{path}"')

    if not imported_dit:
        raise ParseError(f'Import failed, reason unknown\nPath: "{path}"')

    if imported_dit.lstrip().startswith('<!DOCTYPE html>'):
        raise ParseError((
            'Import failed, file is <!DOCTYPE html>.'
            '\nLoad raw text, not webpage.'
        ))

    namespace.add(name, parse(imported_dit))

    return dit


def _nearest_token(dit: str, tokens: List[str]) -> str:
    """Get the nearest token which clearly identifies the next statement"""
    occurs = []
    for token in tokens:
        occur = dit.find(token)
        if occur != -1:
            occurs.append((occur, token))

    if len(occurs) == 0:
        raise ParseError(f'Found no tokens: {tokens}')

    (index, token) = min(occurs)
    return dit[index:index + len(token)]


def find_name(dit: str) -> str:
    """Returns everything up to the nearest token, any token except periods.
    Useful when a name ends in white space, or some other limiter."""
    tokens = [' ', '\t', '\n', '{', ';', '=', '(', ',', ')', '}']
    return dit[:dit.find(_nearest_token(dit, tokens))]


def _regex_helper(dit: str, base: str, statement):
    """Changes 'name' and 'expr' to predefined regexes, then
    tests the dit for matching."""
    # In theory, all regexes should be precompiled constants
    # But this works fine atm and its not very expensive
    name = r'[A-Za-z_][A-Za-z0-9-_]*'
    # [A-Za-z_][A-Za-z0-9-_]*\s*(\.\s*[A-Za-z_][A-Za-z0-9-_]*)*
    expr = rf'{name}\s*(\.\s*{name})*'
    final = base.replace('name', name).replace('expr', expr)
    pattern = re.compile(final)
    if not pattern.match(dit):
        raise ParseError(f'Invalid {statement} syntax: "{dit}"')


def _rep_strip(dit: str, replace_str: str) -> str:
    """Replace first instance of replace_str and left strip"""
    return dit.replace(replace_str, '', 1).lstrip()
