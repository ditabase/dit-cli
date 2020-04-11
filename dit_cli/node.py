"""Home of the Node class"""

from typing import List, TYPE_CHECKING

from dit_cli import CONFIG
from dit_cli.exceptions import NodeError
from dit_cli.dataclasses import Expression, Attribute, NameConflict
if TYPE_CHECKING:
    from dit_cli.namespace import Namespace


class Node:
    """Represents a class or object in this namespace."""

    def __init__(self, namespace: 'Namespace', name: str, type_: str):
        namespace.raise_if_defined(name)

        self.namespace: 'Namespace' = namespace
        self.name: str = name
        self.type_: str = type_

        self.attrs: List[Attribute] = []
        self.conflicts: List[NameConflict] = []
        self.extends: List[Node] = []
        self.validator: dict = None  # {code, lang}
        self.print: dict = None  # {code, lang, expr, class_}

    def add_extend(self, extend_expr: List[str]):
        """Make the current node extend another node,
        given the name of that node."""
        if _expr_is_string(extend_expr):
            if self.type_ == 'class':
                raise NodeError('Cannot extend String')
            else:
                raise NodeError('Top level objects cannot be String')

        new_c: Node = self.namespace.read(extend_expr)

        if self == new_c:
            raise NodeError(
                f'Illegal recursive extension in class "{self.name}"')

        if new_c in self.extends:
            raise NodeError((
                f'"{self.name}" already '
                f'extends "{new_c.name}"'
            ))

        # Check if the new class (and all it's parent classes) have
        # duplicate names to existing extended classes,
        # and need deobfuscation.
        if self.type_ == 'class':
            _extend_conflicts(self, new_c)
        self.extends.append(new_c)

    def add_attribute(self, type_expr: List[str],
                      name: str, list_: bool = False):
        """Make the current node contain a new attribute"""
        if _expr_is_string(type_expr):
            new_c = 'String'
        else:
            new_c = self.namespace.read(type_expr)

        if self == new_c:
            raise NodeError(
                f'Illegal recursive attribution in class "{self.name}"')

        for attr in self.attrs:
            if name == attr.name:
                raise NodeError(
                    f'"{self.name}" already has attribute "{name}"')

        attr = Attribute(name, new_c, list_, None, None)

        # Check if this specifc attribute already exists in parent classes.
        _attr_conflicts(attr, self, self)
        self.attrs.append(attr)

    def set_print(self, expr: List[str] = None,
                  code: str = None, lang: str = None):
        """Give the current node a print function,
        either with code or a contained variable"""
        # Make sure variable to be printed is defined
        class_ = None
        if expr:
            read_expr = Expression(self.namespace, self, None, expr)
            class_ = self.namespace.read(read_expr)

        # Make sure language exists in config
        # WET also appears in set_validator
        if lang and not lang in CONFIG:
            raise NodeError(f'"{lang}" does not exist in .dit-languages')

        self.print = {'expr': expr, 'code': code,
                      'lang': lang, 'class_': class_}

    def set_validator(self, code: str, lang: str):
        """Give the current node a validator"""
        # Make sure language exists in config
        # WET also appears in set_validator
        if lang and not lang in CONFIG:
            raise NodeError(f'"{lang}" does not exist in .dit-languages')
        self.validator = {'code': code, 'lang': lang}


def _expr_is_string(expr: List[str]) -> bool:
    return len(expr) == 1 and expr[0] == 'String'


def _extend_conflicts(orig: Node, new_c: Node):
    # Look through new_c tree, and add conflicts
    def _recurse_target(orig: Node, source: Node, target: Node):
        for tar in target.extends:
            _recurse_target(orig, source, tar)

        for src_attr in source.attrs:
            for tar_attr in target.attrs:
                if src_attr.name == tar_attr.name:
                    conf = NameConflict(target, tar_attr.name)
                    orig.conflicts.append(conf)

    # Look through existing tree
    def _recurse_orig(orig: Node, source: Node, target: Node):
        for src in source.extends:
            _recurse_orig(orig, src, target)

        _recurse_target(orig, source, target)

    # Start with just the extensions of this class
    for ext in orig.extends:
        _recurse_orig(orig, ext, new_c)


def _attr_conflicts(attr: Attribute, orig: Node, target: Node):
    # Recurse through all target classes (target starts as orig)
    for tar in target.extends:
        _attr_conflicts(attr, orig, tar)

    # Look for comparisons, but only to this attr
    for tar_attr in target.attrs:
        if attr.name == tar_attr.name:
            conf = NameConflict(target, tar_attr.name)
            orig.conflicts.append(conf)
