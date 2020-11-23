import copy
from itertools import zip_longest
from typing import List as ListHint
from typing import NoReturn, Optional

from dit_cli.data_classes import CodeLocation
from dit_cli.exceptions import (
    CriticalError,
    DitError,
    EndOfClassError,
    EndOfFileError,
    SyntaxError_,
    TypeMismatchError,
)
from dit_cli.grammar import (
    DOTABLES,
    EXPRESSION_STARTERS,
    LANGS,
    NAMEABLES,
    PRIMITIVES,
    TYPES,
    VALUE_CLASS_ABLES,
    Grammar,
    prim_to_value,
)
from dit_cli.interpret_context import InterpretContext
from dit_cli.object import (
    Arg,
    Body,
    Class,
    Declarable,
    Dit,
    Function,
    Instance,
    List,
    Object,
    ReturnController,
    String,
    Token,
    Type,
)


def interpret(body: Body) -> None:
    if isinstance(body, Function) and body.is_built_in:
        body.py_func(body.attrs[0])
        return
    if not body.is_ready():
        return
    inter = InterpretContext(body)
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
    err: DitError, inter: InterpretContext, loc: Optional[CodeLocation] = None
) -> None:
    if err.origin is not None:
        return
    if loc is None:
        loc = inter.char_feed.loc
    code = inter.char_feed.get_line(loc)
    if inter.body.path is None:
        raise CriticalError("A body had no path during exception")
    err.set_origin(inter.body.path, loc, code)


def _raise_helper(
    message: str,
    inter: InterpretContext,
    loc: Optional[CodeLocation] = None,
) -> NoReturn:
    err = SyntaxError_(message)
    loc = loc if loc is not None else inter.next_tok.loc
    _generate_origin(err, inter, loc)
    raise err


def _statement_dispatch(inter: InterpretContext) -> None:
    func = STATEMENT_DISPATCH[inter.next_tok.grammar]
    func(inter)


def _expression_dispatch(inter: InterpretContext) -> Optional[Arg]:
    if inter.anon_tok:
        func = EXPRESSION_DISPATCH[inter.anon_tok.grammar]
    else:
        func = EXPRESSION_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _listof(inter: InterpretContext) -> None:
    # listOf String values;
    inter.advance_tokens()
    inter.dec.listof = True
    if inter.next_tok.grammar in PRIMITIVES:
        _primitive(inter)
    elif inter.next_tok.grammar in DOTABLES:
        type_ = _expression_dispatch(inter)
        if not isinstance(type_, Class):
            raise NotImplementedError
        else:
            inter.dec.type_ = type_
    else:
        _raise_helper("Expected type for listOf declaration", inter)


def _primitive(inter: InterpretContext) -> None:
    # String value;
    inter.advance_tokens()
    _type(inter)

def _value_any(inter: InterpretContext) -> Optional[Arg]:
    if inter.next_tok.obj
    _statement_dispatch()


def _value_string(inter: InterpretContext) -> Optional[Arg]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_list(inter: InterpretContext) -> Optional[Arg]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_class(inter: InterpretContext) -> Optional[Arg]:
    if inter.func_sig:
        inter.advance_tokens(False)
        if inter.next_tok.grammar == Grammar.DOT:
            return _dotable(inter)
        else:
            return inter.curr_tok.obj

    inter.advance_tokens(True)
    if inter.next_tok.grammar in VALUE_CLASS_ABLES:
        return _parenable(inter)
    elif inter.anon_tok:
        # This prevents using an anonymous class as a type
        # Triggering terminal will call missing ';'
        _terminal(inter)
    else:
        # This value class is being used as var type
        _type(inter)


def _type(inter: InterpretContext) -> None:

    inter.dec.type_ = _token_to_type(inter.curr_tok)
    if inter.next_tok.grammar in NAMEABLES:
        res = _expression_dispatch(inter)
        if res is None:
            raise NotImplementedError
        elif isinstance(res, str):
            inter.dec.name = res
    else:
        _raise_helper("Expected a new name to follow type", inter)
    inter.advance_tokens()
    _declare(inter)
    _equalable(inter)


