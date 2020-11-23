from __future__ import annotations

from dataclasses import dataclass
from typing import Any as AnyHint
from typing import Callable, Generator, Iterator
from typing import List as ListHint
from typing import Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dit_cli.data_classes import CodeLocation
from dit_cli.exceptions import CriticalError, FileError, TypeMismatchError
from dit_cli.grammar import Grammar, prim_to_value, value_to_prim


class d_Thing(object):
    def __init__(self, grammar: Grammar, name: str) -> None:
        self.grammar = grammar
        self.name = name
        self.public_type: str = "Object"
        self.py_func: Callable = None  # type: ignore

    def set_value(self, new_value: AnyHint) -> None:
        # Python "virtual" method
        raise CriticalError("Virtual func Object.set_value called")

'''
class Any(Object):
    def __init__(self, name: str) -> None:
        super().__init__(Grammar.VALUE_ANY, name)
        self.any_value: Object = None  # type: ignore

    def set_value(self, new_value: Arg) -> None:
        if isinstance(new_value, str):
            self.any_value = String(self.name)
        elif isinstance(new_value, list):
            self.any_value = List(Grammar.VALUE_ANY, self.name)
        elif isinstance(new_value, Object):  # type: ignore
            self.any_value = new_value
        else:
            raise CriticalError("Unrecognized type for Any assignment")
'''

class d_String(d_Thing):
    def __init__(self, name: str) -> None:
        super().__init__(Grammar.VALUE_STRING, name)
        self.string_value: str = None  # type: ignore
        self.public_type: str = "String"

    def set_value(self, new_value: Arg) -> None:
        if isinstance(new_value, Any):
            new_value = new_value.any_value
        elif isinstance(new_value, str):
            self.string_value = new_value
        elif isinstance(new_value, String):
            self.string_value = new_value.string_value
        elif isinstance(new_value, list):
            raise TypeMismatchError("Cannot assign List to String")
        elif isinstance(new_value, Object):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to String")
        else:
            raise CriticalError("Unrecognized type for string assignment")


class d_List(Object):
    def __init__(self, grammar: Grammar, name: str) -> None:
        super().__init__(Grammar.VALUE_LIST, name)
        self.contained_grammar: Grammar = grammar
        self.list_value: ListHint[Arg] = None  # type: ignore
        self.public_type: str = "List"

    def set_value(self, new_value: Arg) -> None:
        if isinstance(new_value, Any):
            new_value = new_value.any_value
        elif isinstance(new_value, list):
            self.list_value = new_value
        elif isinstance(new_value, List):
            self.list_value = new_value.list_value
        elif isinstance(new_value, str):
            raise TypeMismatchError("Cannot assign String to List")
        elif isinstance(new_value, Object):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to List")
        else:
            raise CriticalError("Unrecognized type for list assignment")

        _check_list_type(self)


def _check_list_type(list_: List) -> None:
    if list_.contained_grammar == Grammar.VALUE_ANY:
        return
    prim: str = value_to_prim(list_.contained_grammar).value
    for ele in _traverse(list_.list_value):
        if isinstance(ele, str):
            if list_.contained_grammar != Grammar.VALUE_STRING:
                raise TypeMismatchError(f"List of type '{prim}' contained 'String'")
        elif isinstance(ele, Object):  # type: ignore
            if ele.grammar != list_.contained_grammar:
                e_prim = value_to_prim(ele.grammar).value
                raise TypeMismatchError(f"List of type '{prim}' contained '{e_prim}'")
        else:
            raise CriticalError("Unrecognized type for list check")


def _traverse(item: Arg) -> Iterator[Union[Object, str]]:
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    if isinstance(item, list):
        for i in item:
            for j in _traverse(i):
                yield j
    else:
        yield item


class Body(Object):
    def __init__(self, grammar: Grammar, name: str) -> None:
        super().__init__(grammar, name)
        self.path: str = None  # type: ignore
        self.primitive_loc: CodeLocation = None  # type: ignore
        self.start_loc: CodeLocation = None  # type: ignore
        self.end_loc: CodeLocation = None  # type: ignore
        self.view: memoryview = None  # type: ignore
        self.containing_scope: Body = None  # type: ignore
        self.attrs: ListHint[Object] = []
        self.public_type: str = "Body"

    def is_ready(self) -> bool:
        if self.view is None:
            raise CriticalError("A body had no view during readying")
        return len(self.view) > 0

    def set_value(self, new_value: Arg) -> None:
        if isinstance(new_value, Any):
            new_value = new_value.any_value
        elif isinstance(new_value, Body):
            self.attrs = new_value.attrs
            self.containing_scope = new_value.containing_scope
            self.view = new_value.view
            self.path = new_value.path
            return
        elif isinstance(new_value, str):
            raise TypeMismatchError(f"Cannot assign String to {self.public_type}")
        elif isinstance(new_value, list):
            raise TypeMismatchError(f"Cannot assign List to {self.public_type}")
        else:  # isinstance(new_value, Object):
            raise TypeMismatchError(
                f"Cannot assign {new_value.public_type} to {self.public_type}"
            )

    def add_attr(self, dec: Declarable) -> Object:
        if dec.name is None:
            raise CriticalError("An declarable had no name")
        if self.find_attr(dec.name):
            raise CriticalError(f"A duplicate attribute was found: '{dec.name}'")
        obj = _type_to_obj(dec, self)
        self.attrs.append(obj)
        return obj

    def find_attr(self, name: str, previous: Optional[Body] = None) -> Optional[Object]:
        if previous:
            # search in previous, no matter what kind of body object it is
            for attr in previous.attrs:
                if attr.name == name:
                    return attr
            return None
        for scope in _all_scopes(self):
            for attr in scope.attrs:
                if attr.name == name:
                    return attr
        return None

    def finalize(self) -> None:
        if self.path is None:
            self.path = self.containing_scope.path
        if self.view is None:
            # Dit sets the view itself, from a file/URL
            self.view = memoryview(
                self.containing_scope.view[self.start_loc.pos : self.end_loc.pos]
            )


