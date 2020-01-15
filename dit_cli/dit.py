"""Home of the main dit validation code.
The parser, tree structure, code eval,
and everything else will either be here or be called from here."""

from typing import List, Type
import re

import networkx as nx

from dit_cli.exceptions import DitError
from dit_cli.exceptions import ValidationError
from dit_cli.exceptions import FormatError
from dit_cli.parser import Parser


PARSER = None


def validate_dit(dit):
    """Validates a string as a dit. Called from the CLI."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Strip header and assign parser
        global PARSER
        (dit, PARSER) = Parser.handle_header(dit)

        # Discard dit and get the graph
        graph = get_graph(dit)

        return 'dit is valid, no errors found'
    except DitError as error:
        return error


def get_graph(dit: str) -> Type[nx.DiGraph]:
    """Returns a filled NetworkX DiGraph representing the dit file"""
    graph = nx.Graph()
    tokens = []

    # The header counts as a containing token
    tokens.append('header')

    # Initiate the recursive parse, which fills the graph
    parse_next_token(dit, tokens, graph)

    add_edges(graph)

    return graph


def parse_next_token(dit: str, tokens: List[str], graph: Type[nx.DiGraph]) -> str:
    """Gather all the dit objects into the DiGraph,
    recursively, one token at a time."""
    global PARSER

    # Check what token was handled just before us.
    # Either it was a containing token...
    if PARSER.is_container(tokens[-1]):
        # while as long as there are tokens, return as soon as there aren't
        while True:
            open_raw, open_name = PARSER.get_open(dit)
            dit = PARSER.trim_dit_safe(dit, open_raw, open_name)
            tokens.append(open_name)

            # Add new nodes/objects as necessary
            if tokens[-1] in ['object', 'field']:
                validate_object_during_parse(graph)
                new_node(graph, tokens[-1] == 'field')
            elif tokens[-1] == 'override':
                graph.nodes[len(graph) - 1]['overrides'].new_override()

            # Recurse and reassign dit
            dit = parse_next_token(dit, tokens, graph)

            # Clear the last token, we just consumed it in the last recurse
            tokens.pop()

            # Should we loop again? Let's see...
            # If the dit is empty, we're done
            if len(dit) == 0:
                # Make sure we validate the last object we just finished!
                validate_object_during_parse(graph)
                return None

            # If not, look for tokens.
            close_token = PARSER.get_close_if_present(dit, tokens[-1])

            # If there's a close, that's the base case
            if close_token:
                return PARSER.trim_dit(dit, close_token)
            # If there's an open, then yes, loop again
            elif PARSER.get_open_if_present(dit):
                pass
            # If neither, that's an error
            else:
                raise ValidationError((
                    'Parse Error: Expected an opening token, '
                    'closing token, or end of file.'
                    '\nLength of dit: {}'
                    'Next 30 characters: {}'
                ).format(len(dit), dit[:30]))

    # ...or a value token,
    elif PARSER.is_value(tokens[-1]):
        value = PARSER.get_value(dit, tokens[-1])
        dit = PARSER.trim_dit(dit, value)

        close_token = PARSER.get_close(dit, tokens[-1])
        dit = PARSER.trim_dit(dit, close_token)

        node = graph.nodes[len(graph) - 1]
        # Assign value based on the token that contained this value
        if tokens[-2] == 'object' or tokens[-2] == 'field':
            node[tokens[-1]] = value
        elif tokens[-2] == 'extend':
            node['extends'].append(value)
        elif tokens[-2] == 'override':
            node['overrides'].set_value(tokens[-1], value)
        else:
            assert True, (
                'Impossible Error: Reached else of value switch '
                'with tokens[-1]: {}'
            ).format(tokens[-1])

        return dit

    else:
        assert True, (
            'Impossible Error: Reached end of parseNextToken with tokens "{}"'
        ).format(tokens)


def validate_object_during_parse(graph: Type[nx.DiGraph]):
    """Validate basic information about an object during parse time.
    Cannot validate important things like object relationships or code yet."""

    if len(graph) == 0:
        return

    node = graph.nodes[len(graph) - 1]

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
    for node_id in graph.nodes():
        if graph.nodes[node_id]['name'] == node['name']:
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


def new_node(graph, is_field):
    """Initialize a new node"""

    # Next node index is always at 1 more than the previous, hence len(graph)
    graph.add_node(len(graph))
    index = len(graph) - 1
    graph.nodes[index]['is_field'] = is_field

    graph.nodes[index]['extends'] = []
    graph.nodes[index]['overrides'] = OverridesList()


def add_edges(graph: Type[nx.DiGraph]):
    """Add edges using data embedded in nodes"""
    for node in graph.nodes():
        for extend in graph.nodes[node]['extends']:
            graph.add_edge(node, node_by_name(
                graph, extend), relationship='extends')

        for over in graph.nodes[node]['overrides'].list:
            graph.add_edge(node, node_by_name(
                graph, over['name']), relationship='overrides')


def node_by_name(graph: Type[nx.DiGraph], name: str) -> int:
    """Turn a name into a node id"""
    return list(filter(lambda n: n[1]['name'] == name, graph.nodes(data=True)))[0][0]


class OverridesList:
    """Holds names and code for override objects"""

    def __init__(self):
        self.list = []

    def new_override(self):
        """Add a new override object to the end of the list"""
        self.list.append({
            'name': None,
            'converter': None
        })

    def set_value(self, key, value):
        """Set the key of the current override object to the value"""
        self.list[len(self.list) - 1][key] = value
