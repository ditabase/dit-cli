"""Terminal coloring utility, using ANSI color codes."""
import os
from enum import Enum


class Color(Enum):
    """ANSI color codes
    https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters"""

    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    NEGATIVE = "\033[7m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BLACK_LIGHT = "\033[90m"
    RED_LIGHT = "\033[91m"
    GREEN_LIGHT = "\033[92m"
    YELLOW_LIGHT = "\033[93m"
    BLUE_LIGHT = "\033[94m"
    PURPLE_LIGHT = "\033[95m"
    CYAN_LIGHT = "\033[96m"
    WHITE_LIGHT = "\033[97m"

    BACK_BLACK = "\033[40m"
    BACK_RED = "\033[41m"
    BACK_GREEN = "\033[42m"
    BACK_YELLOW = "\033[43m"
    BACK_BLUE = "\033[44m"
    BACK_PURPLE = "\033[45m"
    BACK_CYAN = "\033[46m"
    BACK_WHITE = "\033[47m"

    BACK_BLACK_LIGHT = "\033[100m"
    BACK_RED_LIGHT = "\033[101m"
    BACK_GREEN_LIGHT = "\033[102m"
    BACK_YELLOW_LIGHT = "\033[103m"
    BACK_BLUE_LIGHT = "\033[1010m"
    BACK_PURPLE_LIGHT = "\033[105m"
    BACK_CYAN_LIGHT = "\033[106m"
    BACK_WHITE_LIGHT = "\033[107m"

    END = "\033[0m"


def color(message: str, *colors: Color, always_color: bool = False,) -> str:
    """Add 1 or more colors to a string, and get that string back.
    If NO_COLOR has any value, no colors will be added.
    This supports https://no-color.org/"""
    if not always_color and os.environ.get("NO_COLOR") is not None:
        return message
    out = ""
    for col in colors:
        out += col.value
    return out + message + Color.END.value


if __name__ == "__main__":
    for col_ in dir(Color):
        if col_[0:1] != "_" and col_ != "END":
            print("{:>20} {}".format(col_, getattr(Color, col_) + col_ + Color.END))
