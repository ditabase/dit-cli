"""Stores several dataclasses, which have no dependencies, but are
used in various places all over the project"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from dit_cli.object import Object
    from dit_cli.grammar import Grammar


@dataclass
class ScriptEvalJob:
    """Represents a script to be evaled. Sent from the evaler to the lang_daemon."""

    lang: str
    file_path: str
    active: bool = False
    crash: bool = False
    result: str = None


@dataclass
class CodeLocation:
    """Represents a position in a memoryview of code
    view[pos] will always be the current char
    line is incremented at every \n and col is reset to 0"""

    pos: int
    col: int
    line: int


@dataclass
class Token:
    """A single bit of meaning taken from dit code.
    loc must be copy.deepcopy from the char_feed before this is created
    data will contain the name of NEW_NAME grammars,
    or a reference to the Object of VALUE_x grammars."""

    grammar: "Grammar"
    loc: CodeLocation
    data: Union[str, "Object"] = None
