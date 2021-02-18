import json
import os

import pytest
from _pytest.python import Metafunc

from dit_cli.cli import run_string
from dit_cli.lang_daemon import start_daemon

os.environ["NO_COLOR"] = "1"
PATH = "tests/json_data"


def load_from_json():
    for file_name in os.listdir(PATH):
        with open(PATH + "/" + file_name) as file_:
            test_json = json.load(file_)
            for test in test_json["dits"]:
                yield test


def pytest_generate_tests(metafunc: Metafunc):
    start_daemon()
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


def test_dits(dit_json, capfd):
    run_string(dit_json["dit"], "tests/fail.dit")
    output, err = capfd.readouterr()

    if len(output) == 0:
        assert "Finished successfully\n" == dit_json["expected"]
    else:
        if output == dit_json["expected"]:
            assert output == dit_json["expected"]
        else:
            assert output == dit_json["expected"] + "\n"