def _token_to_type(token: Token) -> Type:
    if token.obj:
        return token.obj  # type: ignore
    else:
        return token.grammar


def _value_instance(inter: InterpretContext) -> Optional[Arg]:
    inter.advance_tokens()
    return _dotable(inter)


def _value_function(inter: InterpretContext) -> Optional[Arg]:
    inter.advance_tokens()
    return _parenable(inter)


def _value_dit(inter: InterpretContext) -> Optional[Arg]:
    if inter.anon_tok is None:
        inter.advance_tokens()
    return _dotable(inter)


def _parenable(inter: InterpretContext) -> Optional[Arg]:
    if inter.next_tok.grammar == Grammar.PAREN_LEFT:
        return _paren_left(inter)
    else:
        return _dotable(inter)


def _dotable(inter: InterpretContext) -> Optional[Arg]:
    if inter.next_tok.grammar == Grammar.DOT:
        # ... ThisDit.Ele ...
        dot = _dot(inter)
        inter.next_tok = dot
        inter.anon_tok = None
        return _expression_dispatch(inter)
    else:
        return _equalable(inter)


def _dot(inter: InterpretContext) -> Token:
    inter.advance_tokens(False)  # We want to manage the next word ourselves
    if inter.next_tok.grammar != Grammar.WORD:
        _raise_helper(f"'{inter.next_tok.grammar}' is not dotable", inter)
    if inter.anon_tok:
        previous: Body = inter.anon_tok.obj  # type: ignore
    else:
        previous: Body = inter.prev_tok.obj  # type: ignore
    result = inter.body.find_attr(inter.next_tok.word, previous=previous)
    if result:
        # The dot had a known variable, which we just need to return
        return Token(result.grammar, copy.deepcopy(inter.next_tok.loc), obj=result)
    else:
        # The name was not found in the dotted body, so its a new name.
        # This means we are declaring a new var in the dotted body.
        inter.next_tok.grammar = Grammar.NEW_NAME
        inter.dotted_body = previous  # Save for assignment
        return inter.next_tok


def _equalable(inter: InterpretContext) -> Optional[Arg]:
    if inter.dec.type_:
        # type_ should have been cleared by a _declare call
        _raise_helper(f"'{inter.curr_tok.obj.name}' has already been declared", inter)
    elif inter.next_tok.grammar == Grammar.EQUALS:
        if inter.anon_tok:
            # prevent assignment to anonymous tokens.
            raise NotImplementedError
        if inter.assignee is None:
            inter.assignee = inter.curr_tok.obj
        _equals(inter)
    else:
        return _terminal(inter)


def _terminal(inter: InterpretContext) -> Arg:
    if inter.next_tok.grammar not in [
        Grammar.SEMI,
        Grammar.COMMA,
        Grammar.BRACKET_RIGHT,
        Grammar.PAREN_RIGHT,
    ]:
        if inter.func_sig:
            pass
        elif inter.comma_depth == 0:
            _missing_terminal(inter, "Expected ';'")
        else:
            _missing_terminal(inter, "Expected ']'")

    if inter.anon_tok is not None:
        return inter.anon_tok.obj
    else:
        inter.terminal_loc = copy.deepcopy(inter.curr_tok.loc)
        return inter.curr_tok.obj


def _new_name(inter: InterpretContext) -> str:
    if inter.dec.type_ is None:
        _raise_helper(f"Undeclared variable '{inter.next_tok.word}'", inter)
    return inter.next_tok.word


def _equals(inter: InterpretContext) -> None:
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    inter.assignee.set_value(value)
    inter.assignee = None  # type: ignore
    _terminal(inter)


def _declare(inter: InterpretContext) -> None:
    if None in [inter.dec.type_, inter.dec.name]:
        raise NotImplementedError
    body = inter.dotted_body if inter.dotted_body else inter.body
    inter.assignee = body.add_attr(inter.dec)
    inter.dotted_body = None  # type: ignore
    inter.dec.type_ = None  # type: ignore
    inter.dec.name = None  # type: ignore
    inter.dec.listof = False


