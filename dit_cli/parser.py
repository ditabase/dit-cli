"""Fill the tree by parsing through the dit string.
Runs entirely functionally from parse(), assigning to tree."""


from __future__ import annotations
from typing import List

import re

from dit_cli.exceptions import ParseError
from dit_cli.tree import Tree, Assigners, Node
from dit_cli import CONFIG, traverse


def parse(dit: str) -> Tree:
    tree = Tree()
    assigners = Assigners()

    while len(dit) > 0:
        token = _nearest_token(dit, ['{', '(', ';', '=', '//'])
        if token == '{':
            dit = _parse_class(dit, tree)
        elif token == '(':
            dit = _parse_assigner(dit, tree, assigners)
        elif token == ';':
            dit = _parse_object(dit, tree)
        elif token == '=':
            dit = _parse_assign(dit, tree, assigners)
        elif token == '//':
            dit = _parse_comment(dit)

    return tree


def prep_code(code: str, class_: Node, obj: Node, tree: Tree) -> str:
    start = 0
    while True:
        escape = code.find('@@', start)
        if escape == -1:
            break
        if code[escape:escape + 4] == '@@@@':
            code = code[:escape] + code[escape + 2:]  # Keep only one @@
            start = escape + 2
            continue
        if code[escape:escape + 3] == '@@@':
            escape += 1

        raw_var = _find_name(code[escape + 2:])
        variable = _parse_variable(raw_var)
        contain = tree.get_contain(variable, class_=class_, obj=obj)

        value = _get_var_string(contain, class_)

        code = code[:escape] + value + code[escape + 2 + len(raw_var):]
        start = escape + len(value)

    return code


def _get_var_string(contain, class_: Node):
    lang = CONFIG[class_.validator['language']]
    if contain is None:
        return lang['null_type']
    data = []
    for item in traverse(contain['data']):
        if contain['id_'] == -1:
            data.append(lang['str_open'] + item + lang['str_close'])

    if len(data) == 1:
        return data[0]
    else:
        value = lang['list_open']
        for item in data:
            value += item + lang['list_delimiter']
        value += lang['list_close']
        return value


