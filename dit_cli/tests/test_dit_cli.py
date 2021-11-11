import json
import os

import pytest
from _pytest.python import Metafunc

from dit_cli.cli import run_string
from dit_cli.lang_daemon import start_daemon

os.environ["NO_COLOR"] = "1"
if "PYODIDE" in os.environ:
    PATH = "/lib/python3.9/site-packages/dit_cli/tests/json_data"
else:
    PATH = "tests/json_data"


def load_from_json():
    for file_name in os.listdir(PATH):
        with open(PATH + "/" + file_name) as file_:
            test_json = json.load(file_)
            for test in test_json["dits"]:
                yield test


def pytest_generate_tests(metafunc: Metafunc):
    # start_daemon()
    print("cwd: " + str(os.listdir()))
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
    if "long" in dit_json and not pytest.all_val:  # type: ignore
        pytest.skip("Long test")
    # res = driver.execute_async_script(f'run_string({dit_json["dit"]}, "tests/fail.dit"')
    run_string(dit_json["dit"], "tests/fail.dit")
    output, err = capfd.readouterr()

    if len(output) == 0:
        assert "Finished successfully\n" == dit_json["expected"]
    else:
        if output == dit_json["expected"]:
            assert output == dit_json["expected"]
        else:
            assert output == dit_json["expected"] + "\n"