def _string(inter: InterpretContext) -> str:
    left = inter.next_tok.grammar.value
    data = ""
    while inter.char_feed.current() != left:
        data += inter.char_feed.current()
        inter.char_feed.pop()
    inter.advance_tokens()  # next_tok is now ' "
    inter.advance_tokens()  # next_tok is now ; , ] )
    return data


def _bracket_left(inter: InterpretContext) -> ListHint[Arg]:
    return _arg_list(inter, Grammar.BRACKET_RIGHT)


def _paren_left(inter: InterpretContext) -> Optional[Arg]:
    orig_loc = copy.deepcopy(inter.curr_tok.loc)
    func: Function = inter.curr_tok.obj  #  type: ignore
    args = _arg_list(inter, Grammar.PAREN_RIGHT)
    for param, arg in zip_longest(func.parameters, args):
        param: Declarable
        arg: Arg
        # assert 0
        if arg is None:
            func_name = func.name if func.name else "anonymous func"
            missing_count = len(func.parameters) - len(args)
            _raise_helper(
                f"{func_name} missing {missing_count} required arguments", inter
            )
        elif param.type_ is None:
            raise NotImplementedError
        elif param.type_ == Grammar.PRIMITIVE_ANY:
            pass
        elif isinstance(param.type_, Class):
            if not isinstance(arg, Instance):
                raise NotImplementedError
            elif arg.parent is not param.type_:
                raise NotImplementedError
        elif isinstance(arg, Object):
            value_grammar = prim_to_value(param.type_)
            if value_grammar != arg.grammar:
                raise NotImplementedError
        elif isinstance(arg, str):
            if param.type_ != Grammar.PRIMITIVE_STRING:
                raise NotImplementedError
        elif isinstance(arg, list):  # type: ignore
            if param.listof is None:
                raise NotImplementedError
        else:
            raise CriticalError("Unrecognized type for function argument")

        attr = func.add_attr(param)
        attr.set_value(arg)

    try:
        interpret(func)
    except DitError as err:
        err.add_trace(func.path, orig_loc, func.name)
        raise err
    except ReturnController as ret:
        _check_return_type(inter, ret, func)
        return ret.value
    # finally:
    # func.parameters.clear()

    return None


def _check_return_type(inter: InterpretContext, ret: ReturnController, func: Function):
    if isinstance(ret.value, str) or isinstance(ret.value, String):
        if func.return_ == Grammar.PRIMITIVE_STRING:
            return
        else:
            actual = "String"
    elif isinstance(ret.value, list) or isinstance(ret.value, List):
        raise NotImplementedError
    elif isinstance(ret.value, Instance):
        if ret.value.parent is func.return_:
            return
        else:
            actual = ret.value.parent.name
    else:
        actual = "NotImplemented"

    if isinstance(func.return_, Grammar):
        expected = func.return_.value
    else:
        expected = func.return_.public_type
    mes = f"Expected '{expected}' for return, got '{actual}'"
    err = TypeMismatchError(mes)
    err.set_origin(func.path, ret.orig_loc, inter.char_feed.get_line(ret.orig_loc))


def _return(inter: InterpretContext) -> NoReturn:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if not isinstance(inter.body, Function):
        _raise_helper("'return' outside of function", inter)
    inter.advance_tokens()
    ret = _expression_dispatch(inter)
    if ret is None:
        raise NotImplementedError
    raise ReturnController(ret, orig_loc)


def _throw(inter: InterpretContext) -> None:
    pass


def _trailing_comma(inter: InterpretContext, right: Grammar) -> Optional[NoReturn]:
    if inter.next_tok.grammar not in [Grammar.COMMA, right]:
        _missing_terminal(inter, f"Expected '{right.value}'")

    if inter.next_tok.grammar == Grammar.COMMA:
        inter.advance_tokens()


