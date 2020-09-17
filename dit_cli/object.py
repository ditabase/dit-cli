from typing import Any, Generator
from typing import List as ListHint
from typing import NoReturn, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dit_cli.exceptions import FileError, TypeMismatchError, VarError
from dit_cli.grammar import Grammar


class Object(object):
    def __init__(self, name: str, grammar: Grammar) -> None:
        self.name: str = name
        self.grammar: Grammar = grammar
        self.public_type: str = "Object"

    def set_value(self, new_data: Any) -> NoReturn:
        # Python "virtual" method
        raise NotImplementedError


class String(Object):
    def __init__(self, name: str) -> None:
        super().__init__(name, Grammar.VALUE_STRING)
        self.string_value: str = None
        self.public_type: str = "String"

    def set_value(self, new_value: Union[str, "String"]) -> None:
        if isinstance(new_value, str):
            self.string_value = new_value
        elif isinstance(new_value, String):
            self.string_value = new_value.string_value
        elif isinstance(new_value, list):
            raise TypeMismatchError("Cannot assign List to String")
        elif isinstance(new_value, Object):
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to String")
        else:
            raise VarError("Unrecognized type for assignment")  # might be impossible


class List(Object):
    def __init__(self, name: str, grammar: Grammar) -> None:
        super().__init__(name, grammar)
        self.list_value: list = None
        self.public_type: str = "List"

    def set_value(self, new_value: Union[list, "List"]) -> None:
        if isinstance(new_value, list):
            self.list_value = new_value
        elif isinstance(new_value, List):
            self.list_value = new_value.list_value
        elif isinstance(new_value, str):
            raise TypeMismatchError("Cannot assign String to List")
        elif isinstance(new_value, Object):
            raise TypeMismatchError(f"Cannot assign {new_value.public_type} to List")
        else:
            raise VarError("Unrecognized type for assignment")  # might be impossible

        _check_list_type(self)


def _traverse(item) -> Union[str, Object]:
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    if isinstance(item, list):
        for i in iter(item):
            for j in _traverse(i):
                yield j
    else:
        yield item


def _check_list_type(list_: List):
    if list_.grammar == Grammar.VALUE_ANY:
        return
    prim = _value_to_prim(list_.grammar).value
    for ele in _traverse(list_.list_value):
        if isinstance(ele, str):
            if list_.grammar != Grammar.VALUE_STRING:
                raise TypeMismatchError(f"List of type '{prim}' contained 'String'")
            return
        elif isinstance(ele, Object):
            if ele.grammar != list_.grammar:
                e_prim = _value_to_prim(ele.grammar).value
                raise TypeMismatchError(f"List of type '{prim}' contained '{e_prim}'")


class Body(Object):
    def __init__(
        self,
        name: str,
        grammar: Grammar,
        path: str,
        view: memoryview,
        parent_scope: "Body",
    ) -> None:
        super().__init__(name, grammar)
        self.path: str = path
        self.view: memoryview = view
        self.parent_scope: Body = parent_scope
        self.attrs: ListHint[Object] = []
        self.public_type: str = "Body"

    def set_value(self, new_value: "Body") -> None:
        if not isinstance(new_value, Body):
            raise NotImplementedError
        self.attrs = new_value.attrs
        self.parent_scope = new_value.parent_scope
        self.view = new_value.view
        self.path = new_value.path

    def add_attr(self, name: str, grammar: Grammar, list_: bool) -> Object:
        if self.find_attr(name):
            raise NotImplementedError
        obj = _gram_to_obj(grammar, name, list_)
        self.attrs.append(obj)
        return obj

    def find_attr(self, name: str, previous: "Body" = None) -> Object:
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


def _all_scopes(body: Body) -> Generator["Body", None, None]:
    yield body
    if body.parent_scope:
        for scope in _all_scopes(body.parent_scope):
            yield scope


class Class(Body):
    def __init__(self, name: str, parent: Body, start: int, end: int) -> None:
        if parent:
            view = memoryview(parent.view[start:end])
            super().__init__(name, Grammar.VALUE_CLASS, parent.path, view, parent)
        else:
            # Class var primitives.
            super().__init__(name, Grammar.VALUE_CLASS, None, None, None)
        self.public_type: str = "Class"


class Instance(Object):
    def __init__(self) -> None:
        self.public_type: str = "Instance"
        raise NotImplementedError

    def find_attr(
        self, name: str, instance: "Instance" = None, previous: "Body" = None
    ) -> Object:
        raise NotImplementedError


class Function(Body):
    def __init__(self) -> None:
        self.public_type: str = "Function"
        raise NotImplementedError


class Dit(Body):
    def __init__(self, name: str, path: str) -> None:
        super().__init__(name, Grammar.VALUE_DIT, path, _handle_filepath(path), None)
        self.public_type: str = "Dit"

    @staticmethod
    def from_str(name: str, dit: str, mock_path: str) -> "Dit":
        view = memoryview(dit.encode())
        return Body(name, Grammar.VALUE_DIT, mock_path, view, None)


def _handle_filepath(path: str) -> memoryview:
    if not path:
        return None
    if path.startswith("https://") or path.startswith("http://"):
        try:
            contents = urlopen(path).read().decode()
        except (HTTPError, URLError) as error:
            raise FileError(f"Import failed, {error}")
    else:
        try:
            with open(path) as file_object:
                contents = file_object.read()
        except FileNotFoundError:
            raise FileError("Import failed, file not found")
        except PermissionError:
            raise FileError("Import failed, permission denied")

    return memoryview(contents.encode())


def _prim_to_value(grammar: Grammar) -> Grammar:
    if grammar == Grammar.PRIMITIVE_ANY:
        return Grammar.VALUE_ANY
    if grammar == Grammar.PRIMITIVE_STRING:
        return Grammar.VALUE_STRING
    if grammar == Grammar.PRIMITIVE_CLASS:
        return Grammar.VALUE_CLASS
    if grammar == Grammar.PRIMITIVE_FUNCTION:
        return Grammar.VALUE_FUNCTION
    if grammar == Grammar.PRIMITIVE_DIT:
        return Grammar.VALUE_DIT


def _value_to_prim(grammar: Grammar) -> Grammar:
    if grammar == Grammar.VALUE_ANY:
        return Grammar.PRIMITIVE_ANY
    if grammar == Grammar.VALUE_STRING:
        return Grammar.PRIMITIVE_STRING
    if grammar == Grammar.VALUE_CLASS:
        return Grammar.PRIMITIVE_CLASS
    if grammar == Grammar.PRIMITIVE_FUNCTION:
        return Grammar.PRIMITIVE_FUNCTION
    if grammar == Grammar.VALUE_DIT:
        return Grammar.PRIMITIVE_DIT


def _gram_to_obj(grammar: Grammar, name: str, list_: bool) -> Object:
    value_grammar = _prim_to_value(grammar)
    if list_:
        return List(name, value_grammar)
    if grammar == Grammar.PRIMITIVE_STRING:
        return String(name)
    if grammar == Grammar.PRIMITIVE_CLASS:
        return Class(name, None, None, None)
    if grammar == Grammar.PRIMITIVE_INSTANCE:
        raise NotImplementedError
    if grammar == Grammar.PRIMITIVE_FUNCTION:
        raise NotImplementedError
    if grammar == Grammar.PRIMITIVE_DIT:
        return Dit(name, None)
    raise NotImplementedError
