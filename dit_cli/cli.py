"""The CLI for dit"""
import argparse

import dit_cli.settings
from dit_cli import __version__
from dit_cli.exceptions import DitError
from dit_cli.interpreter import interpret
from dit_cli.lang_daemon import start_daemon
from dit_cli.oop import d_Dit


def main():
    """Run the dit_cli, via argparse"""
    arg_parser = argparse.ArgumentParser(
        description="Utility for the dit container file."
    )

    arg_parser.add_argument(
        "filepath", metavar="filepath", type=str, help="path to the dit file"
    )
    arg_parser.add_argument("-v", "--version", action="version", version=__version__)
    args = arg_parser.parse_args()

    try:
        dit = d_Dit()
        dit.name = "-main-"
        dit.path = args.filepath
        dit_cli.settings.DIT_FILEPATH = args.filepath
        dit.finalize()
        start_daemon()
        interpret(dit)
    except DitError as err:
        final = err.get_cli_trace()
        print(final)


if __name__ == "__main__":
    main()
