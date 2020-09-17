"""The CLI for dit"""
import argparse

from dit_cli import __version__
from dit_cli.color import Color, color
from dit_cli.exceptions import DitError
from dit_cli.interpreter import start_interpret


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
        start_interpret(args.filepath)
        print(color("Finished successfully", Color.GREEN_LIGHT))
    except DitError as err:
        final = err.get_cli_trace()
        print(final)


if __name__ == "__main__":
    main()
