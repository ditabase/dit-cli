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

    # Shapes
    TRI_LEFT = "<|"
    TRI_RIGHT = "|>"
    CIR_LEFT = "(|"
    CIR_RIGHT = "|)"
    BAR_BRACE_LEFT = "{|"
    BAR_BRACE_RIGHT = "|}"

    # Singles
    QUOTE_DOUBLE = '"'
    QUOTE_SINGLE = "'"
    DOT = "."
    POINT = "!"
    EQUALS = "="
    PLUS = "+"
    MINUS = "-"
    COMMA = ","
    COLON = ":"
    SEMI = ";"
    PAREN_LEFT = "("
    PAREN_RIGHT = ")"
    BRACKET_LEFT = "["
    BRACKET_RIGHT = "]"
    BRACE_LEFT = "{"
    BRACE_RIGHT = "}"

    # Escapes
    BACKSLASH = "\\"
    ESCAPE_TAB = "t"
    ESCAPE_NEWLINE = "n"

    # Keywords
    CLASS = "class"
    LANG = "lang"
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
    TRUE = "true"
    FALSE = "false"

    # Primitives (basically keywords)
    PRIMITIVE_THING = "Thing"
    PRIMITIVE_STR = "Str"
    PRIMITIVE_BOOL = "Bool"
    PRIMITIVE_NUM = "Num"
    PRIMITIVE_JSON = "JSON"
    PRIMITIVE_CLASS = "Class"
    PRIMITIVE_INSTANCE = "Instance"
    PRIMITIVE_FUNC = "Func"
    PRIMITIVE_DIT = "Dit"
    PRIMITIVE_LANG = "Lang"

    # Special values
    WORD = 0
    NEW_NAME = 1
    DIGIT = 14

    VALUE_NULL = 15
    VALUE_THING = 2
    VALUE_STR = 3
    VALUE_BOOL = 11
    VALUE_NUM = 12
    VALUE_LIST = 4
    VALUE_JSON = 13
    VALUE_CLASS = 5
    VALUE_INSTANCE = 6
    VALUE_FUNC = 7
    VALUE_DIT = 8
    VALUE_LANG = 10

    EOF = 9


MAKE = "Make"
THIS = "this"


def prim_to_value(grammar: d_Grammar) -> d_Grammar:
    return PRIM_TO_VALUE_DISPATCH[grammar]


PRIM_TO_VALUE_DISPATCH = {
    d_Grammar.PRIMITIVE_THING: d_Grammar.VALUE_THING,
    d_Grammar.PRIMITIVE_STR: d_Grammar.VALUE_STR,
    d_Grammar.PRIMITIVE_BOOL: d_Grammar.VALUE_BOOL,
    d_Grammar.PRIMITIVE_NUM: d_Grammar.VALUE_NUM,
    d_Grammar.PRIMITIVE_JSON: d_Grammar.VALUE_JSON,
    d_Grammar.PRIMITIVE_CLASS: d_Grammar.VALUE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE: d_Grammar.VALUE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC: d_Grammar.VALUE_FUNC,
    d_Grammar.PRIMITIVE_DIT: d_Grammar.VALUE_DIT,
    d_Grammar.PRIMITIVE_LANG: d_Grammar.VALUE_LANG,
    d_Grammar.VALUE_THING: d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STR: d_Grammar.VALUE_STR,
    d_Grammar.VALUE_BOOL: d_Grammar.VALUE_BOOL,
    d_Grammar.VALUE_NUM: d_Grammar.VALUE_NUM,
    d_Grammar.VALUE_LIST: d_Grammar.VALUE_LIST,
    d_Grammar.VALUE_JSON: d_Grammar.VALUE_JSON,
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
    d_Grammar.VALUE_STR: d_Grammar.PRIMITIVE_STR,
    d_Grammar.VALUE_BOOL: d_Grammar.PRIMITIVE_BOOL,
    d_Grammar.VALUE_NUM: d_Grammar.PRIMITIVE_NUM,
    d_Grammar.VALUE_JSON: d_Grammar.PRIMITIVE_JSON,
    d_Grammar.VALUE_LIST: d_Grammar.LISTOF,
    d_Grammar.VALUE_CLASS: d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.VALUE_INSTANCE: d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.VALUE_FUNC: d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.VALUE_DIT: d_Grammar.PRIMITIVE_DIT,
    d_Grammar.VALUE_LANG: d_Grammar.PRIMITIVE_LANG,
    d_Grammar.PRIMITIVE_THING: d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STR: d_Grammar.PRIMITIVE_STR,
    d_Grammar.PRIMITIVE_BOOL: d_Grammar.PRIMITIVE_BOOL,
    d_Grammar.PRIMITIVE_NUM: d_Grammar.PRIMITIVE_NUM,
    d_Grammar.PRIMITIVE_JSON: d_Grammar.PRIMITIVE_JSON,
    d_Grammar.PRIMITIVE_CLASS: d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE: d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC: d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT: d_Grammar.PRIMITIVE_DIT,
    d_Grammar.PRIMITIVE_LANG: d_Grammar.PRIMITIVE_LANG,
    d_Grammar.NULL: d_Grammar.NULL,
    d_Grammar.VOID: d_Grammar.VOID,
}

