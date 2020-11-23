import copy
import re
from typing import Optional

from dit_cli.built_in import BUILT_INS
from dit_cli.data_classes import CodeLocation
from dit_cli.exceptions import CriticalError, EndOfFileError, SyntaxError_
from dit_cli.grammar import DOUBLES, KEYWORDS, SINGLES, Grammar
from dit_cli.object import Body, Declarable, Object, Token

WHITESPACE = re.compile(r"\s")
LETTER = re.compile(r"[A-Za-z0-9_]")


class CharFeed:
    def __init__(self, view: memoryview, loc: CodeLocation) -> None:
        self.view: memoryview = view
        self.loc: CodeLocation = loc

    def eof(self, target: Optional[int] = None) -> bool:
        if target is None:
            target = self.loc.pos + 1
        return target >= len(self.view)

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

    def find_char_ahead(self, char: str, loc: CodeLocation) -> int:
        char_pos = loc.pos + 1
        while not self.eof(target=char_pos):
            if chr(self.view[char_pos]) == char:
                return char_pos
            char_pos += 1
        return char_pos

    def get_line(self, loc: CodeLocation) -> str:
        beg = loc.pos - loc.col + 1
        end = self.find_char_ahead("\n", loc=loc)
        return bytes(self.view[beg:end]).decode()

    def _dev(self) -> str:
        return bytes(self.view[self.loc.pos : self.loc.pos + 30]).decode()


class InterpretContext:
    def __init__(self, body: Body) -> None:
        # We need to start from 0 pos, but maintain the line and column
        # from the parent body.
        new_loc = CodeLocation(0, body.start_loc.col, body.start_loc.line)
        self.char_feed = CharFeed(body.view, new_loc)
        self.eof: bool = False
        self.body: Body = body

        self.prev_tok: Token = None  # type: ignore
        self.curr_tok: Token = None  # type: ignore
        self.next_tok: Token = None  # type: ignore
        self.anon_tok: Optional[Token] = None  # anon is actually *usually* None

        self.dec: Declarable = Declarable()
        self.assignee: Object = None  # type: ignore
        self.dotted_body: Body = None  # type: ignore
        self.comma_depth: int = 0
        self.func_sig: bool = False
        self.terminal_loc: CodeLocation = None  # type: ignore

    def advance_tokens(self, find_word: bool = True) -> None:
        self._manipulate_tokens(self.get_token(find_word=find_word))

    def shift_tokens(self) -> None:
        # next_tok will be manually assigned
        # This is for use with "find_word" = False,
        # so the interpreter can manually determine what a WORD is
        self._manipulate_tokens(None)  # type: ignore

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
                return Token(grammar, token_loc)
        for built_in in BUILT_INS:
            if word == built_in["name"]:
                return Token(Grammar.VALUE_FUNC, token_loc, obj=built_in["dit_func"])
        # Used by var.class.attr expressions
        # They find the word themselves.
        if find_word is False:
            return Token(Grammar.WORD, token_loc, word=word)
        # Most names
        attr = inter.body.find_attr(word)
        if attr:
            return Token(attr.grammar, token_loc, obj=attr)
        else:
            return Token(Grammar.NEW_NAME, token_loc, word=word)
    else:
        return None


def _handle_eof(inter: InterpretContext) -> Token:
    inter.eof = True
    return Token(Grammar.EOF, copy.deepcopy(inter.char_feed.loc))


def _comment(feed: CharFeed) -> None:
    com = feed.current() + feed.pop()
    if com == Grammar.COMMENT_MULTI_OPEN.value:
        _comment_multi(feed)
    elif com == Grammar.COMMENT_SINGLE_OPEN.value:
        _comment_single(feed)


def _comment_multi(feed: CharFeed) -> None:
    while True:
        # com = feed.current() + feed.peek()
        if feed.current() + feed.peek() == Grammar.COMMENT_MULTI_CLOSE.value:
            feed.pop()  # pop *
            if not feed.eof():  # it's fine if */ is the last in the file
                feed.pop()  # pop /
            return
        feed.pop()


def _comment_single(feed: CharFeed) -> None:
    if feed.eof():
        return
    while feed.current() != Grammar.COMMENT_SINGLE_CLOSE.value:
        if feed.eof():
            return
        else:
            feed.pop()