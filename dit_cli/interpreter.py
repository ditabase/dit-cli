import copy
import os
from typing import Callable
from typing import List as ListHint
from typing import NoReturn, Optional, TypedDict, Union

from dit_cli.data_classes import CodeLocation, Token
from dit_cli.exceptions import (
    DitError,
    EndOfClassError,
    EndOfFileError,
    SyntaxError_,
)
from dit_cli.grammar import (
    DOTABLES,
    EXPRESSION_STARTERS,
    KEYWORDS,
    NON_VALUES_STARTERS,
    PRIMITIVES,
    SINGLES,
    TYPES,
    VALUE_CLASS_ABLES,
    VALUES,
    Grammar,
)
from dit_cli.interpret_context import InterpretContext
from dit_cli.object import (
    Body,
    Class,
    Dit,
    Function,
    Instance,
    List,
    Object,
    String,
)


class Dispatch(TypedDict):
    gram: Grammar
    func: Callable[[InterpretContext], Union[str, list, Object]]


def start_interpret(path: str) -> None:
    _interpret(Dit("__main__", path), 1, 1)


def _test_interpret(dit: str, mock_path: str):
    _interpret(Dit.from_str("__main__", dit, mock_path), 1, 1)
    print("Finished successfully")


def _interpret(body: Body, ini_col: int, ini_line: int) -> None:
    if len(body.view) == 0:
        return
    inter = InterpretContext(body, ini_col, ini_line)
    try:
        at_eof = False
        while not at_eof:
            if inter.char_feed.eof():
                at_eof = True  # one extra iteration for the last char
            inter.advance_tokens()
            if inter.next_tok.grammar == Grammar.EOF:
                return  # Only at EOF whitespace or comment
            else:
                _statement_dispatch(inter)
    except DitError as err:
        _generate_origin(err, inter)
        raise
    return


def _generate_origin(
    err: DitError, inter: InterpretContext, loc: CodeLocation = None
) -> None:
    if err.origin is not None:
        return

    if not loc:
        loc = inter.char_feed.loc

    code = inter.char_feed.get_line(loc)
    err.set_origin(inter.body.path, loc, code)


def _raise_helper(message: str, inter: InterpretContext) -> NoReturn:
    err = SyntaxError_(message)
    _generate_origin(err, inter, inter.next_tok.loc)
    raise err


def _statement_dispatch(inter: InterpretContext) -> Union[Object, str, list]:
    func = STATEMENT_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _expression_dispatch(inter: InterpretContext) -> Union[Object, str, list]:
    func = EXPRESSION_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _listof(inter: InterpretContext) -> None:
    # listOf String values;
    inter.advance_tokens()
    inter.listof = True
    if inter.next_tok.grammar in PRIMITIVES:
        _primitive(inter)
    elif inter.next_tok.grammar in DOTABLES:
        type_ = _expression_dispatch(inter)
        if not isinstance(type_, Class):
            raise NotImplementedError
        else:
            inter.type_ = type_
    else:
        _raise_helper("Expected type for listOf declaration", inter)


def _primitive(inter: InterpretContext) -> None:
    # String value;
    inter.advance_tokens()
    inter.type_ = inter.curr_tok.grammar

    if inter.next_tok.grammar == Grammar.NEW_NAME:
        name = inter.next_tok.data
    elif inter.next_tok.grammar in DOTABLES:
        name = _expression_dispatch(inter)
    else:
        _raise_helper("Expected new name for declaration", inter)

    inter.new_name = name
    inter.advance_tokens()
    _declare(inter)
    _equalable(inter)


def _value_string(inter: InterpretContext) -> Optional[Body]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_list(inter: InterpretContext) -> Optional[Body]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_class(inter: InterpretContext,) -> Optional[Body]:
    inter.advance_tokens()
    if inter.next_tok.grammar in VALUE_CLASS_ABLES:
        return _parenable(inter)
    else:
        # This value class is being used as var type
        inter.type_ = inter.curr_tok.data if not inter.side_tok else inter.side_tok.data


def _value_instance(inter: InterpretContext) -> Optional[Body]:
    inter.advance_tokens()
    return _dotable(inter)


def _value_function(inter: InterpretContext) -> Optional[Body]:
    inter.advance_tokens()
    return _parenable(inter)


def _value_dit(inter: InterpretContext) -> Optional[Body]:
    if not inter.side_tok:
        inter.advance_tokens()
    return _dotable(inter)


