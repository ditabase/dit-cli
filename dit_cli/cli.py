"""The CLI for dit"""


import click

from dit_cli.exceptions import DitError
from dit_cli.parser import parse
from dit_cli.evaler import validate_object, serialize
from dit_cli.dataclasses import EvalContext


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
@click.argument('query_string')
def query(filepath, query_string):
    """Return data from @@variable sequence"""
    query_string = query_string.replace("'", '').replace('"', '')
    if query_string[:2] == '@@':
        query_string = query_string[2:]
    click.echo(validate_dit(filepath.read(), query_string=query_string))


def validate_dit(dit, query_string=None):
    """Validates a string as a dit."""

    # Catch all validation errors. The entire validation is done inside this try.
    try:
        # Discard dit and get the namespace
        namespace = parse(dit)

        # TODO: Add class higherachy check, to restrict circular inheritance
        # I might never do this, I'm not sure.

        for space in _all_namespaces(namespace):
            for node in space.nodes:
                if node.type_ == 'object':
                    validate_object(node)

        if query_string is None:
            return 'dit is valid, no errors found'
        else:
            eva = EvalContext(None, None, namespace)
            return serialize(eva, query_string)
    except DitError as error:
        return error


def _all_namespaces(namespace):
    for parent in namespace.parents:
        yield parent['namespace']
    yield namespace


main.add_command(validate)
main.add_command(query)

if __name__ == '__main__':
    main()
