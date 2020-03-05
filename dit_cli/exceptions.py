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

    def __init__(self, error: CalledProcessError, class_,
                 purpose: str, lang: dict):
        message = (
            f'{class_.name} {lang["name"]} {purpose}\n'
            f'Error message follows:\n\n{error.stderr.decode("utf-8")}')
        super().__init__('CodeError', message)


class ParseError(DitError):
    """Raised when there anything goes wrong during paring the file"""

    def __init__(self, message):
        super().__init__('ParseError', message)


class TreeError(DitError):
    """Raised when anything goes wrong with tree functions"""

    def __init__(self, message):
        super().__init__('TreeError', message)
