"""All Exceptions used by dit_cli"""

from subprocess import CalledProcessError


class DitError(Exception):
    """Base Class for all dit exceptions"""

    def __init__(self, prepend, message):
        super().__init__(prepend + ': ' + message)


class FormatError(DitError):
    """Raised when the file has an illegal style or structure"""

    def __init__(self, message):
        super().__init__('FormatError', message)


class ValidationError(DitError):
    """Raised when a validator returns something other than true"""

    def __init__(self, message, name):
        super().__init__(f'ValidationError<{name}>', message)


class CodeError(DitError):
    """Raised when a code block has any kind of language specifc error"""

    def __init__(self, error: CalledProcessError, name: str,
                 purpose: str, lang: dict):
        message = (
            f'{name} {lang["name"]} {purpose}\n'
            f'Error message follows:\n\n{error.stderr.decode()}')
        super().__init__('CodeError', message)


class ParseError(DitError):
    """Raised when there anything goes wrong during paring the file"""

    def __init__(self, message):
        super().__init__('ParseError', message)


class NodeError(DitError):
    """Raised when anything goes wrong with a node"""

    def __init__(self, message):
        super().__init__('NodeError', message)


class AssignError(DitError):
    """Raised when anything goes wrong with an assigner"""

    def __init__(self, message):
        super().__init__('AssignError', message)


class VarError(DitError):
    """Raised when anything goes wrong with variables"""

    def __init__(self, message):
        super().__init__('VarError', message)
