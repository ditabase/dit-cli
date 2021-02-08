"""All fundamental grammatical concepts in dit, with their string representations"""
from enum import Enum


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

    # Shapes
    TRI_LEFT = "<|"
    TRI_RIGHT = "|>"
    CIR_LEFT = "(|"
    CIR_RIGHT = "|)"

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

    # Escapes
    BACKSLASH = "\\"
    ESCAPE_TAB = "t"
    ESCAPE_NEWLINE = "n"

    # Keywords
    CLASS = "class"
    SIG = "sig"
    FUNC = "func"
    VOID = "void"
    LISTOF = "listOf"
    IMPORT = "import"
    FROM = "from"
    AS = "as"
    PULL = "pull"
    USE = "use"
    STATIC = "static"
    INSTANCE = "instance"
    THROW = "throw"
    RETURN = "return"
    NULL = "null"
    LANG = "lang"

    # Primitives (basically keywords)
    PRIMITIVE_THING = "Thing"
    PRIMITIVE_STRING = "String"
    PRIMITIVE_CLASS = "Class"
    PRIMITIVE_INSTANCE = "Instance"
    PRIMITIVE_FUNC = "Func"
    PRIMITIVE_DIT = "Dit"
    PRIMITIVE_LANG = "Lang"

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
    d_Grammar.PRIMITIVE_INSTANCE: d_Grammar.VALUE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC: d_Grammar.VALUE_FUNC,
    d_Grammar.PRIMITIVE_DIT: d_Grammar.VALUE_DIT,
    d_Grammar.PRIMITIVE_LANG: d_Grammar.VALUE_LANG,
    d_Grammar.VALUE_THING: d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STRING: d_Grammar.VALUE_STRING,
    d_Grammar.VALUE_LIST: d_Grammar.VALUE_LIST,
    d_Grammar.VALUE_CLASS: d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE: d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC: d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT: d_Grammar.VALUE_DIT,
    d_Grammar.VALUE_LANG: d_Grammar.VALUE_LANG,
    d_Grammar.NULL: d_Grammar.NULL,
    d_Grammar.VOID: d_Grammar.VOID,
}


def value_to_prim(grammar: d_Grammar) -> d_Grammar:
    return VALUE_TO_PRIM_DISPATCH[grammar]


VALUE_TO_PRIM_DISPATCH = {
    d_Grammar.VALUE_THING: d_Grammar.PRIMITIVE_THING,
    d_Grammar.VALUE_STRING: d_Grammar.PRIMITIVE_STRING,
    d_Grammar.VALUE_LIST: d_Grammar.LISTOF,
    d_Grammar.VALUE_CLASS: d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.VALUE_INSTANCE: d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.VALUE_FUNC: d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.VALUE_DIT: d_Grammar.PRIMITIVE_DIT,
    d_Grammar.VALUE_LANG: d_Grammar.PRIMITIVE_LANG,
    d_Grammar.PRIMITIVE_THING: d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STRING: d_Grammar.PRIMITIVE_STRING,
    d_Grammar.PRIMITIVE_CLASS: d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE: d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC: d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT: d_Grammar.PRIMITIVE_DIT,
    d_Grammar.PRIMITIVE_LANG: d_Grammar.PRIMITIVE_LANG,
    d_Grammar.NULL: d_Grammar.NULL,
    d_Grammar.VOID: d_Grammar.VOID,
}
