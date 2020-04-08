"""Dataclasses for all dit functions.
Includes the variable system for reading and writing values."""
from typing import List, Union, Any
from dataclasses import dataclass
from copy import copy

from dit_cli.exceptions import VarError
from dit_cli.node import Node
from dit_cli.dataclasses import Attribute, Expression, NameConflict
from dit_cli.assigner import Assigner


class Namespace:
    """Stores a list of nodes, assigners, and imported parent namespaces"""

    def __init__(self):
        # {name: str, namespace: Namespace}
        self.parents: List[dict] = []
        self.nodes: List[Node] = []
        self.assigners: List[Assigner] = []

    def add(self, name: str, namespace: 'Namespace'):
        """Add an imported namespace to this namespace behind a name"""
        self.raise_if_defined(name)
        self.parents.append({'name': name, 'namespace': namespace})

    def raise_if_defined(self, name: str):
        """Search for a single new name, and raise if it already exists
        as a class, object, assigner, or namespace"""
        def _raise(type_: str):
            raise VarError(f'"{name}" is already defined ({type_})')

        for parent in self.parents:
            if name == parent['name']:
                _raise('namespace')

        for node in self.nodes:
            if name == node.name:
                _raise(node.type_)

        for assign in self.assigners:
            if name == assign.name:
                _raise('assigner')

    def raise_if_undefined(self, expr: Union[List[str], Expression]):
        """Search for a variable, and raise if it does not exist"""
        self.read(expr)

    def read(self, expr: Union[List[str], Expression]):
        """Return the value stored by a variable"""
        return self.write(expr, None)

    def read_data(self, expr: Union[List[str], Expression]):
        """If the result is an attribute, return the data instead of
        the entire attribute"""
        result = self.read(expr)

        # Prefer not to use duck typing since I know exactly what instance
        # I'm looking for, and what all possible returns are.
        # Also, result.data might work on things other than just Attributes.
        if isinstance(result, Attribute):
            return result.data
        else:
            return result

    def write(self, expr: Union[List[str], Expression], data: Any):
        """Write data to a variable. If it has already been written,
        overwrite and return whatever was there."""
        if isinstance(expr, list):
            expr = Expression(self, None, None, expr)
        return _process_expression(expr, data=data)


@dataclass
class _SearchResult:
    """The result of looking for a single variable in an expression.
    For example, 'attribute' in 'Thing.attribute.value'.
    The result can be any dit construct, so context is required.

    Context Enum: namespace, class, object, assigner, attr

    context: What type of thing was found.

    value: The actual result of the search."""
    context: str
    value: Union[Attribute, 'Namespace', Node, Assigner]


def _process_expression(expr: Expression, data: Any):
    """Core of the variable system.
    Handles all CRUD operations for any variable interation.
    Searches and finds each part of a variable, and creates/assigns
    objects/data as needed.
    """
    conf: NameConflict = None

    # Now that we have the Expression,
    # we can pull the data out and discard it
    namespace = expr.namespace
    class_ = expr.class_
    obj = expr.obj
    expr = expr.expression

    if class_:
        current = class_
    else:
        current = namespace

    for index, var in enumerate(expr):
        res = _find_var(var, current)
        if res is None:
            _raise_helper(var, expr, 'Undefined variable')

        if index < len(expr) - 1:  # There are more elements
            if res.context == 'namespace':
                namespace = res.value
                current = namespace
            elif res.context == 'object':
                obj = res.value
                class_ = obj.extends[0]
                current = class_
            elif res.context == 'class':
                conf = _get_conflict(
                    expr[index + 1], class_, res.value)
                class_ = res.value
                current = class_
            elif res.context == 'assigner':
                _raise_helper(var, expr, 'Cannot reference assigner')
            elif res.context == 'attr':
                class_attr = res.value
                class_ = class_attr.class_
                current = class_
                obj_attr = _find_attribute(obj, var, conf)
                if class_attr.class_ == 'String':
                    _raise_helper(var, expr, 'Cannot reference string')
                if class_attr.list_:
                    # TODO: You should be able to reference lists of objects.
                    # It would implicitly understand that you want to
                    # mess with each item in the list, rather than the list
                    # as a whole.
                    _raise_helper(var, expr, 'Cannot reference list')

                if data is not None and obj_attr is None:
                    new_obj = Node(namespace, var, 'object')
                    new_obj.extends.append(class_attr.class_)
                    new_attr: Attribute = copy(class_attr)
                    new_attr.data = new_obj
                    new_attr.conf = conf
                    obj.attrs.append(new_attr)
                    obj = new_obj
                else:
                    obj = None if obj_attr is None else obj_attr.data

        else:
            if data is None:
                if res.context != 'attr':
                    # For almost everything, we can just return the data.
                    return res.value
                else:
                    # We have to find the object version of the attribute.
                    # res.value is a class_attr
                    return _find_attribute(obj, var, conf)
            else:
                if res.context not in ['object', 'attr']:
                    _raise_helper(var, expr,
                                  f'Cannot assign to {res.context}')
                elif res.context == 'object':
                    # Assign entire top level object
                    _check_obj_type(data, res.value)
                    res.value.attrs = data.attrs
                    return
                elif res.context == 'attr':
                    _check_data_type(data, res.value, class_.name, False)
                    attr: Attribute = _find_attribute(obj, var, conf)
                    if attr is None:
                        new_attr: Attribute = copy(res.value)
                        new_attr.data = data
                        new_attr.conf = conf
                        obj.attrs.append(new_attr)
                        return
                    else:
                        old_data = attr.data
                        attr.data = data
                        return old_data