def _parenable(inter: InterpretContext) -> Optional[Object]:
    if inter.next_tok.grammar == Grammar.PAREN_LEFT:
        raise NotImplementedError
    else:
        return _dotable(inter)


def _dotable(inter: InterpretContext) -> Optional[Body]:
    if inter.next_tok.grammar == Grammar.DOT:
        # ... ThisDit.Ele ...
        dot = _dot(inter)
        inter.next_tok = dot
        inter.side_tok = None
        return _expression_dispatch(inter)

    else:
        return _equalable(inter)


def _dot(inter: InterpretContext) -> Token:
    inter.advance_tokens(False)  # We want to manage the next word ourselves
    if inter.next_tok.grammar != Grammar.WORD:
        _raise_helper(f"'{inter.next_tok.grammar}' is not dotable", inter)
    previous = inter.prev_tok.data if not inter.side_tok else inter.side_tok.data
    result = inter.body.find_attr(inter.next_tok.data, previous=previous)
    if result:
        return Token(result.grammar, copy.deepcopy(inter.next_tok.loc), result)
    else:
        inter.dotted_body = previous  # Save for assignment
        inter.next_tok.grammar = Grammar.NEW_NAME
        return inter.next_tok


def _equalable(inter: InterpretContext) -> None:
    if inter.next_tok.grammar == Grammar.EQUALS:
        if inter.side_tok:
            raise NotImplementedError
        if not inter.assignee:
            inter.assignee = inter.curr_tok.data
        _equals(inter)
    else:
        return _terminal(inter)


def _terminal(inter: InterpretContext) -> Object:
    if inter.next_tok.grammar not in [
        Grammar.SEMI,
        Grammar.COMMA,
        Grammar.BRACKET_RIGHT,
    ]:
        if inter.list_depth == 0:
            _missing_terminal(inter, "Expected ';'")
        else:
            _missing_terminal(inter, "Expected ']'")

    temp_side = inter.side_tok  # Save the side token, if there is one
    inter.side_tok = None  # side token is always cleared on any terminal
    ret = inter.curr_tok.data if not temp_side else temp_side.data

    if inter.next_tok.grammar == Grammar.SEMI:
        _semi(inter)
    return ret


def _new_name(inter: InterpretContext) -> str:
    if not inter.type_:
        _raise_helper(f"Undeclared variable '{inter.next_tok.data}'", inter)
    return inter.next_tok.data


def _equals(inter: InterpretContext) -> None:
    inter.advance_tokens()
    # assignee will be cleared by the semicolon, so we save it
    saved_assignee: Object = inter.assignee
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    saved_assignee.set_value(value)
    _terminal(inter)


def _semi(inter: InterpretContext) -> None:
    inter.reset()


def _declare(inter: InterpretContext) -> None:
    if inter.type_ is None or inter.new_name is None or inter.assignee is not None:
        raise NotImplementedError
    body = inter.dotted_body if inter.dotted_body else inter.body
    inter.assignee = body.add_attr(inter.new_name, inter.type_, inter.listof)
    inter.type_ = None
    inter.new_name = None


def _string(inter: InterpretContext) -> str:
    left = inter.next_tok.grammar.value
    data = ""
    while inter.char_feed.current() != left:
        data += inter.char_feed.current()
        inter.char_feed.pop()
    inter.advance_tokens()  # next_tok is now ' "
    inter.advance_tokens()  # next_tok is now ; , ] )
    return data


def _bracket_left(inter: InterpretContext) -> list:
    inter.advance_tokens(inter)
    data = []
    if inter.next_tok.grammar == Grammar.BRACKET_RIGHT:  # empty list
        inter.advance_tokens()  # next_tok is now ; , ] )
        return data

    inter.list_depth += 1
    while True:
        value = _expression_dispatch(inter)
        if value is None:
            raise NotImplementedError
        data.append(value)

        if inter.next_tok.grammar not in [Grammar.COMMA, Grammar.BRACKET_RIGHT]:
            _missing_terminal(inter, "Expected ']'")

        if inter.next_tok.grammar == Grammar.COMMA:
            inter.advance_tokens()

        # We check for a right bracket even if there was already a comma
        # This is to let trailing commas pass safely.
        if inter.next_tok.grammar == Grammar.BRACKET_RIGHT:
            inter.list_depth -= 1
            inter.advance_tokens()  # next_tok is now ; , ] )
            return data


