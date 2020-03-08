"""Tree of dit classes and objects, represented by node objects."""
from typing import List
from dit_cli.exceptions import TreeError
from dit_cli import CONFIG


class Node:
    """A dataclass which represents an node in the tree."""

    def __init__(self, name: str, type_: str):
        self.name: str = name
        self.type_: str = type_
        self.extends: List[int] = []

        # {name: str, prefix: str, id_: int, list_: bool, data: ?}
        self.contains: List[dict] = []
        self.validator: dict = None  # {code, lang}

        # id_ is for when the variable is an extended class
        self.print: dict = None  # {code, lang, variable, id_}
        self.conflicts: List[dict] = []  # {class_, var}


class Tree:
    """Stores a directed tree of Node objects.
    Each node is either a dit class or object.
    The connections between nodes represent extension or containment"""

    def __init__(self):
        self.nodes: List[Node] = []

    def new(self, name: str, type_: str) -> Node:
        """Add a blank node to this tree and return it"""
        for node in self.nodes:
            if name == node.name:
                raise TreeError(
                    f'Variable "{name}" has already been defined')
        self.nodes.append(Node(name, type_))
        return self.cur()

    def cur(self) -> Node:
        """Return the current node, which is always the last one, [-1]"""
        return self.nodes[-1]

    def add_extend(self, extend_name: str):
        """Make the current node extend another node,
        given the name of that node."""
        id_ = _id_from_name(extend_name, self)
        if id_ in self.cur().extends:
            raise TreeError(
                f'"{self.cur().name}" already extends "{extend_name}"')

        for extend in self.cur().extends:
            for old_contain in self.nodes[extend].contains:
                for new_contain in self.nodes[id_].contains:
                    if old_contain['name'] == new_contain['name']:
                        self.cur().conflicts.append(
                            {'class_': extend_name, 'var': old_contain['name']})

        self.cur().extends.append(id_)

    def add_contain(self, type_name: str, var_name: str,
                    list_: bool = False):
        """Make the current node contain something,
        given info about what it should contain"""
        if type_name == 'String':
            id_ = -1
        else:
            id_ = _id_from_name(type_name, self)

        for contain in self.cur().contains:
            if var_name == contain['name']:
                raise TreeError(
                    f'Variable "{var_name}" has already been defined')

        for extend in self.cur().extends:
            for old_contain in self.nodes[extend].contains:
                if old_contain['name'] == var_name:
                    self.cur().conflicts.append(
                        {'class_': self.nodes[extend].name, 'var': var_name})

        contain = {'id_': id_, 'name': var_name, 'list_': list_,
                   'data': None, 'prefix': None}
        self.cur().contains.append(contain)

    def set_print(self, variable: List[str] = None,
                  code: str = None, lang: str = None):
        """Give the current node a print function,
        either with code or a contained variable"""
        # Make sure variable to be printed is defined
        id_ = None
        if variable:
            result = _process_var(self, variable, class_=self.cur())
            if result is not None:
                id_ = _id_from_name(result.name, self)

        # Make sure language exists in config
        # WET also appears in set_validator
        if lang and not lang in CONFIG:
            raise TreeError(f'"{lang}" does not exist in .dit-languages')

        self.cur().print = {'variable': variable,
                            'code': code, 'lang': lang, 'id_': id_}

    def set_validator(self, code: str, lang: str):
        """Give the current node a validator"""
        # Make sure language exists in config
        # WET also appears in set_validator
        if lang and not lang in CONFIG:
            raise TreeError(f'"{lang}" does not exist in .dit-languages')
        self.cur().validator = {'code': code, 'lang': lang}

    def is_defined(self, variable: List[str]):
        """Check that a parsed variable exists somewhere in this tree"""
        _process_var(self, variable)

    def assign_var(self, variable: List[str], data):
        """Assign the data attribute of a contain,
        creating new objects/contains whereever necessary."""
        _process_var(self, variable, data=data)

    def get_contain(self, variable: List[str], class_: Node = None,
                    obj: Node = None):
        """Get the contain or data associated with a variable"""
        return _process_var(self, variable, class_=class_, obj=obj)

    def get_data(self, variable: List[str]):
        """Get the data, and only the data, associated with a variable"""
        result = self.get_contain(variable)
        try:
            return result['data']  # If it really is a contain
        except TypeError:
            return result


