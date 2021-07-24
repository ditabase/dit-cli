from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
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
from dit_cli.grammar import (
    PARENTS,
    PRIORITY,
    d_Grammar,
    prim_to_value,
    value_to_prim,
)
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

    def __repr__(self) -> str:
        return self.name

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
        if not cls.null_singleton:
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
        if not target.name:
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


class d_Variable:
    """
    Stores a string name and a list of prefixes.
    The prefixes are only used with inheritance.
    In all other cases, it basically just uses the name.
    Names are unique within each scope.
    """

    def __init__(self, name: str, prefix: Optional[List[d_Class]] = None) -> None:
        self.name: str = name
        self.prefix: List[d_Class] = prefix or []

    def __hash__(self) -> int:
        return hash((self.name, tuple(self.prefix)))

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, d_Variable):
            return False
        elif self.name != o.name:
            return False
        elif self.prefix != o.prefix:
            return False
        return True

    def __repr__(self) -> str:
        out = "["
        for c in self.prefix:
            out += c.name + "."
        out += self.name
        return out + "]"


class d_Container(d_Thing):
    def __init__(self) -> None:
        super().__init__()
        self.attrs: Dict[d_Variable, Ref_Thing] = {}

    def find_attr(self, name: str, scope_mode: bool = False) -> Optional[d_Thing]:
        var = d_Variable(name)
        if isinstance(self, d_Instance):
            var = self.compose_prefix(name)
        if scope_mode:
            if not isinstance(self, d_Body):
                raise d_CriticalError("A Container was given for scope mode")
            # We need to check for this name in upper scopes
            # Str someGlobal = 'cat';
            # class someClass {{ Str someInternal = someGlobal; }}
            return _find_attr_in_scope(var, self)
        else:
            # We're dotting, so only 'self' counts, no upper scopes.
            # We also need to check for inherited parent classes
            # someInst.someMember = ...
            return _find_attr_in_self(var, self)

    def set_value(self, val: d_Thing) -> None:
        self.is_null = val.is_null

        if isinstance(self, d_Instance) and isinstance(val, d_Instance):
            self.attrs = val.attrs
        elif type(self) == type(val):
            self.attrs = val.attrs  # type: ignore
            self.parent_scope = val.parent_scope  # type: ignore
            self.view = val.view  # type: ignore
            self.path = val.path  # type: ignore
        elif self.can_be_anything:
            super().set_value(val)
        else:  # isinstance(val, d_Thing):
            raise d_TypeMismatchError(
                f"Cannot assign {val.public_type} to {self.public_type}"  # type: ignore
            )

    def add_attr(
        self, dec: Declarable, value: Optional[d_Thing] = None, use_ref: bool = False
    ) -> d_Thing:
        ref = None
        if dec.name is None:
            raise d_CriticalError("A declarable had no name")

        _check_for_duplicates(self, dec.name)

        if value:
            res = check_value(value, dec)
            if res:
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

        fin_val = ref or value
        fin_var = d_Variable(fin_val.name)
        if isinstance(self, d_Instance):
            fin_var = self.compose_prefix(fin_val.name)

        self.attrs[fin_var] = fin_val
        return value


def _check_for_duplicates(thing: d_Container, name: str) -> None:
    if isinstance(thing, d_Instance):
        var = thing.compose_prefix(name)
    else:
        var = d_Variable(name)
    if var in thing.attrs:
        raise d_CriticalError(f"A duplicate attribute was found: '{name}'")


def _find_attr_in_scope(var: d_Variable, body: d_Body) -> Optional[d_Thing]:
    if var in body.attrs:
        return body.attrs[var].get_thing()
    elif body.parent_scope:
        return _find_attr_in_scope(var, body.parent_scope)
    else:
        return None


