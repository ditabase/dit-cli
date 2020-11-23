from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator, Iterator, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dit_cli.data_classes import CodeLocation
from dit_cli.exceptions import CriticalError, FileError, TypeMismatchError
from dit_cli.grammar import d_Grammar, prim_to_value, value_to_prim


class d_Thing(object):
    def __init__(self, grammar: d_Grammar, name: str) -> None:
        self.grammar = grammar
        self.name = name
        self.public_type: str = "Thing"
        self.py_func: Callable = None  # type: ignore
        self.is_anything: bool = False

    def set_value(self, new_value: d_Arg) -> None:
        # Python "virtual" method
        raise CriticalError("Virtual func Thing.set_value called")


class d_String(d_Thing):
    def __init__(self, name: str) -> None:
        super().__init__(d_Grammar.VALUE_STRING, name)
        self.string_value: str = None  # type: ignore
        self.public_type: str = "String"

    def set_value(self, new_value: d_Arg) -> None:
        if isinstance(new_value, str):
            self.string_value = new_value
        elif isinstance(new_value, d_String):
            self.string_value = new_value.string_value
        elif isinstance(new_value, list):
            raise TypeMismatchError("Cannot assign List to String")
        elif type(new_value) == d_Thing:
            pass
        elif isinstance(new_value, d_Thing):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to String")
        else:
            raise CriticalError("Unrecognized type for string assignment")


class d_List(d_Thing):
    def __init__(self, grammar: d_Grammar, name: str) -> None:
        super().__init__(d_Grammar.VALUE_LIST, name)
        self.contained_grammar: d_Grammar = grammar
        self.list_value: List[d_Arg] = None  # type: ignore
        self.public_type: str = "List"

    def set_value(self, new_value: d_Arg) -> None:
        if isinstance(new_value, list):
            self.list_value = new_value
        elif isinstance(new_value, d_List):
            self.list_value = new_value.list_value
        elif isinstance(new_value, str):
            raise TypeMismatchError("Cannot assign String to List")
        elif type(new_value) == d_Thing:
            pass
        elif isinstance(new_value, d_Thing):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to List")
        else:
            raise CriticalError("Unrecognized type for list assignment")

        _check_list_type(self)


def _check_list_type(list_: d_List) -> None:
    if list_.contained_grammar == d_Grammar.VALUE_THING:
        return
    prim: str = value_to_prim(list_.contained_grammar).value
    for ele in _traverse(list_.list_value):
        if isinstance(ele, str):
            if list_.contained_grammar != d_Grammar.VALUE_STRING:
                raise TypeMismatchError(f"List of type '{prim}' contained 'String'")
        elif isinstance(ele, d_Thing):  # type: ignore
            if ele.grammar != list_.contained_grammar:
                e_prim = value_to_prim(ele.grammar).value
                raise TypeMismatchError(f"List of type '{prim}' contained '{e_prim}'")
        else:
            raise CriticalError("Unrecognized type for list check")


def _traverse(item: d_Arg) -> Iterator[Union[d_Thing, str]]:
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    if isinstance(item, list):
        for i in item:
            for j in _traverse(i):
                yield j
    else:
        yield item


class d_Body(d_Thing):
    def __init__(self, d_Grammar: d_Grammar, name: str) -> None:
        super().__init__(d_Grammar, name)
        self.path: str = None  # type: ignore
        self.primitive_loc: CodeLocation = None  # type: ignore
        self.start_loc: CodeLocation = None  # type: ignore
        self.end_loc: CodeLocation = None  # type: ignore
        self.view: memoryview = None  # type: ignore
        self.containing_scope: d_Body = None  # type: ignore
        self.attrs: List[d_Thing] = []
        self.public_type: str = "Body"

    def is_ready(self) -> bool:
        if self.view is None:
            raise CriticalError("A body had no view during readying")
        return len(self.view) > 0

    def set_value(self, new_value: d_Arg) -> None:
        if type(new_value) == d_Thing:
            pass
        elif isinstance(new_value, d_Body):
            self.attrs = new_value.attrs
            self.containing_scope = new_value.containing_scope
            self.view = new_value.view
            self.path = new_value.path
            return
        elif isinstance(new_value, str):
            raise TypeMismatchError(f"Cannot assign String to {self.public_type}")
        elif isinstance(new_value, list):
            raise TypeMismatchError(f"Cannot assign List to {self.public_type}")
        else:  # isinstance(new_value, d_Thing):
            raise TypeMismatchError(
                f"Cannot assign {new_value.public_type} to {self.public_type}"
            )

    def add_attr(self, dec: Declarable) -> d_Thing:
        if dec.name is None:
            raise CriticalError("An declarable had no name")
        if self.find_attr(dec.name):
            raise CriticalError(f"A duplicate attribute was found: '{dec.name}'")
        obj = _type_to_obj(dec, self)
        self.attrs.append(obj)
        return obj

    def find_attr(
        self, name: str, previous: Optional[d_Body] = None
    ) -> Optional[d_Thing]:
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
            # d_Dit sets the view itself, from a file/URL
            self.view = memoryview(
                self.containing_scope.view[self.start_loc.pos : self.end_loc.pos]
            )


