from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator, Iterator, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dit_cli.data_classes import CodeLocation
from dit_cli.exceptions import CriticalError, FileError, TypeMismatchError
from dit_cli.grammar import d_Grammar, prim_to_value, value_to_prim


class d_Thing(object):
    null_singleton: Optional[d_Thing] = None

    def __init__(self) -> None:
        self.public_type: str = "Thing"
        self.grammar: d_Grammar = d_Grammar.VALUE_THING

        self.name: str = None  # type: ignore
        self.py_func: Callable = None  # type: ignore
        self.can_be_anything: bool = False
        self.is_null: bool = True

    def set_value(self, new_value: d_Thing) -> None:
        # alter own class to *become* the type it is assigned to.
        # note that 'can_be_anything' is still True
        # and public_type is still "Thing"
        if isinstance(new_value, d_Thing):  # type: ignore
            self.__class__ = new_value.__class__
            self.grammar = new_value.grammar
            self.public_type = new_value.public_type
        else:
            raise CriticalError("Unrecognized type for thing assignment")

        # After altering class, set the actual value using subclass set_value
        self.set_value(new_value)

    @classmethod
    def get_null_thing(cls) -> d_Thing:
        if cls.null_singleton is None:
            cls.null_singleton = d_Thing()
            cls.null_singleton.grammar = d_Grammar.NULL
            cls.null_singleton.public_type = "null"
        return cls.null_singleton


