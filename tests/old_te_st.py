import json
import os

"""
import pathlib

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome("/home/isaiah/drivers/chromedriver", options=chrome_options)
"""

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
    '''
    pyodide_code = pathlib.Path("tests/pyodide.js").read_text()
    driver.execute_script(pyodide_code)
    pyodide_code += """
await loadPyodide(
{
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.17.0/full/",
    fullStdLib: false,
});
await pyodide.runPythonAsync(`import micropip
await micropip.install('setuptools')
await micropip.install('https://dev.ditabase.io/js/dit_cli-0.5.1-py3-none-any.whl')
from dit_cli.cli import run_string
`);"""

    driver.execute_async_script(pyodide_code)
'''
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

