"""Home of the main dit validation code.
The parser, tree structure, code eval,
and everything else will either be here or be called from here."""

from dit_cli.exceptions import DitError
from dit_cli.parser import parse
from dit_cli.evaler import validate_object


def validate_dit(dit):
    """Validates a string as a dit. Called from the CLI."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Discard dit and get the tree
        tree = parse(dit)

        # TODO: Add class higherachy check, such as Arborescence.
        # I might never do this, I'm not sure.

        for node in tree.nodes:
            if node.type_ == 'object':
                validate_object(node, tree)

        return 'dit is valid, no errors found'
    except DitError as error:
        return error