class d_String(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "String"
        self.grammar = d_Grammar.VALUE_STRING

        self.string_value: str = None  # type: ignore

    def set_value(self, new_value: d_Thing) -> None:
        self.is_null = new_value.is_null
        if isinstance(new_value, d_String):
            # String test = 'cat';
            # All normal string assignments to String or Thing
            self.string_value = new_value.string_value
        elif self.can_be_anything:
            # Thing test = 'cat';
            # test = ['dog', 'bird'];
            super().set_value(new_value)
        elif type(new_value) is d_Thing:
            # Thing test1;
            # String test2 = test1;
            pass
        elif isinstance(new_value, d_Thing):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to String")
        else:
            raise CriticalError("Unrecognized type for string assignment")


class d_List(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "List"
        self.grammar = d_Grammar.VALUE_LIST

        self.contained_type: d_Type = None  # type: ignore
        self.list_value: List[d_Thing] = None  # type: ignore

    def set_value(self, new_value: d_Thing) -> None:
        self.is_null = new_value.is_null
        if isinstance(new_value, d_List):
            # listOf String = ['1', '2'];
            self.list_value = new_value.list_value
            _check_list_type(self)
        elif self.can_be_anything:
            super().set_value(new_value)
        elif type(new_value) is d_Thing:
            # listof Thing test1;
            # listOf String test2 = test1;
            pass
        elif isinstance(new_value, d_Thing):  # type: ignore
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to List")
        else:
            raise CriticalError("Unrecognized type for list assignment")


def _check_list_type(list_: d_List) -> None:
    if list_.can_be_anything:
        list_.contained_type = d_Grammar.VALUE_THING
        return
    elif list_.contained_type == d_Grammar.VALUE_THING:
        return
    elif isinstance(list_.contained_type, d_Class):
        raise NotImplementedError

    actual: str = value_to_prim(list_.contained_type).value
    for ele in _traverse(list_.list_value):
        ele: d_Thing
        if ele.is_null:
            continue
        elif ele.grammar != list_.contained_type:
            expected = value_to_prim(ele.grammar).value
            raise TypeMismatchError(f"List of type '{actual}' contained '{expected}'")


def _traverse(item: Union[list, d_Thing]) -> Iterator[d_Thing]:
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    if isinstance(item, list):
        for i in item:
            for j in _traverse(i):
                yield j
    else:
        yield item


class d_Body(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.path: str = None  # type: ignore
        self.primitive_loc: CodeLocation = None  # type: ignore
        self.start_loc: CodeLocation = None  # type: ignore
        self.end_loc: CodeLocation = None  # type: ignore
        self.view: memoryview = None  # type: ignore
        self.containing_scope: d_Body = None  # type: ignore
        self.attrs: List[d_Thing] = []

    def is_ready(self) -> bool:
        if self.view is None:
            raise CriticalError("A body had no view during readying")
        return len(self.view) > 0

    def set_value(self, new_value: d_Thing) -> None:
        self.is_null = new_value.is_null
        if isinstance(new_value, d_Body):
            self.attrs = new_value.attrs
            self.containing_scope = new_value.containing_scope
            self.view = new_value.view
            self.path = new_value.path
        elif type(new_value) is d_Thing:
            # Thing test;
            # Func test2 = test;
            pass
        elif self.can_be_anything:
            super().set_value(new_value)
        else:  # isinstance(new_value, d_Thing):
            raise TypeMismatchError(
                f"Cannot assign {new_value.public_type} to {self.public_type}"  # type: ignore
            )

    def add_attr(self, dec: Declarable, value: Optional[d_Thing] = None) -> d_Thing:
        if dec.name is None:
            raise CriticalError("A declarable had no name")
        if self.find_attr(dec.name):
            raise CriticalError(f"A duplicate attribute was found: '{dec.name}'")
        if value is not None:
            res = _check_value(value, dec)
            if res is not None:
                raise TypeMismatchError(f"Cannot assign {res.actual} to {res.expected}")
            value.name = dec.name
            if dec.type_ == d_Grammar.PRIMITIVE_THING:
                value.can_be_anything = True
        else:
            value = _type_to_obj(dec, self)

        self.attrs.append(value)
        return value

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
    thing: d_Thing = None  # type: ignore
    if dec.type_ is None:
        raise CriticalError("A declarable had no type")
    elif isinstance(dec.type_, d_Class):
        thing = d_Instance()
        thing.parent = dec.type_

    if dec.listof:
        thing = d_List()
        # this prim_to_value might fail with classes
        thing.contained_type = prim_to_value(dec.type_)  # type: ignore
    elif dec.type_ == d_Grammar.PRIMITIVE_THING:
        thing = d_Thing()
        thing.can_be_anything = True
    elif dec.type_ == d_Grammar.PRIMITIVE_STRING:
        thing = d_String()
    elif dec.type_ == d_Grammar.PRIMITIVE_CLASS:
        thing = d_Class()
        thing.containing_scope = containing_scope
    elif dec.type_ == d_Grammar.PRIMITIVE_INSTANCE:
        thing = d_Instance()
    elif dec.type_ == d_Grammar.PRIMITIVE_FUNC:
        thing = d_Function()
        thing.containing_scope = containing_scope
    elif dec.type_ == d_Grammar.PRIMITIVE_DIT:
        thing = d_Dit()

    if thing is None:
        raise CriticalError("Unrecognized type for declaration")
    else:
        thing.name = dec.name
        return thing


class d_Dit(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Dit"
        self.grammar = d_Grammar.VALUE_DIT

        self.start_loc = CodeLocation(0, 1, 1)

    @staticmethod
    def from_str(name: str, code: str, mock_path: str) -> d_Dit:
        # Currently used by integration tests, which have dits stored in json files
        dit = d_Dit()
        dit.name = name
        dit.path = mock_path
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
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Class"
        self.grammar = d_Grammar.VALUE_CLASS


class d_Instance(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Instance"
        self.grammar = d_Grammar.VALUE_INSTANCE
        self.parent: d_Class = None  # type: ignore
        self.attrs: List[d_Thing] = []

    def find_attr(self, name: str) -> Optional[d_Thing]:
        for attr in self.attrs:
            if attr.name == name:
                return attr
        return None


class d_Language(d_Thing):
    pass


class d_Function(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Function"
        self.grammar = d_Grammar.VALUE_FUNC

        self.orig_loc: CodeLocation = None  # type: ignore
        self.lang: d_Grammar = None  # type: ignore
        self.return_: d_Type = None  # type: ignore
        self.return_list: bool = None  # type: ignore
        self.parameters: List[Declarable] = []
        self.is_built_in: bool = False


d_Type = Union[d_Grammar, d_Class]


class FlowControlException(Exception):
    """Base class for all exceptions used for flow control rather than errors."""

    def __init__(self, token: Token):
        self.token: Token = token


class ReturnController(FlowControlException):
    """Raised when a function executes a return statement"""

    def __init__(
        self, value: d_Thing, func: d_Function, orig_loc: CodeLocation
    ) -> None:

        if value.grammar == d_Grammar.NULL:
            super().__init__(Token(d_Grammar.NULL, orig_loc))
        return_declarable = Declarable(type_=func.return_, listof=func.return_list)
        res = _check_value(value, return_declarable)
        if res is not None:
            raise TypeMismatchError(
                f"Expected '{res.expected}' for return, got '{res.actual}'"
            )
        if isinstance(value, d_List):
            super().__init__(Token(d_Grammar.VALUE_LIST, orig_loc, thing=value))
        elif isinstance(func.return_, d_Class):
            raise NotImplementedError
        elif isinstance(value, d_Thing):  # type: ignore
            super().__init__(Token(func.return_, func.orig_loc, thing=value))


@dataclass
class CheckResult:
    expected: str
    actual: str


def _check_value(thing: d_Thing, dec: Declarable) -> Optional[CheckResult]:
    """Check if a declarable could be a thing. The declarable represents
    what we want this thing to be."""
    if isinstance(dec.type_, d_Class):
        raise NotImplementedError

    listof_act = "listof " if dec.listof else ""
    expected = f"{listof_act}{value_to_prim(dec.type_).value}"
    if isinstance(thing, d_List):
        if dec.listof:
            thing.contained_type = prim_to_value(dec.type_)
            _check_list_type(thing)
            return
        else:
            return CheckResult(expected=expected, actual="List")
            # raise TypeMismatchError(f"Cannot assign List to {actual}")
    elif dec.listof:
        return CheckResult(expected="List", actual=thing.public_type)
        # raise TypeMismatchError(f"Cannot assign {thing.public_type} to List")
    elif dec.type_ == d_Grammar.PRIMITIVE_THING:
        return
    elif thing.is_null:
        return
    elif value_to_prim(dec.type_) != value_to_prim(thing.grammar):
        return CheckResult(expected=expected, actual=thing.public_type)
        # raise TypeMismatchError(f"Cannot assign {thing.public_type} to {actual}")


def _all_scopes(body: d_Body) -> Generator[d_Body, None, None]:
    yield body
    if body.containing_scope:
        for scope in _all_scopes(body.containing_scope):
            yield scope


class ThrowController(FlowControlException):
    """Raised when a function executes a throw statement"""

    def __init__(self, value: d_Thing):
        raise NotImplementedError
        super().__init__(token)


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
    """All the information required to declare a new variable."""

    type_: d_Type = None  # type: ignore
    name: str = None  # type: ignore
    listof: bool = False  # type: ignore

    def reset(self):
        self.type_ = None  # type: ignore
        self.name = None  # type: ignore
        self.listof = False  # type: ignore


@dataclass
class ArgumentLocation:
    """An argument and the location where it was found"""

    loc: CodeLocation
    thing: d_Thing
