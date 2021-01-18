import json
import os
import sys
from threading import Thread

import pytest
from _pytest.python import Metafunc

import dit_cli.settings
from dit_cli.exceptions import DitError
from dit_cli.interpreter import interpret
from dit_cli.lang_daemon import start_daemon
from dit_cli.oop import d_Dit

dit_cli.settings.DIT_FILEPATH = "tests/fail.dit"

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
        start_daemon()
        orig_out = sys.stdout
        sys.stdout = open("/tmp/dit/test_output.txt", "w")
        dit = d_Dit.from_str("__main__", dit_json["dit"], "tests/fail.dit")
        interpret(dit)
        sys.stdout.close()
        sys.stdout = orig_out
        with open("/tmp/dit/test_output.txt", "r") as output:
            data = output.read()
            if len(data) == 0:
                data += "Finished successfully\n"
            assert data == dit_json["expected"]
    except DitError as err:
        assert err.get_cli_trace() == dit_json["expected"]