def _find_var(var: str, current: Union[Namespace, Node]) -> _SearchResult:
    """Look for the var, and return a dict with results.

    Search in node first, if available, then progress to namespace."""
    if isinstance(current, Node):
        res = _search_node(var, current)
        if res:
            return res
        else:
            return _search_namespace(var, current.namespace)
    elif isinstance(current, Namespace):
        return _search_namespace(var, current)


def _search_namespace(var: str, namespace: Namespace) -> _SearchResult:
    """Search through this namespace, trying to find if the given var
    is part of it.

    dict: {context, data}

    context: ['namespace', 'object', 'class', 'assigner']

    data: Namespace, Node, or Assign"""
    for parent in namespace.parents:
        if parent['name'] == var:
            return _SearchResult('namespace', parent['namespace'])

    for node in namespace.nodes:
        if node.name == var:
            return _SearchResult(node.type_, node)

    for assign in namespace.assigners:
        if assign.name == var:
            return _SearchResult('assigner', assign)

    return None


def _search_node(var: str, class_: Node) -> _SearchResult:
    """Search through this class_, trying to find the given var.
    Will recurse through extended classes if it isn't contained
    at the starting class_."""
    # Is the var an attribute here in this node?
    for attr in class_.attrs:
        if var == attr.name:
            return _SearchResult('attr', attr)

    for extend in class_.extends:
        # Maybe it's an explicitly extended class?
        if extend.name == var:
            return _SearchResult('class', extend)
        else:
            # Or somewhere in an extended class?
            res = _search_node(var, extend)
            if res is not None:
                return res

    return None


def _get_prefix(var: str, extend: Node, class_: Node) -> str:
    """Get the explicitly extended class prefix,
    if there's a conflict and the prefix is needed. Otherwise None"""
    for conf in class_.conflicts:
        if (conf['class_'] == extend.name and conf['var'] == var):
            return extend.name + '.' + var
    return None


def _get_conflict(var: str, class_: Node, extend: Node):
    for conf in class_.conflicts:
        if conf.class_ == extend and conf.var == var:
            return conf
    return None


def _find_attribute(obj: Node, var: str, conf: NameConflict) -> dict:
    """Search for and return a contained value in this object,
    based on the variable and possibly prefix."""
    if obj is None:
        return None
    for attr in obj.attrs:
        if conf:
            if conf == attr.conf:
                return attr
        elif var == attr.name:
            return attr
    return None


def _check_data_type(data, attr: Attribute, class_name: str,
                     dat_is_list: bool):
    """Make sure given bit of data matches what it's being assigned to.
    raise if it isn't"""
    if attr.class_ != 'String':
        attr_name = attr.class_.name
    expr = class_name + '.' + attr.name
    att_is_str = attr.class_ == 'String'

    if isinstance(data, str):
        dat = 'String'
    elif isinstance(data, list):
        if not attr.list_:
            if att_is_str:
                raise VarError(f'Expected string "{expr}", got list')
            else:
                raise VarError(f'Expected class "{attr_name}", got list')
        for item in data:
            _check_data_type(item, attr, class_name, True)
        return
    else:
        # data must be an object
        dat = data.extends[0]
    dat_is_str = dat == 'String'

    if att_is_str and not dat_is_str:
        raise VarError(f'Expected string "{expr}", got "{dat.name}"')

    if not att_is_str and dat_is_str:
        raise VarError(f'Expected class "{attr_name}", got string')

    if not att_is_str and not dat_is_str and attr.class_ != dat:
        if not _check_inheritance(attr.class_, dat):
            raise VarError(f'Expected "{attr_name}", got "{dat.name}"')

    if attr.list_ and not dat_is_list:
        raise VarError(f'"{expr}" expected a list')


def _check_obj_type(data, obj: Node):
    """Special check for when assigning to a top level object.
    Has very different context from _check_data_type, but WET repeats
    some code."""
    class_ = obj.extends[0]
    if isinstance(data, str):
        raise VarError(f'Expected class "{class_.name}", got string')
    if isinstance(data, list):
        raise VarError(f'Expected class "{class_.name}", got list')
    dat = data.extends[0]
    if not _check_inheritance(class_, dat):
        raise VarError(f'Expected "{class_.name}", got "{dat.name}"')


def _check_inheritance(target: Node, current: Node) -> bool:
    """Check whether the current type is actually a child class of the
    target type"""
    if target == current:
        return True
    for extend in current.extends:
        recurse = _check_inheritance(target, extend)
        if recurse:
            return True

    return False


def _raise_helper(var: str, expr: List[str], message: str):
    err = message + ' "' + var + '" in "' + '.'.join(expr) + '"'
    raise VarError(err)
