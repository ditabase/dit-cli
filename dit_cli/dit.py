"""Home of the main dit validation code.
The parser, tree structure, code eval,
and everything else will either be here or be called from here."""

from typing import List, Type

import re
import networkx as nx


PARSER = None


def validate_dit(dit, file_path):
    """Validates a string as a dit. Called from the CLI."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Strip header and assign parser
        dit = handle_header(dit)

        # Discard dit and get the graph
        graph = get_graph(dit)

        return '{} is valid'.format(file_path)
    except ValidationError as error:
        return error


def handle_header(dit: str) -> str:
    """Find, remove and return the <!DOCTYPE dit 'parser'> header"""

    global PARSER

    dit_header = dit[: dit.find('>') + 1]
    doc_type_regex = '^<!DOCTYPE dit ([a-z])+>$'
    doc_type_error = (
        'Dit error: file did not begin with "<!DOCTYPE dit xml>". '
        'Found Header reads: {}'
    ).format(dit_header)

    if not re.search(doc_type_regex, dit_header):
        raise ValidationError(doc_type_error)

    PARSER = Parser(dit[dit.find('dit ') + 4:dit.find('>')])
    dit = PARSER.trim_dit(dit, dit_header)
    return dit


def get_graph(dit: str) -> Type[nx.DiGraph]:
    """Returns a filled NetworkX DiGraph representing the dit file"""
    graph = nx.Graph()
    tokens = []

    # The header counts as a containing token
    tokens.append('header')

    # Initiate the recursive parse, which fills the graph
    parse_next_token(dit, tokens, graph)

    add_edges(graph)

    for node in graph.nodes():
        for extend in graph.nodes[node]['extends']:
            print('Object {} extends {}'.format(
                graph.nodes[node]['name'],
                graph.nodes[node_by_name(graph, extend)]['name']
            ))

        for override in graph.nodes[node]['overrides'].list:
            print('Object {} overrides {}'.format(
                graph.nodes[node]['name'],
                graph.nodes[node_by_name(graph, override['name'])]['name']
            ))

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
            open_token = PARSER.get_open(dit)
            dit = PARSER.trim_dit_safe(dit, open_token[0], tokens)
            tokens.append(open_token[1])

            # Add new nodes/objects as necessary
            if tokens[-1] == 'object':
                new_node(graph, False)
            elif tokens[-1] == 'field':
                new_node(graph, True)
            elif tokens[-1] == 'override':
                graph.nodes[len(graph) - 1]['overrides'].new_override()

            # Recurse and reassign dit
            dit = parse_next_token(dit, tokens, graph)

            # Clear the last token, we just consumed it in the last recurse
            tokens.pop()

            # Should we loop again? Let's see...
            # If the dit is empty, we're done
            if len(dit) == 0:
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


def new_node(graph, is_field):
    """Initialize a new node"""

    # Next node index is always at 1 more than the previous, hence len(graph)
    graph.add_node(len(graph))
    index = len(graph) - 1
    graph.nodes[index]['name'] = None
    graph.nodes[index]['description'] = None
    graph.nodes[index]['example'] = None
    graph.nodes[index]['validator'] = None
    graph.nodes[index]['payload'] = None
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


class Parser:
    """Contains all string functions which interact directly with the dit.
    Will include abstractions for different parser types in the future.
    Currently, only XML is valid."""

    def __init__(self, parser_type: str):
        self.check_type(parser_type)
        self.containing_tokens = [
            'header', 'dit', 'objects',
            'fields', 'object', 'field',
            'extends', 'extend', 'overrides',
            'override', 'contains', 'contain'
        ]

        self.value_tokens = [
            'name', 'description', 'example',
            'validator', 'converter', 'variable',
            'payload'
        ]

        self.white_space_tokens = [
            'validator', 'converter', 'payload'
        ]

    def trim_dit(self, dit: str, replace_str: str) -> str:
        """Clear value and white space from dit"""
        return dit.replace(replace_str, '', 1).lstrip()

    def trim_dit_safe(self, dit: str, replace_str: str, tokens: List[str]) -> str:
        """Clear value from the dit,
        and clear white space if the
        current token is not a white space token"""
        if tokens[-1] in self.white_space_tokens:
            return dit.replace(replace_str, '', 1)
        else:
            return self.trim_dit(dit, replace_str)

    def is_token(self, token: str) -> bool:
        """Check if a str is on any list of valid tokens"""
        return token in self.containing_tokens or token in self.value_tokens

    def is_container(self, token: str) -> bool:
        """Check if str is a containing token"""
        return token in self.containing_tokens

    def is_value(self, token: str) -> bool:
        """Check if str is a value token"""
        return token in self.value_tokens

    def get_open(self, dit: str) -> (str, str):
        """Get the opening token, raise if there isn't one."""
        open_raw = dit[dit.index('<'):dit.index('>') + 1]
        open_value = open_raw[open_raw.index('<') + 1: open_raw.index('>')]
        open_regex = '^<([a-z])+>$'

        if not re.search(open_regex, open_raw):
            raise ValidationError((
                'Parse Error: Could not find valid open token within "{}".'
            ).format(open_raw))

        if not self.is_token(open_value):
            raise ValidationError((
                'Parse Error: The token "{}" is not a valid token name.'
            ).format(open_value))

        return (open_raw, open_value)

    def get_close(self, dit: str, open_value: str) -> str:
        """Get the closing token, raise if there isn't one."""
        close_raw = dit[dit.index('<'):dit.index('>') + 1]
        close_regex = '^</' + open_value + '>$'

        if not re.search(close_regex, close_raw):
            raise ValidationError((
                'Parse Error: Could not find valid close token within "{}".'
            ).format(close_raw))
        return close_raw

    def get_value(self, dit: str, open_value: str) -> str:
        """Get all text until the next close"""
        calculated_close = '</{}>'.format(open_value)
        return dit[:dit.index(calculated_close)]

    def get_open_if_present(self, dit: str) -> bool:
        """Returns the open, or false if there isn't one.
        Will never raise a ValidationException."""
        try:
            return self.get_open(dit)
        except ValidationError:
            return False

    def get_close_if_present(self, dit: str, open_value: str) -> bool:
        """Returns the close, or false if there isn't one.
        Will never raise a ValidationException."""
        try:
            return self.get_close(dit, open_value)
        except ValidationError:
            return False

    def check_type(self, parser_type: str):
        """Raise an error if it's not 'xml'"""

        if parser_type != 'xml':
            raise ValidationError((
                'Feature WIP: "{}" is not currently supported. '
                'The parser will be eventually be arbitrary, '
                'but for now, only "xml" is valid'
            ).format(parser_type))


class ValidationError(Exception):
    """Raised when anything goes wrong during validation of a dit"""
