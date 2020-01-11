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

    file_text = load_file_to_string(file_path)
    validation_result = validate_dit(file_text, file_path)
    click.echo(validation_result)


def load_file_to_string(file_path):
    """Load a file into a string"""
    with open(file_path) as file_object:
        file_text = file_object.read()
        return file_text


main.add_command(validate)

if __name__ == '__main__':
    main()
