"""The CLI for dit"""
import argparse
import sys

import dit_cli.settings
from dit_cli import __version__
from dit_cli.exceptions import d_DitError
from dit_cli.interpreter import interpret
from dit_cli.lang_daemon import kill_all, start_daemon
from dit_cli.oop import d_Dit


def main():
    """Run the dit_cli, via argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "filepath", nargs="?", type=argparse.FileType("r"), default=sys.stdin
    )
    args = parser.parse_args()
    if sys.stdin.isatty() and args.filepath.name == "<stdin>":
        parser.error("must provide one of filepath or stdin pipe")
    code = args.filepath.read()
    start_daemon()
    run_string(code, args.filepath.name)


def run_string(dit_string: str, path: str):
    try:
        dit_cli.settings.DIT_FILEPATH = path
        dit = d_Dit.from_str("Main", dit_string, path)
        dit.finalize()
        interpret(dit)
    except d_DitError as err:
        final = err.get_cli_trace()
        print(final)
    finally:
        kill_all()


if __name__ == "__main__":
    main()
