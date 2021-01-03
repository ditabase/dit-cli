import pytest
from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter


def pytest_runtest_logreport(report: TestReport):
    report.nodeid = report.nodeid[report.nodeid.find("[") :]