def _parse_class(dit: str, tree: Tree) -> str:
    line = dit[:dit.find('{') + 1]
    _regex_helper(line, r'^name\s*{$', 'class')
    tree.new(_find_name(dit), 'class')
    dit = _rep_strip(dit, line)

    # extends must come first
    if dit.startswith('extends'):
        # 'extends some_class, second_class;'
        line = dit[:dit.find(';') + 1]
        _regex_helper(line, r'^extends \s*name(,\s*name)*;$', 'extends')
        ext = line[len('extends') + 1: line.find(';')]
        ext = ''.join(ext.split())  # Remove all whitespace
        for extend in ext.split(','):
            tree.add_extend(extend)
        dit = _rep_strip(dit, line)

    while dit[0] != '}':
        end = _nearest_token(dit, [';', '{{'])
        line = dit[:dit.find(end) + len(end)]
        token = _nearest_token(
            line, ['extends', ';', 'print', 'validator', '//', 'list'])
        if token == 'extends':
            raise ParseError('"extends" must come first, or not at all')
        elif token == ';':
            # 'some_class some_object_name;'
            (type_name, var_name) = _parse_declaration(line)
            tree.add_contain(type_name, var_name)
        elif token == 'print':
            if end == ';':
                # 'print some_variable'
                _regex_helper(line, r'^print \s*variable;$', 'print')
                variable = _parse_variable(_rep_strip(line, 'print'))
                tree.set_print(variable)
            elif end == '{{':
                # 'print {{ console.log('some custom code'); }}
                _regex_helper(line, r'^print name\s*\{\{$', 'print')
                language = _find_name(_rep_strip(dit, 'print'))
                (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
                tree.set_print(code=code, language=language)
        elif token == 'validator':
            # 'validator {{ return 'Some custom validation code'; }}
            _regex_helper(line, r'^validator name\s*\{\{$', 'validator')
            language = _find_name(_rep_strip(dit, 'validator'))
            (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
            tree.set_validator(code, language)
        elif token == '//':
            dit = _parse_comment(dit)
        elif token == 'list':
            # 'list 1 some_class some_object_name;'
            _regex_helper(line, r'^list \s*\d+ \s*name \s*name;$', 'list')
            side_line = _rep_strip(line, 'list')
            list_depth = _find_name(side_line)
            side_line = _rep_strip(side_line, list_depth)
            (type_name, var_name) = _parse_declaration(side_line)
            tree.add_contain(type_name, var_name, list_depth=int(list_depth))

        if end == ';' and token != '//':
            dit = _rep_strip(dit, line)

    return _rep_strip(dit, '}')


def _parse_assigner(dit: str, tree: Tree, assigners: Assigners) -> str:
    line = dit[:dit.index('{') + 1]
    _regex_helper(
        line, r'^name \s*name\(name(,\s*name)*\)\s*{$', 'assigner')
    dit = _rep_strip(dit, line)

    # Get Type and Function names 'type_name assigner_name()'
    type_name = _find_name(line)
    line = _rep_strip(line, type_name)
    assigner_name = _find_name(line)
    line = _rep_strip(line, assigner_name)
    assigners.new(type_name, assigner_name, tree)

    # Get Paramenters '(each, para, meter, here)'
    line = ''.join(line.split())
    line = line.replace('(', '').replace(')', '').replace('{', '')
    parameters = line.split(',')

    # Get Assignments
    dit = re.sub(r'\s\/\/[^\n]*\n', '', dit)  # replace comments with nothing
    line = dit[:dit.index('}') + 1]
    _regex_helper(line, r'^(variable\s*=\s*name;\s*)+\s*}$', 'arg assign')
    dit = _rep_strip(dit, line)
    line = ''.join(line.split())  # clear white space
    line = line.replace('}', '')
    statements = line.split(';')
    assignments = []
    for statement in statements:
        if statement:
            split_state = statement.split('=')
            variable = split_state[0].split('.')
            assign = {'variable': variable, 'parameter': split_state[1]}
            assignments.append(assign)

    assigners.set_assign(assignments, parameters, tree)

    return dit


def _parse_object(dit: str, tree: Tree) -> str:
    line = dit[:dit.find(';') + 1]
    (type_name, var_name) = _parse_declaration(line)
    if type_name == 'String':
        raise ParseError(f'Object cannot be of type String: "{line}""')
    tree.new(var_name, 'object')
    tree.add_extend(type_name)
    return _rep_strip(dit, line)


def _parse_assign(dit: str, tree: Tree, assigners: Assigners) -> str:
    left = dit[:dit.find('=') + 1]
    _regex_helper(left, r'^variable\s*=$', 'assignment')
    variable = _parse_variable(left)
    tree.is_defined(variable.copy())
    dit = _rep_strip(dit, left)

    memory = []
    data = []
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
            data[-1] = _list_from_data(data)
            dit = _rep_strip(dit, token)
        elif token == ')':
            if len(memory) == 0:
                raise ParseError(f'Closing ")" but no opening "("')
            mem = memory.pop()
            if mem[0] != ')':
                raise ParseError(f'"{mem[0]}" expected, found instead ")"')
            parameters = _list_from_data(data)
            data[-1] = mem[1].get_object(tree, parameters)
            dit = _rep_strip(dit, token)
        elif re.match(r'^[A-Za-z_]$', token):
            name = _find_name(dit)
            dit = _rep_strip(dit, name)
            if dit[0] == '(':
                memory.append((')', assigners.is_defined(name)))
                data.append(None)  # Used as a unique placeholder
                dit = _rep_strip(dit, '(')
            else:
                data.append(tree.get_data(_parse_variable(name)))
        else:
            raise ParseError('Expected ";"')

        if len(dit) == 0:
            raise ParseError('Expected ";"')
        if dit[0] == ',':
            dit = _rep_strip(dit, ',')

    if memory:
        raise ParseError(f'Expected "{memory[0][0]}"')

    tree.assign_var(variable, data[0])
    return _rep_strip(dit, ';')


def _list_from_data(data):
    for index, item in enumerate(reversed(data)):
        if item is None:
            list_ = data[-index: len(data)]
            del data[-index: len(data)]
            return list_


def _parse_declaration(dit: str) -> (str, str):
    _regex_helper(dit, r'^name \s*name\s*;$', 'declaration')
    type_name = _find_name(dit)
    var_name = _find_name(_rep_strip(dit, type_name))
    return (type_name, var_name)


def _parse_escape(dit: str, left: str, right: str, esc: str) -> (str, str):
    """Parse a sequence with escaped ending tokens, like "3\""

    Dit must start at the very beginning of the sequence.
    Will return a tuple with the replaced dit and the sequence"""
    end = 0
    while True:
        end = dit.find(right, end + len(right))
        if end == -1:
            raise ParseError(f'Missing closing sequence: {right}')
        if dit[end - len(right): end] != esc:
            break
    sequence = dit[dit.find(left) + len(left): end]
    dit = dit[end + len(right):].lstrip()
    return (dit, sequence)


def _parse_variable(dit: str) -> List[str]:
    dit = ''.join(dit.split())  # Remove all whitespace
    dit = dit.replace(';', '').replace('=', '')  # Remove line endings
    return dit.split('.')


def _parse_comment(dit: str) -> str:
    return _rep_strip(dit, dit[:dit.find('\n')])


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


def _find_name(dit: str) -> str:
    """Returns everything up to the nearest token, any token except periods.
    Useful when a name ends in white space, or some other limiter."""
    tokens = [' ', '\t', '\n', '{', ';', '=', '(', ',']
    return dit[:dit.find(_nearest_token(dit, tokens))]


def _regex_helper(dit: str, base: str, statement):
    """Changes 'name' and 'variable to predefined regexes, then
    tests the dit for matching."""
    name = r'[A-Za-z_][A-Za-z0-9-_]*'
    # [A-Za-z_][A-Za-z0-9-_]*\s*(\.\s*[A-Za-z_][A-Za-z0-9-_]*)*
    variable = rf'{name}\s*(\.\s*{name})*'
    final = base.replace('name', name).replace('variable', variable)
    pattern = re.compile(final)
    if not pattern.match(dit):
        raise ParseError(f'Invalid {statement} syntax: "{dit}"')


def _rep_strip(dit: str, replace_str: str) -> str:
    """Replace first value and left strip"""
    return dit.replace(replace_str, '', 1).lstrip()