def _type_to_obj(dec: Declarable, containing_scope: d_Body) -> d_Thing:
    if dec.type_ is None:
        raise CriticalError("A declarable had no type")
    elif isinstance(dec.type_, d_Class):
        return d_Instance(dec.name, dec.type_)

    if dec.listof:
        return d_List(prim_to_value(dec.type_), dec.name)
    if dec.type_ == d_Grammar.PRIMITIVE_THING:
        return d_Thing(d_Grammar.VALUE_THING, dec.name)
    if dec.type_ == d_Grammar.PRIMITIVE_STRING:
        return d_String(dec.name)
    if dec.type_ == d_Grammar.PRIMITIVE_CLASS:
        return d_Class(dec.name, containing_scope)
    if dec.type_ == d_Grammar.PRIMITIVE_INSTANCE:
        return d_Instance(dec.name, parent=None)  # type: ignore
    if dec.type_ == d_Grammar.PRIMITIVE_FUNC:
        return d_Function(dec.name, containing_scope)
    if dec.type_ == d_Grammar.PRIMITIVE_DIT:
        return d_Dit(dec.name, path=None)  # type: ignore

    raise CriticalError("Unrecognized type for declaration")


def _all_scopes(body: d_Body) -> Generator[d_Body, None, None]:
    yield body
    if body.containing_scope:
        for scope in _all_scopes(body.containing_scope):
            yield scope


class d_Dit(d_Body):
    def __init__(self, name: str, path: str) -> None:
        super().__init__(d_Grammar.VALUE_DIT, name)
        self.path = path
        self.start_loc = CodeLocation(0, 1, 1)
        self.public_type: str = "Dit"

    @staticmethod
    def from_str(name: str, code: str, mock_path: str) -> "d_Dit":
        # Currently used by integration tests, which have dits stored in json files
        dit = d_Dit(name=name, path=mock_path)
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


class d_Class(d_Body):
    def __init__(self, name: str, containing_scope: d_Body) -> None:
        super().__init__(d_Grammar.VALUE_CLASS, name=name)
        self.containing_scope = containing_scope
        self.public_type: str = "Class"


class d_Instance(d_Thing):
    def __init__(self, name: str, parent: d_Class) -> None:
        super().__init__(d_Grammar.VALUE_INSTANCE, name)
        self.parent = parent
        self.attrs: List[d_Thing] = []
        self.public_type: str = "Instance"

    def find_attr(self, name: str) -> Optional[d_Thing]:
        for attr in self.attrs:
            if attr.name == name:
                return attr
        return None


class d_Language(d_Thing):
    pass


class d_Function(d_Body):
    def __init__(self, name: str, containing_scope: d_Body) -> None:
        super().__init__(d_Grammar.VALUE_FUNC, name)
        self.public_type: str = "Function"
        self.containing_scope = containing_scope
        self.lang: Language = None  # type: ignore
        self.return_: d_Type = None  # type: ignore
        self.parameters: List[Declarable] = []
        self.is_built_in: bool = False


d_Arg = Union[d_Thing, str, list]
d_Type = Union[d_Grammar, d_Class]


class FlowControlException(Exception):
    """Base class for all exceptions used for flow control rather than errors."""

    def __init__(self, value: d_Arg, orig_loc: CodeLocation):
        self.value: d_Arg = value
        self.orig_loc: CodeLocation = orig_loc


class ReturnController(FlowControlException):
    """Raised when a function executes a return statement"""

    def __init__(self, value: d_Arg, orig_loc: CodeLocation):
        super().__init__(value, orig_loc)


class ThrowController(FlowControlException):
    """Raised when a function executes a throw statement"""

    def __init__(self, value: d_Arg, orig_loc: CodeLocation):
        super().__init__(value, orig_loc)


@dataclass
class Token:
    """A single bit of meaning taken from dit code.
    loc must be copy.deepcopy from the char_feed before this is created
    word will contain the name of NEW_NAME grammars.
    obj will contain the d_Thing of VALUE_x grammars."""

    grammar: d_Grammar
    loc: CodeLocation
    word: str = None  # type: ignore
    thing: d_Thing = None  # type: ignore


@dataclass
class Declarable:
    type_: d_Type = None  # type: ignore
    name: str = None  # type: ignore
    listof: bool = False  # type: ignore
