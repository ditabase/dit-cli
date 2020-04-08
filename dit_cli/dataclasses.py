"""Stores several dataclasses, which have no dependencies, but are
used in various places all over the project"""

from dataclasses import dataclass, field
from typing import List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from dit_cli.namespace import Namespace
    from dit_cli.node import Node


@dataclass
class Expression:
    """Represents a variable expression 'SomeVar.SomeOtherVar' to be used
    by the variable system. Includes context of where this expression
    appears so that expressions do not need to be fully qualified.

    Only the expression is needed, so long as it is fully qualified.
    If a class is given, the expression will start from there.
    If an object is given, assignments will target that object."""
    namespace: 'Namespace'
    class_: 'Node'
    obj: 'Node'
    expression: List[str]


@dataclass
class NameConflict:
    """Stores info about identical names of attributes
    caused by inheritance."""
    class_: 'Node'
    var: str
    # quick with dataclasses, this is how you assign a default
    # This is just an empty list.
    namespaces: List['Namespace'] = field(default_factory=lambda: [])


@dataclass
class Attribute:
    """Stores info about a value that a node contains,
    as well as that value itself. This could be a string, list, or object.
    This is how the recursive containment structure works.
    All objects are either top level, contained by a namespace, or contained
    by another object in one of these Attributes.

    Includes a NameConflict, in case this specific attribute's name
    conflicts with another Attribute in the same Node."""
    name: str
    class_: 'Node'
    list_: bool
    data: Any
    conf: NameConflict


@dataclass
class EvalContext:
    """Stores info about the the current evaluation state.
    Used to generate Expressions, or create code of the correct type."""
    obj: 'Node'
    class_: 'Node'
    namespace: 'Namespace'
    lang: dict = None
    print_: bool = False
