import copy
from itertools import zip_longest
from typing import List, NoReturn, Optional, Union

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
    d_Grammar,
    prim_to_value,
    value_to_prim,
)
from dit_cli.interpret_context import InterpretContext
from dit_cli.oop import (
    ArgumentLocation,
    Declarable,
    ReturnController,
    Token,
    arg_to_prim,
    d_Arg,
    d_Body,
    d_Class,
    d_Dit,
    d_Function,
    d_Instance,
    d_List,
    d_Null,
    d_String,
    d_Thing,
    d_Type,
)


def interpret(body: d_Body) -> None:
    if isinstance(body, d_Function) and body.is_built_in:
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
            if inter.next_tok.grammar == d_Grammar.EOF:
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


def _expression_dispatch(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.anon_tok:
        func = EXPRESSION_DISPATCH[inter.anon_tok.grammar]
    elif inter.call_tok:
        func = EXPRESSION_DISPATCH[inter.call_tok.grammar]  # type: ignore
    else:
        func = EXPRESSION_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _listof(inter: InterpretContext) -> None:
    # listOf d_String values;
    inter.advance_tokens()
    inter.dec.listof = True
    if inter.next_tok.grammar in PRIMITIVES:
        _primitive(inter)
    elif inter.next_tok.grammar in DOTABLES:
        type_ = _expression_dispatch(inter)
        if not isinstance(type_, d_Class):
            raise NotImplementedError
        else:
            inter.dec.type_ = type_
    else:
        _raise_helper("Expected type for listOf declaration", inter)


def _primitive(inter: InterpretContext) -> None:
    # String value;
    inter.advance_tokens()
    _type(inter)


def _value_thing(inter: InterpretContext) -> Optional[d_Arg]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_string(inter: InterpretContext) -> Optional[d_Arg]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_list(inter: InterpretContext) -> Optional[d_Arg]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_class(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.func_sig:
        inter.advance_tokens(False)
        if inter.next_tok.grammar == d_Grammar.DOT:
            return _dotable(inter)
        else:
            return inter.curr_tok.thing

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


def _token_to_type(token: Token) -> d_Type:
    if token.thing:
        return token.thing  # type: ignore
    else:
        return token.grammar


def _value_instance(inter: InterpretContext) -> Optional[d_Arg]:
    inter.advance_tokens()
    return _dotable(inter)


def _value_function(inter: InterpretContext) -> Optional[d_Arg]:
    inter.advance_tokens()
    return _parenable(inter)


def _value_dit(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.anon_tok is None:
        inter.advance_tokens()
    return _dotable(inter)


def _null(inter: InterpretContext) -> d_Null:
    inter.advance_tokens()
    return d_Null()


def _parenable(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.next_tok.grammar == d_Grammar.PAREN_LEFT:
        return _paren_left(inter)
    else:
        return _dotable(inter)


def _dotable(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.next_tok.grammar == d_Grammar.DOT:
        # ... ThisDit.Ele ...
        dot = _dot(inter)
        inter.next_tok = dot
        inter.anon_tok = None
        inter.call_tok = None
        return _expression_dispatch(inter)
    else:
        return _equalable(inter)


def _dot(inter: InterpretContext) -> Token:
    inter.advance_tokens(False)  # We want to manage the next word ourselves
    if inter.next_tok.grammar != d_Grammar.WORD:
        _raise_helper(f"'{inter.next_tok.grammar}' is not dotable", inter)
    if inter.anon_tok:
        previous: d_Body = inter.anon_tok.thing  # type: ignore
    elif inter.call_tok:
        previous: d_Body = inter.call_tok.thing  # type: ignore
    else:
        previous: d_Body = inter.prev_tok.thing  # type: ignore
    result = inter.body.find_attr(inter.next_tok.word, previous=previous)
    if result:
        # The dot had a known variable, which we just need to return
        return Token(result.grammar, copy.deepcopy(inter.next_tok.loc), thing=result)
    else:
        # The name was not found in the dotted body, so its a new name.
        # This means we are declaring a new var in the dotted body.
        inter.next_tok.grammar = d_Grammar.NEW_NAME
        inter.dotted_body = previous  # Save for assignment
        return inter.next_tok


def _equalable(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.dec.type_:
        # type_ should have been cleared by a _declare call
        _raise_helper(f"'{inter.curr_tok.thing.name}' has already been declared", inter)
    elif inter.next_tok.grammar == d_Grammar.EQUALS:
        if inter.anon_tok is not None or inter.call_tok is not None:
            # prevent assignment to anonymous tokens.
            raise NotImplementedError
        if inter.assignee is None:
            inter.assignee = inter.curr_tok.thing
        _equals(inter)
    else:
        return _terminal(inter)


def _terminal(inter: InterpretContext) -> d_Arg:
    if inter.next_tok.grammar not in [
        d_Grammar.SEMI,
        d_Grammar.COMMA,
        d_Grammar.BRACKET_RIGHT,
        d_Grammar.PAREN_RIGHT,
    ]:
        if inter.func_sig:
            pass
        elif inter.comma_depth == 0:
            _missing_terminal(inter, "Expected ';'")
        else:
            _missing_terminal(inter, "Expected ']'")

    if inter.anon_tok is not None:
        ret = inter.anon_tok.thing
        inter.anon_tok = None
        return ret
    elif inter.call_tok is not None:
        if isinstance(inter.call_tok, d_Null):
            return inter.call_tok
        else:
            ret = inter.call_tok.thing
            inter.call_tok = None
            return ret
    else:
        inter.terminal_loc = copy.deepcopy(inter.curr_tok.loc)
        return inter.curr_tok.thing


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


def _bracket_left(inter: InterpretContext) -> List[d_Arg]:
    return [item.arg for item in _arg_list(inter, d_Grammar.BRACKET_RIGHT)]  # type: ignore


def _paren_left(inter: InterpretContext) -> Optional[d_Arg]:
    if inter.anon_tok is not None:
        func: d_Function = inter.anon_tok.thing  #  type: ignore
    elif inter.call_tok is not None:
        func: d_Function = inter.call_tok.thing  #  type: ignore
    else:
        func: d_Function = inter.curr_tok.thing  #  type: ignore
    func.orig_loc = copy.deepcopy(inter.curr_tok.loc)
    arg_locs = _arg_list(inter, d_Grammar.PAREN_RIGHT)
    func_name = f"{func.name}()" if func.name is not None else "<anonymous function>()"
    miss = abs(len(func.parameters) - len(arg_locs))

    for param, arg_loc in zip_longest(func.parameters, arg_locs):
        param: Declarable
        arg_loc: ArgumentLocation
        if arg_loc is None:
            _raise_helper(f"{func_name} missing {miss} required arguments", inter)
        elif param is None:
            # TODO: implement proper k-args functionality
            _raise_helper(f"{func_name} given {miss} too many arguments", inter)
        elif param.type_ == d_Grammar.PRIMITIVE_THING:
            pass  # No need to check this
        elif param.type_ in PRIMITIVES:
            prim = arg_to_prim(arg_loc.arg)
            if param.type_ != prim:
                _raise_helper(
                    f"{func_name} expected '{prim.value}'", inter, arg_loc.loc
                )
        elif isinstance(param.type_, d_Class):
            if not isinstance(arg_loc.arg, d_Instance):
                raise NotImplementedError
            elif arg_loc.arg.parent is not param.type_:
                raise NotImplementedError
        else:
            raise CriticalError("Unrecognized type for function argument")
        attr = func.add_attr(param)
        attr.set_value(arg_loc.arg)

    try:
        interpret(func)
    except DitError as err:
        err.add_trace(func.path, func.orig_loc, func.name)
        raise err
    except ReturnController as ret:
        inter.call_tok = _get_return_thing(inter, ret, func)
    else:
        if func.return_ is not None and func.return_ != d_Grammar.VOID:
            _raise_helper(f"{func_name} expected a return", inter, func.orig_loc)
        else:
            # func ended without 'return' keyword
            inter.call_tok = d_Null()

    func.attrs.clear()
    if isinstance(inter.call_tok, d_Null):
        return _terminal(inter)
    else:
        return _parenable(inter)


def _return(inter: InterpretContext) -> NoReturn:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if not isinstance(inter.body, d_Function):
        _raise_helper("'return' outside of function", inter)
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    return_thing = _get_return_thing(inter, value, inter.body)
    raise ReturnController(return_thing, orig_loc)


def _get_return_thing(
    inter: InterpretContext, value: d_Arg, func: d_Function
) -> Union[Token, d_Null]:
    if isinstance(value, d_Null):
        return value
    elif isinstance(value, str):
        if func.return_ == d_Grammar.VALUE_STRING:
            return Token(func.return_, orig_loc, thing=d_String(None))  # type: ignore
        else:
            _fail_return_type(inter, value, func, "String")
    elif isinstance(value, list) or isinstance(value, d_List):
        if func.return_list:
            if isinstance(value, list):
                thing = d_List(func.return_, None)  # type: ignore
                thing.set_value(value)
                return Token(d_Grammar.VALUE_LIST, func.orig_loc, thing=thing)
            else:
                if func.return_ == value.contained_type:
                    return Token(d_Grammar.VALUE_LIST, func.orig_loc, thing=value)
                else:
                    if isinstance(func.return_, d_Class):
                        actual = f"listOf {func.return_.name}"
                    else:
                        actual = f"listOf {func.return_.value}"
                    _fail_return_type(inter, value, func, actual)
        else:
            _fail_return_type(inter, value, func, "List")
    elif isinstance(func.return_, d_Class):
        raise NotImplementedError
    elif isinstance(value, d_Thing):  # type: ignore
        if func.return_ == value.grammar:
            return Token(func.return_, func.orig_loc, thing=value)
        else:
            _fail_return_type(inter, value, func, value.public_type)
    else:
        raise CriticalError("Unrecognized return value")


def _fail_return_type(
    inter: InterpretContext,
    value: d_Arg,
    func: d_Function,
    actual_return: str,
) -> NoReturn:
    if isinstance(func.return_, d_Grammar):
        expected_return = value_to_prim(func.return_).value
    elif isinstance(func.return_, d_Class):  # type: ignore
        if func.return_.name is None:
            expected_return = "<anonymous class>"
        else:
            expected_return = func.return_.name
    else:
        raise CriticalError("Unrecognized return type")
    mes = f"Expected '{expected_return}' for return, got '{actual_return}'"
    err = TypeMismatchError(mes)
    err.set_origin(func.path, func.orig_loc, inter.char_feed.get_line(func.orig_loc))
    raise err


def _throw(inter: InterpretContext) -> None:
    pass


def _trailing_comma(inter: InterpretContext, right: d_Grammar) -> Optional[NoReturn]:
    if inter.next_tok.grammar not in [d_Grammar.COMMA, right]:
        _missing_terminal(inter, f"Expected '{right.value}'")

    if inter.next_tok.grammar == d_Grammar.COMMA:
        inter.advance_tokens()


def _arg_list(inter: InterpretContext, right: d_Grammar) -> List[ArgumentLocation]:
    args: List[ArgumentLocation] = []
    inter.advance_tokens()
    inter.comma_depth += 1
    while True:
        if inter.next_tok.grammar == right:
            inter.comma_depth -= 1
            inter.advance_tokens()
            return args
        loc = copy.deepcopy(inter.next_tok.loc)
        arg = _expression_dispatch(inter)
        if arg is None:
            raise NotImplementedError
        args.append(ArgumentLocation(loc, arg))
        _trailing_comma(inter, right)


def _import(inter: InterpretContext) -> Optional[d_Dit]:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    dit = d_Dit(name=None, path=None)  # type: ignore

    inter.advance_tokens(False)
    gra = inter.next_tok.grammar
    if gra != d_Grammar.WORD and gra not in EXPRESSION_STARTERS:
        _raise_helper("Expected a name or filepath string for import", inter)

    if gra == d_Grammar.WORD:
        # import SomeName from "someFilePath.dit";
        # WET: Identical to section in _class
        if inter.body.find_attr(inter.next_tok.word):
            _raise_helper(f"'{inter.next_tok.word}' has already been declared", inter)
        dit.name = inter.next_tok.word
        inter.advance_tokens()
        if inter.next_tok.grammar != d_Grammar.FROM:
            _raise_helper("Expected 'from'", inter)
        inter.advance_tokens()

    if inter.next_tok.grammar not in EXPRESSION_STARTERS:
        _raise_helper("Expected a filepath string for import", inter)

    string_loc = copy.deepcopy(inter.next_tok.loc)
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    if isinstance(value, str):
        dit.path = value
    elif isinstance(value, d_String):
        if isinstance(value.string_value, d_Null):
            _raise_helper("Cannot import from null", inter, string_loc)
        else:
            dit.path = value.string_value
    elif isinstance(value, list):
        _raise_helper("Expected string value, not list", inter)
    elif isinstance(value, d_Thing):  # type: ignore
        _raise_helper(f"Expected string value, not {value.public_type}", inter)
    else:
        raise CriticalError("Unrecognized value for path assignment")

    dit.finalize()
    try:
        interpret(dit)
    except DitError as err:
        err.add_trace(dit.path, orig_loc, "import")
        raise

    # handled slightly differently from other bodies.
    # import always ends with a semicolon, even with a name.
    anon = _handle_anon(inter, dit, orig_loc)
    if anon:
        return anon  # type: ignore
    else:
        # Thus, this explicit call to _terminal.
        _terminal(inter)


def _class(inter: InterpretContext) -> Optional[d_Class]:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    class_ = d_Class(name=None, containing_scope=inter.body)  # type: ignore

    inter.advance_tokens(False)
    if inter.next_tok.grammar not in [d_Grammar.WORD, d_Grammar.BRACE_LEFT]:
        _raise_helper("Expected name or body to follow class", inter)

    if inter.next_tok.grammar == d_Grammar.WORD:
        # WET: Identical to section in _import
        if inter.body.find_attr(inter.next_tok.word):
            _raise_helper(f"'{inter.next_tok.word}' has already been declared", inter)
        class_.name = inter.next_tok.word
        inter.advance_tokens()  # get {{
        if inter.next_tok.grammar != d_Grammar.BRACE_LEFT:
            _raise_helper("Expected a class body", inter)

    _brace_left(inter, class_)
    class_.finalize()
    try:
        interpret(class_)
    except EndOfFileError as err:
        raise EndOfClassError from err
    return _handle_anon(inter, class_, orig_loc)  # type: ignore


def _func(inter: InterpretContext) -> Optional[d_Function]:
    # func Ditlang d_String test(d_String right, d_String left) {{}}
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = d_Function(name=None, containing_scope=inter.body)  # type: ignore
    inter.func_sig = True

    inter.advance_tokens()
    if inter.next_tok.grammar in LANGS:
        # func Python
        func.lang = inter.next_tok.grammar  # type: ignore
    elif inter.next_tok.grammar == d_Grammar.VALUE_LANG:
        # func JavaCustom
        func.lang = inter.next_tok.thing  # type: ignore
    elif inter.next_tok.grammar in DOTABLES:
        # func commonLangs.5Lua
        result = _expression_dispatch(inter)  # type: ignore
        if result.grammar != d_Grammar.VALUE_LANG:
            func.lang = result  # type: ignore
        else:
            raise NotImplementedError
    elif inter.next_tok.word == "Javascript":
        _raise_helper("Did you mean 'JavaScript'?", inter)
    else:
        _raise_helper("Expected language value", inter)

    inter.advance_tokens()
    if inter.next_tok.grammar == d_Grammar.LISTOF:
        func.return_list = True
        inter.advance_tokens()

    if inter.next_tok.grammar in DOTABLES:
        # func Ditlang numLib.Number

        result: d_Thing = _expression_dispatch(inter)  # type: ignore
        if result.grammar == d_Grammar.VALUE_CLASS:
            func.return_ = result  # type: ignore
        else:
            mes = (
                "Expected class for return type, "
                f"'{result.name}' is of type '{result.public_type}'"
            )
            _raise_helper(mes, inter, inter.terminal_loc)
    elif inter.next_tok.grammar == d_Grammar.VOID:
        # func Ditlang void
        if func.return_list:
            _raise_helper("Cannot have listOf void", inter)
        func.return_ = d_Grammar.VOID
        inter.advance_tokens(False)
    elif inter.next_tok.grammar in TYPES:
        # func Ditlang d_String
        func.return_ = prim_to_value(_token_to_type(inter.next_tok))  # type: ignore
        inter.advance_tokens(False)
    else:
        _raise_helper("Expected return type", inter)

    if inter.next_tok.grammar == d_Grammar.WORD:
        # func Ditlang void someName
        result = inter.body.find_attr(inter.next_tok.word)  # type: ignore
        if result:
            _raise_helper(f"'{result.name}' has already been declared", inter)
        else:
            func.name = inter.next_tok.word
            # Advance only if the name was there
            # If no name, then this is an anonymous function
            inter.advance_tokens()

    if inter.next_tok.grammar != d_Grammar.PAREN_LEFT:
        # func Ditlang void someName(
        _raise_helper("Expected parameter list", inter)

    inter.advance_tokens()
    while True:
        if inter.next_tok.grammar == d_Grammar.PAREN_RIGHT:
            inter.advance_tokens()
            break

        if inter.next_tok.grammar in DOTABLES:
            # someName(numLib.Number
            result = _expression_dispatch(inter)  # type: ignore
            if result.grammar == d_Grammar.VALUE_CLASS:
                param_type = _token_to_type(inter.next_tok)
            else:
                mes = (
                    "Expected class for parameter type, "
                    f"'{result.name}' is of type '{result.public_type}'"
                )
                _raise_helper(mes, inter, inter.terminal_loc)
        elif inter.next_tok.grammar in PRIMITIVES:
            # someName(d_String
            param_type = _token_to_type(inter.next_tok)
        else:
            _raise_helper("Expected parameter type", inter)

        inter.advance_tokens(False)
        if inter.next_tok.grammar != d_Grammar.WORD:
            _raise_helper("Expected parameter name", inter)
        else:
            # someName(d_String someParam
            param_name = inter.next_tok.word
            result = inter.body.find_attr(param_name)  # type: ignore
            if result:
                _raise_helper(f"'{param_name}' has already been declared", inter)
            elif param_name in [p.name for p in func.parameters]:
                _raise_helper(f"'{param_name}' is already a parameter name", inter)
        func.parameters.append(Declarable(param_type, param_name))

        inter.advance_tokens()
        _trailing_comma(inter, d_Grammar.PAREN_RIGHT)

    if inter.next_tok.grammar != d_Grammar.BRACE_LEFT:
        _raise_helper("Expected function body", inter)

    _brace_left(inter, func)
    func.finalize()
    inter.func_sig = False
    return _handle_anon(inter, func, orig_loc)  # type: ignore


def _brace_left(inter: InterpretContext, body: d_Body) -> None:
    depth = 1
    body.start_loc = copy.deepcopy(inter.char_feed.loc)
    while depth > 0:
        cur = inter.char_feed.current() + inter.char_feed.peek()
        if cur == d_Grammar.BRACE_LEFT.value:
            depth += 1
            inter.advance_tokens()
        elif cur == d_Grammar.BRACE_RIGHT.value:
            depth -= 1
            body.end_loc = copy.deepcopy(inter.char_feed.loc)
            inter.advance_tokens()
        else:
            inter.char_feed.pop()


def _handle_anon(
    inter: InterpretContext, body: d_Body, orig_loc: CodeLocation
) -> Optional[d_Body]:
    if body.name:
        # traditional statement, stop here
        inter.body.attrs.append(body)
        return None
    else:
        # anonymous expression, need to dispatch it
        inter.anon_tok = Token(body.grammar, orig_loc, thing=body)
        return _expression_dispatch(inter)  # type: ignore


def _missing_terminal(inter: InterpretContext, message: str) -> NoReturn:
    tok = inter.curr_tok
    target = tok.loc
    line = inter.char_feed.get_line(target)

    if isinstance(tok.grammar.value, str):
        length = len(tok.grammar.value)  # class, String, =
    elif tok.thing is not None:
        length = len(tok.thing.name)  # Object names
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
    d_Grammar.QUOTE_DOUBLE:           _illegal_statement,
    d_Grammar.QUOTE_SINGLE:           _illegal_statement,
    d_Grammar.DOT:                    _illegal_statement,
    d_Grammar.EQUALS:                 _illegal_statement,
    d_Grammar.PLUS:                   _not_implemented,
    d_Grammar.COMMA:                  _illegal_statement,
    d_Grammar.SEMI:                   _illegal_statement,
    d_Grammar.PAREN_LEFT:             _illegal_statement,
    d_Grammar.PAREN_RIGHT:            _illegal_statement,
    d_Grammar.BRACKET_LEFT:           _illegal_statement,
    d_Grammar.BRACKET_RIGHT:          _illegal_statement,
    d_Grammar.BACKSLASH:              _illegal_statement,
    d_Grammar.COMMENT_START:          _illegal_statement,
    d_Grammar.BRACE_LEFT:             _illegal_statement,
    d_Grammar.BRACE_RIGHT:            _illegal_statement,
    d_Grammar.TRIANGLE_LEFT:          _not_implemented,
    d_Grammar.TRIANGLE_RIGHT:         _not_implemented,
    d_Grammar.CIRCLE_LEFT:            _not_implemented,
    d_Grammar.CIRCLE_RIGHT:           _not_implemented,
    d_Grammar.CLASS:                  _class,
    d_Grammar.FUNC:                   _func,
    d_Grammar.DITLANG:                _illegal_statement,
    d_Grammar.PYTHON:                 _illegal_statement,
    d_Grammar.JAVASCRIPT:             _illegal_statement,
    d_Grammar.VOID:                   _illegal_statement,
    d_Grammar.LISTOF:                 _listof,
    d_Grammar.IMPORT:                 _import,
    d_Grammar.FROM:                   _illegal_statement,
    d_Grammar.THROW:                  _throw,
    d_Grammar.RETURN:                 _return,
    d_Grammar.THIS:                   _not_implemented,
    d_Grammar.NULL:                   _illegal_statement,
    d_Grammar.PRIMITIVE_THING:        _primitive,
    d_Grammar.PRIMITIVE_STRING:       _primitive,
    d_Grammar.PRIMITIVE_CLASS:        _primitive,
    d_Grammar.PRIMITIVE_INSTANCE:     _primitive,
    d_Grammar.PRIMITIVE_FUNC:         _primitive,
    d_Grammar.PRIMITIVE_DIT:          _primitive,
    d_Grammar.WORD:                   _illegal_statement,
    d_Grammar.NEW_NAME:               _new_name,
    d_Grammar.VALUE_THING:            _value_thing,
    d_Grammar.VALUE_STRING:           _value_string,
    d_Grammar.VALUE_LIST:             _value_list,
    d_Grammar.VALUE_CLASS:            _value_class,
    d_Grammar.VALUE_INSTANCE:         _value_instance,
    d_Grammar.VALUE_FUNC:             _value_function,
    d_Grammar.VALUE_DIT:              _value_dit,
    d_Grammar.EOF:                    _trigger_eof_err,
}


EXPRESSION_DISPATCH = {
    d_Grammar.QUOTE_DOUBLE:           _string,
    d_Grammar.QUOTE_SINGLE:           _string,
    d_Grammar.DOT:                    _illegal_expression,
    d_Grammar.EQUALS:                 _illegal_expression,
    d_Grammar.PLUS:                   _not_implemented,
    d_Grammar.COMMA:                  _illegal_expression,
    d_Grammar.SEMI:                   _illegal_expression,
    d_Grammar.PAREN_LEFT:             _illegal_expression,
    d_Grammar.PAREN_RIGHT:            _illegal_expression,
    d_Grammar.BRACKET_LEFT:           _bracket_left,
    d_Grammar.BRACKET_RIGHT:          _illegal_expression,
    d_Grammar.BACKSLASH:              _illegal_expression,
    d_Grammar.COMMENT_START:          _illegal_expression,
    d_Grammar.BRACE_LEFT:             _illegal_expression,
    d_Grammar.BRACE_RIGHT:            _illegal_expression,
    d_Grammar.TRIANGLE_LEFT:          _not_implemented,
    d_Grammar.TRIANGLE_RIGHT:         _not_implemented,
    d_Grammar.CIRCLE_LEFT:            _not_implemented,
    d_Grammar.CIRCLE_RIGHT:           _not_implemented,
    d_Grammar.CLASS:                  _class,
    d_Grammar.FUNC:                   _func,
    d_Grammar.DITLANG:                _illegal_expression,
    d_Grammar.PYTHON:                 _illegal_expression,
    d_Grammar.JAVASCRIPT:             _illegal_expression,
    d_Grammar.VOID:                   _illegal_expression,
    d_Grammar.LISTOF:                 _illegal_expression,
    d_Grammar.IMPORT:                 _import,
    d_Grammar.FROM:                   _illegal_expression,
    d_Grammar.THROW:                  _illegal_expression,
    d_Grammar.RETURN:                 _illegal_expression,
    d_Grammar.THIS:                   _not_implemented,
    d_Grammar.NULL:                   _null,
    d_Grammar.PRIMITIVE_THING:        _illegal_expression,
    d_Grammar.PRIMITIVE_STRING:       _illegal_expression,
    d_Grammar.PRIMITIVE_CLASS:        _illegal_expression,
    d_Grammar.PRIMITIVE_INSTANCE:     _illegal_expression,
    d_Grammar.PRIMITIVE_FUNC:         _illegal_expression,
    d_Grammar.PRIMITIVE_DIT:          _illegal_expression,
    d_Grammar.WORD:                   _illegal_expression,
    d_Grammar.NEW_NAME:               _new_name,
    d_Grammar.VALUE_THING:            _value_thing,
    d_Grammar.VALUE_STRING:           _value_string,
    d_Grammar.VALUE_LIST:             _value_list,
    d_Grammar.VALUE_CLASS:            _value_class,
    d_Grammar.VALUE_INSTANCE:         _value_instance,
    d_Grammar.VALUE_FUNC:             _value_function,
    d_Grammar.VALUE_DIT:              _value_dit,
    d_Grammar.EOF:                    _trigger_eof_err,
}
# fmt: on
