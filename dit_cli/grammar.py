"""All fundamental grammatical concepts in dit, with their string representations"""
from enum import Enum


# test
class d_Grammar(Enum):
    """Enum with all dit grammatical types."""

    # Comments
    COMMENT_START = "/"
    COMMENT_SINGLE_OPEN = "//"
    COMMENT_SINGLE_CLOSE = "\n"
    COMMENT_MULTI_OPEN = "/*"
    COMMENT_MULTI_CLOSE = "*/"

    # Doubles
    BRACE_LEFT = "{{"
    BRACE_RIGHT = "}}"
    TRIANGLE_LEFT = "<|"
    TRIANGLE_RIGHT = "|>"
    CIRCLE_LEFT = "(|"
    CIRCLE_RIGHT = "|)"

    # Singles
    QUOTE_DOUBLE = '"'
    QUOTE_SINGLE = "'"
    DOT = "."
    EQUALS = "="
    PLUS = "+"
    COMMA = ","
    SEMI = ";"
    PAREN_LEFT = "("
    PAREN_RIGHT = ")"
    BRACKET_LEFT = "["
    BRACKET_RIGHT = "]"
    BACKSLASH = "\\"

    # Keywords
    CLASS = "class"
    FUNC = "func"
    DITLANG = "Ditlang"
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    VOID = "void"
    LISTOF = "listOf"
    IMPORT = "import"
    FROM = "from"
    THROW = "throw"
    RETURN = "return"
    THIS = "this"

    # Primitives (basically keywords)
    PRIMITIVE_THING = "Thing"
    PRIMITIVE_STRING = "String"
    PRIMITIVE_CLASS = "Class"
    PRIMITIVE_INSTANCE = "Instance"
    PRIMITIVE_FUNC = "Func"
    PRIMITIVE_DIT = "Dit"

    # Special values
    WORD = 0
    NEW_NAME = 1

    VALUE_THING = 2
    VALUE_STRING = 3
    VALUE_LIST = 4
    VALUE_CLASS = 5
    VALUE_INSTANCE = 6
    VALUE_FUNC = 7
    VALUE_DIT = 8
    VALUE_LANG = 10

    EOF = 9


def prim_to_value(grammar: d_Grammar) -> d_Grammar:
    return PRIM_TO_VALUE_DISPATCH[grammar]


PRIM_TO_VALUE_DISPATCH = {
    d_Grammar.PRIMITIVE_THING: d_Grammar.VALUE_THING,
    d_Grammar.PRIMITIVE_STRING: d_Grammar.VALUE_STRING,
    d_Grammar.PRIMITIVE_CLASS: d_Grammar.VALUE_CLASS,
    d_Grammar.PRIMITIVE_FUNC: d_Grammar.VALUE_FUNC,
    d_Grammar.PRIMITIVE_DIT: d_Grammar.VALUE_DIT,
}


def value_to_prim(grammar: d_Grammar) -> d_Grammar:
    return VALUE_TO_PRIM_DISPATCH[grammar]


VALUE_TO_PRIM_DISPATCH = {
    d_Grammar.VALUE_THING: d_Grammar.PRIMITIVE_THING,
    d_Grammar.VALUE_STRING: d_Grammar.PRIMITIVE_STRING,
    d_Grammar.VALUE_CLASS: d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.VALUE_FUNC: d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.VALUE_DIT: d_Grammar.PRIMITIVE_DIT,
}

VALUE_CLASS_ABLES = [
    d_Grammar.DOT,
    d_Grammar.EQUALS,
    d_Grammar.COMMA,
    d_Grammar.SEMI,
    d_Grammar.PAREN_LEFT,
    d_Grammar.BRACKET_RIGHT,
    d_Grammar.EOF,  # to trigger _missing_terminal
]

LANGS = [d_Grammar.DITLANG, d_Grammar.PYTHON, d_Grammar.JAVASCRIPT]

NON_VALUES_STARTERS = [
    d_Grammar.DOT,
    d_Grammar.EQUALS,
    d_Grammar.PLUS,
    d_Grammar.COMMA,
    d_Grammar.SEMI,
    d_Grammar.PAREN_LEFT,
    d_Grammar.PAREN_RIGHT,
    d_Grammar.BRACKET_RIGHT,
    d_Grammar.BACKSLASH,
    d_Grammar.VOID,
    d_Grammar.DITLANG,
    d_Grammar.PYTHON,
    d_Grammar.JAVASCRIPT,
    d_Grammar.LISTOF,
    d_Grammar.FROM,
    d_Grammar.THROW,
    d_Grammar.RETURN,
    d_Grammar.THIS,
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STRING,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
]

EXPRESSION_STARTERS = [
    d_Grammar.QUOTE_DOUBLE,
    d_Grammar.QUOTE_SINGLE,
    d_Grammar.BRACKET_LEFT,
    d_Grammar.CLASS,
    d_Grammar.FUNC,
    d_Grammar.IMPORT,
    d_Grammar.NEW_NAME,
    d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STRING,
    d_Grammar.VALUE_LIST,
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
]

SINGLES = [
    d_Grammar.QUOTE_DOUBLE,
    d_Grammar.QUOTE_SINGLE,
    d_Grammar.DOT,
    d_Grammar.EQUALS,
    d_Grammar.PLUS,
    d_Grammar.COMMA,
    d_Grammar.SEMI,
    d_Grammar.PAREN_LEFT,
    d_Grammar.PAREN_RIGHT,
    d_Grammar.BRACKET_LEFT,
    d_Grammar.BRACKET_RIGHT,
    d_Grammar.BACKSLASH,
]

DOUBLES = [
    d_Grammar.BRACE_LEFT,
    d_Grammar.BRACE_RIGHT,
    d_Grammar.TRIANGLE_LEFT,
    d_Grammar.TRIANGLE_RIGHT,
    d_Grammar.CIRCLE_LEFT,
    d_Grammar.CIRCLE_RIGHT,
]

KEYWORDS = [
    d_Grammar.CLASS,
    d_Grammar.FUNC,
    d_Grammar.DITLANG,
    d_Grammar.PYTHON,
    d_Grammar.JAVASCRIPT,
    d_Grammar.VOID,
    d_Grammar.LISTOF,
    d_Grammar.IMPORT,
    d_Grammar.FROM,
    d_Grammar.THROW,
    d_Grammar.RETURN,
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STRING,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
]
VALUES = [
    d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STRING,
    d_Grammar.VALUE_LIST,
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
]

TYPES = [
    d_Grammar.VOID,
    d_Grammar.VALUE_CLASS,
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STRING,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
]

PRIMITIVES = [
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STRING,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
]

DOTABLES = [
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
]

NAMEABLES = [
    d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STRING,
    d_Grammar.VALUE_LIST,
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
    d_Grammar.NEW_NAME,
]
