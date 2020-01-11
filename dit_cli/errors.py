"""Storage for error strings"""

# pylint: disable=invalid-name
# pylint: disable=line-too-long
errors = {
    "dit": {
        "doc_type": 'Dit error: file did not begin with "<!DOCTYPE dit xml>".\nFirst 25 characters: {}'.format(dit_string[:25])
    }
}
