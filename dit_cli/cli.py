"""The CLI for dit"""


import click

from dit_cli.exceptions import DitError
from dit_cli.parser import parse
from dit_cli.evaler import validate_object, serialize


@click.group()
def main():
    """Utility for dit files"""


@click.command()
@click.argument('filepath', type=click.File('r'))
def validate(filepath):
    """Validate the file"""
    click.echo(validate_dit(filepath.read()))


@click.command()
@click.argument('filepath', type=click.File('r'))
@click.argument('query')
def query(filepath, query):
    """Return data from @@variable sequence"""
    if query[:2] == '@@':
        query = query[2:]
    query = query.replace("'", '').replace('"', '')
    click.echo(validate_dit(filepath.read(), query=query))


def validate_dit(dit, query=None):
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

        if query is None:
            return 'dit is valid, no errors found'
        else:
            return serialize(query, tree)
    except DitError as error:
        return error


main.add_command(validate)
main.add_command(query)

if __name__ == '__main__':
    main()
