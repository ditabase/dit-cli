import copy
from itertools import zip_longest
from typing import List, NoReturn, Optional, Tuple, Union

from dit_cli.built_in import b_Ditlang
from dit_cli.exceptions import (
    d_CodeError,
    d_CriticalError,
    d_DitError,
    d_EndOfClangError,
    d_EndOfFileError,
    d_NameError,
    d_SyntaxError,
    d_TypeMismatchError,
)
from dit_cli.grammar import (
    DOTABLES,
    DUPLICABLES,
    MAKE,
    NAMEABLES,
    PRIMITIVES,
    STRINGABLES,
    THIS,
    TYPES,
    VALUE_CLANG_ABLES,
    d_Grammar,
    prim_to_value,
)
from dit_cli.interpret_context import DIGIT, InterpretContext
from dit_cli.lang_daemon import run_job
from dit_cli.oop import (
    ArgumentLocation,
    Declarable,
    GuestDaemonJob,
    JobType,
    Ref_Thing,
    ReturnController,
    Token,
    check_value,
    d_Body,
    d_Bool,
    d_Class,
    d_Container,
    d_Dit,
    d_Func,
    d_Inst,
    d_JSON,
    d_Lang,
    d_List,
    d_Num,
    d_Str,
    d_Thing,
    d_Type,
    d_Variable,
)
from dit_cli.preprocessor import preprocess
from dit_cli.settings import CodeLocation


def interpret(body: d_Body) -> Optional[d_Thing]:
    """Read text from a body and interpret it as ditlang code.
    Creates a new InterpretContext and executes statements on tokens,
    one after another, until EOF.

    Used recursively. Classes, functions, and imported dits are all interpreted
    recursively as new bodies with new InterpretContexts.
    Classes and dits are only interpreted once. Functions are re-interpreted
    every time they are called."""

    if not body.is_ready():
        return
    inter = InterpretContext(body)
    last_ret: Optional[d_Thing] = None
    try:
        at_eof = False
        while not at_eof:
            if inter.char_feed.eof():
                at_eof = True  # one extra iteration for the last char
            inter.advance_tokens()
            if inter.next_tok.grammar == d_Grammar.EOF:
                return last_ret  # Only at EOF whitespace or comment
            else:
                last_ret = _statement_dispatch(inter)
                inter.named_statement = False
    except d_DitError as err:
        if not err.origin:
            _generate_origin(err, inter)
        raise
    return last_ret


def _generate_origin(
    err: d_DitError, inter: InterpretContext, loc: Optional[CodeLocation] = None
) -> None:
    if not err.loc:
        # If the code is total garbage, the next token may not be assigned.
        # In that case, we default to wherever the char_feed happens to be.
        if inter.next_tok:
            err.loc = inter.next_tok.loc
        else:
            err.loc = inter.char_feed.loc

    if inter.body.path is None:
        raise d_CriticalError("A body had no path during exception")
    code = inter.char_feed.get_line(err.loc)
    err.set_origin(inter.body.path, code)


def _statement_dispatch(inter: InterpretContext) -> Optional[d_Thing]:
    """Execute the interpretation function that goes with the next_tok.
    Uses the large grammer -> function dictionary at the end of this file.
    Every grammer is paired with one function."""
    func = STATEMENT_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _expression_dispatch(inter: InterpretContext) -> Optional[d_Thing]:
    """Interpret the next expression and return a value if applicable.
    Also processes anon_tok, which results from anonymous classes, imports and functions
    Also processes call_tok, which results from all function calls."""
    gra = (inter.anon_tok or inter.call_tok or inter.next_tok).grammar
    func = EXPRESSION_DISPATCH[gra]
    return func(inter)


def _listof(inter: InterpretContext) -> None:
    # listOf Str values;
    inter.advance_tokens()
    inter.dec.listof = True
    if inter.next_tok.grammar in PRIMITIVES:
        _primitive(inter)
    elif inter.next_tok.grammar in DOTABLES:
        _expression_dispatch(inter)

    else:
        raise d_SyntaxError("Expected type for listOf declaration")


def _primitive(inter: InterpretContext) -> None:
    # Str value;
    inter.advance_tokens()
    _type(inter)


def _value_equalable(inter: InterpretContext) -> Optional[d_Thing]:
    # Thing test;
    # test = 'cat';
    # or, in an expression...
    # Thing test = 'cat';
    # someFunc(test);
    # These code examples are applicable to most _value_X functions
    inter.advance_tokens()
    return _equalable(inter)


def _value_class(inter: InterpretContext) -> Optional[d_Thing]:
    return _value_clang(inter)


def _value_lang(inter: InterpretContext) -> Optional[d_Thing]:
    return _value_clang(inter)