def _import(inter: InterpretContext) -> Dit:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    inter.advance_tokens()
    name = None
    path = None

    if inter.next_tok.grammar == Grammar.NEW_NAME:
        # import SomeName from "someFilePath.dit";
        name = inter.next_tok.data
        inter.advance_tokens()
        if inter.next_tok.grammar != Grammar.FROM:
            _raise_helper("Expected 'from'", inter)
        inter.advance_tokens()

    if inter.next_tok.grammar not in EXPRESSION_STARTERS:
        _raise_helper("Expected a filepath string for import", inter)

    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    if isinstance(value, str):
        path = value
    elif isinstance(value, String):
        path = value.string_value
    elif isinstance(value, list):
        _raise_helper("Expected string value, not list", inter)
    else:
        _raise_helper(f"Expected string value, not {value.public_type}", inter)

    dit = Dit(name, path)
    try:
        _interpret(dit, 1, 1)
    except DitError as err:
        err.add_trace(path, orig_loc, "import")
        raise
    # WET: Similar to end of _class
    if name:
        # traditional import statement, stop here
        inter.body.attrs.append(dit)
        _terminal(inter)
    else:
        # anonymous import expression, need to check for inline dots
        inter.side_tok = Token(Grammar.VALUE_DIT, orig_loc, data=dit)
        return _value_dit(inter)


def _class(inter: InterpretContext) -> Class:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    inter.advance_tokens()
    name = None
    if inter.next_tok.grammar not in [Grammar.NEW_NAME, Grammar.BRACE_LEFT]:
        _raise_helper("Expected name or body to follow class", inter)

    if inter.next_tok.grammar == Grammar.NEW_NAME:
        name = inter.next_tok.data
        inter.advance_tokens()  # get {{
        if inter.next_tok.grammar != Grammar.BRACE_LEFT:
            _raise_helper("Expected a class body", inter)

    depth = 1
    start = copy.deepcopy(inter.char_feed.loc)
    end = None
    while depth > 0:
        cur = inter.char_feed.current() + inter.char_feed.peek()
        if cur == Grammar.BRACE_LEFT.value:
            depth += 1
            inter.advance_tokens()
        elif cur == Grammar.BRACE_RIGHT.value:
            depth -= 1
            end = inter.char_feed.loc.pos
            inter.advance_tokens()
        else:
            inter.char_feed.pop()
    class_ = Class(name, inter.body, start.pos, end)
    try:
        _interpret(class_, start.col, start.line)
    except EndOfFileError as err:
        raise EndOfClassError from err
    if name:
        # traditional class statement, stop here
        inter.body.attrs.append(class_)
    else:
        # anonymous class expression, need to dispatch it
        inter.side_tok = Token(Grammar.VALUE_CLASS, orig_loc, data=class_)
        return _value_class(inter)


def _missing_terminal(inter: InterpretContext, message: str) -> NoReturn:
    tok = inter.curr_tok
    target = tok.loc
    line = inter.char_feed.get_line(target)

    if isinstance(tok.grammar.value, str):
        length = len(tok.grammar.value)  # class, String, =
    elif isinstance(tok.data, Object):
        length = len(tok.data.name)  # Object names
    else:
        length = len(tok.data)  # New Names

    # Shift locaton to end of token
    target.pos += length
    target.col += length

    err = SyntaxError_(message)
    err.set_origin(inter.body.path, target, line)
    raise err


def _trigger_eof_err(inter: InterpretContext) -> NoReturn:
    inter.char_feed.pop()


def _not_implemented(inter: InterpretContext) -> NoReturn:
    raise NotImplementedError


def _illegal_statement(inter: InterpretContext) -> NoReturn:
    _raise_helper("Illegal start of statement", inter)


def _illegal_expression(inter: InterpretContext) -> NoReturn:
    _raise_helper("Illegal start of expression", inter)


