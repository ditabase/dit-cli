"""Holds the Parser class"""

from __future__ import annotations

import re

from dit_cli.exceptions import ParseError
from dit_cli.exceptions import FormatError


class Parser:
    """Contains all string functions which interact directly with the dit.
    Will include abstractions for different parser types in the future.
    Currently, only XML is valid."""

    def __init__(self, parser_type: str):
        Parser.check_type(parser_type)
        self.containing_tokens = [
            'header', 'dit', 'objects',
            'fields', 'object', 'field',
            'extends', 'extend', 'overrides',
            'override', 'contains', 'contain',
        ]

        self.value_tokens = [
            'name', 'description', 'example',
            'validator', 'converter', 'variable',
            'payload'
        ]

        self.white_space_tokens = [
            'validator', 'converter', 'payload'
        ]

        self.config_tokens = [
            'config', 'language'
        ]

        self.all_tokens = self.containing_tokens + \
            self.value_tokens + self.config_tokens

    def trim_dit(self, dit: str, replace_str: str) -> str:
        """Clear value and white space from dit"""
        return dit.replace(replace_str, '', 1).lstrip()

    def trim_dit_safe(self, dit: str, replace_str: str, open_name: str) -> str:
        """Clear value from the dit,
        and clear white space if the
        current token is not a white space token"""
        if open_name in self.white_space_tokens:
            return dit.replace(replace_str, '', 1)
        else:
            return self.trim_dit(dit, replace_str)

    def is_token(self, token: str) -> bool:
        """Check if a str is on any list of valid tokens"""
        return token in self.all_tokens

    def is_container(self, token: str) -> bool:
        """Check if str is a containing token"""
        return token in self.containing_tokens

    def is_value(self, token: str) -> bool:
        """Check if str is a value token"""
        return token in self.value_tokens

    def get_xml_tag(self, dit: str) -> str:
        """Get an XML tag, whether it has a closing '/' or not"""
        left_brace = dit.find('<')

        if left_brace == -1:
            raise ParseError((
                'No opening brace found.'
                'Next 30 characters:\n{}'
            ).format(dit[:30]))

        right_brace = dit.find('>')

        if right_brace == -1:
            raise ParseError((
                'No closing brace found.'
                'Next 30 characters:\n{}'
            ).format(dit[:30]))

        if left_brace > right_brace:
            raise ParseError((
                'Missing "<" in "{}"'
            ).format(dit[:right_brace + 1]))

        tag = dit[left_brace:right_brace + 1]

        # '</description' is 14 chars
        if len(tag) > 14:
            raise ParseError((
                'Missing ">" in "{}"'
            ).format(tag))

        return tag

    def get_open(self, dit: str) -> (str, str):
        """Get the opening token, raise if there isn't one."""

        open_raw = self.get_xml_tag(dit)
        open_regex = '^<([a-z])+>$'

        if not re.search(open_regex, open_raw):
            raise ParseError((
                'Could not find valid open tag within "{}".'
            ).format(open_raw))

        open_value = open_raw[1: -1]

        if not self.is_token(open_value):
            raise ParseError((
                'The token "{}" is not a valid token name.'
            ).format(open_value))

        return (open_raw, open_value)

    def get_close(self, dit: str, open_value: str) -> str:
        """Get the closing token, raise if there isn't one."""
        close_raw = self.get_xml_tag(dit)
        close_regex = '^</' + open_value + '>$'

        if not re.search(close_regex, close_raw) and close_raw != '</config>':
            raise ParseError((
                'Could not find valid close token within "{}".'
            ).format(close_raw))
        return close_raw

    def get_value(self, dit: str, open_value: str) -> str:
        """Get all text until the next close"""
        calculated_close = '</{}>'.format(open_value)
        return dit[:dit.index(calculated_close)]

    def get_open_if_present(self, dit: str):
        """Returns the open, or false if there isn't one.
        Will never raise a ValidationException."""
        try:
            return self.get_open(dit)
        except ParseError:
            return False

    def get_close_if_present(self, dit: str, open_value: str):
        """Returns the close, or false if there isn't one.
        Will never raise a ValidationException."""
        try:
            return self.get_close(dit, open_value)
        except ParseError:
            return False

    @staticmethod
    def handle_header(dit: str) -> (str, Parser):
        """Find, remove and return the <!DOCTYPE dit 'parser'> header"""

        dit_header = dit[: dit.find('>') + 1]
        doc_type_regex = '^<!DOCTYPE dit ([a-z])+>$'

        if not re.search(doc_type_regex, dit_header):
            raise FormatError((
                'File did not begin with "<!DOCTYPE dit xml>". '
                'Found Header reads: {}'
            ).format(dit_header))

        parser = Parser(dit[dit.find('dit ') + 4:dit.find('>')])
        dit = parser.trim_dit(dit, dit_header)
        return dit, parser

    @staticmethod
    def check_type(parser_type: str):
        """Raise an error if it's not 'xml'"""

        if parser_type != 'xml':
            raise FormatError((
                '"{}" is not currently supported. '
                'The parser will be eventually be arbitrary, '
                'but for now, only "xml" is valid'
            ).format(parser_type))
