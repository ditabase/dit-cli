"""Home of the main dit validation code.
The parser, tree structure, code eval,
and everything else will either be here or be called from here."""


def validate_dit(dit_string, file_path):
    """Validates a string as a dit. Called from the CLI."""

    # Catch all validation errors
    try:
        doc_type_error = (
            'Dit error: file did not begin with "<!DOCTYPE dit xml>" '
            'Beginning of dit reads:\n{}').format(dit_string[:40])

        if not dit_string.startswith('<!DOCTYPE dit xml>'):
            raise ValidationError(doc_type_error)

        return '{} is valid'.format(file_path)
    except ValidationError as error:
        return error


class ValidationError(Exception):
    """Raised when anything goes wrong during validation of a dit"""
