"""Pytest unit tests"""

import os
from dit_cli.cli import load_file_to_string
from dit_cli.dit import validate_dit

SCRIPT_DIR = os.path.dirname(__file__)
LENGTHS_VALID = os.path.join(SCRIPT_DIR, 'dits/lengths.dit')


def test_validate():
    """Check that validation returns true on valid file"""
    assert validate_dit(load_file_to_string(
        LENGTHS_VALID), 'lengths.dit') == 'lengths.dit is valid'
