"""The CLI for dit"""
import argparse
import sys

from dit_cli import __version__
from dit_cli.color import Color, color
from dit_cli.exceptions import DitError
from dit_cli.interpreter import interpret
from dit_cli.oop import d_Dit


class PrintLogger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log: str = ""
        self.any_print: bool = False

    def write(self, message):
        self.terminal.write(message)
        self.log += message
        self.any_print = True

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass


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
        sys.stdout = PrintLogger()
        dit = d_Dit()
        dit.name = "__main__"
        dit.path = args.filepath
        dit.finalize()
        interpret(dit)
        if not sys.stdout.any_print:
            print(color("Finished successfully", Color.GREEN_LIGHT))
    except DitError as err:
        final = err.get_cli_trace()
        print(final)


if __name__ == "__main__":
    main()
