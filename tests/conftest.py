import pytest
from _pytest.config import Config
from _pytest.reports import TestReport


def pytest_runtest_logreport(report: TestReport):
    report.nodeid = report.nodeid[report.nodeid.find("[") :]


def pytest_addoption(parser):
    parser.addoption("-A", "--all", action="store", default=False, help="The user")


def pytest_configure(config: Config):
    pytest.all_val = config.getoption("all")  # type: ignore