def _arg_list(inter: InterpretContext, right: Grammar) -> ListHint[Arg]:
    args: ListHint[Arg] = []
    inter.advance_tokens()
    inter.comma_depth += 1
    while True:
        if inter.next_tok.grammar == right:
            inter.comma_depth -= 1
            inter.advance_tokens()
            return args
        arg = _expression_dispatch(inter)
        if arg is None:
            raise NotImplementedError
        args.append(arg)
        _trailing_comma(inter, right)


def _import(inter: InterpretContext) -> Optional[Dit]:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    dit = Dit(name=None, path=None)  # type: ignore

    inter.advance_tokens(False)
    gra = inter.next_tok.grammar
    if gra != Grammar.WORD and gra not in EXPRESSION_STARTERS:
        _raise_helper("Expected a name or filepath string for import", inter)

    if gra == Grammar.WORD:
        # import SomeName from "someFilePath.dit";
        # WET: Identical to section in _class
        if inter.body.find_attr(inter.next_tok.word):
            _raise_helper(f"'{inter.next_tok.word}' has already been declared", inter)
        dit.name = inter.next_tok.word
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
        dit.path = value
    elif isinstance(value, String):
        dit.path = value.string_value
    elif isinstance(value, list):
        _raise_helper("Expected string value, not list", inter)
    elif isinstance(value, Object):  # type: ignore
        _raise_helper(f"Expected string value, not {value.public_type}", inter)
    else:
        raise CriticalError("Unrecognized value for path assignment")

    dit.finalize()
    try:
        interpret(dit)
    except DitError as err:
        err.add_trace(dit.path, orig_loc, "import")
        raise
    anon = _handle_anon(inter, dit, orig_loc)
    if anon:
        return anon  # type: ignore
    else:
        _terminal(inter)


def _class(inter: InterpretContext) -> Optional[Class]:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    class_ = Class(name=None, containing_scope=inter.body)  # type: ignore

    inter.advance_tokens(False)
    if inter.next_tok.grammar not in [Grammar.WORD, Grammar.BRACE_LEFT]:
        _raise_helper("Expected name or body to follow class", inter)

    if inter.next_tok.grammar == Grammar.WORD:
        # WET: Identical to section in _import
        if inter.body.find_attr(inter.next_tok.word):
            _raise_helper(f"'{inter.next_tok.word}' has already been declared", inter)
        class_.name = inter.next_tok.word
        inter.advance_tokens()  # get {{
        if inter.next_tok.grammar != Grammar.BRACE_LEFT:
            _raise_helper("Expected a class body", inter)

    _brace_left(inter, class_)
    class_.finalize()
    try:
        interpret(class_)
    except EndOfFileError as err:
        raise EndOfClassError from err
    return _handle_anon(inter, class_, orig_loc)  # type: ignore