class Assigner:
    """A dataclass which represents an assigner"""

    def __init__(self, name: str, id_: int):
        self.name: str = name
        self.id_: int = id_
        self.assignments: List[dict] = []  # {variable, position}

    def get_object(self, tree: Tree, paramenters) -> Node:
        """Create and return a new anonymous object based on this assigner"""
        if len(paramenters) < len(self.assignments):
            raise TreeError(f'Not enough arguments for assigner "{self.name}"')
        if len(paramenters) > len(self.assignments):
            raise TreeError(f'Too many arguments for assigner "{self.name}')

        # All assigned objects have no name. This has no easy fix.
        # There is way to know what the name should be.
        # Top level objects get user defined names,
        # and objects created by assigning class fields can just take
        # the variable name of their class.
        # For now, all assigned objects are anonymous
        obj = Node('anonymous', 'object')
        obj.extends.append(self.id_)
        for assign in self.assignments:
            _process_var(tree, assign['variable'], class_=tree.nodes[self.id_],
                         obj=obj, data=paramenters[assign['position']])
        return obj


class Assigners:
    """Stores the dit assigners for this parser"""

    def __init__(self):
        self.assigners: List[Assigner] = []

    def new(self, type_name: str, assigner_name: str, tree: Tree):
        """Create a new assigner"""
        id_ = _id_from_name(type_name, tree)

        if assigner_name in [func.name for func in self.assigners]:
            raise TreeError(
                f'Assigner "{assigner_name}" has already been defined')

        self.assigners.append(Assigner(assigner_name, id_))

    def cur(self) -> Assigner:
        """Get the current assigner, which is always the last one [-1]"""
        return self.assigners[-1]

    def set_assign(self, raw_assigns: List[dict],
                   parameters: List[str], tree: Tree):
        """Set the assignments for the current assigner"""

        for raw in raw_assigns:
            _process_var(tree, raw['variable'],
                         class_=tree.nodes[self.cur().id_])
            if raw['parameter'] not in parameters:
                raise TreeError(f'Undefined parameter "{raw["parameter"]}"')
            for (position, parameter) in enumerate(parameters):
                if parameter == raw['parameter']:
                    assignment = {'variable': raw['variable'],
                                  'position': position}
                    break

            self.cur().assignments.append(assignment)

    def is_defined(self, name: str):
        """Check if an assigner by a given name exists"""
        for assign in self.assigners:
            if name == assign.name:
                return assign

        raise TreeError(f'Undefined assigner "{name}"')


def _process_var(tree: Tree, variable: List[str], class_: Node = None,
                 obj=None, data=None):
    """Core of the variable system.
    Handles all CRUD operations for any variable interation.
    Searches and finds each part of a variable, and creates/assigns
    objects/data as needed.
    """

    # TODO: _process_var needs refactor
    # This is probably the worst/most ugly code in the project.
    # The CRUD should be split into separate functions, which means
    # a lot more helper functions so that each Read and Update aren't
    # repeating code.
    #
    # My code smell tells me the real issue is with the dictionaries,
    # and the fact that contain info and node info are seperated.
    # I think refactoring the data structures would make this much more
    # readable without changing the flow control at all.
    first_var = None
    if not class_:
        node_id = _id_from_name(variable[0], tree)
        if len(variable) == 1 and data is not None:  # assign entire node
            tree.nodes[node_id].contains = data.contains
            return
        obj = tree.nodes[node_id]
        if obj.type_ == 'class':
            raise TreeError(f'Cannot assign to class: {variable[0]}')
        class_ = tree.nodes[obj.extends[0]]
        first_var = variable.pop(0)

    prefix = None
    for index, var in enumerate(variable):
        result = _recurse_var(var, class_, tree)
        if result[0] == 'not found':
            var_string = _print_var(variable, first_var)
            raise TreeError(f'Undefined variable "{var}"{var_string}')

        if index < len(variable) - 1:  # There are more elements
            if result[0] == 'extend':
                prefix = _get_prefix(variable[index + 1], result[1], result[2])
                class_ = result[1]
                continue
            elif result[0] == 'contain':
                class_contain = result[1]
                obj_contain = _find_contain(obj, var, prefix)
                if class_contain['id_'] == -1:
                    var_string = _print_var(variable, first_var)
                    raise TreeError(
                        f'Cannot reference string "{var}"{var_string}')
                if class_contain['list_']:
                    # TODO: You should be able to reference lists of objects.
                    # It would implicitly understand that you want to
                    # mess with each item in the list, rather than the list
                    # as a whole.
                    var_string = _print_var(variable, first_var)
                    raise TreeError(
                        f'Cannot reference list "{var}"{var_string}')

                if data is not None and obj_contain is None:
                    new_obj = Node(var, 'object')
                    new_obj.extends.append(class_contain['id_'])
                    new_contain = class_contain.copy()
                    new_contain['data'] = new_obj
                    new_contain['prefix'] = prefix
                    obj.contains.append(new_contain)
                    obj = new_obj
                else:
                    obj = None if obj_contain is None else obj_contain['data']

                class_ = tree.nodes[class_contain['id_']]
                continue

        if result[0] == 'extend':
            if data:
                raise TreeError(f'Cannot assign to class: {var}')
            else:
                return result[1]
        elif result[0] == 'contain':
            contain = _find_contain(obj, var, prefix)
            if data is None and contain is None:
                return None
            elif data is None and contain is not None:
                return contain
            elif data is not None:
                class_contain = result[1]
                _check_data_type(data, False, class_, tree, class_contain)
                if contain is None:
                    new_contain = class_contain.copy()
                    new_contain['data'] = data
                    new_contain['prefix'] = prefix
                    obj.contains.append(new_contain)
                    return
                else:
                    old_data = contain['data']
                    contain['data'] = data
                    return old_data
    return obj


