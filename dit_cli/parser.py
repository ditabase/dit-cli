"""Fill the tree by parsing through the dit string.
Runs entirely functionally from parse(), assigning to tree."""


from __future__ import annotations
from typing import List

import re

from dit_cli.exceptions import ParseError
from dit_cli.tree import Tree, Assigners


def parse(dit: str) -> Tree:
    """Parse the given dit file, and return a valid tree"""
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


def _parse_class(dit: str, tree: Tree) -> str:
    # Some_Class {
    #   extends Some_Other_Class, more_classes;
    #   Some_Class some_contained_object;
    #   list Some_Class some_object;
    #   print some_contained_object; // could be this or
    #   print some_language {{ A code block }}
    #   validator some_language {{ A code block }}
    # }
    line = dit[:dit.find('{') + 1]
    _regex_helper(line, r'^name\s*{$', 'class')
    tree.new(find_name(dit), 'class')
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
                variable = parse_variable(_rep_strip(line, 'print'))
                tree.set_print(variable)
            elif end == '{{':
                # 'print {{ console.log('some custom code'); }}
                _regex_helper(line, r'^print name\s*\{\{$', 'print')
                lang = find_name(_rep_strip(dit, 'print'))
                (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
                tree.set_print(code=code, lang=lang)
        elif token == 'validator':
            # 'validator {{ return 'Some custom validation code'; }}
            _regex_helper(line, r'^validator name\s*\{\{$', 'validator')
            lang = find_name(_rep_strip(dit, 'validator'))
            (dit, code) = _parse_escape(dit, '{{', '}}', '@@')
            tree.set_validator(code, lang)
        elif token == '//':
            dit = _parse_comment(dit)
        elif token == 'list':
            # 'list some_class some_object_name;'
            _regex_helper(line, r'^list \s*name \s*name;$', 'list')
            (type_name, var_name) = _parse_declaration(_rep_strip(line, 'list'))
            tree.add_contain(type_name, var_name, list_=True)

        if end == ';' and token != '//':
            dit = _rep_strip(dit, line)

    return _rep_strip(dit, '}')


def _parse_assigner(dit: str, tree: Tree, assigners: Assigners) -> str:
    # Some_Class some_assigner(param1, param2) {
    #   some_field_of_Class = param1;
    #   other_field_of_Class = param2;
    # }
    line = dit[:dit.index('{') + 1]
    _regex_helper(
        line, r'^name \s*name\(name(,\s*name)*\)\s*{$', 'assigner')
    dit = _rep_strip(dit, line)

    # Get Type and Function names 'type_name assigner_name()'
    type_name = find_name(line)
    line = _rep_strip(line, type_name)
    assigner_name = find_name(line)
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
        if statement:  # Ignore first and last blank statements
            split_state = statement.split('=')
            variable = split_state[0].split('.')
            assign = {'variable': variable, 'parameter': split_state[1]}
            assignments.append(assign)

    assigners.set_assign(assignments, parameters, tree)

    return dit


def _parse_object(dit: str, tree: Tree) -> str:
    # Some_Class some_object;
    line = dit[:dit.find(';') + 1]
    (type_name, var_name) = _parse_declaration(line)
    if type_name == 'String':
        raise ParseError(f'Object cannot be of type String: "{line}""')
    tree.new(var_name, 'object')
    tree.add_extend(type_name)
    return _rep_strip(dit, line)


def _parse_assign(dit: str, tree: Tree, assigners: Assigners) -> str:
    # Rather complicated, more like a typical parser.
    # Each step can be anything.
    left = dit[:dit.find('=') + 1]
    _regex_helper(left, r'^variable\s*=$', 'assignment')
    variable = parse_variable(left)
    tree.is_defined(variable.copy())
    dit = _rep_strip(dit, left)

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
            # Compress items into actual list and put it back into data.
            data[-1] = _list_from_data(data)
            dit = _rep_strip(dit, token)
        elif token == ')':
            if len(memory) == 0:
                raise ParseError(f'Closing ")" but no opening "("')
            mem = memory.pop()
            if mem[0] != ')':
                raise ParseError(f'"{mem[0]}" expected, found instead ")"')
            parameters = _list_from_data(data)
            assigner = mem[1]
            data[-1] = assigner.get_object(tree, parameters)
            dit = _rep_strip(dit, token)
        elif re.match(r'^[A-Za-z_]$', token):
            name = find_name(dit)
            dit = _rep_strip(dit, name)
            if dit[0] == '(':
                memory.append((')', assigners.is_defined(name)))
                data.append(None)  # Used as a unique placeholder
                dit = _rep_strip(dit, '(')
            else:
                data.append(tree.get_data(parse_variable(name)))
        else:
            raise ParseError('Expected ";"')

        if len(dit) == 0:
            raise ParseError('Expected ";"')
        if dit[0] == ',':
            dit = _rep_strip(dit, ',')

    if memory:
        raise ParseError(f'Expected "{memory[0][0]}"')

    # After the loop, len(data) will always be 1
    tree.assign_var(variable, data[0])
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


def _parse_declaration(dit: str) -> (str, str):
    """Parse a 'Some_Class some_object;' style object declaration,
    which appears in classes, assigners, and at top level."""
    _regex_helper(dit, r'^name \s*name\s*;$', 'declaration')
    type_name = find_name(dit)
    var_name = find_name(_rep_strip(dit, type_name))
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


def parse_variable(dit: str) -> List[str]:
    """Turn a string into it's components, seperated by '.'"""
    dit = ''.join(dit.split())  # Remove all whitespace
    dit = dit.replace(';', '').replace('=', '')  # Remove line endings
    return dit.split('.')


def _parse_comment(dit: str) -> str:
    new_line = dit.find('\n')
    if new_line == -1:
        raise ParseError('Comment must end with newline')
    return _rep_strip(dit, dit[:new_line])


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
    """Changes 'name' and 'variable to predefined regexes, then
    tests the dit for matching."""
    # In theory, all regexes should be precompiled constants
    # But this works fine atm and its not very expensive
    name = r'[A-Za-z_][A-Za-z0-9-_]*'
    # [A-Za-z_][A-Za-z0-9-_]*\s*(\.\s*[A-Za-z_][A-Za-z0-9-_]*)*
    variable = rf'{name}\s*(\.\s*{name})*'
    final = base.replace('name', name).replace('variable', variable)
    pattern = re.compile(final)
    if not pattern.match(dit):
        raise ParseError(f'Invalid {statement} syntax: "{dit}"')


def _rep_strip(dit: str, replace_str: str) -> str:
    """Replace first instance of replace_str and left strip"""
    return dit.replace(replace_str, '', 1).lstrip()