def _func(inter: InterpretContext) -> Optional[Function]:
    # func Ditlang String test(String right, String left) {{}}
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = Function(name=None, containing_scope=inter.body)  # type: ignore
    inter.func_sig = True

    inter.advance_tokens()
    if inter.next_tok.grammar in LANGS:
        # func Python
        func.lang = inter.next_tok.grammar  # type: ignore
    elif inter.next_tok.grammar == Grammar.VALUE_LANG:
        # func JavaCustom
        func.lang = inter.next_tok.obj  # type: ignore
    elif inter.next_tok.grammar in DOTABLES:
        # func commonLangs.Lua
        result = _expression_dispatch(inter)  # type: ignore
        if result.grammar != Grammar.VALUE_LANG:
            func.lang = result  # type: ignore
        else:
            raise NotImplementedError
    elif inter.next_tok.word == "Javascript":
        _raise_helper("Did you mean 'JavaScript'?", inter)
    else:
        _raise_helper("Expected language value", inter)

    inter.advance_tokens()
    if inter.next_tok.grammar in DOTABLES:
        # func Ditlang numLib.Number

        result: Object = _expression_dispatch(inter)  # type: ignore
        if result.grammar == Grammar.VALUE_CLASS:
            func.return_ = result  # type: ignore
        else:
            mes = (
                "Expected class for return type, "
                f"'{result.name}' is of type '{result.public_type}'"
            )
            _raise_helper(mes, inter, inter.terminal_loc)
    elif inter.next_tok.grammar in TYPES:
        # func Ditlang void
        # func Ditlang String
        func.return_ = _token_to_type(inter.next_tok)
        inter.advance_tokens(False)
    else:
        _raise_helper("Expected return type", inter)

    if inter.next_tok.grammar == Grammar.WORD:
        # func Ditlang void someName
        result = inter.body.find_attr(inter.next_tok.word)  # type: ignore
        if result:
            _raise_helper(f"'{result.name}' has already been declared", inter)
        else:
            func.name = inter.next_tok.word
            # Advance only if the name was there
            # If no name, then this is an anonymous function
            inter.advance_tokens()

    if inter.next_tok.grammar != Grammar.PAREN_LEFT:
        # func Ditlang void someName(
        _raise_helper("Expected parameter list", inter)

    inter.advance_tokens()
    while True:
        if inter.next_tok.grammar == Grammar.PAREN_RIGHT:
            inter.advance_tokens()
            break

        if inter.next_tok.grammar in DOTABLES:
            # someName(numLib.Number
            result = _expression_dispatch(inter)  # type: ignore
            if result.grammar == Grammar.VALUE_CLASS:
                param_type = _token_to_type(inter.next_tok)
            else:
                mes = (
                    "Expected class for parameter type, "
                    f"'{result.name}' is of type '{result.public_type}'"
                )
                _raise_helper(mes, inter, inter.terminal_loc)
        elif inter.next_tok.grammar in PRIMITIVES:
            # someName(String
            param_type = _token_to_type(inter.next_tok)
        else:
            _raise_helper("Expected parameter type", inter)

        inter.advance_tokens(False)
        if inter.next_tok.grammar != Grammar.WORD:
            _raise_helper("Expected parameter name", inter)
        else:
            # someName(String someParam
            param_name = inter.next_tok.word
            result = inter.body.find_attr(param_name)  # type: ignore
            if result:
                _raise_helper(f"'{param_name}' has already been declared", inter)
            elif param_name in [p.name for p in func.parameters]:
                _raise_helper(f"'{param_name}' is already a parameter name", inter)
        func.parameters.append(Declarable(param_type, param_name))

        inter.advance_tokens()
        _trailing_comma(inter, Grammar.PAREN_RIGHT)

    if inter.next_tok.grammar != Grammar.BRACE_LEFT:
        _raise_helper("Expected function body", inter)

    _brace_left(inter, func)
    func.finalize()
    inter.func_sig = False
    return _handle_anon(inter, func, orig_loc)  # type: ignore


def _brace_left(inter: InterpretContext, body: Body) -> None:
    depth = 1
    body.start_loc = copy.deepcopy(inter.char_feed.loc)
    while depth > 0:
        cur = inter.char_feed.current() + inter.char_feed.peek()
        if cur == Grammar.BRACE_LEFT.value:
            depth += 1
            inter.advance_tokens()
        elif cur == Grammar.BRACE_RIGHT.value:
            depth -= 1
            body.end_loc = copy.deepcopy(inter.char_feed.loc)
            inter.advance_tokens()
        else:
            inter.char_feed.pop()


def _handle_anon(
    inter: InterpretContext, body: Body, orig_loc: CodeLocation
) -> Optional[Body]:
    if body.name:
        # traditional statement, stop here
        inter.body.attrs.append(body)
        return None
    else:
        # anonymous expression, need to dispatch it
        inter.anon_tok = Token(body.grammar, orig_loc, obj=body)
        return _expression_dispatch(inter)  # type: ignore


def _missing_terminal(inter: InterpretContext, message: str) -> NoReturn:
    tok = inter.curr_tok
    target = tok.loc
    line = inter.char_feed.get_line(target)

    if isinstance(tok.grammar.value, str):
        length = len(tok.grammar.value)  # class, String, =
    elif tok.obj is not None:
        length = len(tok.obj.name)  # Object names
    else:
        length = len(tok.word)  # New Names

    # Shift locaton to end of token
    target.pos += length
    target.col += length

    err = SyntaxError_(message)
    err.set_origin(inter.body.path, target, line)
    raise err


