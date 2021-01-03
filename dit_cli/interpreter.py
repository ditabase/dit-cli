import copy
from itertools import zip_longest
from typing import List, NoReturn, Optional

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
    d_Body,
    d_Class,
    d_Container,
    d_Dit,
    d_Function,
    d_Instance,
    d_Language,
    d_List,
    d_String,
    d_Thing,
    d_Type,
)

MAKE = "-make-"
THIS = "this"


def interpret(body: d_Body) -> None:
    """Read text from a body and interpret it as ditlang code.
    Creates a new InterpretContext and executes statements on tokens,
    one after another, until EOF.

    Used recursively. Classes, functions, and imported dits are all interpreted
    recursively as new bodies with new InterpretContexts.
    Classes and dits are only interpreted once. Functions are re-interpreted
    every time they are called."""
    if isinstance(body, d_Function) and body.is_built_in:
        # WIP, used for internal 'str()' implementation
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
                inter.named_statement = False
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
    """Execute the interpretation function that goes with the next_tok.
    Uses the large grammer -> function dictionary at the end of this file.
    Every grammer is paired with one function."""
    func = STATEMENT_DISPATCH[inter.next_tok.grammar]
    func(inter)


def _expression_dispatch(inter: InterpretContext) -> Optional[d_Thing]:
    """Interpret the next expression and return a value if applicable.
    Also processes anon_tok, which results from anonymous classes, imports and functions
    Also processes call_tok, which results from all function calls."""
    if inter.anon_tok:
        func = EXPRESSION_DISPATCH[inter.anon_tok.grammar]
    elif inter.call_tok:
        func = EXPRESSION_DISPATCH[inter.call_tok.grammar]
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


def _value_thing(inter: InterpretContext) -> Optional[d_Thing]:
    # Thing test;
    # test = 'cat';
    # or, in an expression...
    # Thing test = 'cat';
    # someFunc(test);
    # These code examples are generally applicable to most _value_X functions
    inter.advance_tokens()
    return _equalable(inter)


