"""Home of the main dit validation code.
The parser, tree structure, code eval,
and everything else will either be here or be called from here."""

import re

from dit_cli.tree import Tree
from dit_cli.exceptions import DitError, FormatError
from dit_cli.parser import parse
from dit_cli.evaler import run_scripts
from dit_cli import CONFIG


def validate_dit(dit):
    """Validates a string as a dit. Called from the CLI."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Deprecated, no more header, no customizable parsers.
        # Strip header and assign parser
        # global PARSER
        # (dit, PARSER) = Parser.handle_header(dit)

        # Discard dit and get the tree
        tree = parse(dit)

        # TODO: Add class higherachy check, such as Arborescence

        return 'dit is valid, no errors found'
    except DitError as error:
        return error


def validate_node_during_parse(tree: Tree):
    """Validate basic information about an object during parse time.
    Cannot validate important things like object relationships or code yet."""

    if len(tree) == 0:
        return

    node = tree.nodes[len(tree) - 1]

    if 'name' not in node or not node['name']:
        raise FormatError((
            'A dit object had no name. '
            'The entire node follows:\n{}'
        ).format(node))

    # Currently only white space, should probably ban other stuff
    invalid_name_regex = r'\s'

    if re.search(invalid_name_regex, node['name']):
        raise FormatError((
            'A dit object had an illegal name: "{}"'
        ).format(node['name']))

    # No duplicate names
    count = 0
    for node_id in tree.nodes():
        if tree.nodes[node_id]['name'] == node['name']:
            count += 1

    if count > 1:
        raise FormatError((
            'There are {} objects with the name "{}"'
        ).format(count, node['name']))

    # There must be *something* to check the payload with
    if ('validator' not in node and len(node['extends']) == 0 and
            len(node['overrides'].list) == 0):
        raise FormatError((
            '{} had no validator and did not extend or override anything.'
        ))

    for extend in node['extends']:
        if not extend:
            raise FormatError((
                '"{}" had an extend with no name.'
            ).format(node['name']))
        if re.search(invalid_name_regex, extend):
            raise FormatError((
                '"{}" had an extend with an illegal name: "{}"'
            ).format(node['name'], extend))

    for override in node['overrides'].list:
        if not override['name']:
            raise FormatError((
                '"{}" had an override with no name.'
            ).format(node['name']))
        if re.search(invalid_name_regex, override['name']):
            raise FormatError((
                '"{}" had an override with an illegal name: "{}"'
            ).format(node['name'], override['name']))
        if not override['converter']:
            raise FormatError((
                '"{}" overrode "{}" with no converter.'
            ).format(node['name'], override['name']))

    if node['is_field'] and 'payload' not in node:
        raise FormatError((
            '"{}" was a field, but did not have a payload.'
        ).format(node['name']))

    if not node['is_field'] and 'payload' in node:
        raise FormatError((
            '"{}" was an object, but had a payload.'
        ).format(node['name']))


def validate_object_after_parse(node_id, tree):
    """Validate complex information that required the entire tree.
    Also call actual validation code"""
    node = tree.nodes[node_id]
    for extend_name in node['extends']:
        for override in node['overrides'].list:
            if extend_name == override['name']:
                raise FormatError((
                    '"{}" both extends and overrides "{}"'
                ).format(node['name'], extend_name))

    if node['is_field']:
        run_scripts(node_id, tree, node['payload'])