def _trigger_eof_err(inter: InterpretContext) -> NoReturn:
    inter.char_feed.pop()
    raise CriticalError("EOF reached, but failed to trigger")


def _not_implemented(inter: InterpretContext) -> NoReturn:
    raise NotImplementedError


def _illegal_statement(inter: InterpretContext) -> NoReturn:
    _raise_helper("Illegal start of statement", inter)


def _illegal_expression(inter: InterpretContext) -> NoReturn:
    _raise_helper("Illegal start of expression", inter)


# disable black formatting temporarily
# fmt: off
STATEMENT_DISPATCH = {
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
    Grammar.FUNC:                   _func,
    Grammar.DITLANG:                _illegal_statement,
    Grammar.PYTHON:                 _illegal_statement,
    Grammar.JAVASCRIPT:             _illegal_statement,
    Grammar.VOID:                   _illegal_statement,
    Grammar.LISTOF:                 _listof,
    Grammar.IMPORT:                 _import,
    Grammar.FROM:                   _illegal_statement,
    Grammar.THROW:                  _throw,
    Grammar.RETURN:                 _return,
    Grammar.THIS:                   _not_implemented,
    Grammar.PRIMITIVE_ANY:          _primitive,
    Grammar.PRIMITIVE_STRING:       _primitive,
    Grammar.PRIMITIVE_CLASS:        _primitive,
    Grammar.PRIMITIVE_INSTANCE:     _primitive,
    Grammar.PRIMITIVE_FUNC:         _primitive,
    Grammar.PRIMITIVE_DIT:          _primitive,
    Grammar.WORD:                   _illegal_statement,
    Grammar.NEW_NAME:               _new_name,
    Grammar.VALUE_ANY:              _value_any,
    Grammar.VALUE_STRING:           _value_string,
    Grammar.VALUE_LIST:             _value_list,
    Grammar.VALUE_CLASS:            _value_class,
    Grammar.VALUE_INSTANCE:         _value_instance,
    Grammar.VALUE_FUNC:             _value_function,
    Grammar.VALUE_DIT:              _value_dit,
    Grammar.EOF:                    _trigger_eof_err,
}


EXPRESSION_DISPATCH = {
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
    Grammar.FUNC:                   _func,
    Grammar.DITLANG:                _illegal_expression,
    Grammar.PYTHON:                 _illegal_expression,
    Grammar.JAVASCRIPT:             _illegal_expression,
    Grammar.VOID:                   _illegal_expression,
    Grammar.LISTOF:                 _illegal_expression,
    Grammar.IMPORT:                 _import,
    Grammar.FROM:                   _illegal_expression,
    Grammar.THROW:                  _illegal_expression,
    Grammar.RETURN:                 _illegal_expression,
    Grammar.THIS:                   _not_implemented,
    Grammar.PRIMITIVE_ANY:          _illegal_expression,
    Grammar.PRIMITIVE_STRING:       _illegal_expression,
    Grammar.PRIMITIVE_CLASS:        _illegal_expression,
    Grammar.PRIMITIVE_INSTANCE:     _illegal_expression,
    Grammar.PRIMITIVE_FUNC:         _illegal_expression,
    Grammar.PRIMITIVE_DIT:          _illegal_expression,
    Grammar.WORD:                   _illegal_expression,
    Grammar.NEW_NAME:               _new_name,
    Grammar.VALUE_ANY:              _not_implemented,
    Grammar.VALUE_STRING:           _value_string,
    Grammar.VALUE_LIST:             _value_list,
    Grammar.VALUE_CLASS:            _value_class,
    Grammar.VALUE_INSTANCE:         _value_instance,
    Grammar.VALUE_FUNC:             _value_function,
    Grammar.VALUE_DIT:              _value_dit,
    Grammar.EOF:                    _trigger_eof_err,
}
# fmt: on
