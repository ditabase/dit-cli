"""All fundamental grammatical concepts in dit, with their string representations"""
from enum import Enum


# test
class Grammar(Enum):
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
    PRIMITIVE_ANY = "Any"
    PRIMITIVE_STRING = "String"
    PRIMITIVE_CLASS = "Class"
    PRIMITIVE_INSTANCE = "Instance"
    PRIMITIVE_FUNC = "Func"
    PRIMITIVE_DIT = "Dit"

    # Special values
    WORD = 0
    NEW_NAME = 1

    VALUE_ANY = 2
    VALUE_STRING = 3
    VALUE_LIST = 4
    VALUE_CLASS = 5
    VALUE_INSTANCE = 6
    VALUE_FUNC = 7
    VALUE_DIT = 8
    VALUE_LANG = 10

    EOF = 9


def prim_to_value(grammar: Grammar) -> Grammar:
    return PRIM_TO_VALUE_DISPATCH[grammar]


PRIM_TO_VALUE_DISPATCH = {
    Grammar.PRIMITIVE_ANY: Grammar.VALUE_ANY,
    Grammar.PRIMITIVE_STRING: Grammar.VALUE_STRING,
    Grammar.PRIMITIVE_CLASS: Grammar.VALUE_CLASS,
    Grammar.PRIMITIVE_FUNC: Grammar.VALUE_FUNC,
    Grammar.PRIMITIVE_DIT: Grammar.VALUE_DIT,
}


def value_to_prim(grammar: Grammar) -> Grammar:
    return VALUE_TO_PRIM_DISPATCH[grammar]


VALUE_TO_PRIM_DISPATCH = {
    Grammar.VALUE_ANY: Grammar.PRIMITIVE_ANY,
    Grammar.VALUE_STRING: Grammar.PRIMITIVE_STRING,
    Grammar.VALUE_CLASS: Grammar.PRIMITIVE_CLASS,
    Grammar.VALUE_FUNC: Grammar.PRIMITIVE_FUNC,
    Grammar.VALUE_DIT: Grammar.PRIMITIVE_DIT,
}

VALUE_CLASS_ABLES = [
    Grammar.DOT,
    Grammar.EQUALS,
    Grammar.COMMA,
    Grammar.SEMI,
    Grammar.PAREN_LEFT,
    Grammar.BRACKET_RIGHT,
    Grammar.EOF,  # to trigger _missing_terminal
]

LANGS = [Grammar.DITLANG, Grammar.PYTHON, Grammar.JAVASCRIPT]

NON_VALUES_STARTERS = [
    Grammar.DOT,
    Grammar.EQUALS,
    Grammar.PLUS,
    Grammar.COMMA,
    Grammar.SEMI,
    Grammar.PAREN_LEFT,
    Grammar.PAREN_RIGHT,
    Grammar.BRACKET_RIGHT,
    Grammar.BACKSLASH,
    Grammar.VOID,
    Grammar.DITLANG,
    Grammar.PYTHON,
    Grammar.JAVASCRIPT,
    Grammar.LISTOF,
    Grammar.FROM,
    Grammar.THROW,
    Grammar.RETURN,
    Grammar.THIS,
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNC,
    Grammar.PRIMITIVE_DIT,
]

EXPRESSION_STARTERS = [
    Grammar.QUOTE_DOUBLE,
    Grammar.QUOTE_SINGLE,
    Grammar.BRACKET_LEFT,
    Grammar.CLASS,
    Grammar.FUNC,
    Grammar.IMPORT,
    Grammar.NEW_NAME,
    Grammar.VALUE_ANY,
    Grammar.VALUE_STRING,
    Grammar.VALUE_LIST,
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNC,
    Grammar.VALUE_DIT,
]

SINGLES = [
    Grammar.QUOTE_DOUBLE,
    Grammar.QUOTE_SINGLE,
    Grammar.DOT,
    Grammar.EQUALS,
    Grammar.PLUS,
    Grammar.COMMA,
    Grammar.SEMI,
    Grammar.PAREN_LEFT,
    Grammar.PAREN_RIGHT,
    Grammar.BRACKET_LEFT,
    Grammar.BRACKET_RIGHT,
    Grammar.BACKSLASH,
]

DOUBLES = [
    Grammar.BRACE_LEFT,
    Grammar.BRACE_RIGHT,
    Grammar.TRIANGLE_LEFT,
    Grammar.TRIANGLE_RIGHT,
    Grammar.CIRCLE_LEFT,
    Grammar.CIRCLE_RIGHT,
]

KEYWORDS = [
    Grammar.CLASS,
    Grammar.FUNC,
    Grammar.DITLANG,
    Grammar.PYTHON,
    Grammar.JAVASCRIPT,
    Grammar.VOID,
    Grammar.LISTOF,
    Grammar.IMPORT,
    Grammar.FROM,
    Grammar.THROW,
    Grammar.RETURN,
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNC,
    Grammar.PRIMITIVE_DIT,
]
VALUES = [
    Grammar.VALUE_ANY,
    Grammar.VALUE_STRING,
    Grammar.VALUE_LIST,
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNC,
    Grammar.VALUE_DIT,
]

TYPES = [
    Grammar.VOID,
    Grammar.VALUE_CLASS,
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNC,
    Grammar.PRIMITIVE_DIT,
]

PRIMITIVES = [
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNC,
    Grammar.PRIMITIVE_DIT,
]

DOTABLES = [
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNC,
    Grammar.VALUE_DIT,
]

NAMEABLES = [
    Grammar.VALUE_ANY,
    Grammar.VALUE_STRING,
    Grammar.VALUE_LIST,
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNC,
    Grammar.VALUE_DIT,
    Grammar.NEW_NAME,
]
