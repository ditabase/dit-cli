"""Home of the Assigner class"""

from typing import List, TYPE_CHECKING

from dit_cli.node import Node
from dit_cli.exceptions import AssignError
from dit_cli.dataclasses import Expression
if TYPE_CHECKING:
    from dit_cli.namespace import Namespace


class Assigner:
    """A dataclass which represents an assigner"""

    def __init__(self, namespace: 'Namespace',
                 name: str, class_expr: List[str]):
        namespace.raise_if_defined(name)

        self.namespace: 'Namespace' = namespace
        self.name: str = name
        self.class_: Node = self.namespace.read(class_expr)
        self.assignments: List[dict] = []  # {expr, pos}
        self.namespace.assigners.append(self)
        self.arg_count: int = None

    def get_object(self, args) -> Node:
        """Create and return a new anonymous object
        based on this assigner"""
        if len(args) != self.arg_count:
            raise AssignError((
                f'Assigner "{self.name}" expected '
                f'{self.arg_count} args, got {len(args)}'
            ))

        # All assigned objects are anonymous
        anon = Node(self.namespace, 'anonymous', 'object')
        anon.extends.append(self.class_)
        for assign in self.assignments:
            expr = Expression(self.namespace, self.class_,
                              anon, assign['expr'])
            self.namespace.write(expr, data=args[assign['pos']])
        return anon

    def set_assign(self, assigns: List[dict], args: List[str]):
        """Set the assignments for the current assigner"""
        self.arg_count = len(args)
        for assign in assigns:
            expr = Expression(self.name, self.class_, None, assign['expr'])
            self.namespace.raise_if_undefined(expr)
            if assign['arg'] not in args:
                raise AssignError((
                    f'Undefined arg "{assign["arg"]}" '
                    f'for Assigner {self.name}'
                ))
            for pos, arg in enumerate(args):
                if arg == assign['arg']:
                    assignment = {'expr': assign['expr'], 'pos': pos}
                    break

            self.assignments.append(assignment)
