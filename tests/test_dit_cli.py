import io
import json
import os
from contextlib import redirect_stdout

import pytest
from _pytest.python import Metafunc

from dit_cli.exceptions import DitError
from dit_cli.interpreter import interpret
from dit_cli.oop import d_Dit

# test: pytest.thing = None
os.environ["NO_COLOR"] = "1"
PATH = "tests/json_data"


def load_from_json():
    for file_name in os.listdir(PATH):
        with open(PATH + "/" + file_name) as file_:
            test_json = json.load(file_)
            for test in test_json["dits"]:
                yield test


def pytest_generate_tests(metafunc: Metafunc):
    for fixture in metafunc.fixturenames:
        if fixture == "dit_json":
            test_dicts = list(load_from_json())
            titles = []
            for test_dict in test_dicts:
                if len(test_dict["title"]) > 62:
                    raise ValueError(
                        f"The test titled [{test_dict['title']}] is too long."
                    )
                titles.append(test_dict["title"])
            metafunc.parametrize(argnames=fixture, argvalues=test_dicts, ids=titles)


def test_dits(dit_json):
    try:
        output = io.StringIO()
        with redirect_stdout(output):
            dit = d_Dit.from_str("__main__", dit_json["dit"], "tests/fail.dit")
            interpret(dit)
            if len(output.getvalue()) == 0:
                print("Finished successfully")
        assert output.getvalue() == dit_json["expected"]
    except DitError as err:
        assert err.get_cli_trace() == dit_json["expected"]