def _get_prefix(var: str, extend: Node, class_: Node) -> str:
    """Get the explicitly extended class prefix,
    if there's a conflict and the prefix is needed. Otherwise None"""
    for con in class_.conflicts:
        if (con['class_'] == extend.name and con['var'] == var):
            return extend.name + '.' + var
    return None


def _find_contain(obj: Node, var: str, prefix: str) -> dict:
    """Search for and return a contained value in this object,
    based on the variable and possibly prefix."""
    if obj is None:
        return None
    for contain in obj.contains:
        if prefix:
            if prefix == contain['prefix']:
                return contain
        elif var == contain['name']:
            return contain
    return None


def _recurse_var(var: str, node: Node, tree: Tree):
    """Search through this node, trying to find if the given variable
    is part of it. Will recurse through extended classes if it isn't contained
    at the start node"""
    # Is var contained here, in this node?
    for contain in node.contains:
        if var == contain['name']:
            return ('contain', contain, node)

    for id_ in node.extends:
        extend = tree.nodes[id_]
        # Maybe it's an explicitly extended class?
        if extend.name == var:
            return ('extend', extend, node)
        else:
            # Or somewhere in an extended class?
            (enum, data, new_node) = _recurse_var(var, extend, tree)
            if enum != 'not found':
                return (enum, data, new_node)

    return ('not found', None, None)


def _check_data_type(data, list_: bool, class_: Node, tree: Tree, contain: dict):
    """Make sure given bit of data matches what it's being assigned to.
    raise if it isn't"""
    if isinstance(data, str):
        id_ = -1
    elif isinstance(data, list):
        for item in data:
            _check_data_type(item, True, class_, tree, contain)
        return
    else:
        id_ = data.extends[0]

    if contain['id_'] == -1 and id_ != -1:
        class_string = class_.name + '.' + contain["name"]
        data_name = tree.nodes[id_].name
        raise TreeError(f'Expected string "{class_string}", got "{data_name}"')
    if contain['id_'] != -1 and id_ == -1:
        contain_name = tree.nodes[contain['id_']].name
        raise TreeError(f'Expected "{contain_name}", got string')
    if contain['id_'] != -1 and id_ != -1 and contain['id_'] != id_:
        if _check_inheritance(contain['id_'], id_, tree):
            return
        contain_name = tree.nodes[contain['id_']].name
        data_name = tree.nodes[id_].name
        raise TreeError(
            f'Expected "{contain_name}", got "{data_name}"')
    if contain['list_'] and not list_:
        class_name = class_.name + '.' + contain["name"]
        raise TreeError(f'"{class_name}" expected a list')


def _check_inheritance(target: int, current: int, tree: Tree) -> bool:
    """Check whether the current type is actually a child class of the
    target type"""
    if target == current:
        return True
    for extend in tree.nodes[current].extends:
        recurse = _check_inheritance(target, extend, tree)
        if recurse:
            return True

    return False


def _id_from_name(name: str, tree: Tree) -> int:
    """Find an node in the tree by the given name"""
    for id_, node in enumerate(tree.nodes):
        if node.name == name:
            return id_

    raise TreeError(f'Undefined variable "{name}"')


def _print_var(variable: List[str], first_var):
    if first_var:
        variable.insert(0, first_var)
    if len(variable) == 1:
        return ''
    else:
        return ' in "' + '.'.join(variable) + '"'