def _value_clang(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.declaring_func:
        # sig someLang someClass...
        # This class/lang is being used as a return type or language
        # in a function signature.
        inter.advance_tokens(False)
        if inter.next_tok.grammar == d_Grammar.DOT:
            return _dotable(inter)
        else:
            return inter.curr_tok.thing

    inter.advance_tokens(True)
    if (
        isinstance(inter.curr_tok.thing, d_Class)
        and inter.next_tok.grammar == d_Grammar.PAREN_LEFT
    ):
        # This class is being instantiated
        # someClass anInstance = someClass();
        return _parenable(inter)
    elif (
        isinstance(inter.curr_tok.thing, d_Lang)
        and inter.dec.type_ is d_Grammar.PRIMITIVE_LANG
    ):
        # This lang is being legally redeclared
        # lang JavaScript {||}
        # Lang JavaScript ...
        return
    elif inter.next_tok.grammar in VALUE_CLANG_ABLES:
        # someClass = someOtherClass;
        # someLang.someLangFunc();
        # This class is being dotted, equaled, etc.
        return _dotable(inter)
    elif inter.anon_tok:
        # class {||} someInstance = ?... this makes no sense.
        # This prevents using an anonymous class as a type
        # Triggering terminal will call missing ';'
        _terminal(inter)
    else:
        # someClass someInstance...
        # This class is being used as var type
        _type(inter)


def _type(inter: InterpretContext) -> None:
    # Str test ...
    # someClass test ...
    # Str someDotable.monkeyPatch ...
    # This function is reused by _primitive and _value_class
    inter.dec.type_ = _token_to_type(inter.curr_tok)
    if inter.next_tok.grammar in DUPLICABLES:
        raise d_SyntaxError(f"'{inter.next_tok.thing.name}' has already been declared")
    if inter.next_tok.grammar in NAMEABLES:
        _expression_dispatch(inter)
    else:
        raise d_SyntaxError("Expected a new name to follow type")

    if inter.next_tok.grammar == d_Grammar.NEW_NAME:
        # to handle the specific case when a lang is being legally redeclared
        # The tokens were already advanced in _value_lang.
        inter.advance_tokens()
    _equalable(inter)


def _token_to_type(token: Token) -> d_Type:
    if token.thing:
        return token.thing  # type: ignore
    else:
        return token.grammar


def _value_inst(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _dotable(inter)


def _value_function(inter: InterpretContext) -> Optional[d_Thing]:
    inter.advance_tokens()
    return _parenable(inter)


def _value_dit(inter: InterpretContext) -> Optional[d_Thing]:
    if not inter.anon_tok:
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
    if inter.next_tok.grammar != d_Grammar.WORD:
        raise d_SyntaxError(f"'{inter.next_tok.grammar}' is not dotable")

    # Allows dotting of anonymous tokens and function calls.
    target = (inter.anon_tok or inter.call_tok or inter.prev_tok).thing

    if isinstance(target, d_Inst):
        # We need to prepare in case the instance has inherited parents
        target.clear_prefix_to_func()
        inter.dotted_inst = target
    elif not isinstance(target, d_Container):
        raise d_CriticalError(f"Expected container, got {target.public_type}")

    result = target.find_attr(inter.next_tok.word)
    if not result and inter.dotted_inst:
        # this.B.attribute
        # We are doing explicit name disambiguation, looking in parent B instead of A.
        # B obviously doesn't have the attribute, the instance does.
        # So we look again in the instance.
        result = inter.dotted_inst.find_attr(inter.next_tok.word)

    if result:
        # The dot had a known variable, which we just need to return
        if isinstance(result, d_Func) and inter.dotted_inst:
            # this.func()
            # if `func` is an inherited function, we need to remember that we
            # called it so the prefixes are set up correctly.
            inter.dotted_inst.add_func_sep()
        return Token(result.grammar, copy.deepcopy(inter.next_tok.loc), thing=result)
    else:
        # The name was not found in the dotted body, so its a new name.
        # This means we are declaring a new var in the dotted body.
        # AKA Monkey patching
        inter.next_tok.grammar = d_Grammar.NEW_NAME
        inter.dotted_body = target  # Save for assignment
        return inter.next_tok


def _equalable(inter: InterpretContext) -> Optional[d_Thing]:
    if (
        isinstance(inter.curr_tok.thing, d_Lang)
        and inter.prev_tok.grammar == d_Grammar.PRIMITIVE_LANG
    ):
        # Since Langs can be redeclared, we just remove the type_
        # and pretend it was never there in the first place.
        # Lang JavaScript ...
        inter.dec.type_ = None  # type: ignore
    if inter.dec.type_ and not inter.dec.name:
        # _new_name should have been found, not an existing variable.
        # Str existingValue ...
        raise d_SyntaxError(f"'{inter.curr_tok.thing.name}' has already been declared")
    elif inter.next_tok.grammar == d_Grammar.EQUALS:
        # Assign existing or new variables
        # Str value = ...
        equal_loc = copy.deepcopy(inter.next_tok.loc)
        _equals(inter, equal_loc)
        inter.dec.reset()
    elif inter.dec.type_ and not inter.equaling:
        # create variable without assignment
        # Str count;
        _add_attr_wrap(inter)
        inter.dec.reset()

    return _terminal(inter)


def _equals(inter: InterpretContext, equal_loc: CodeLocation) -> None:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if inter.anon_tok or inter.call_tok:
        # prevent assignment to anonymous tokens.
        raise NotImplementedError
    if inter.dec.type_:
        assignee = None
    else:
        assignee = inter.curr_tok.thing

    inter.advance_tokens()
    inter.equaling = True
    value = _expression_dispatch(inter)
    inter.equaling = False
    if not value:
        if inter.named_statement:
            # Prevent assignment of non-anonymous statements.
            # Class anonName = class RealName {||}
            raise d_SyntaxError(
                "A named declaration cannot be used for assignment", orig_loc
            )
        else:
            raise d_CriticalError("No value for _expression_dispatch in _equals")
    if assignee:
        assignee.set_value(value)
    else:
        try:
            _add_attr_wrap(inter, value=value)
        except d_TypeMismatchError as err:
            err.loc = equal_loc
            raise


def _add_attr_wrap(inter: InterpretContext, value: Optional[d_Thing] = None):
    if inter.dotted_inst:
        inter.dotted_inst.add_attr(inter.dec, value=value)
        inter.dotted_inst = None  # type: ignore
    elif inter.dotted_body:
        inter.dotted_body.add_attr(inter.dec, value=value)
        inter.dotted_body = None  # type: ignore
    else:
        inter.body.add_attr(inter.dec, value=value)


def _terminal(inter: InterpretContext) -> d_Thing:
    # someValue;
    # someListArg,
    # someListArg]
    # someFuncArg)
    # someTriangleVar! (the exclamation point is inserted by the preprocessor)
    if inter.next_tok.grammar not in [
        d_Grammar.SEMI,
        d_Grammar.COMMA,
        d_Grammar.BRACKET_RIGHT,
        d_Grammar.PAREN_RIGHT,
        d_Grammar.POINT,
    ]:
        if inter.declaring_func or inter.in_json:
            pass
        elif inter.comma_depth == 0:
            _missing_terminal(inter, "Expected ';'")
        else:
            _missing_terminal(inter, "Expected ']'")

    if not inter.equaling:
        # this.A.Make();
        # someClass.doThing();
        # We dotted something, and need to clear that out.
        # But not if we're equaling:
        # this.A.value = someClass.value;
        # _terminal will actually be called again, and these will be cleared then.
        inter.dotted_body = None  # type: ignore
        inter.dotted_inst = None  # type: ignore

    if inter.anon_tok:
        ret = inter.anon_tok.thing
        inter.anon_tok = None
        return ret
    elif inter.call_tok:
        ret = inter.call_tok.thing
        inter.call_tok = None
        return ret
    else:
        inter.terminal_loc = copy.deepcopy(inter.curr_tok.loc)
        # This return is how _equals gets it's value.
        return inter.curr_tok.thing


def _point(inter: InterpretContext) -> None:
    # If a semicolon and exclamation point are both present, this will allow
    # the point to pass safely
    # <|return 1|> -> return 1!
    # <|return 1;|> -> return 1;!
    # Notice the point is by itself, and will be run as a statement.
    pass


def _new_name(inter: InterpretContext) -> None:
    inter.dec.name = inter.next_tok.word
    if not inter.dec.type_:
        # new name without a type declaration is only allowed with an equals
        # unknownName = ...
        inter.advance_tokens()
        if inter.next_tok.grammar != d_Grammar.EQUALS:
            raise d_NameError(
                f"Undefined variable '{inter.curr_tok.word}'", inter.curr_tok.loc,
            )
        # if there is an equals, then we just pretend the declaration was 'Thing'
        inter.dec.type_ = d_Grammar.PRIMITIVE_THING
        equal_loc = copy.deepcopy(inter.next_tok.loc)
        _equals(inter, equal_loc)
        inter.dec.reset()
        _terminal(inter)


def _str(inter: InterpretContext) -> d_Str:
    # note that _str is reused for parsing JSON element names
    left = inter.next_tok.grammar.value
    data = ""
    if inter.char_feed.current() != left:
        while True:
            if inter.char_feed.current() == "\n":
                lok = copy.deepcopy(inter.next_tok.loc)
                length = len(data)
                lok.pos += length
                lok.col += length
                raise d_SyntaxError("Unexpected EOL while reading string", lok)
            elif inter.char_feed.current() == d_Grammar.BACKSLASH.value:
                # Str test = "some\t"
                # Str test = 'Let\'s'
                escape_char = inter.char_feed.pop()
                inter.char_feed.pop()
                if escape_char in [
                    d_Grammar.QUOTE_DOUBLE.value,
                    d_Grammar.QUOTE_SINGLE.value,
                    d_Grammar.BACKSLASH.value,
                ]:
                    data += escape_char
                elif escape_char == d_Grammar.ESCAPE_NEWLINE.value:
                    data += "\n"
                elif escape_char == d_Grammar.ESCAPE_TAB.value:
                    data += "\t"
            else:
                data += inter.char_feed.current()
                inter.char_feed.pop()

            if inter.char_feed.current() == left:
                break

    inter.advance_tokens()  # next_tok is now ' "
    inter.advance_tokens()  # next_tok is now ; , ] ) :
    thing = d_Str()
    thing.str_ = data
    thing.is_null = False
    return thing


def _bool(inter: InterpretContext) -> d_Bool:
    # b = true;
    # doThing(false);
    val = d_Bool()
    val.is_null = False
    val.bool_ = inter.next_tok.grammar == d_Grammar.TRUE
    inter.advance_tokens()
    return val


def _plus(inter: InterpretContext) -> d_Num:
    return _digit_sign(inter, False)


def _minus(inter: InterpretContext) -> d_Num:
    return _digit_sign(inter, True)


def _digit_sign(inter: InterpretContext, neg: bool) -> d_Num:
    # make sure the sign is being used as a positive or negative,
    # not for arithmetic
    if DIGIT.match(inter.char_feed.current()):
        inter.advance_tokens()
        return _digit(inter, neg)
    else:
        raise d_SyntaxError(
            "Expected digit.\nOther arithmetic ops are not yet supported.",
            inter.char_feed.loc,  # Default uses inter.next_tok.lok
        )


def _digit(inter: InterpretContext, neg: bool = False) -> d_Num:
    num = inter.next_tok.word
    num = "-" + num if neg else num
    lead_zero = num == "0"
    frac = False
    exp = False
    while True:
        cur = inter.char_feed.current()
        if DIGIT.match(cur):
            # 3
            if lead_zero and len(num) == 1:
                raise d_SyntaxError("Leading zeros are not allowed")
            num += cur
            inter.char_feed.pop()
            lead_zero = False
        elif cur == ".":
            # 3.
            if frac == True:
                raise d_SyntaxError("Invalid fraction syntax")
            num += cur
            inter.char_feed.pop()
            frac == True
        elif cur == "e" or cur == "E":
            # 3e ... 10
            if exp == True:
                raise d_SyntaxError("Invalid exponent syntax")
            num += cur
            inter.char_feed.pop()
            exp == True
        elif cur == "-" or cur == "+":
            # -3
            num += cur
            inter.char_feed.pop()
        else:
            break
    return _finalize_num(inter, num)


def _finalize_num(inter: InterpretContext, num: str) -> d_Num:
    # advance to terminal
    # num = 3.14;
    inter.advance_tokens()
    fin_num = d_Num()
    fin_num.is_null = False
    try:
        fin_num.num = int(num)
    except ValueError:
        fin_num.num = float(num)
    return fin_num


def _bracket_left(inter: InterpretContext) -> d_List:
    list_ = d_List()
    list_.list_ = [item.thing for item in _arg_list(inter, d_Grammar.BRACKET_RIGHT)]
    list_.is_null = False
    return list_


def _brace_left(inter: InterpretContext) -> d_JSON:
    # JSON j = { ...
    inter.in_json = True
    js = d_JSON()
    js.is_null = False
    js.json_ = {}
    inter.advance_tokens()

    while True:
        if inter.next_tok.grammar == d_Grammar.BRACE_RIGHT:
            # JSON j = { ... }
            inter.in_json = False
            inter.advance_tokens()
            return js
        elif inter.next_tok.grammar == d_Grammar.QUOTE_DOUBLE:
            # JSON j = { "item1": ...
            if inter.curr_tok.grammar not in [d_Grammar.BRACE_LEFT, d_Grammar.COMMA]:
                raise d_SyntaxError("Expected ','", inter.curr_tok.loc)
            name = _str(inter).str_
            if inter.next_tok.grammar != d_Grammar.COLON:
                raise d_SyntaxError("Expected ':'", inter.next_tok.loc)
            else:
                inter.advance_tokens()
            ele = _expression_dispatch(inter)
            js.json_[name] = ele
        elif inter.next_tok.grammar == d_Grammar.COMMA:
            # JSON j = { "item1": 1, ...
            inter.advance_tokens()
            if inter.next_tok.grammar == d_Grammar.BRACE_RIGHT:
                raise d_SyntaxError(
                    "Trailing commas are not allowed", inter.curr_tok.loc
                )
        else:
            raise d_SyntaxError("Unexpected token for JSON")


def _paren_left(inter: InterpretContext) -> Optional[d_Thing]:
    func = (inter.anon_tok or inter.call_tok or inter.curr_tok).thing
    if isinstance(func, d_Class):
        # This means we must be instantiating, and need the Make func
        # Number num = Number('3');
        func = _make(inter)
    elif not isinstance(func, d_Func):
        raise d_CriticalError(f"Expected function, got {func.public_type}")

    func.new_call()  # handles recursive attribute stack

    stored_inst = None
    if inter.dotted_inst and not inter.equaling:
        # We are activating a function of this instance, so the func needs 'this'
        # Subject to change when static functions are implemented
        # num.inc();
        func.add_attr(
            Declarable(inter.dotted_inst.parent, THIS), inter.dotted_inst, use_ref=True,
        )
        stored_inst = inter.dotted_inst
    inter.dotted_inst = None  # type: ignore

    _get_func_args(inter, func)

    if not func.code and func.lang is not b_Ditlang:
        preprocess(func)

    inter.call_tok = _run_func(inter, func)

    func.end_call()

    if stored_inst:
        stored_inst.pop_func_sep()

    if inter.call_tok.grammar == d_Grammar.NULL:
        return _terminal(inter)
    else:
        return _parenable(inter)


def _handle_get_config(inter: InterpretContext, getConfig: d_Func) -> None:
    # Load the .ditconf files from cwd to root
    config_files: List[d_Dit] = getConfig.py_func(getConfig)
    if not config_files:
        raise NotImplementedError
    for dit in config_files:
        # interpret each file
        interpret(dit)

        for var in dit.attrs:
            conf_lang = dit.attrs[var].get_thing()
            if isinstance(conf_lang, d_Lang):
                # for each lang in the conf file
                local_lang = inter.body.find_attr(var.name)
                if local_lang:
                    # If they exit both places, merge them
                    local_lang.set_value(conf_lang)
                else:
                    # or just put the conf lang here
                    inter.body.attrs[var] = conf_lang


def _make(inter: InterpretContext) -> d_Func:
    class_: d_Class = inter.curr_tok.thing  # type: ignore
    make = class_.find_attr(MAKE)
    if not make:
        raise d_SyntaxError(f"Class '{class_.name}' does not define a Make")
    elif isinstance(make, d_Func):
        func: d_Func = make
        inst = d_Inst()
        inst.is_null = False
        inst.parent = class_
        func.add_attr(Declarable(class_, THIS), inst, use_ref=True)
        return func
    else:
        raise NotImplementedError


def _return(inter: InterpretContext) -> NoReturn:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if not isinstance(inter.body, d_Func):
        raise d_SyntaxError("'return' outside of function")
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if not value:
        raise NotImplementedError
    try:
        raise ReturnController(value, inter.body, orig_loc)
    except d_TypeMismatchError as err:
        err.loc = orig_loc
        raise
        # mis.set_origin(inter.body.path, orig_loc, inter.char_feed.get_line(orig_loc))
        # raise mis


def _get_func_args(inter: InterpretContext, func: d_Func) -> None:
    func.call_loc = copy.deepcopy(inter.curr_tok.loc)
    arg_locs = _arg_list(inter, d_Grammar.PAREN_RIGHT)
    miss = abs(len(func.parameters) - len(arg_locs))
    name = func.pub_name()

    for param, arg_loc in zip_longest(func.parameters, arg_locs):
        param: Declarable
        arg_loc: ArgumentLocation
        if not arg_loc:
            raise d_SyntaxError(f"{name} missing {miss} required arguments")
        elif not param:
            # TODO: implement proper k-args functionality
            raise d_SyntaxError(f"{name} given {miss} too many arguments")
        else:
            res = check_value(arg_loc.thing, param)
            if res:
                o = f"{name} expected '{res.expected}', got '{res.actual}'{res.extra}"
                raise d_TypeMismatchError(o, arg_loc.loc)

        func.add_attr(param, arg_loc.thing, use_ref=True)


def _run_func(inter: InterpretContext, func: d_Func) -> Token:
    try:
        if func.is_built_in:
            if func.name == "getConfig":
                _handle_get_config(inter, func)
            else:
                func.py_func(func)
        elif func.lang is b_Ditlang:
            interpret(func)
        else:
            if not func.code:
                raise ReturnController(d_Thing.get_null_thing(), func, func.call_loc)
            _job_loop(GuestDaemonJob(JobType.CALL_FUNC, func))

    except d_CodeError as err:
        err.loc = func.call_loc
        # err.set_origin(
        #    inter.body.path, func.call_loc, inter.char_feed.get_line(func.call_loc)
        # )
        raise err
    except d_DitError as err:
        err.add_trace(func.path, func.call_loc, func.name)
        raise err
    except ReturnController as ret:
        if func.lang is not b_Ditlang:
            job = GuestDaemonJob(JobType.RETURN_KEYWORD, func)
            run_job(job)
        return ret.token
    except d_TypeMismatchError as mis:
        raise NotImplementedError
    else:
        if func.return_ and func.return_ != d_Grammar.VOID:
            raise d_SyntaxError(f"{func.pub_name()} expected a return", func.call_loc)
        elif func.name == MAKE:
            thing = func.find_attr(THIS)
            if not thing:
                raise NotImplementedError
            return Token(d_Grammar.VALUE_INST, func.call_loc, thing=thing)
        else:
            # func ended without 'return' keyword
            return Token(d_Grammar.NULL, func.call_loc)


def _job_loop(job: GuestDaemonJob) -> None:
    while True:
        res = run_job(job)
        if res.type_ == JobType.FINISH_FUNC:
            break
        elif res.type_ == JobType.EXE_DITLANG:
            if not isinstance(res.result, str):
                raise NotImplementedError
            mock_func = job.func.get_mock(res.result)
            value = interpret(mock_func)
            job.type_ = JobType.DITLANG_CALLBACK
            if not value:
                pass
            elif isinstance(value, (d_Thing, d_Bool, d_Num, d_Str, d_List, d_JSON)):
                job.result = value.get_data()  # type: ignore
            else:
                raise NotImplementedError


def _throw(inter: InterpretContext) -> None:
    raise NotImplementedError


def _trailing_comma(inter: InterpretContext, right: d_Grammar) -> Optional[NoReturn]:
    if inter.next_tok.grammar not in [d_Grammar.COMMA, right]:
        _missing_terminal(inter, f"Expected '{right.value}'")

    if inter.next_tok.grammar == d_Grammar.COMMA:
        inter.advance_tokens()


def _arg_list(inter: InterpretContext, right: d_Grammar) -> List[ArgumentLocation]:
    # someFunc('arg1', 'arg2');
    # listOf Str = ['a', 'b', ['c'], 'd'];
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
        if not arg:
            raise NotImplementedError
        args.append(ArgumentLocation(loc, arg))
        _trailing_comma(inter, right)


def _import(inter: InterpretContext) -> Optional[d_Dit]:
    # import LINK
    # import NAMESPACE from LINK
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    name = None

    inter.advance_tokens(False)
    gra = inter.next_tok.grammar
    if gra != d_Grammar.WORD and gra not in STRINGABLES:
        raise d_SyntaxError("Expected a name or filepath string for import")

    if gra == d_Grammar.WORD:
        # import SomeName from "someFilePath.dit";
        if inter.body.find_attr(inter.next_tok.word, scope_mode=True):
            raise d_SyntaxError(f"'{inter.next_tok.word}' has already been declared")
        name = inter.next_tok.word
        inter.advance_tokens()
        if inter.next_tok.grammar != d_Grammar.FROM:
            raise d_SyntaxError("Expected 'from'")
        inter.advance_tokens()

    dit = _import_or_pull(inter, orig_loc)
    dit.name = name  # type: ignore
    return _import_or_pull_end(inter, dit, orig_loc)


def _pull(inter: InterpretContext) -> None:
    # pull TARGET (as REPLACEMENT), ... from LINK
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    targets: List[Tuple[str, Optional[str]]] = []
    langs: List[Optional[d_Lang]] = []
    while True:
        # pull ...
        # pull THING, ...
        # pull THING as NAME, ...
        inter.advance_tokens(False)
        if inter.next_tok.grammar != d_Grammar.WORD:
            raise d_SyntaxError("Expected name to pull from linked dit")
        # pull NAME ...
        target = inter.next_tok.word
        loc = copy.deepcopy(inter.next_tok.loc)
        replacement = None
        inter.advance_tokens()
        if inter.next_tok.grammar == d_Grammar.AS:
            # pull NAME as ...
            inter.advance_tokens(False)
            if inter.next_tok.grammar != d_Grammar.WORD:
                raise d_SyntaxError("Expected name to replace target name")
            replacement = inter.next_tok.word
            loc = inter.next_tok.loc
            inter.advance_tokens()

        name = replacement or target
        result = inter.body.find_attr(name, True)
        if result:
            if isinstance(result, d_Lang):
                # Langauges can overwrite langs already in this dit
                # lang someLang {||}
                # pull someLang from LINK
                langs.append(result)
            else:
                raise d_SyntaxError(f"'{name}' has already been declared", loc)
        else:
            langs.append(None)
        targets.append((target, replacement))

        if inter.next_tok.grammar == d_Grammar.FROM:
            break
        elif inter.next_tok.grammar == d_Grammar.COMMA:
            continue
        else:
            raise d_SyntaxError("Expected 'from' or ',' to follow target")

    inter.advance_tokens()
    dit = _import_or_pull(inter, orig_loc)
    for (tar, rep), lang in zip(targets, langs):
        # pull TARGET (as REPLACEMENT), ... from LINK
        result = dit.find_attr(tar)
        if not result:
            raise d_SyntaxError(f"'{tar}' is not a valid member of this dit")
        result.name = rep or tar
        if lang and isinstance(result, d_Lang):
            # explicit call to set_value, to activate Priority comparisons
            lang.set_value(result)
            result.attrs = lang.attrs  # TODO: proper unassigned lang logic
        else:
            inter.body.attrs[d_Variable(result.name)] = result
    _import_or_pull_end(inter, dit, orig_loc)


def _import_or_pull(inter: InterpretContext, orig_loc: CodeLocation) -> d_Dit:
    # The next token is always the link. We just need to get the dit and return it.
    # import LINK
    # import NAMESPACE from LINK
    # pull ... from LINK
    dit = d_Dit()
    dit.is_null = False
    if inter.next_tok.grammar in [d_Grammar.NULL, d_Grammar.VALUE_NULL]:
        raise d_SyntaxError("Cannot import from null")
    elif inter.next_tok.grammar not in STRINGABLES:
        raise d_SyntaxError("Expected a filepath string for import")

    value = _expression_dispatch(inter)
    if inter.dec.name and not inter.equaling:
        dit.path = inter.dec.name
        inter.dec.name = None  # type: ignore
    elif not value:
        raise NotImplementedError
    elif isinstance(value, d_Str):
        dit.path = value.str_
    else:
        raise d_SyntaxError(f"Expected str value, not {value.public_type}")

    dit.finalize()
    try:
        interpret(dit)
    except d_DitError as err:
        err.add_trace(dit.path, orig_loc, "import")
        raise
    return dit


def _import_or_pull_end(
    inter: InterpretContext, dit: d_Dit, orig_loc: CodeLocation
) -> None:
    # handled slightly differently from other bodies.
    # import always ends with a semicolon, even with a name.
    anon = _handle_anon(inter, dit, orig_loc)
    if anon:
        return anon  # type: ignore
    else:
        # Thus, this explicit call to _terminal.
        _terminal(inter)


def _class(inter: InterpretContext) -> Optional[d_Class]:
    class_ = d_Class()
    class_.parent_scope = inter.body
    class_.is_null = False
    return _clang(inter, class_)  # type: ignore


def _lang(inter: InterpretContext) -> None:
    lang = d_Lang()
    lang.parent_scope = inter.body
    lang.is_null = False
    return _clang(inter, lang)  # type: ignore


def _clang(
    inter: InterpretContext, clang: Union[d_Class, d_Lang]
) -> Optional[Union[d_Class, d_Lang]]:
    # class/lang NAME {||}
    # class/lang {||}; <- Anonymous version
    lang = None
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    clang_name = "class" if isinstance(clang, d_Class) else "lang"

    inter.advance_tokens(False)
    if inter.next_tok.grammar not in [d_Grammar.WORD, d_Grammar.BAR_BRACE_LEFT]:
        raise d_SyntaxError(f"Expected name or body to follow {clang_name}")

    if inter.next_tok.grammar == d_Grammar.WORD:
        result = inter.body.find_attr(inter.next_tok.word, scope_mode=True)
        if result:
            if isinstance(result, d_Lang):
                # Langs are allowed to be redeclared
                # lang someLang {||}
                # lang someLang {||}
                lang = result
            else:
                raise d_SyntaxError(
                    f"'{inter.next_tok.word}' has already been declared"
                )
        clang.name = inter.next_tok.word
        inter.advance_tokens()  # get {|
        if inter.next_tok.grammar != d_Grammar.BAR_BRACE_LEFT:
            raise d_SyntaxError(f"Expected a {clang_name} body")

    _bar_brace_left(inter, clang)
    clang.finalize()
    try:
        interpret(clang)
    except d_EndOfFileError as err:
        raise d_EndOfClangError(clang_name) from err
    return _handle_anon(inter, clang, orig_loc, lang)  # type: ignore


def _sig(inter: InterpretContext) -> Optional[d_Func]:
    # sig JavaScript Str ... \n func
    dotable_loc = None
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
        if func.return_list and not func.return_:
            # sig ... listOf ...
            if gra == d_Grammar.VOID:
                raise d_SyntaxError("Cannot have listOf void")
            elif gra not in TYPES and gra not in DOTABLES:
                raise d_SyntaxError("Expected type to follow listOf", dotable_loc)
            elif gra in DOTABLES:
                dotable_loc = copy.deepcopy(inter.next_tok.loc)

        if gra == d_Grammar.FUNC:
            return _func(inter)
        elif gra == d_Grammar.EOF or None not in switches:
            raise d_SyntaxError("Expected 'func' to follow sig")
        elif thing:
            # handles dotables and explicit Lang/Class objects
            _sig_thing_handler(inter, func)
            did_dispatch = True
        elif gra in TYPES or gra == d_Grammar.VOID:
            # sig ... Str ...
            # sig ... void ...
            _sig_assign_return(inter, func)
            func.return_ = prim_to_value(gra)
        elif gra == d_Grammar.LISTOF:
            # sig ... listOf ...
            if func.return_:
                raise d_SyntaxError("Unexpected 'listOf' after type")
            func.return_list = True
        elif inter.next_tok.grammar == d_Grammar.NEW_NAME:
            raise NotImplementedError
            # TODO: finish unassigned langs feature, issue #14
            # We allow langs to be declared on the fly. This lets library dits
            # specify a language without having to import it, which would be annoying.
            # The lang must be more fully assigned in the dit where it will be called.
            lang = d_Lang()
            lang.is_null = False
            lang.parent_scope = inter.body
            lang.name = inter.next_tok.word
            inter.body.attrs[d_Variable(lang.name)] = lang
            func.lang = lang
        else:
            raise d_SyntaxError("Unrecognized token for signature")


def _sig_thing_handler(inter: InterpretContext, func: d_Func) -> None:
    thing = _expression_dispatch(inter)
    if not thing:
        raise NotImplementedError
    elif isinstance(thing, d_Lang):
        if func.lang:
            raise d_SyntaxError("Language was already assigned")
        func.lang = thing
    elif isinstance(thing, d_Class):
        _sig_assign_return(inter, func)
        func.return_ = thing
    else:
        mes = (
            "Expected Class or Lang, "
            f"'{thing.name}' is of type '{thing.public_type}'"
        )
        raise d_SyntaxError(mes, inter.terminal_loc)


def _sig_assign_return(inter: InterpretContext, func: d_Func) -> None:
    if func.return_:
        raise d_SyntaxError("Return type was already assigned")
    func.return_list = bool(func.return_list)


def _func(inter: InterpretContext) -> Optional[d_Func]:
    # func test(Str right, Str left) {||}
    # func () {||}
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = _sig_or_func(inter)
    if not func.return_:
        func.return_ = d_Grammar.VOID
    if not func.return_list:
        func.return_list = False
    if not func.lang:
        func.lang = b_Ditlang
    inter.advance_tokens(False)
    if inter.next_tok.grammar == d_Grammar.WORD:
        # func someName
        result: d_Thing = inter.body.find_attr(inter.next_tok.word, scope_mode=True)  # type: ignore
        if result:
            raise d_SyntaxError(f"'{result.name}' has already been declared")
        else:
            func.name = inter.next_tok.word
            # Advance only if the name was there
            # If no name, then this is an anonymous function
            inter.advance_tokens()

    if inter.next_tok.grammar != d_Grammar.PAREN_LEFT:
        # func Ditlang void someName(
        raise d_SyntaxError("Expected parameter list")

    inter.advance_tokens()
    while True:
        if inter.next_tok.grammar == d_Grammar.PAREN_RIGHT:
            inter.advance_tokens()
            break

        param_list = False
        if inter.next_tok.grammar == d_Grammar.LISTOF:
            param_list = True
            inter.advance_tokens()

        if inter.next_tok.grammar in DOTABLES:
            # someName(numLib.Number
            result: d_Thing = _expression_dispatch(inter)  # type: ignore
            if result.grammar == d_Grammar.VALUE_CLASS:
                param_type = _token_to_type(inter.curr_tok)
            else:
                mes = (
                    "Expected class for parameter type, "
                    f"'{result.name}' is of type '{result.public_type}'"
                )
                raise d_SyntaxError(mes, inter.terminal_loc)
        elif inter.next_tok.grammar in PRIMITIVES:
            # someName(d_String
            param_type = _token_to_type(inter.next_tok)
            inter.advance_tokens(False)
        else:
            raise d_SyntaxError("Expected parameter type")

        if inter.next_tok.grammar != d_Grammar.WORD:
            raise d_SyntaxError("Expected parameter name")
        else:
            # someName(d_String someParam
            param_name = inter.next_tok.word
            result: d_Thing = inter.body.find_attr(param_name, scope_mode=True)  # type: ignore
            if result:
                raise d_SyntaxError(f"'{param_name}' has already been declared")
            elif param_name in [p.name for p in func.parameters]:
                raise d_SyntaxError(f"'{param_name}' is already a parameter name")
        func.parameters.append(Declarable(param_type, param_name, param_list))

        inter.advance_tokens()
        _trailing_comma(inter, d_Grammar.PAREN_RIGHT)

    if inter.next_tok.grammar != d_Grammar.BAR_BRACE_LEFT:
        raise d_SyntaxError("Expected function body")

    _bar_brace_left(inter, func)
    func.finalize()
    inter.declaring_func = None  # type: ignore
    return _handle_anon(inter, func, orig_loc)  # type: ignore


def _sig_or_func(inter: InterpretContext) -> d_Func:
    # sig Python Str ...
    # OR
    # func hello() {||}
    if not inter.declaring_func:
        func = d_Func()
        func.parent_scope = inter.body
        func.is_null = False
        inter.declaring_func = func

    return inter.declaring_func


def _bar_brace_left(inter: InterpretContext, body: d_Body) -> None:
    depth = 1
    body.start_loc = copy.deepcopy(inter.char_feed.loc)
    while depth > 0:
        cur = inter.char_feed.current() + inter.char_feed.peek()
        if cur == d_Grammar.BAR_BRACE_LEFT.value:
            depth += 1
            inter.advance_tokens()
        elif cur == d_Grammar.BAR_BRACE_RIGHT.value:
            depth -= 1
            body.end_loc = copy.deepcopy(inter.char_feed.loc)
            inter.advance_tokens()
        else:
            inter.char_feed.pop()


def _handle_anon(
    inter: InterpretContext,
    anon_body: d_Body,
    orig_loc: CodeLocation,
    lang: Optional[d_Lang] = None,
) -> Optional[d_Body]:
    if anon_body.name:
        # traditional statement, stop here
        if lang and isinstance(anon_body, d_Lang):
            # a language is being redeclared, must call set_value to
            # activate priority comparison stuff
            lang.set_value(anon_body)
        else:
            inter.body.attrs[d_Variable(anon_body.name)] = anon_body
        inter.named_statement = True
        return None
    else:
        # anonymous expression, need to dispatch it
        inter.anon_tok = Token(anon_body.grammar, orig_loc, thing=anon_body)
        return _expression_dispatch(inter)  # type: ignore


def _missing_terminal(inter: InterpretContext, message: str) -> NoReturn:
    tok = inter.curr_tok
    target = tok.loc
    code = inter.char_feed.get_line(target)

    if isinstance(tok.grammar.value, str):
        length = len(tok.grammar.value)  # class, Str, =
    elif tok.thing:
        length = len(tok.thing.name)  # Object names
    else:
        length = len(tok.word)  # New Names

    # Shift locaton to end of token
    target.pos += length
    target.col += length

    err = d_SyntaxError(message, target)
    err.set_origin(inter.body.path, code)
    raise err


def _trigger_eof_err(inter: InterpretContext) -> NoReturn:
    inter.char_feed.pop()
    raise d_CriticalError("EOF reached, but failed to trigger")


def _not_implemented(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("This keyword is reserved for later development")


def _illegal_statement(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("Illegal start of statement")


def _illegal_expression(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("Illegal start of expression")


# disable black formatting temporarily
# fmt: off
STATEMENT_DISPATCH = {
    d_Grammar.QUOTE_DOUBLE:           _illegal_statement,
    d_Grammar.QUOTE_SINGLE:           _illegal_statement,
    d_Grammar.DOT:                    _illegal_statement,
    d_Grammar.POINT:                  _point,
    d_Grammar.EQUALS:                 _illegal_statement,
    d_Grammar.PLUS:                   _illegal_statement,
    d_Grammar.MINUS:                  _illegal_statement,
    d_Grammar.COMMA:                  _illegal_statement,
    d_Grammar.SEMI:                   _illegal_statement,
    d_Grammar.COLON:                  _illegal_statement,
    d_Grammar.PAREN_LEFT:             _illegal_statement,
    d_Grammar.PAREN_RIGHT:            _illegal_statement,
    d_Grammar.BRACKET_LEFT:           _illegal_statement,
    d_Grammar.BRACKET_RIGHT:          _illegal_statement,
    d_Grammar.BACKSLASH:              _illegal_statement,
    d_Grammar.COMMENT_START:          _illegal_statement,
    d_Grammar.TRI_LEFT:               _illegal_statement,
    d_Grammar.TRI_RIGHT:              _illegal_statement,
    d_Grammar.CIR_LEFT:               _illegal_statement,
    d_Grammar.CIR_RIGHT:              _illegal_statement,
    d_Grammar.BAR_BRACE_LEFT:         _illegal_statement,
    d_Grammar.BAR_BRACE_RIGHT:        _illegal_statement,
    d_Grammar.BRACE_LEFT:             _illegal_statement,
    d_Grammar.BRACE_RIGHT:            _illegal_statement,
    d_Grammar.CLASS:                  _class,
    d_Grammar.LANG:                   _lang,
    d_Grammar.SIG:                    _sig,
    d_Grammar.FUNC:                   _func,
    d_Grammar.VOID:                   _illegal_statement,
    d_Grammar.LISTOF:                 _listof,
    d_Grammar.IMPORT:                 _import,
    d_Grammar.FROM:                   _illegal_statement,
    d_Grammar.AS:                     _illegal_statement,
    d_Grammar.PULL:                   _pull,
    d_Grammar.USE:                    _not_implemented,
    d_Grammar.STATIC:                 _not_implemented,
    d_Grammar.INST:                   _not_implemented,
    d_Grammar.THROW:                  _throw,
    d_Grammar.RETURN:                 _return,
    d_Grammar.NULL:                   _illegal_statement,
    d_Grammar.TRUE:                   _illegal_statement,
    d_Grammar.FALSE:                  _illegal_statement,
    d_Grammar.PRIMITIVE_THING:        _primitive,
    d_Grammar.PRIMITIVE_STR:          _primitive,
    d_Grammar.PRIMITIVE_BOOL:         _primitive,
    d_Grammar.PRIMITIVE_NUM:          _primitive,
    d_Grammar.PRIMITIVE_JSON:         _primitive,
    d_Grammar.PRIMITIVE_CLASS:        _primitive,
    d_Grammar.PRIMITIVE_INST:         _primitive,
    d_Grammar.PRIMITIVE_FUNC:         _primitive,
    d_Grammar.PRIMITIVE_DIT:          _primitive,
    d_Grammar.PRIMITIVE_LANG:         _primitive,
    d_Grammar.WORD:                   _illegal_statement,
    d_Grammar.NEW_NAME:               _new_name,
    d_Grammar.DIGIT:                  _illegal_statement,
    d_Grammar.VALUE_NULL:             _value_equalable,
    d_Grammar.VALUE_THING:            _value_equalable,
    d_Grammar.VALUE_STR:              _value_equalable,
    d_Grammar.VALUE_BOOL:             _value_equalable,
    d_Grammar.VALUE_NUM:              _value_equalable,
    d_Grammar.VALUE_LIST:             _value_equalable,
    d_Grammar.VALUE_JSON:             _value_equalable,
    d_Grammar.VALUE_CLASS:            _value_class,
    d_Grammar.VALUE_INST:         _value_inst,
    d_Grammar.VALUE_FUNC:             _value_function,
    d_Grammar.VALUE_DIT:              _value_dit,
    d_Grammar.VALUE_LANG:             _value_lang,
    d_Grammar.EOF:                    _trigger_eof_err,
}


EXPRESSION_DISPATCH = {
    d_Grammar.QUOTE_DOUBLE:           _str,
    d_Grammar.QUOTE_SINGLE:           _str,
    d_Grammar.DOT:                    _illegal_expression,
    d_Grammar.POINT:                  _illegal_expression,
    d_Grammar.EQUALS:                 _illegal_expression,
    d_Grammar.PLUS:                   _plus,
    d_Grammar.MINUS:                  _minus,
    d_Grammar.COMMA:                  _illegal_expression,
    d_Grammar.SEMI:                   _illegal_expression,
    d_Grammar.COLON:                  _illegal_expression,
    d_Grammar.PAREN_LEFT:             _illegal_expression,
    d_Grammar.PAREN_RIGHT:            _illegal_expression,
    d_Grammar.BRACKET_LEFT:           _bracket_left,
    d_Grammar.BRACKET_RIGHT:          _illegal_expression,
    d_Grammar.BACKSLASH:              _illegal_expression,
    d_Grammar.COMMENT_START:          _illegal_expression,
    d_Grammar.TRI_LEFT:               _illegal_expression,
    d_Grammar.TRI_RIGHT:              _illegal_expression,
    d_Grammar.CIR_LEFT:               _illegal_expression,
    d_Grammar.CIR_RIGHT:              _illegal_expression,
    d_Grammar.BAR_BRACE_LEFT:         _illegal_expression,
    d_Grammar.BAR_BRACE_RIGHT:        _illegal_expression,
    d_Grammar.BRACE_LEFT:             _brace_left,
    d_Grammar.BRACE_RIGHT:            _illegal_expression,
    d_Grammar.CLASS:                  _class,
    d_Grammar.LANG:                   _lang,
    d_Grammar.SIG:                    _sig,
    d_Grammar.FUNC:                   _func,
    d_Grammar.VOID:                   _illegal_expression,
    d_Grammar.LISTOF:                 _illegal_expression,
    d_Grammar.IMPORT:                 _import,
    d_Grammar.FROM:                   _illegal_expression,
    d_Grammar.PULL:                   _illegal_expression,
    d_Grammar.USE:                    _not_implemented,
    d_Grammar.STATIC:                 _not_implemented,
    d_Grammar.INST:                   _not_implemented,
    d_Grammar.THROW:                  _throw,
    d_Grammar.THROW:                  _illegal_expression,
    d_Grammar.RETURN:                 _illegal_expression,
    d_Grammar.NULL:                   _null,
    d_Grammar.TRUE:                   _bool,
    d_Grammar.FALSE:                  _bool,
    d_Grammar.PRIMITIVE_THING:        _illegal_expression,
    d_Grammar.PRIMITIVE_STR:          _illegal_expression,
    d_Grammar.PRIMITIVE_BOOL:         _illegal_expression,
    d_Grammar.PRIMITIVE_NUM:          _illegal_expression,
    d_Grammar.PRIMITIVE_JSON:         _illegal_expression,
    d_Grammar.PRIMITIVE_CLASS:        _illegal_expression,
    d_Grammar.PRIMITIVE_INST:         _illegal_expression,
    d_Grammar.PRIMITIVE_FUNC:         _illegal_expression,
    d_Grammar.PRIMITIVE_DIT:          _illegal_expression,
    d_Grammar.PRIMITIVE_LANG:         _illegal_expression,
    d_Grammar.WORD:                   _illegal_expression,
    d_Grammar.NEW_NAME:               _new_name,
    d_Grammar.DIGIT:                  _digit,
    d_Grammar.VALUE_NULL:             _value_equalable,
    d_Grammar.VALUE_THING:            _value_equalable,
    d_Grammar.VALUE_STR:              _value_equalable,
    d_Grammar.VALUE_BOOL:             _value_equalable,
    d_Grammar.VALUE_NUM:              _value_equalable,
    d_Grammar.VALUE_LIST:             _value_equalable,
    d_Grammar.VALUE_JSON:             _value_equalable,
    d_Grammar.VALUE_CLASS:            _value_class,
    d_Grammar.VALUE_INST:         _value_inst,
    d_Grammar.VALUE_FUNC:             _value_function,
    d_Grammar.VALUE_DIT:              _value_dit,
    d_Grammar.VALUE_LANG:             _value_lang,
    d_Grammar.EOF:                    _trigger_eof_err,
}
# fmt: on
