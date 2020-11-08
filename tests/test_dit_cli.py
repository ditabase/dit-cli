import io
import json
import os
from contextlib import redirect_stdout

from dit_cli.exceptions import DitError
from dit_cli.interpreter import interpret
from dit_cli.object import Dit

os.environ["NO_COLOR"] = "1"
PATH = "tests/json_data"


def load_from_json():
    for file_name in os.listdir(PATH):
        with open(PATH + "/" + file_name) as file_:
            test_json = json.load(file_)
            for test in test_json["dits"]:
                yield test


def pytest_generate_tests(metafunc):
    for fixture in metafunc.fixturenames:
        if fixture == "dit_json":
            tests = load_from_json()
            metafunc.parametrize(fixture, tests)


def test_dits(dit_json):
    try:
        output = io.StringIO()
        with redirect_stdout(output):
            dit = Dit.from_str("__main__", dit_json["dit"], "tests/fail.dit")
            interpret(dit)
            print("Finished successfully")
        assert output.getvalue() == dit_json["expected"]
    except DitError as err:
        assert err.get_cli_trace() == dit_json["expected"]
