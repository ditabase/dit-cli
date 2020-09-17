import copy
import re
from typing import Optional, Union

from dit_cli.data_classes import CodeLocation, Token
from dit_cli.exceptions import EndOfFileError, SyntaxError_
from dit_cli.grammar import DOUBLES, KEYWORDS, SINGLES, Grammar
from dit_cli.object import Body, Class, Object

WHITESPACE = re.compile(r"\s")
LETTER = re.compile(r"[A-Za-z0-9_]")


class CharFeed:
    def __init__(self, view: memoryview, loc: CodeLocation) -> None:
        self.view: memoryview = view
        self.loc: CodeLocation = loc

    def eof(self, target: int = None) -> bool:
        if not target:
            target = self.loc.pos + 1
        return target >= len(self.view)

    def get_char(self, target: int) -> str:
        if self.eof(target=target):
            return None
        else:
            return chr(self.view[target])

    def current(self) -> str:
        return chr(self.view[self.loc.pos])

    def peek(self) -> str:
        try:
            return chr(self.view[self.loc.pos + 1])
        except IndexError as err:
            raise EndOfFileError from err

    def pop(self) -> str:
        char = self.peek()
        self.loc.pos += 1
        if char == "\n":
            self.loc.line += 1
            self.loc.col = 0
        else:
            self.loc.col += 1
        return char

    def find_char_ahead(self, char: str, loc: CodeLocation = None) -> int:
        if not loc:
            loc = self.loc
        char_pos = loc.pos + 1
        while not self.eof(target=char_pos):
            if chr(self.view[char_pos]) == char:
                return char_pos
            char_pos += 1
        return char_pos

    def get_line(self, loc: CodeLocation = None) -> str:
        if not loc:
            loc = self.loc
        beg = loc.pos - loc.col + 1
        end = self.find_char_ahead("\n", loc=loc)
        return bytes(self.view[beg:end]).decode()

    def _dev(self) -> str:
        return bytes(self.view[self.loc.pos : self.loc.pos + 30]).decode()


class InterpretContext:
    def __init__(self, body: Body, ini_col: int, ini_line: int) -> None:
        self.char_feed = CharFeed(body.view, CodeLocation(0, ini_col, ini_line))
        self.body: Body = body
        self.prev_tok: Token = None
        self.curr_tok: Token = None
        self.next_tok: Token = None
        self.side_tok: Token = None
        self.list_depth: int = 0
        self.eof: bool = False

        self.reset()

    def reset(self) -> None:
        self.listof: bool = False
        self.assignee: Object = None
        self.type_: Union[Grammar, Class] = None
        self.new_name: str = None
        self.dotted_body: Body = None

    def advance_tokens(self, find_word: bool = True) -> None:
        self._manipulate_tokens(self.get_token(find_word=find_word))

    def shift_tokens(self) -> None:
        self._manipulate_tokens(None)

    def _manipulate_tokens(self, tok: Token) -> None:
        self.prev_tok = self.curr_tok
        self.curr_tok = self.next_tok
        self.next_tok = tok

    def get_token(self, find_word: bool = True) -> Token:
        if self.eof:
            return _handle_eof(self)

        res = _clear_whitespace_and_comments(self)
        if res is not None:
            return res

        res = _find_double_chars(self)
        if res is not None:
            return res

        res = _find_single_chars(self)
        if res is not None:
            return res

        res = _find_words(self, find_word)
        if res is not None:
            return res

        raise SyntaxError_(f"Unrecognized token '{self.char_feed.current()}'")


def _clear_whitespace_and_comments(inter: InterpretContext) -> Optional[Token]:
    while True:
        if WHITESPACE.match(inter.char_feed.current()):
            if inter.char_feed.eof():
                return _handle_eof(inter)
            else:
                inter.char_feed.pop()
        elif inter.char_feed.current() == Grammar.COMMENT_START.value:
            _comment(inter.char_feed)
            if inter.char_feed.eof():
                return _handle_eof(inter)
        else:
            return None


def _find_double_chars(inter: InterpretContext) -> Optional[Token]:
    if inter.char_feed.eof():  # Can't be double if we only have 1 char
        return None

    cur = inter.char_feed.current() + inter.char_feed.peek()
    lok = copy.deepcopy(inter.char_feed.loc)
    for grammar in DOUBLES:
        if cur == grammar.value:
            inter.char_feed.pop()  # pop first char in double
            if inter.char_feed.eof():
                inter.eof = True
            else:
                inter.char_feed.pop()  # pop the second if it's safe
            return Token(grammar, lok)


def _find_single_chars(inter: InterpretContext) -> Optional[Token]:
    cur = inter.char_feed.current()
    lok = copy.deepcopy(inter.char_feed.loc)
    for grammar in SINGLES:
        if cur == grammar.value:
            # WET, appears in _find_double_chars
            if inter.char_feed.eof():
                inter.eof = True
            else:
                inter.char_feed.pop()
            return Token(grammar, lok)
    return None


def _find_words(inter: InterpretContext, find_word: bool) -> Optional[Token]:
    token_loc = copy.deepcopy(inter.char_feed.loc)
    word = ""
    while LETTER.match(inter.char_feed.current()):
        word += inter.char_feed.current()
        if inter.char_feed.eof():
            inter.eof = True
            break
        else:
            inter.char_feed.pop()

    if word:
        # Keywords first
        for grammar in KEYWORDS:
            if word == grammar.value:
                return Token(grammar, token_loc, data=word)
        # Used by var.class.attr expressions
        # They find the word themselves.
        if not find_word:
            return Token(Grammar.WORD, token_loc, data=word)
        # Most names
        attr = inter.body.find_attr(word)
        if attr:
            return Token(attr.grammar, token_loc, data=attr)
        else:
            return Token(Grammar.NEW_NAME, token_loc, data=word)
    else:
        return None


def _handle_eof(inter: InterpretContext) -> Token:
    inter.eof = True
    return Token(Grammar.EOF, copy.deepcopy(inter.char_feed.loc))


def _comment(inter: InterpretContext) -> None:
    com = inter.current() + inter.pop()
    if com == Grammar.COMMENT_MULTI_OPEN.value:
        _comment_multi(inter)
    elif com == Grammar.COMMENT_SINGLE_OPEN.value:
        _comment_single(inter)


def _comment_multi(inter: InterpretContext) -> None:
    while True:
        # com = inter.current() + inter.peek()
        if inter.current() + inter.peek() == Grammar.COMMENT_MULTI_CLOSE.value:
            inter.pop()  # pop *
            if not inter.eof():  # it's fine if */ is the last in the file
                inter.pop()  # pop /
            return
        inter.pop()


def _comment_single(inter: InterpretContext) -> None:
    if inter.eof():
        return
    while inter.current() != Grammar.COMMENT_SINGLE_CLOSE.value:
        if inter.eof():
            return
        else:
            inter.pop()