# disable black formatting temporarily
# fmt: off
STATEMENT_DISPATCH: Dispatch = {
    Grammar.QUOTE_DOUBLE:           _illegal_statement,
    Grammar.QUOTE_SINGLE:           _illegal_statement,
    Grammar.DOT:                    _illegal_statement,
    Grammar.EQUALS:                 _illegal_statement,
    Grammar.PLUS:                   _not_implemented,
    Grammar.COMMA:                  _illegal_statement,
    Grammar.SEMI:                   _illegal_statement,
    Grammar.PAREN_LEFT:             _illegal_statement,
    Grammar.PAREN_RIGHT:            _illegal_statement,
    Grammar.BRACKET_LEFT:           _illegal_statement,
    Grammar.BRACKET_RIGHT:          _illegal_statement,
    Grammar.BACKSLASH:              _illegal_statement,
    Grammar.COMMENT_START:          _illegal_statement,
    Grammar.BRACE_LEFT:             _illegal_statement,
    Grammar.BRACE_RIGHT:            _illegal_statement,
    Grammar.TRIANGLE_LEFT:          _not_implemented,
    Grammar.TRIANGLE_RIGHT:         _not_implemented,
    Grammar.CIRCLE_LEFT:            _not_implemented,
    Grammar.CIRCLE_RIGHT:           _not_implemented,
    Grammar.CLASS:                  _class,
    Grammar.VOID:                   _illegal_statement,
    Grammar.LISTOF:                 _listof,
    Grammar.IMPORT:                 _import,
    Grammar.FROM:                   _illegal_statement,
    Grammar.THROW:                  _not_implemented,
    Grammar.RETURN:                 _not_implemented,
    Grammar.SELF:                   _not_implemented,
    Grammar.PRIMITIVE_ANY:          _primitive,
    Grammar.PRIMITIVE_STRING:        _primitive,
    Grammar.PRIMITIVE_CLASS:        _primitive,
    Grammar.PRIMITIVE_INSTANCE:     _primitive,
    Grammar.PRIMITIVE_FUNCTION:     _primitive,
    Grammar.PRIMITIVE_DIT:          _primitive,
    Grammar.WORD:                   _not_implemented,
    Grammar.NEW_NAME:               _new_name,
    Grammar.VALUE_ANY:              _not_implemented,
    Grammar.VALUE_STRING:           _value_string,
    Grammar.VALUE_LIST:             _value_list,
    Grammar.VALUE_CLASS:            _value_class,
    Grammar.VALUE_INSTANCE:         _value_instance,
    Grammar.VALUE_FUNCTION:         _value_function,
    Grammar.VALUE_DIT:              _value_dit,
    Grammar.EOF:                    _trigger_eof_err,
}


EXPRESSION_DISPATCH: Dispatch = {
    Grammar.QUOTE_DOUBLE:           _string,
    Grammar.QUOTE_SINGLE:           _string,
    Grammar.DOT:                    _illegal_expression,
    Grammar.EQUALS:                 _illegal_expression,
    Grammar.PLUS:                   _not_implemented,
    Grammar.COMMA:                  _illegal_expression,
    Grammar.SEMI:                   _illegal_expression,
    Grammar.PAREN_LEFT:             _illegal_expression,
    Grammar.PAREN_RIGHT:            _illegal_expression,
    Grammar.BRACKET_LEFT:           _bracket_left,
    Grammar.BRACKET_RIGHT:          _illegal_expression,
    Grammar.BACKSLASH:              _illegal_expression,
    Grammar.COMMENT_START:          _illegal_expression,
    Grammar.BRACE_LEFT:             _illegal_expression,
    Grammar.BRACE_RIGHT:            _illegal_expression,
    Grammar.TRIANGLE_LEFT:          _not_implemented,
    Grammar.TRIANGLE_RIGHT:         _not_implemented,
    Grammar.CIRCLE_LEFT:            _not_implemented,
    Grammar.CIRCLE_RIGHT:           _not_implemented,
    Grammar.CLASS:                  _class,
    Grammar.VOID:                   _illegal_expression,
    Grammar.LISTOF:                 _illegal_expression,
    Grammar.IMPORT:                 _import,
    Grammar.FROM:                   _illegal_expression,
    Grammar.THROW:                  _not_implemented,
    Grammar.RETURN:                 _not_implemented,
    Grammar.SELF:                   _not_implemented,
    Grammar.PRIMITIVE_ANY:          _illegal_expression,
    Grammar.PRIMITIVE_STRING:       _illegal_expression,
    Grammar.PRIMITIVE_CLASS:        _illegal_expression,
    Grammar.PRIMITIVE_INSTANCE:     _illegal_expression,
    Grammar.PRIMITIVE_FUNCTION:     _illegal_expression,
    Grammar.PRIMITIVE_DIT:          _illegal_expression,
    Grammar.WORD:                   _illegal_expression,
    Grammar.NEW_NAME:               _new_name,
    Grammar.VALUE_ANY:              _not_implemented,
    Grammar.VALUE_STRING:           _value_string,
    Grammar.VALUE_LIST:             _value_list,
    Grammar.VALUE_CLASS:            _value_class,
    Grammar.VALUE_INSTANCE:         _value_instance,
    Grammar.VALUE_FUNCTION:         _value_function,
    Grammar.VALUE_DIT:              _value_dit,
    Grammar.EOF:                    _trigger_eof_err,
}
# fmt: on
