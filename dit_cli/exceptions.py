"""All Exceptions used by dit_cli"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dit_cli.color import Color, color
from dit_cli.settings import CodeLocation


@dataclass
class Trace:
    """Represents a point along the stack trace of an error,
    or the origin itself."""

    filepath: str
    loc: CodeLocation
    code: str = None  # type: ignore
    caller: str = None  # type: ignore


class d_DitError(Exception):
    """Base Class for all dit exceptions"""

    def __init__(self, message: str, loc: CodeLocation = None):
        self.warning = message
        self.loc: CodeLocation = loc  # type: ignore
        super().__init__(self.warning)
        self.origin: Trace = None  # type: ignore
        self.traces: List[Trace] = []

    def set_origin(self, filepath: str, code: str):
        """Sets the location in code of this error.
        The location will be highlighted in the terminal by a carrot ^"""
        self.origin = Trace(filepath, self.loc, code=code)

    def add_trace(self, filepath: str, trace_loc: CodeLocation, caller: str):
        """Adds a stack trace point for this error.
        The caller will named as 'at caller' in the trace"""
        self.traces.append(Trace(filepath, trace_loc, caller=caller))

    def get_cli_trace(self) -> str:
        """Combines the origin and all stacktraces into a single error
        message which can be printed to the terminal.
        Includes ANSI text coloring."""
        if not self.origin:
            # For some reason, the context was not filled in
            # This is correct for some errors.
            return self.warning
        if self.origin.code is None:
            raise d_CriticalError("A stack trace origin had no code")
        output = (
            "Line: "
            + str(self.origin.loc.line)
            + " Col: "
            + str(self.origin.loc.col)
            + " "
            + color(f"({self.origin.filepath})", Color.FAINT)
            # Line: 1 Col: 34 (someDirectory/someImportedDit.dit)
            + "\n"
            + self.origin.code
            # d_String test = 'Missing Semicolon'
            + "\n"
            + " " * (self.origin.loc.col - 1)  # pad spaces before ^
            + "^"
            #                                  ^
            + "\n" * 2
            + self.warning
            # SyntaxError: Expected ';'
        )

        for trace in self.traces:
            if trace.caller is None:
                raise d_CriticalError("A stack trace had no caller")
            output += (
                "\n\tat "
                + trace.caller
                + color(f" ({trace.filepath})", Color.FAINT)
                + ":"
                + str(trace.loc.line)
                + ":"
                + str(trace.loc.col)
                #         at import (someDirectory/someFile.dit):1:1
            )
        """Total example message follows:

        Line: 1 Col: 34 (someDirectory/someImportedDit.dit)
        d_String test = 'Missing Semicolon'
                                        ^

        SyntaxError: Expected ';'
                at import (someDirectory/someFile.dit):1:1
        """

        return output


class d_CodeError(d_DitError):
    """Raised when a code block has any kind of language specific error"""

    def __init__(self, error: str, lang: str, file: str, loc: CodeLocation = None):
        message = (
            f"Crash from {lang} in file {file}\n" f"Error message follows:\n\n{error}"
        )
        super().__init__(_concat("CodeError", message), loc)


class d_SyntaxError(d_DitError):
    """Raised when there anything goes wrong during paring the file"""

    def __init__(
        self, message: str, loc: Optional[CodeLocation] = None,
    ):
        super().__init__(_concat("SyntaxError", message), loc)
        # _set_origin(self, loc)


class d_NameError(d_DitError):
    """Raised when a name is accessed but does not exist"""

    def __init__(
        self, message: str, loc: Optional[CodeLocation] = None,
    ):
        super().__init__(_concat("NameError", message), loc)
        # _set_origin(self, loc)


class d_AttributeError(d_DitError):
    """Raised when a name is accessed but does not exist"""

    def __init__(self, message: str, loc: CodeLocation = None):
        super().__init__(_concat("AttributeError", message), loc)


class d_TypeMismatchError(d_DitError):
    """Raised when something is assigned to a variable of an incompatible type"""

    def __init__(self, message: str, loc: CodeLocation = None):
        super().__init__(_concat("TypeMismatchError", message), loc)


class d_FileError(d_DitError):
    """Raised when anything goes wrong with importing a file or URL,
    but NOT from the CLI. That file is checked directly in cli.py"""

    def __init__(self, message: str, loc: CodeLocation = None):
        super().__init__(_concat("FileError", message), loc)


class d_EndOfFileError(d_DitError):
    """Raised when the end of the file is reached unexpectedly"""

    def __init__(self, loc: CodeLocation = None) -> None:
        super().__init__(_concat("EndOfFileError", "Unexpected end of file"), loc)


class d_EndOfClangError(d_DitError):
    """Raised when the end of a class is reached unexpectedly"""

    def __init__(self, clang_name, loc: CodeLocation = None) -> None:
        super().__init__(
            _concat("EndOfFileError", f"Unexpected end of {clang_name}"), loc
        )


class d_MissingPropError(d_DitError):
    """Raised when a language was missing a required property to be used
    as a a guest language"""

    def __init__(self, lang: str, prop: str, loc: CodeLocation = None):
        super().__init__(
            _concat(
                "MissingPropError",
                f"lang '{lang}' was missing a required prop, '{prop}'",
            ),
            loc,
        )


class d_CriticalError(d_DitError):
    """Essentially an assertion. This exception should never be raised.
    Will error out to the command line like other exceptions."""

    def __init__(self, message: str, loc: CodeLocation = None):
        super().__init__(_concat("CriticalError", message), loc)


"""
def _set_origin(
    err: d_DitError, inter: InterpretContext = None, loc: Optional[CodeLocation] = None
):
    if not inter:
        return
    loc = loc or inter.next_tok.loc
    err.set_origin(inter.body.path, loc, inter.char_feed.get_line(loc))
"""


def _concat(prepend: str, message: str) -> str:
    return color(prepend + ": ", Color.RED) + message
