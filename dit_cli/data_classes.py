"""Stores several dataclasses, which have no dependencies, but are
used in various places all over the project"""

from dataclasses import dataclass


@dataclass
class ScriptEvalJob:
    """Represents a script to be evaled. Sent from the evaler to the lang_daemon."""

    lang: str
    file_path: str
    active: bool = False
    crash: bool = False
    result: str = None  # type: ignore


@dataclass
class CodeLocation:
    """Represents a position in a memoryview of code
    view[pos] will always be the current char
    line is incremented at every \n and col is reset to 0"""

    pos: int
    col: int
    line: int