NAMEABLES = [
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
    d_Grammar.VALUE_LANG,
    d_Grammar.NEW_NAME,
]

DUPLICABLES = [
    d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STR,
    d_Grammar.VALUE_LIST,
]

VALUE_CLANG_ABLES = [
    d_Grammar.DOT,
    d_Grammar.EQUALS,
    d_Grammar.COMMA,
    d_Grammar.SEMI,
    d_Grammar.BRACKET_RIGHT,
    d_Grammar.BRACE_RIGHT,
    d_Grammar.EOF,  # to trigger _missing_terminal
]

PRIMITIVES = [
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STR,
    d_Grammar.PRIMITIVE_BOOL,
    d_Grammar.PRIMITIVE_NUM,
    d_Grammar.PRIMITIVE_JSON,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
    d_Grammar.PRIMITIVE_LANG,
]

DOTABLES = [
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
    d_Grammar.VALUE_LANG,
]

STRINGABLES = [
    d_Grammar.QUOTE_DOUBLE,
    d_Grammar.QUOTE_SINGLE,
    d_Grammar.VALUE_THING,
    d_Grammar.VALUE_STR,
    d_Grammar.VALUE_CLASS,
    d_Grammar.VALUE_INSTANCE,
    d_Grammar.VALUE_FUNC,
    d_Grammar.VALUE_DIT,
    d_Grammar.VALUE_LANG,
]

TYPES = [
    d_Grammar.VALUE_CLASS,
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STR,
    d_Grammar.PRIMITIVE_BOOL,
    d_Grammar.PRIMITIVE_NUM,
    d_Grammar.PRIMITIVE_JSON,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
    d_Grammar.PRIMITIVE_LANG,
]

DOUBLES = [
    d_Grammar.TRI_LEFT,
    d_Grammar.TRI_RIGHT,
    d_Grammar.CIR_LEFT,
    d_Grammar.CIR_RIGHT,
    d_Grammar.BAR_BRACE_LEFT,
    d_Grammar.BAR_BRACE_RIGHT,
]

SINGLES = [
    d_Grammar.QUOTE_DOUBLE,
    d_Grammar.QUOTE_SINGLE,
    d_Grammar.DOT,
    d_Grammar.POINT,
    d_Grammar.EQUALS,
    d_Grammar.PLUS,
    d_Grammar.MINUS,
    d_Grammar.COMMA,
    d_Grammar.COLON,
    d_Grammar.SEMI,
    d_Grammar.PAREN_LEFT,
    d_Grammar.PAREN_RIGHT,
    d_Grammar.BRACKET_LEFT,
    d_Grammar.BRACKET_RIGHT,
    d_Grammar.BRACE_LEFT,
    d_Grammar.BRACE_RIGHT,
    d_Grammar.BACKSLASH,
]

KEYWORDS = [
    d_Grammar.CLASS,
    d_Grammar.LANG,
    d_Grammar.SIG,
    d_Grammar.FUNC,
    d_Grammar.VOID,
    d_Grammar.LISTOF,
    d_Grammar.IMPORT,
    d_Grammar.FROM,
    d_Grammar.AS,
    d_Grammar.PULL,
    d_Grammar.USE,
    d_Grammar.STATIC,
    d_Grammar.INSTANCE,
    d_Grammar.THROW,
    d_Grammar.RETURN,
    d_Grammar.NULL,
    d_Grammar.TRUE,
    d_Grammar.FALSE,
    d_Grammar.PRIMITIVE_THING,
    d_Grammar.PRIMITIVE_STR,
    d_Grammar.PRIMITIVE_BOOL,
    d_Grammar.PRIMITIVE_NUM,
    d_Grammar.PRIMITIVE_JSON,
    d_Grammar.PRIMITIVE_CLASS,
    d_Grammar.PRIMITIVE_INSTANCE,
    d_Grammar.PRIMITIVE_FUNC,
    d_Grammar.PRIMITIVE_DIT,
    d_Grammar.PRIMITIVE_LANG,
]