def _find_attr_in_self(
    var: d_Variable,
    con: d_Container,
    orig_inst: d_Instance = None,
    search_record: d_Variable = None,
) -> Optional[d_Thing]:
    """
    Find an attribute within the target container.
    `var` is the original variable we were given, and `con` is the current container.
    `orig_inst` is the instance we started checking in, which we store when
    we start searching in inherited parent classes.
    `search_record` lists every class we've checked through so currently.

    This is is indirectly recursive with `_search_inherited_parents`, so this
    will be called several times to search through different containers.
    """
    if var in con.attrs:
        # Always check within our own attrs first
        return con.attrs[var].get_thing()
    if search_record and orig_inst:
        if _do_prefixes_match(var, search_record):
            if search_record in orig_inst.attrs:
                # the prefixes might match, but the variable might not actually exist
                return orig_inst.attrs[search_record].get_thing()
    if isinstance(con, d_Instance):
        # If we're an instance, we only have one parent, recurse on that parent
        return _find_attr_in_self(var, con.parent, con)
    if isinstance(con, d_Class) and orig_inst:
        return _search_inherited_parents(var, con, orig_inst, search_record)
    return None


def _do_prefixes_match(given_var: d_Variable, search_record: d_Variable) -> bool:
    """
    Check if prefixes are close enough to match.
    The `search_record` may not exactly match `given_var`.
    We check from the end of each var until one has no items to match.
    """
    if search_record == given_var:
        # Maybe they're a perfect match!
        return True
    elif search_record.name != given_var.name:
        # If the names don't match, there's no point in checking the prefixes
        return False
    elif not given_var.prefix:
        # if the given had no prefixes, we take the first match we can find
        return True

    giv_iter = iter(reversed(given_var.prefix))
    ser_iter = iter(reversed(search_record.prefix))
    giv = next(giv_iter, None)
    ser = next(ser_iter, None)
    while True:
        if giv == ser:
            # giv is the same as ser, we need to check the next set
            giv = next(giv_iter, None)
            ser = next(ser_iter, None)
            if None in (giv, ser):
                # If either are out of entries, then the prefixes are close enough
                return True
        else:
            # we need to move all the way down ser to find at least one match
            # for the current giv. If we can't find one, they aren't a match.
            ser = next(ser_iter, None)
            if not ser:
                return False


def _search_inherited_parents(
    var: d_Variable,
    class_: d_Class,
    orig_inst: d_Instance,
    search_record: d_Variable = None,
) -> Optional[d_Thing]:
    """
    Search through the parents of `class_` to see if we can find `var`.
    """
    parents = class_.get_parents()
    if not parents:
        return None

    # check if we're looking for an explicit parent
    for parent in parents.list_:  # type: ignore
        parent: d_Class
        if var.name == parent.name:
            orig_inst.clear_prefix_to_class()
            orig_inst.add_parent_prefix(parent)
            orig_inst.add_class_sep()
            return parent

    # Now we manually search the entire parent graph.
    # search_record will remember the prefix of our current search context.
    # We will use it to check the instance attrs for matches.
    search_record = search_record or d_Variable(var.name)
    for parent in parents.list_:  # type: ignore
        search_record.prefix.append(parent)
        orig_inst.add_parent_prefix(parent)
        result = _find_attr_in_self(var, parent, orig_inst, search_record)
        if result:
            return result
        search_record.prefix.pop()
        orig_inst.pop_parent_prefix()


class PrefixSeperator(Enum):
    FUNC_SEP = 0
    CLASS_SEP = 1


