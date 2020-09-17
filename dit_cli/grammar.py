"""All fundamental grammatical concepts in dit, with their string representations"""
from enum import Enum


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
    VOID = "void"
    LISTOF = "listOf"
    IMPORT = "import"
    FROM = "from"
    THROW = "throw"
    RETURN = "return"
    SELF = "self"

    # Primitives (basically keywords)
    PRIMITIVE_ANY = "Any"
    PRIMITIVE_STRING = "String"
    PRIMITIVE_CLASS = "Class"
    PRIMITIVE_INSTANCE = "Instance"
    PRIMITIVE_FUNCTION = "Func"
    PRIMITIVE_DIT = "Dit"

    # Special values
    WORD = 0
    NEW_NAME = 1

    VALUE_ANY = 2
    VALUE_STRING = 3
    VALUE_LIST = 4
    VALUE_CLASS = 5
    VALUE_INSTANCE = 6
    VALUE_FUNCTION = 7
    VALUE_DIT = 8

    EOF = 9


VALUE_CLASS_ABLES = [
    Grammar.DOT,
    Grammar.EQUALS,
    Grammar.COMMA,
    Grammar.SEMI,
    Grammar.PAREN_LEFT,
    Grammar.BRACKET_RIGHT,
    Grammar.EOF,  # to trigger _missing_terminal
]

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
    Grammar.LISTOF,
    Grammar.FROM,
    Grammar.THROW,
    Grammar.RETURN,
    Grammar.SELF,
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNCTION,
    Grammar.PRIMITIVE_DIT,
]

EXPRESSION_STARTERS = [
    Grammar.QUOTE_DOUBLE,
    Grammar.QUOTE_SINGLE,
    Grammar.BRACKET_LEFT,
    Grammar.CLASS,
    Grammar.IMPORT,
    Grammar.NEW_NAME,
    Grammar.VALUE_ANY,
    Grammar.VALUE_STRING,
    Grammar.VALUE_LIST,
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNCTION,
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
    Grammar.PRIMITIVE_FUNCTION,
    Grammar.PRIMITIVE_DIT,
]
VALUES = [
    Grammar.VALUE_ANY,
    Grammar.VALUE_STRING,
    Grammar.VALUE_LIST,
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNCTION,
    Grammar.VALUE_DIT,
]

TYPES = [
    Grammar.VALUE_CLASS,
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNCTION,
    Grammar.PRIMITIVE_DIT,
]

PRIMITIVES = [
    Grammar.PRIMITIVE_ANY,
    Grammar.PRIMITIVE_STRING,
    Grammar.PRIMITIVE_CLASS,
    Grammar.PRIMITIVE_INSTANCE,
    Grammar.PRIMITIVE_FUNCTION,
    Grammar.PRIMITIVE_DIT,
]

DOTABLES = [
    Grammar.VALUE_CLASS,
    Grammar.VALUE_INSTANCE,
    Grammar.VALUE_FUNCTION,
    Grammar.VALUE_DIT,
]