def _value_string(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_list(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _equalable(inter)


def _value_class(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.declaring_func is not None:
        # func Ditlang someClass...
        # This class is being used as a type in a function signature
        inter.advance_tokens(False)
        if inter.next_tok.grammar == d_Grammar.DOT:
            return _dotable(inter)
        else:
            return inter.curr_tok.thing

    inter.advance_tokens(True)
    if inter.next_tok.grammar in VALUE_CLASS_ABLES:
        # someClass = someOtherClass;
        # someClass anInstance = someClass();
        # This class is being dotted, equaled, parened, etc.
        return _parenable(inter)
    elif inter.anon_tok:
        # class {{}} someInstance = ?... this makes no sense.
        # This prevents using an anonymous class as a type
        # Triggering terminal will call missing ';'
        _terminal(inter)
    else:
        # someClass someInstance...
        # This class is being used as var type
        _type(inter)


def _type(inter: InterpretContext) -> None:
    # String test;
    # someClass test;
    # This function is reused by _primitive and _value_class
    inter.dec.type_ = _token_to_type(inter.curr_tok)
    if inter.next_tok.grammar in NAMEABLES:
        _expression_dispatch(inter)
    else:
        _raise_helper("Expected a new name to follow type", inter)
    inter.advance_tokens()
    _equalable(inter)


def _token_to_type(token: Token) -> d_Type:
    if token.thing:
        return token.thing  # type: ignore
    else:
        return token.grammar


def _value_instance(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _dotable(inter)


def _value_function(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _parenable(inter)


def _value_dit(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.anon_tok is None:
        inter.advance_tokens()
    return _dotable(inter)


def _null(inter: InterpretContext) -> d_Thing:
    # someThing = null;
    inter.advance_tokens()
    return d_Thing.get_null_thing()


def _parenable(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.next_tok.grammar == d_Grammar.PAREN_LEFT:
        # someFunc(...
        # someClass(...
        return _paren_left(inter)
    else:
        return _dotable(inter)


def _dotable(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.next_tok.grammar == d_Grammar.DOT:
        # ... someBody.Ele ...
        dot = _dot(inter)
        inter.next_tok = dot
        inter.anon_tok = None
        inter.call_tok = None
        return _expression_dispatch(inter)
    else:
        return _equalable(inter)


def _dot(inter: InterpretContext) -> Token:
    inter.advance_tokens(False)  # We want to manage the next word ourselves
    target: d_Container = None  # type: ignore
    if inter.next_tok.grammar != d_Grammar.WORD:
        _raise_helper(f"'{inter.next_tok.grammar}' is not dotable", inter)
    if inter.anon_tok:
        target = inter.anon_tok.thing  # type: ignore
    elif inter.call_tok:
        target = inter.call_tok.thing  # type: ignore
    else:
        target = inter.prev_tok.thing  # type: ignore
    result = target.find_attr(inter.next_tok.word)
    if result:
        # The dot had a known variable, which we just need to return
        if isinstance(target, d_Instance):
            inter.dotted_inst = target
        return Token(result.grammar, copy.deepcopy(inter.next_tok.loc), thing=result)
    else:
        # The name was not found in the dotted body, so its a new name.
        # This means we are declaring a new var in the dotted body.
        inter.next_tok.grammar = d_Grammar.NEW_NAME
        inter.dotted_body = target  # Save for assignment
        return inter.next_tok


def _equalable(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.dec.type_ is not None and inter.dec.name is None:
        # _new_name should have been found, not an existing variable.
        _raise_helper(f"'{inter.curr_tok.thing.name}' has already been declared", inter)
    if inter.next_tok.grammar == d_Grammar.EQUALS:
        inter.equaling = True
        _equals(inter)
        inter.equaling = False
        inter.dec.reset()
    elif inter.dec.type_ is not None and not inter.equaling:
        # create variable without assignment
        _add_attr_wrap(inter)
        inter.dec.reset()

    return _terminal(inter)


def _equals(inter: InterpretContext) -> None:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if inter.anon_tok is not None or inter.call_tok is not None:
        # prevent assignment to anonymous tokens.
        raise NotImplementedError
    if inter.dec.type_ is None:
        assignee = inter.curr_tok.thing
    else:
        assignee = None
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if value is None:
        if inter.named_statement:
            _raise_helper(
                "A named declaration cannot be used for assignment", inter, orig_loc
            )
        else:
            raise CriticalError("No value for _expression_dispatch in _equals")
    if assignee is not None:
        assignee.set_value(value)
    else:
        _add_attr_wrap(inter, value=value)


def _add_attr_wrap(inter: InterpretContext, value: Optional[d_Thing] = None):
    if inter.dotted_body is not None:
        inter.dotted_body.add_attr(inter.dec, value=value)
        inter.dotted_body = None  # type: ignore
    else:
        inter.body.add_attr(inter.dec, value=value)


def _terminal(inter: InterpretContext) -> d_Thing:
    # someValue;
    # someListArg,
    # someListArg]
    # someFuncArg)
    if inter.next_tok.grammar not in [
        d_Grammar.SEMI,
        d_Grammar.COMMA,
        d_Grammar.BRACKET_RIGHT,
        d_Grammar.PAREN_RIGHT,
    ]:
        if inter.declaring_func is not None:
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
        ret = inter.call_tok.thing
        inter.call_tok = None
        return ret
    else:
        inter.terminal_loc = copy.deepcopy(inter.curr_tok.loc)
        return inter.curr_tok.thing


def _new_name(inter: InterpretContext) -> None:
    if inter.dec.type_ is None:
        _raise_helper(f"Undeclared variable '{inter.next_tok.word}'", inter)
    inter.dec.name = inter.next_tok.word


def _string(inter: InterpretContext) -> d_String:
    left = inter.next_tok.grammar.value
    data = ""
    while inter.char_feed.current() != left:
        data += inter.char_feed.current()
        inter.char_feed.pop()
    inter.advance_tokens()  # next_tok is now ' "
    inter.advance_tokens()  # next_tok is now ; , ] )
    thing = d_String()
    thing.string_value = data
    thing.is_null = False
    return thing


def _bracket_left(inter: InterpretContext) -> d_List:
    list_ = d_List()
    list_.list_value = [
        item.thing for item in _arg_list(inter, d_Grammar.BRACKET_RIGHT)
    ]
    list_.is_null = False
    return list_


def _paren_left(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.anon_tok is not None:
        func: d_Function = inter.anon_tok.thing  #  type: ignore
    elif inter.call_tok is not None:
        func: d_Function = inter.call_tok.thing  #  type: ignore
    elif isinstance(inter.curr_tok.thing, d_Class):
        # This means we must be instantiating, and need the -make- func
        # Number num = Number('3');
        func = _make(inter)
    else:
        func: d_Function = inter.curr_tok.thing  #  type: ignore

    if inter.dotted_inst is not None:
        # We are activating a function of this instance, so the func needs 'this'
        # Subject to change when static functions are implemented
        # num.inc();
        func.add_attr(Declarable(inter.dotted_inst.parent, THIS), inter.dotted_inst)

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
            prim = value_to_prim(arg_loc.thing.grammar)
            if param.type_ != prim:
                _raise_helper(
                    f"{func_name} expected '{prim.value}'", inter, arg_loc.loc
                )
        elif isinstance(param.type_, d_Class):
            if not isinstance(arg_loc.thing, d_Instance):
                raise NotImplementedError
            elif arg_loc.thing.parent is not param.type_:
                raise NotImplementedError
        else:
            raise CriticalError("Unrecognized type for function argument")
        func.add_attr(param, arg_loc.thing)

    try:
        interpret(func)
    except DitError as err:
        err.add_trace(func.path, func.orig_loc, func.name)
        raise err
    except ReturnController as ret:
        inter.call_tok = ret.token
    except TypeMismatchError as mis:
        raise NotImplementedError
    else:
        if func.return_ is not None and func.return_ != d_Grammar.VOID:
            _raise_helper(f"{func_name} expected a return", inter, func.orig_loc)
        elif func.name == MAKE:
            thing = func.find_attr(THIS)
            if thing is None:
                raise NotImplementedError
            inter.call_tok = Token(d_Grammar.VALUE_INSTANCE, func.orig_loc, thing=thing)
        else:
            # func ended without 'return' keyword
            inter.call_tok = Token(d_Grammar.NULL, func.orig_loc)

    func.attrs.clear()
    inter.dotted_inst = None  # type: ignore
    if inter.call_tok.grammar == d_Grammar.NULL:
        return _terminal(inter)
    else:
        return _parenable(inter)


def _make(inter: InterpretContext) -> d_Function:
    class_: d_Class = inter.curr_tok.thing  # type: ignore
    make = class_.find_attr(MAKE)
    if make is None:
        _raise_helper(f"Class '{class_.name}' does not define a -make-", inter)
    elif isinstance(make, d_Function):
        func: d_Function = make
        inst = d_Instance()
        inst.is_null = False
        inst.parent = class_
        func.add_attr(Declarable(class_, THIS), inst)
        return func
    else:
        raise NotImplementedError


def _return(inter: InterpretContext) -> NoReturn:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if not isinstance(inter.body, d_Function):
        _raise_helper("'return' outside of function", inter)
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    try:
        raise ReturnController(value, inter.body, orig_loc)
    except TypeMismatchError as mis:
        mis.set_origin(inter.body.path, orig_loc, inter.char_feed.get_line(orig_loc))
        raise mis


def _throw(inter: InterpretContext) -> None:
    raise NotImplementedError


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
    dit = d_Dit()
    dit.is_null = False

    inter.advance_tokens(False)
    gra = inter.next_tok.grammar
    if gra != d_Grammar.WORD and gra not in EXPRESSION_STARTERS:
        _raise_helper("Expected a name or filepath string for import", inter)

    if gra == d_Grammar.WORD:
        # import SomeName from "someFilePath.dit";
        # WET: Identical to section in _class
        if inter.body.find_attr(inter.next_tok.word, scope_mode=True):
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
    if inter.dec.name is not None and not inter.equaling:
        dit.path = inter.dec.name
        inter.dec.name = None  # type: ignore
    elif value is None:
        raise NotImplementedError
    elif value.is_null:
        _raise_helper("Cannot import from null", inter, string_loc)
    elif isinstance(value, d_String):
        dit.path = value.string_value
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
    class_ = d_Class()
    class_.parent_scope = inter.body
    class_.is_null = False

    inter.advance_tokens(False)
    if inter.next_tok.grammar not in [d_Grammar.WORD, d_Grammar.BRACE_LEFT]:
        _raise_helper("Expected name or body to follow class", inter)

    if inter.next_tok.grammar == d_Grammar.WORD:
        # WET: Identical to section in _import
        if inter.body.find_attr(inter.next_tok.word, scope_mode=True):
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


def _sig(inter: InterpretContext) -> Optional[d_Function]:
    # sig JavaScript String ... \n func
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = _sig_or_func(inter)
    did_dispatch = False

    while True:
        if not did_dispatch:
            inter.advance_tokens()
        did_dispatch = False
        gra = inter.next_tok.grammar
        thing = inter.next_tok.thing
        switches = [func.lang, func.return_, func.return_list]

        # listOf needs additional checking
        # There must be a type after it, and not before it.
        if func.return_list and func.return_ is None:
            # sig ... listOf ...
            if gra == d_Grammar.VOID:
                _raise_helper("Cannot have listOf void", inter)
            elif gra not in TYPES and gra not in DOTABLES:
                _raise_helper("Expected type to follow listOf", inter)

        if gra == d_Grammar.FUNC:
            return _func(inter)
        elif gra == d_Grammar.EOF or None not in switches:
            _raise_helper("Expected 'func' to follow sig", inter)
        elif thing is not None:
            # handles dotables and explicit Lang/Class objects
            did_dispatch = _sig_thing_handler(inter, func)
        elif gra in LANGS:
            # sig ... Ditlang ...
            if func.lang is not None:
                _raise_helper("Language was already assigned", inter)
            func.lang = gra
        elif gra in TYPES or gra == d_Grammar.VOID:
            # sig ... String ...
            # sig ... void ...
            _sig_assign_return(inter, func)
            func.return_ = prim_to_value(gra)
        elif gra == d_Grammar.LISTOF:
            # sig ... listOf ...
            if func.return_ is not None:
                _raise_helper("Unexpected 'listOf' after type", inter)
            func.return_list = True
        elif inter.next_tok.word == "Javascript":
            # sig ... Javascript ...
            _raise_helper("Did you mean 'JavaScript'?", inter)
        else:
            _raise_helper("Unrecognized token for signature", inter)


def _sig_thing_handler(inter: InterpretContext, func: d_Function) -> bool:
    thing = _expression_dispatch(inter)
    if thing is None:
        raise NotImplementedError
    elif isinstance(thing, d_Language):
        raise NotImplementedError
    elif isinstance(thing, d_Class):
        _sig_assign_return(inter, func)
        func.return_ = thing
        return True
    else:
        mes = (
            "Expected Class or Lang, "
            f"'{thing.name}' is of type '{thing.public_type}'"
        )
        _raise_helper(mes, inter, inter.terminal_loc)


def _sig_assign_return(inter: InterpretContext, func: d_Function) -> None:
    if func.return_ is not None:
        _raise_helper("Return type was already assigned", inter)
    func.return_list = False if func.return_list is None else func.return_list


def _func(inter: InterpretContext) -> Optional[d_Function]:
    # func test(String right, String left) {{}}
    # func () {{}}
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = _sig_or_func(inter)
    inter.advance_tokens(False)
    if inter.next_tok.grammar == d_Grammar.WORD:
        # func someName
        result: d_Thing = inter.body.find_attr(inter.next_tok.word, scope_mode=True)  # type: ignore
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
            result: d_Thing = _expression_dispatch(inter)  # type: ignore
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
            result: d_Thing = inter.body.find_attr(param_name, scope_mode=True)  # type: ignore
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
    inter.declaring_func = None  # type: ignore
    return _handle_anon(inter, func, orig_loc)  # type: ignore


def _sig_or_func(inter: InterpretContext) -> d_Function:
    # sig Python String ...
    # OR
    # func hello() {{}}
    if inter.declaring_func is None:
        func = d_Function()
        func.parent_scope = inter.body
        func.is_null = False
        inter.declaring_func = func

    return inter.declaring_func


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
        inter.named_statement = True
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
    d_Grammar.SIG:                    _sig,
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
    d_Grammar.SIG:                    _sig,
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
