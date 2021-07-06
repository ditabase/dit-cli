from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dit_cli.exceptions import (
    d_CriticalError,
    d_FileError,
    d_MissingPropError,
    d_SyntaxError,
    d_TypeMismatchError,
)
from dit_cli.grammar import d_Grammar, prim_to_value, value_to_prim
from dit_cli.settings import CodeLocation


class d_Thing(object):
    null_singleton: Optional[d_Thing] = None

    def __init__(self) -> None:
        self.public_type: str = "Thing"
        self.grammar: d_Grammar = d_Grammar.VALUE_THING

        self.name: str = None  # type: ignore
        self.can_be_anything: bool = False
        self.is_null: bool = True
        self.is_built_in: bool = False

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o: object) -> bool:
        # This hash and eq only check name, because they are only
        # used for priority comparison in _compare_names
        if not isinstance(o, d_Thing):
            return False
        elif self.name == o.name:
            return True
        return False

    def __str__(self):
        if self.is_null:
            return d_Grammar.NULL.value
        else:
            raise d_CriticalError("Thing __str__ called on non-null thing.")

    def get_data(self) -> None:
        if self.is_null:
            return None
        else:
            raise d_CriticalError("Thing get_data called on non-null thing.")

    def set_value(self, new_value: d_Thing) -> None:
        # alter own class to *become* the type it is assigned to.
        # note that 'can_be_anything' is still True
        # and public_type is still "Thing"
        if isinstance(new_value, d_Thing):  # type: ignore
            self.__class__ = new_value.__class__
            self.grammar = new_value.grammar
            self.public_type = new_value.public_type
        else:
            raise d_CriticalError("Unrecognized type for thing assignment")

        if not type(new_value) == d_Thing:
            # After altering class, set the actual value using subclass set_value
            self.set_value(new_value)

    @classmethod
    def get_null_thing(cls) -> d_Thing:
        if cls.null_singleton is None:
            cls.null_singleton = d_Thing()
            cls.null_singleton.grammar = d_Grammar.VALUE_NULL
            cls.null_singleton.public_type = d_Grammar.NULL.value
        return cls.null_singleton

    def get_thing(self) -> d_Thing:
        return self


class d_Ref(object):
    def __init__(self, name: str, target: d_Thing) -> None:
        self.name = name
        self.target = target
        if target.name is None:
            target.name = name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, d_Ref):
            return False
        elif self.name == o.name:
            return True
        return False

    def get_thing(self) -> d_Thing:
        return self.target


Ref_Thing = Union[d_Thing, d_Ref]