class d_Instance(d_Container):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Instance"
        self.grammar = d_Grammar.VALUE_INSTANCE
        self.parent: d_Class = None  # type: ignore

        self.cur_prefix: List[prefix_item] = []
        """
            More information in examples/name-conflicts.dit

            Dit supports multiple dynamic inheritance. 
            Classes may inherit multiple parents which assign to the same name. 
            In many languages, if two different classes assign the attribute `value`,
            the attribute is considered to be the same `value`, 
            and the second assignment will overwrite the first.

            In Dit, this is not the case. We want to keep the attributes separate,
            so that you can inherit from parents without needing to carefully check
            what attributes are already defined.

            In Dit, this is not the case. We want to keep the attributes separate,
            so that you can inherit from parents without needing to carefully check
            what attributes are already defined. 
            We do this by hiding attribute assignments behind their parent names.
            We keep track of what class assigned which attributes, 
            and store the variable name behind a list of prefixes.

            `cur_prefix` is the current prefix stack for this instance.
            It contains a list of each class that:
                - was searched through when searching for a variable name
                - was explicitly dotted, followed by a `CLASS_SEP` marker
                - has a function called, followed by a `FUNC_SEP` marker

            Examples of a prefix stack:
                - `[A, FUNC_SEP, B, 'value']`
                - `[A, FUNC_SEP, B,  FUNC_SEP, C, 'value']`
                - `[Z, CLASS_SEP, 'value']`
        """

    def clear_prefix_to_func(self):
        _clear_prefix_to_sep(self, [PrefixSeperator.FUNC_SEP])

    def clear_prefix_to_class(self):
        _clear_prefix_to_sep(
            self, [PrefixSeperator.CLASS_SEP, PrefixSeperator.FUNC_SEP]
        )

    def add_parent_prefix(self, class_: d_Class):
        self.cur_prefix.append(class_)

    def pop_parent_prefix(self):
        self.cur_prefix.pop()

    def add_class_sep(self):
        self.cur_prefix.append(PrefixSeperator.CLASS_SEP)

    def pop_class_sep(self):
        raise NotImplementedError

    def add_func_sep(self):
        self.cur_prefix.append(PrefixSeperator.FUNC_SEP)

    def pop_func_sep(self):
        self.clear_prefix_to_func()
        self.cur_prefix.pop()
        self.clear_prefix_to_func()

    def compose_prefix(self, name: str) -> d_Variable:
        var = d_Variable(name)
        var.prefix = [c for c in self.cur_prefix if isinstance(c, d_Class)]
        return var


def _clear_prefix_to_sep(inst: d_Instance, seperators: List[PrefixSeperator]):
    while True:
        if not inst.cur_prefix:
            break
        elif inst.cur_prefix[-1] in seperators:
            break
        else:
            inst.cur_prefix.pop()


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
    if not dec.type_:
        raise d_CriticalError("A declarable had no type")
    elif isinstance(dec.type_, d_Class):
        thing = d_Instance()
        thing.parent = dec.type_
    elif dec.listof:
        thing = d_List()
        # this prim_to_value might fail with classes
        thing.contained_type = prim_to_value(dec.type_)  # type: ignore
    elif dec.type_ == d_Grammar.PRIMITIVE_THING:
        thing = d_Thing()
        thing.can_be_anything = True
    else:
        # equivalent to thing = d_Str(), just with the Object Dispatch
        thing = OBJECT_DISPATCH[dec.type_]()

    if thing:
        thing.name = dec.name
        return thing
    else:
        raise d_CriticalError("Unrecognized type for declaration")


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

    def get_parents(self) -> Optional[d_List]:
        p = d_Variable(PARENTS)
        if p not in self.attrs:
            return None
        parents = self.attrs[p]
        if not isinstance(parents, d_List):
            raise d_TypeMismatchError("Parents must be a list")
        parents.contained_type = d_Grammar.VALUE_CLASS
        parents.can_be_anything = False
        _check_list_type(parents)  # Parents must be a list of Classes
        return parents


class d_Lang(d_Body):
    def __init__(self) -> None:
        super().__init__()
        self.public_type = "Lang"
        self.grammar = d_Grammar.VALUE_LANG

    def add_attr(self, dec: Declarable, value: Optional[d_Thing]) -> d_Thing:
        result = super().add_attr(dec, value=value)

        # We set the custom 'priority_num' of the new attribute
        # to the current lang 'Priority'
        # Every variable must keep track of the priority at the time it was declared.
        priority = 0
        p = d_Variable(PRIORITY)

        if p in self.attrs:
            item = self.attrs[p]
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
        if not res:
            raise d_MissingPropError(self.name, name)
        elif not isinstance(res, d_Str):
            raise d_SyntaxError(
                f"All properties must be strings. Lang {self.name} with property {name}"
            )
        return res.str_


