"""The CLI for dit"""


import click

from dit_cli.exceptions import DitError
from dit_cli.parser import parse
from dit_cli.evaler import validate_object


@click.group()
def main():
    """Utility for dit files"""


@click.command()
@click.argument('file_path')
def validate(file_path):
    """Validate the following file, according to dit standards"""

    with open(file_path) as file_object:
        click.echo(validate_dit(file_object.read()))


def validate_dit(dit):
    """Validates a string as a dit."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Discard dit and get the tree
        tree = parse(dit)

        # TODO: Add class higherachy check, to restrict circular inheritance
        # I might never do this, I'm not sure.

        for node in tree.nodes:
            if node.type_ == 'object':
                validate_object(node, tree)

        return 'dit is valid, no errors found'
    except DitError as error:
        return error


main.add_command(validate)

if __name__ == '__main__':
    main()
