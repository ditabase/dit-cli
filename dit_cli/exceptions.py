"""All Exceptions used by dit_cli"""

from dataclasses import dataclass
from typing import Any, List

from dit_cli.color import Color, color
from dit_cli.data_classes import CodeLocation


@dataclass
class Trace:
    """Represents a point along the stack trace of an error,
    or the origin itself."""

    filepath: str
    loc: CodeLocation
    code: str = None  # type: ignore
    caller: str = None  # type: ignore


class DitError(Exception):
    """Base Class for all dit exceptions"""

    def __init__(self, prepend: str, message: str):
        self.warning = color(prepend + ": ", Color.RED) + message
        super().__init__(self.warning)
        self.origin: Trace = None  # type: ignore
        self.traces: List[Trace] = []

    def set_origin(self, filepath: str, loc: CodeLocation, code: str):
        """Sets the location in code of this error.
        The location will be highlighted in the terminal by a carrot ^"""
        self.origin = Trace(filepath, loc, code=code)

    def add_trace(self, filepath: str, loc: CodeLocation, caller: str):
        """Adds a stack trace point for this error.
        The caller will named as 'at caller' in the trace"""
        self.traces.append(Trace(filepath, loc, caller=caller))

    def get_cli_trace(self) -> str:
        """Combines the origin and all stacktraces into a single error
        message which can be printed to the terminal.
        Includes ANSI text coloring."""
        if self.origin is None:
            # For some reason, the context was not filled in
            # This is correct for some errors.
            return self.warning
        if self.origin.code is None:
            raise CriticalError("A stack trace origin had no code")
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
                raise CriticalError("A stack trace had no caller")
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


class CodeError(DitError):
    """Raised when a code block has any kind of language specifc error"""

    def __init__(self, error: str, lang: str, file: str):
        message = (
            f"Crash from {lang} in file {file}\n" f"Error message follows:\n\n{error}"
        )
        super().__init__("CodeError", message)


class SyntaxError_(DitError):
    """Raised when there anything goes wrong during paring the file"""

    def __init__(self, message: str):
        super().__init__("SyntaxError", message)


class TypeMismatchError(DitError):
    """Raised when something is assigned to a variable of an incompatible type"""

    def __init__(self, message: str):
        super().__init__("TypeMismatchError", message)


class FileError(DitError):
    """Raised when anything goes wrong with importing a file or URL,
    but NOT from the CLI. That file is checked directly in cli.py"""

    def __init__(self, message: str):
        super().__init__("FileError", message)


class EndOfFileError(DitError):
    """Raised when the end of the file is reached unexpectedly"""

    def __init__(self) -> None:
        super().__init__("EndOfFileError", "Unexpected end of file")


class EndOfClangError(DitError):
    """Raised when the end of a class is reached unexpectedly"""

    def __init__(self, clang_name) -> None:
        super().__init__("EndOfFileError", f"Unexpected end of {clang_name}")


class CriticalError(DitError):
    """Essentially an assertion. This exception should never be raised.
    Will error out to the command line like other exceptions."""

    def __init__(self, message: str):
        super().__init__("CriticalError", message)
