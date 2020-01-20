"""The CLI for dit"""


import click


from dit_cli.dit import validate_dit


@click.group()
def main():
    """Utility for dit files"""


@click.command()
@click.argument('file_path')
def validate(file_path):
    """Validate the following file, according to dit standards"""

    with open(file_path) as file_object:
        click.echo(validate_dit(file_object.read()))


main.add_command(validate)

if __name__ == '__main__':
    main()