def _type_to_obj(dec: Declarable, containing_scope: Body) -> Object:
    if dec.type_ is None:
        raise CriticalError("A declarable had no type")
    elif isinstance(dec.type_, Class):
        return Instance(dec.name, dec.type_)

    if dec.listof:
        return List(prim_to_value(dec.type_), dec.name)
    if dec.type_ == Grammar.PRIMITIVE_ANY:
        return Any(dec.name)
    if dec.type_ == Grammar.PRIMITIVE_STRING:
        return String(dec.name)
    if dec.type_ == Grammar.PRIMITIVE_CLASS:
        return Class(dec.name, containing_scope)
    if dec.type_ == Grammar.PRIMITIVE_INSTANCE:
        return Instance(dec.name, parent=None)  # type: ignore
    if dec.type_ == Grammar.PRIMITIVE_FUNC:
        return Function(dec.name, containing_scope)
    if dec.type_ == Grammar.PRIMITIVE_DIT:
        return Dit(dec.name, path=None)  # type: ignore

    raise CriticalError("Unrecognized type for declaration")


def _all_scopes(body: Body) -> Generator[Body, None, None]:
    yield body
    if body.containing_scope:
        for scope in _all_scopes(body.containing_scope):
            yield scope


class Dit(Body):
    def __init__(self, name: str, path: str) -> None:
        super().__init__(Grammar.VALUE_DIT, name)
        self.path = path
        self.start_loc = CodeLocation(0, 1, 1)
        self.public_type: str = "Dit"

    @staticmethod
    def from_str(name: str, code: str, mock_path: str) -> "Dit":
        # Currently used by integration tests, which have dits stored in json files
        dit = Dit(name=name, path=mock_path)
        dit.view = memoryview(code.encode())
        return dit

    def finalize(self) -> None:
        self.handle_filepath()
        super().finalize()

    def handle_filepath(self) -> None:
        if self.view:
            return
        if self.path is None:
            raise CriticalError("A dit had no path")
        if self.path.startswith("https://") or self.path.startswith("http://"):
            try:
                contents = urlopen(self.path).read().decode()
            except (HTTPError, URLError) as error:
                raise FileError(f"Import failed, {error}")
        else:
            try:
                with open(self.path) as file_object:
                    contents = file_object.read()
            except FileNotFoundError:
                raise FileError("Import failed, file not found")
            except PermissionError:
                raise FileError("Import failed, permission denied")
            except IsADirectoryError:
                raise FileError("Import failed, not a directory")

        self.view = memoryview(contents.encode())


class Class(Body):
    def __init__(self, name: str, containing_scope: Body) -> None:
        super().__init__(Grammar.VALUE_CLASS, name=name)
        self.containing_scope = containing_scope
        self.public_type: str = "Class"


class Instance(Object):
    def __init__(self, name: str, parent: Class) -> None:
        super().__init__(Grammar.VALUE_INSTANCE, name)
        self.parent = parent
        self.attrs: ListHint[Object] = []
        self.public_type: str = "Instance"

    def find_attr(self, name: str) -> Optional[Object]:
        for attr in self.attrs:
            if attr.name == name:
                return attr
        return None


class Language(Object):
    pass


class Function(Body):
    def __init__(self, name: str, containing_scope: Body) -> None:
        super().__init__(Grammar.VALUE_FUNC, name)
        self.public_type: str = "Function"
        self.containing_scope = containing_scope
        self.lang: Language = None  # type: ignore
        self.return_: Type = None  # type: ignore
        self.parameters: ListHint[Declarable] = []
        self.is_built_in: bool = False


Arg = Union[Object, str, list]
Type = Union[Grammar, Class]


class FlowControlException(Exception):
    """Base class for all exceptions used for flow control rather than errors."""

    def __init__(self, value: Arg, orig_loc: CodeLocation):
        self.value: Arg = value
        self.orig_loc: CodeLocation = orig_loc


class ReturnController(FlowControlException):
    """Raised when a function executes a return statement"""

    def __init__(self, value: Arg, orig_loc: CodeLocation):
        super().__init__(value, orig_loc)


class ThrowController(FlowControlException):
    """Raised when a function executes a throw statement"""

    def __init__(self, value: Arg, orig_loc: CodeLocation):
        super().__init__(value, orig_loc)


@dataclass
class Token:
    """A single bit of meaning taken from dit code.
    loc must be copy.deepcopy from the char_feed before this is created
    word will contain the name of NEW_NAME grammars.
    obj will contain the Object of VALUE_x grammars."""

    grammar: Grammar
    loc: CodeLocation
    word: str = None  # type: ignore
    obj: Object = None  # type: ignore


@dataclass
class Declarable:
    type_: Type = None  # type: ignore
    name: str = None  # type: ignore
    listof: bool = False  # type: ignore