def _combine_langs(lang1: d_Lang, lang2: d_Lang) -> Dict[d_Variable, Ref_Thing]:
    # First remove priority values
    # the priority has already been individually assigned to each variable
    pri_var = d_Variable(PRIORITY)
    lang1.attrs.pop(pri_var, None)
    lang2.attrs.pop(pri_var, None)
    set1, set2 = set(lang1.attrs), set(lang2.attrs)
    # Start by pulling all the items that don't have the same names into a list
    out: Dict[d_Variable, Ref_Thing] = {}
    for unique_var in set1.symmetric_difference(set2):
        if unique_var in lang1.attrs:
            out[unique_var] = lang1.attrs[unique_var]
        else:
            out[unique_var] = lang2.attrs[unique_var]

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
        # allows for a different set of attributes for each recursive function call
        self.attr_stack: List[Dict[d_Variable, Ref_Thing]] = []

        self.py_func: Callable = None  # type: ignore
        self.call_loc: CodeLocation = None  # type: ignore
        self.lang: d_Lang = None  # type: ignore
        self.return_: d_Type = None  # type: ignore
        self.return_list: bool = None  # type: ignore
        self.parameters: List[Declarable] = []
        self.code: bytearray = None  # type: ignore
        self.guest_func_path: str = None  # type: ignore

    def new_call(self) -> None:
        if not self.attr_stack:
            # We only have the original attrs, we just need to put that on the stack
            self.attr_stack.append(self.attrs)
        else:
            # This is a recursive call, we need a new attr on the stack
            self.attr_stack.append({})
            self.attrs = self.attr_stack[-1]

    def end_call(self) -> None:
        if len(self.attr_stack) == 1:
            # We don't want to destroy the original attrs, just pop and clear it
            self.attr_stack.pop()
            self.attrs.clear()
        else:
            # Finished a recursive call, so pop the stack and reassign the attrs
            self.attr_stack.pop()
            self.attrs = self.attr_stack[-1]

    def get_mock(self, code: str) -> d_Func:
        mock_func: d_Func = d_Func.from_str("mock_exe_ditlang", code, self.guest_func_path)  # type: ignore
        mock_func.attrs = self.attrs
        mock_func.parent_scope = self.parent_scope
        mock_func.start_loc = CodeLocation(0, 1, 1)
        mock_func.return_ = self.return_
        mock_func.return_list = self.return_list
        return mock_func


d_Type = Union[d_Grammar, d_Class]
prefix_item = Union[d_Class, PrefixSeperator]


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
        if res:
            raise d_TypeMismatchError(
                f"Expected '{res.expected}' for return, got '{res.actual}'"
            )
        if isinstance(value, d_List):
            super().__init__(Token(d_Grammar.VALUE_LIST, orig_loc, thing=value))
        elif isinstance(func.return_, d_Class):
            super().__init__(Token(d_Grammar.VALUE_INSTANCE, orig_loc, thing=value))
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
    elif dec.listof and isinstance(thing, d_List) and not thing.contained_type:
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
    if thing:
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
    RETURN_KEYWORD = "return_keyword"
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


OBJECT_DISPATCH = {
    d_Grammar.PRIMITIVE_THING: d_Thing,
    d_Grammar.PRIMITIVE_STR: d_Str,
    d_Grammar.PRIMITIVE_BOOL: d_Bool,
    d_Grammar.PRIMITIVE_NUM: d_Num,
    d_Grammar.PRIMITIVE_JSON: d_JSON,
    d_Grammar.PRIMITIVE_CLASS: d_Class,
    d_Grammar.PRIMITIVE_INSTANCE: d_Instance,
    d_Grammar.PRIMITIVE_FUNC: d_Func,
    d_Grammar.PRIMITIVE_DIT: d_Dit,
    d_Grammar.PRIMITIVE_LANG: d_Lang,
}