class d_Str(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Str"
        self.grammar = d_Grammar.VALUE_STR

        self.str_: str = None  # type: ignore

    def __str__(self) -> str:
        return self.str_

    def __repr__(self) -> str:
        return f'"{self.str_}"'

    def get_data(self) -> str:
        return self.str_

    def set_value(self, new_value: d_Thing) -> None:
        _simple_set_value(self, new_value)


class d_Bool(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Bool"
        self.grammar = d_Grammar.VALUE_BOOL

        self.bool_: bool = None  # type: ignore

    def __str__(self) -> str:
        return d_Grammar.TRUE.value if self.bool_ else d_Grammar.FALSE.value

    def __repr__(self) -> str:
        return self.__str__()

    def get_data(self) -> bool:
        return self.bool_

    def set_value(self, new_value: d_Thing) -> None:
        _simple_set_value(self, new_value)


class d_Num(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Num"
        self.grammar = d_Grammar.VALUE_NUM

        self.num: float = None  # type: ignore

    def __str__(self) -> str:
        return str(self.num)

    def __repr__(self) -> str:
        return self.__str__()

    def get_data(self) -> float:
        return self.num

    def set_value(self, new_value: d_Thing) -> None:
        _simple_set_value(self, new_value)


class d_List(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "List"
        self.grammar = d_Grammar.VALUE_LIST

        self.contained_type: d_Type = None  # type: ignore
        self.list_: List[d_Thing] = None  # type: ignore

    def __str__(self) -> str:
        return json.dumps(self.get_data())

    def __repr__(self) -> str:
        return self.__str__()

    def get_data(self) -> list:
        out = []
        for item in self.list_:
            out.append(item.get_data())
        return out

    def set_value(self, new_value: d_Thing) -> None:
        self.is_null = new_value.is_null
        if isinstance(new_value, d_List):
            # listOf Str = ['1', '2'];
            self.list_ = new_value.list_
            _check_list_type(self)
        elif self.can_be_anything:
            super().set_value(new_value)
        elif isinstance(new_value, d_Thing):  # type: ignore
            raise d_TypeMismatchError(f"Cannot assign {new_value.public_type} to List")
        else:
            raise d_CriticalError("Unrecognized type for list assignment")


def _check_list_type(list_: d_List) -> None:
    if list_.can_be_anything:
        list_.contained_type = d_Grammar.VALUE_THING
        return
    elif list_.contained_type == d_Grammar.VALUE_THING:
        return

    err = False
    for ele in _traverse(list_.list_):
        ele: d_Thing
        if ele.is_null:
            continue
        elif isinstance(list_.contained_type, d_Class) and not _is_subclass(
            ele, list_.contained_type
        ):
            # mismatch class types.
            # listOf Number numbers= [Bool('3')];
            err = True
        elif ele.grammar != list_.contained_type:
            if ele.grammar == d_Grammar.VALUE_LIST:
                # Nested lists are okay
                # listOf Num grid = [[2, 6], [7, 8], [-1, -7]];
                continue
            else:
                # Mismatched grammars
                # listOf Class classes = ['clearly not a class'];
                err = True

        if err:
            expected = _type_to_str(list_.contained_type)
            actual = _thing_to_str(ele)
            raise d_TypeMismatchError(f"List of type '{expected}' contained '{actual}'")


def _traverse(item: Union[list, d_Thing]) -> Iterator[d_Thing]:
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    if isinstance(item, list):
        for i in item:
            for j in _traverse(i):
                yield j
    else:
        yield item


class d_JSON(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "JSON"
        self.grammar = d_Grammar.VALUE_JSON

        self.json_: dict = None  # type: ignore

    def __str__(self) -> str:
        di = self.get_data()
        ji = json.dumps(di)
        return ji

    def __repr__(self) -> str:
        return self.__str__()

    def get_data(self) -> dict:
        out = {}
        for key, val in self.json_.items():
            out[key] = val.get_data()
        return out

    def set_value(self, new_value: d_Thing) -> None:
        _simple_set_value(self, new_value)


simple_types = Union[d_Str, d_Bool, d_Num, d_JSON]


def _simple_set_value(self: simple_types, val: d_Thing) -> None:
    # Always set null, but still need to check that assignment was allowed
    self.is_null = val.is_null

    # Check if items match, then just assign
    if val.grammar == d_Grammar.VALUE_NULL:
        pass
    elif isinstance(self, d_Str) and isinstance(val, d_Str):
        self.str_ = val.str_
    elif isinstance(self, d_Bool) and isinstance(val, d_Bool):
        self.bool_ = val.bool_
    elif isinstance(self, d_Num) and isinstance(val, d_Num):
        self.num = val.num
    elif isinstance(self, d_JSON) and isinstance(val, d_JSON):
        self.json_ = val.json_
    elif self.can_be_anything:
        # maybe self was originally a Thing and is being reassigned
        # Thing test = true;
        # test = ['dog', 'bird'];
        super(self.__class__, self).set_value(val)  # type: ignore
    else:
        # elif isinstance(val, d_Thing):  # type: ignore
        raise d_TypeMismatchError(
            f"Cannot assign {val.public_type} to {self.public_type}"
        )


class d_Container(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.attrs: Dict[str, Ref_Thing] = {}

    def find_attr(self, name: str, scope_mode: bool = False) -> Optional[d_Thing]:
        if scope_mode:
            if not isinstance(self, d_Body):
                raise d_CriticalError("A Container was given for scope mode")
            # We need to check for this name in upper scopes
            # Str someGlobal = 'cat';
            # class someClass {{ Str someInternal = someGlobal; }}
            return _find_attr_in_scope(name, self)
        else:
            # We're dotting, so only 'self' counts, no upper scopes.
            # We also need to check for inherited parent classes
            # someInst.someMember = ...
            return _find_attr_in_self(name, self)

    def set_value(self, val: d_Thing) -> None:
        self.is_null = val.is_null

        if isinstance(self, d_Instance) and isinstance(val, d_Instance):
            self.attrs = val.attrs
        elif type(self) == type(val):
            self.attrs = val.attrs
            self.parent_scope = val.parent_scope
            self.view = val.view
            self.path = val.path
        elif self.can_be_anything:
            super().set_value(val)
        else:  # isinstance(val, d_Thing):
            raise d_TypeMismatchError(
                f"Cannot assign {val.public_type} to {self.public_type}"  # type: ignore
            )
        """
        elif isinstance(self, d_Dit) and isinstance(val, d_Dit):
            self.attrs = val.attrs
            self.parent_scope = val.parent_scope
            self.view = val.view
            self.path = val.path
        elif isinstance(self, d_Class) and isinstance(val, d_Class):
            self.attrs = val.attrs
            self.parent_scope = val.parent_scope
            self.view = val.view
            self.path = val.path
        elif isinstance(self, d_Lang) and isinstance(val, d_Lang):
            self.attrs = val.attrs
            self.parent_scope = val.parent_scope
            self.view = val.view
            self.path = val.path
        elif isinstance(self, d_Func) and isinstance(val, d_Func):
            self.attrs = val.attrs
            self.parent_scope = val.parent_scope
            self.view = val.view
            self.path = val.path
        
        """

    def add_attr(
        self, dec: Declarable, value: Optional[d_Thing] = None, use_ref: bool = False
    ) -> d_Thing:
        ref = None
        if dec.name is None:
            raise d_CriticalError("A declarable had no name")
        if self.find_attr(dec.name):
            # TODO: this could be naive with inheritance, not sure.
            raise d_CriticalError(f"A duplicate attribute was found: '{dec.name}'")
        if value is not None:
            res = check_value(value, dec)
            if res is not None:
                raise d_TypeMismatchError(
                    f"Cannot assign {res.actual} to {res.expected}"
                )

            if dec.type_ == d_Grammar.PRIMITIVE_THING:
                value.can_be_anything = True
            if use_ref:
                # Use a ref to hide the original name without changing it
                # Currently only used for function parameters afaik
                ref = d_Ref(dec.name, value)
            else:
                value.name = dec.name
        else:
            value = _type_to_obj(dec)

        if ref is not None:
            self.attrs[ref.name] = ref
        else:
            self.attrs[value.name] = value
        return value


def _find_attr_in_scope(name: str, body: d_Body) -> Optional[d_Thing]:
    if name in body.attrs:
        return body.attrs[name].get_thing()
    elif body.parent_scope is not None:
        return _find_attr_in_scope(name, body.parent_scope)
    else:
        return None


def _find_attr_in_self(name: str, con: d_Container) -> Optional[d_Thing]:
    if name in con.attrs:
        return con.attrs[name].get_thing()
    elif isinstance(con, d_Instance):
        return _find_attr_in_self(name, con.parent)
    elif isinstance(con, d_Class):
        for parent in con.parents:
            return _find_attr_in_self(name, parent)
    return None


class d_Instance(d_Container):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Instance"
        self.grammar = d_Grammar.VALUE_INSTANCE
        self.parent: d_Class = None  # type: ignore


class d_Body(d_Container):
    def __init__(self) -> None:
        super().__init__()
        self.path: str = None  # type: ignore
        self.start_loc: CodeLocation = None  # type: ignore
        self.end_loc: CodeLocation = None  # type: ignore
        self.view: memoryview = None  # type: ignore
        self.parent_scope: d_Body = None  # type: ignore

    @classmethod
    def from_str(cls, name: str, code: str, mock_path: str) -> d_Body:
        bod = cls()
        bod.name = name
        bod.path = mock_path
        bod.view = memoryview(code.encode())
        return bod

    def is_ready(self) -> bool:
        if self.view is None:
            raise d_CriticalError("A body had no view during readying")
        return len(self.view) > 0

    def finalize(self) -> None:
        if self.path is None:
            self.path = self.parent_scope.path
        if self.view is None:
            # d_Dit sets the view itself, from a file/URL
            self.view = memoryview(
                self.parent_scope.view[self.start_loc.pos : self.end_loc.pos]
            )


def _type_to_obj(dec: Declarable) -> d_Thing:
    thing: d_Thing = None  # type: ignore
    if dec.type_ is None:
        raise d_CriticalError("A declarable had no type")
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
    elif dec.type_ == d_Grammar.PRIMITIVE_STR:
        thing = d_Str()
    elif dec.type_ == d_Grammar.PRIMITIVE_CLASS:
        thing = d_Class()
    elif dec.type_ == d_Grammar.PRIMITIVE_INSTANCE:
        thing = d_Instance()
    elif dec.type_ == d_Grammar.PRIMITIVE_FUNC:
        thing = d_Func()
    elif dec.type_ == d_Grammar.PRIMITIVE_DIT:
        thing = d_Dit()

    if thing is None:
        raise d_CriticalError("Unrecognized type for declaration")
    else:
        thing.name = dec.name
        return thing


class d_Dit(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Dit"
        self.grammar = d_Grammar.VALUE_DIT

        self.start_loc = CodeLocation(0, 1, 1)

    def finalize(self) -> None:
        self.handle_filepath()
        super().finalize()

    def handle_filepath(self) -> None:
        if self.view is not None:
            return
        if self.path is None:
            raise d_CriticalError("A dit had no path")
        if self.path.startswith("https://") or self.path.startswith("http://"):
            try:
                contents = urlopen(self.path).read().decode()
            except (HTTPError, URLError) as error:
                raise d_FileError(f"Import failed, {error}")
        else:
            try:
                with open(self.path) as file_object:
                    contents = file_object.read()
            except FileNotFoundError:
                raise d_FileError("Import failed, file not found")
            except PermissionError:
                raise d_FileError("Import failed, permission denied")
            except IsADirectoryError:
                raise d_FileError("Import failed, not a directory")

        self.view = memoryview(contents.encode())


class d_Class(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Class"
        self.grammar = d_Grammar.VALUE_CLASS
        self.parents: List[d_Class] = []


class d_Lang(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Lang"
        self.grammar = d_Grammar.VALUE_LANG
        self.parents: List[d_Lang] = []

    def add_attr(self, dec: Declarable, value: Optional[d_Thing]) -> d_Thing:
        result = super().add_attr(dec, value=value)
        priority = 0

        if "Priority" in self.attrs:
            item = self.attrs["Priority"]
            if not isinstance(item, d_Str):
                raise d_TypeMismatchError("Priority must be of type Str")
            priority = int(item.str_)

        if not hasattr(result, "priority_num"):
            result.priority = priority  # type: ignore
        return result

    def set_value(self, new_value: d_Thing) -> None:
        if isinstance(new_value, d_Lang):
            self.attrs = _combine_langs(self, new_value)
        else:
            super().set_value(new_value)

    def get_prop(self, name: str) -> str:
        res = self.find_attr(name)
        if res is None:
            raise d_MissingPropError(self.name, name)
        elif not isinstance(res, d_Str):
            raise d_SyntaxError(
                f"All properties must be strings. Lang {self.name} with property {name}"
            )
        return res.str_


def _combine_langs(lang1: d_Lang, lang2: d_Lang) -> Dict[str, Ref_Thing]:
    lang1.attrs.pop("Priority", None)
    lang2.attrs.pop("Priority", None)
    set1, set2 = set(lang1.attrs), set(lang2.attrs)
    # Start by pulling all the items that don't have the same names into a list
    out: Dict[str, Ref_Thing] = {}
    for unique_name in set1.symmetric_difference(set2):
        if unique_name in lang1.attrs:
            out[unique_name] = lang1.attrs[unique_name]
        else:
            out[unique_name] = lang2.attrs[unique_name]

    # Add the matching names to the list, based on priority
    for match_name in set1.intersection(set2):
        v1, v2 = lang1.attrs[match_name], lang2.attrs[match_name]
        out[match_name] = v1 if v1.priority > v2.priority else v2  # type: ignore
    return out


class d_Func(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Function"
        self.grammar = d_Grammar.VALUE_FUNC

        self.py_func: Callable = None  # type: ignore
        self.call_loc: CodeLocation = None  # type: ignore
        self.lang: d_Lang = None  # type: ignore
        self.return_: d_Type = None  # type: ignore
        self.return_list: bool = None  # type: ignore
        self.parameters: List[Declarable] = []
        self.code: bytearray = None  # type: ignore
        self.guest_func_path: str = None  # type: ignore

    def get_mock(self, code: str) -> d_Func:
        mock_func: d_Func = d_Func.from_str("mock_exe_ditlang", code, self.guest_func_path)  # type: ignore
        mock_func.attrs = self.attrs
        mock_func.parent_scope = self.parent_scope
        mock_func.start_loc = CodeLocation(0, 1, 1)
        mock_func.return_ = self.return_
        mock_func.return_list = self.return_list
        return mock_func


d_Type = Union[d_Grammar, d_Class]


class FlowControlException(Exception):
    """Base class for all exceptions used for flow control rather than errors."""

    def __init__(self, token: Token):
        self.token: Token = token


class ReturnController(FlowControlException):
    """Raised when a function executes a return statement"""

    def __init__(self, value: d_Thing, func: d_Func, orig_loc: CodeLocation) -> None:

        if value.grammar == d_Grammar.NULL:
            super().__init__(Token(d_Grammar.NULL, orig_loc))
        return_declarable = Declarable(type_=func.return_, listof=func.return_list)
        res = check_value(value, return_declarable)
        if res is not None:
            raise d_TypeMismatchError(
                f"Expected '{res.expected}' for return, got '{res.actual}'"
            )
        if isinstance(value, d_List):
            super().__init__(Token(d_Grammar.VALUE_LIST, orig_loc, thing=value))
        elif isinstance(func.return_, d_Class):
            raise NotImplementedError
        elif isinstance(value, d_Thing):  # type: ignore
            super().__init__(Token(func.return_, func.call_loc, thing=value))


@dataclass
class CheckResult:
    expected: str
    actual: str


def check_value(thing: d_Thing, dec: Declarable) -> Optional[CheckResult]:
    """Check if a declarable could be a thing. The declarable represents
    what we want this thing to be."""
    if thing.is_null:
        # assigning null is always allowed
        # listOf someClass test = null;
        return
    elif dec.type_ == d_Grammar.PRIMITIVE_THING:
        if not dec.listof or isinstance(thing, d_List):
            # a 'Thing' can be anything, listOf Thing can have any list
            # Thing test = ...;
            # listOf Thing test = [...];
            return
    elif dec.listof != isinstance(thing, d_List):
        # non matching lists, obvious error
        # listOf Str test = 'cat';
        # Str test = ['cat'];
        return _get_check_result(thing, dec)
    elif dec.listof and isinstance(thing, d_List) and thing.contained_type is None:
        # a list doesn't know its own type when initially declared, so we'll check
        # listOf Str test = ['cat'];
        thing.contained_type = _get_gram_or_class(prim_to_value, type_=dec.type_)
        _check_list_type(thing)
        return
    elif not isinstance(dec.type_, d_Class):
        if value_to_prim(dec.type_) != _get_gram_or_class(value_to_prim, thing=thing):
            # Not matching grammars
            # Str test = func (){{}};
            # listOf Class = ['cat'];
            return _get_check_result(thing, dec)
    elif not _is_subclass(thing, dec.type_):
        # not matching class types
        # sig listOf Bool func test() {{return [Bool('true')];}}
        # listOf Number numbers = test();
        # Number count = Bool('true');
        # Number count = 'cat';
        return _get_check_result(thing, dec)


def _get_check_result(thing: d_Thing, dec: Declarable) -> CheckResult:
    return CheckResult(expected=_dec_to_str(dec), actual=_thing_to_str(thing))


def _is_subclass(thing: d_Thing, target: d_Class) -> bool:
    if isinstance(thing, d_List):
        sub = thing.contained_type
    elif not isinstance(thing, d_Instance):
        return False
    else:
        sub = thing.parent

    if sub is target:
        return True
    else:
        raise NotImplementedError


def _dec_to_str(dec: Declarable) -> str:
    listof = "listOf " if dec.listof else ""
    return listof + _type_to_str(dec.type_)


def _thing_to_str(thing: d_Thing) -> str:
    if isinstance(thing, d_List):
        con = thing.contained_type
        return "listOf " + (_type_to_str(con) if con is not None else "?")
    else:
        return _type_to_str(thing.grammar)


def _type_to_str(type_: d_Type) -> str:
    if isinstance(type_, d_Class):
        return type_.name
    else:
        return value_to_prim(type_).value


def _get_gram_or_class(
    func: Callable, thing: Optional[d_Thing] = None, type_: Optional[d_Type] = None
) -> d_Type:
    if thing is not None:
        if isinstance(thing, d_List):
            type_ = thing.contained_type
        else:
            type_ = thing.grammar

    if isinstance(type_, d_Class):
        return type_
    else:
        return func(type_)


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


import json
from enum import Enum


class JobType(Enum):
    CALL_FUNC = "call_func"
    EXE_DITLANG = "exe_ditlang"
    DITLANG_CALLBACK = "ditlang_callback"
    FINISH_FUNC = "finish_func"
    CRASH = "crash"
    HEART = "heart"
    CLOSE = "close"


@dataclass
class GuestDaemonJob:
    """A function to be evaluated, with its arguments and result"""

    type_: JobType
    func: d_Func
    result: Union[str, list] = None  # type: ignore
    crash: BaseException = None  # type: ignore
    active: bool = False

    def get_json(self) -> bytes:
        py_json: Dict[str, Union[str, list]] = {
            "type": self.type_.value,
            "lang_name": self.func.lang.name,
            "func_name": self.func.name,
            "func_path": self.func.guest_func_path,
            "result": self.result,
        }
        temp = json.dumps(py_json) + "\n"
        return temp.encode()
