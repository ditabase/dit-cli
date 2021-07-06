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
    ReturnController,
    Token,
    check_value,
    d_Body,
    d_Bool,
    d_Class,
    d_Container,
    d_Dit,
    d_Func,
    d_Instance,
    d_JSON,
    d_Lang,
    d_List,
    d_Num,
    d_Str,
    d_Thing,
    d_Type,
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
        _generate_origin(err, inter)
        raise
    return last_ret


def _generate_origin(
    err: d_DitError, inter: InterpretContext, loc: Optional[CodeLocation] = None
) -> None:
    if err.origin is not None:
        return
    if loc is None:
        loc = inter.char_feed.loc
    code = inter.char_feed.get_line(loc)
    if inter.body.path is None:
        raise d_CriticalError("A body had no path during exception")
    err.set_origin(inter.body.path, loc, code)


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
    if inter.anon_tok:
        func = EXPRESSION_DISPATCH[inter.anon_tok.grammar]
    elif inter.call_tok:
        func = EXPRESSION_DISPATCH[inter.call_tok.grammar]
    else:
        func = EXPRESSION_DISPATCH[inter.next_tok.grammar]
    return func(inter)


def _listof(inter: InterpretContext) -> None:
    # listOf Str values;
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
        raise d_SyntaxError("Expected type for listOf declaration", inter)


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
    if inter.declaring_func is not None:
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
        # lang JavaScript {{}}
        # Lang JavaScript ...
        return
    elif inter.next_tok.grammar in VALUE_CLANG_ABLES:
        # someClass = someOtherClass;
        # someLang.someLangFunc();
        # This class is being dotted, equaled, etc.
        return _dotable(inter)
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
    # Str test ...
    # someClass test ...
    # Str someDotable.monkeyPatch ...
    # This function is reused by _primitive and _value_class
    inter.dec.type_ = _token_to_type(inter.curr_tok)
    if inter.next_tok.grammar in DUPLICABLES:
        raise d_SyntaxError(
            f"'{inter.next_tok.thing.name}' has already been declared", inter
        )
    if inter.next_tok.grammar in NAMEABLES:
        _expression_dispatch(inter)
    else:
        raise d_SyntaxError("Expected a new name to follow type", inter)

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
        raise d_SyntaxError(f"'{inter.next_tok.grammar}' is not dotable", inter)
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
    if (
        isinstance(inter.curr_tok.thing, d_Lang)
        and inter.prev_tok.grammar == d_Grammar.PRIMITIVE_LANG
    ):
        # Since Langs can be redeclared, we just remove the type_
        # and pretend it was never there in the first place.
        # Lang JavaScript ...
        inter.dec.type_ = None  # type: ignore
    if inter.dec.type_ is not None and inter.dec.name is None:
        # _new_name should have been found, not an existing variable.
        # Str existingValue ...
        raise d_SyntaxError(
            f"'{inter.curr_tok.thing.name}' has already been declared", inter
        )
    elif inter.next_tok.grammar == d_Grammar.EQUALS:
        # Assign existing or new variables
        # Str value = ...
        _equals(inter)
        inter.dec.reset()
    elif inter.dec.type_ is not None and not inter.equaling:
        # create variable without assignment
        # Str count;
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
    inter.equaling = True
    value = _expression_dispatch(inter)
    inter.equaling = False
    if value is None:
        if inter.named_statement:
            # Prevent assignment of non-anonymous statements.
            # Class anonName = class RealName {{}}
            raise d_SyntaxError(
                "A named declaration cannot be used for assignment", inter, orig_loc
            )
        else:
            raise d_CriticalError("No value for _expression_dispatch in _equals")
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
    # someTriangleVar! (the exclamation point is inserted by the preprocessor)
    if inter.next_tok.grammar not in [
        d_Grammar.SEMI,
        d_Grammar.COMMA,
        d_Grammar.BRACKET_RIGHT,
        d_Grammar.PAREN_RIGHT,
        d_Grammar.POINT,
    ]:
        if inter.declaring_func is not None or inter.in_json:
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


def _point(inter: InterpretContext) -> None:
    # If a semicolon and exclamation point are both present, this will allow
    # the point to pass safely
    # <|return 1|> -> return 1!
    # <|return 1;|> -> return 1;!
    # Notice the point is by itself, and will be run as a statement.
    pass


def _new_name(inter: InterpretContext) -> None:
    inter.dec.name = inter.next_tok.word
    if inter.dec.type_ is None:
        # new name without a type declaration is only allowed with an equals
        # unknownName = ...
        inter.advance_tokens()
        if inter.next_tok.grammar != d_Grammar.EQUALS:
            raise d_NameError(
                f"Undefined variable '{inter.curr_tok.word}'",
                inter,
                inter.curr_tok.loc,
            )
        # if there is an equals, then we just pretend the declaration was 'Thing'
        inter.dec.type_ = d_Grammar.PRIMITIVE_THING
        _equals(inter)
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
                raise d_SyntaxError("Unexpected EOL while reading string", inter, lok)
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
            inter,
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
            if lead_zero and len(num) == 1:
                raise d_SyntaxError("Leading zeros are not allowed", inter)
            num += cur
            inter.char_feed.pop()
            lead_zero = False
        elif cur == ".":
            if frac == True:
                raise d_SyntaxError("Invalid fraction syntax", inter)
            num += cur
            inter.char_feed.pop()
            frac == True
        elif cur == "e" or cur == "E":
            if exp == True:
                raise d_SyntaxError("Invalid exponent syntax", inter)
            num += cur
            inter.char_feed.pop()
            exp == True
        elif cur == "-" or cur == "+":
            num += cur
            inter.char_feed.pop()
        else:
            break
    inter.advance_tokens()
    fin_num = d_Num()
    fin_num.is_null = False
    fin_num.num = float(num)
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
                raise d_SyntaxError("Expected ','", inter, inter.curr_tok.loc)
            name = _str(inter).str_
            if inter.next_tok.grammar != d_Grammar.COLON:
                raise d_SyntaxError("Expected ':'", inter, inter.next_tok.loc)
            else:
                inter.advance_tokens()
            ele = _expression_dispatch(inter)
            js.json_[name] = ele
        elif inter.next_tok.grammar == d_Grammar.COMMA:
            # JSON j = { "item1": 1, ...
            inter.advance_tokens()
            if inter.next_tok.grammar == d_Grammar.BRACE_RIGHT:
                raise d_SyntaxError(
                    "Trailing commas are not allowed", inter, inter.curr_tok.loc
                )
        else:
            raise d_SyntaxError("Unexpected token for JSON", inter)


def _paren_left(inter: InterpretContext) -> Optional[d_Thing]:
    if inter.anon_tok is not None:
        func: d_Func = inter.anon_tok.thing  #  type: ignore
    elif inter.call_tok is not None:
        func: d_Func = inter.call_tok.thing  #  type: ignore
    elif isinstance(inter.curr_tok.thing, d_Class):
        # This means we must be instantiating, and need the Make func
        # Number num = Number('3');
        func = _make(inter)
    else:
        func: d_Func = inter.curr_tok.thing  #  type: ignore

    if inter.dotted_inst is not None:
        # We are activating a function of this instance, so the func needs 'this'
        # Subject to change when static functions are implemented
        # num.inc();
        func.add_attr(
            Declarable(inter.dotted_inst.parent, THIS), inter.dotted_inst, use_ref=True
        )

    func.call_loc = copy.deepcopy(inter.curr_tok.loc)
    arg_locs = _arg_list(inter, d_Grammar.PAREN_RIGHT)
    func_name = f"{func.name}()" if func.name is not None else "<anonymous function>()"
    miss = abs(len(func.parameters) - len(arg_locs))

    for param, arg_loc in zip_longest(func.parameters, arg_locs):
        param: Declarable
        arg_loc: ArgumentLocation
        if arg_loc is None:
            raise d_SyntaxError(f"{func_name} missing {miss} required arguments", inter)
        elif param is None:
            # TODO: implement proper k-args functionality
            raise d_SyntaxError(f"{func_name} given {miss} too many arguments", inter)
        else:
            res = check_value(arg_loc.thing, param)
            if res is not None:
                raise d_SyntaxError(
                    f"{func_name} expected '{res.expected}', got '{res.actual}'",
                    inter,
                    arg_loc.loc,
                )

        func.add_attr(param, arg_loc.thing, use_ref=True)
    if func.code is None and func.lang is not b_Ditlang:
        preprocess(func)
    try:
        if func.is_built_in:
            if func.name == "getConfig":
                _handle_get_config(inter, func)
            else:
                func.py_func(func)
        elif func.lang is b_Ditlang:
            interpret(func)
        else:
            if func.code is None:
                raise ReturnController(d_Thing.get_null_thing(), func, func.call_loc)
            job = GuestDaemonJob(JobType.CALL_FUNC, func)
            while True:
                res = run_job(job)
                if res.type_ == JobType.FINISH_FUNC:
                    break
                elif res.type_ == JobType.EXE_DITLANG:
                    mock_func = func.get_mock(res.result)  # type: ignore
                    value = interpret(mock_func)
                    job.type_ = JobType.DITLANG_CALLBACK
                    if value is None:
                        pass
                    elif isinstance(
                        value, (d_Thing, d_Bool, d_Num, d_Str, d_List, d_JSON)
                    ):
                        job.result = value.get_data()  # type: ignore
                    else:
                        raise NotImplementedError

    except d_CodeError as err:
        err.set_origin(
            inter.body.path, func.call_loc, inter.char_feed.get_line(func.call_loc)
        )
        raise err
    except d_DitError as err:
        err.add_trace(func.path, func.call_loc, func.name)
        raise err
    except ReturnController as ret:
        inter.call_tok = ret.token
    except d_TypeMismatchError as mis:
        raise NotImplementedError
    else:
        if func.return_ is not None and func.return_ != d_Grammar.VOID:
            raise d_SyntaxError(f"{func_name} expected a return", inter, func.call_loc)
        elif func.name == MAKE:
            thing = func.find_attr(THIS)
            if thing is None:
                raise NotImplementedError
            inter.call_tok = Token(d_Grammar.VALUE_INSTANCE, func.call_loc, thing=thing)
        else:
            # func ended without 'return' keyword
            inter.call_tok = Token(d_Grammar.NULL, func.call_loc)

    func.attrs.clear()
    inter.dotted_inst = None  # type: ignore
    if inter.call_tok.grammar == d_Grammar.NULL:
        return _terminal(inter)
    else:
        return _parenable(inter)


def _handle_get_config(inter: InterpretContext, getConfig: d_Func) -> None:
    # Load the .ditconf files from cwd to root
    config_files: List[d_Dit] = getConfig.py_func(getConfig)
    if config_files is None:
        raise NotImplementedError
    for dit in config_files:
        # interpret each file
        interpret(dit)

        for name in dit.attrs:
            conf_lang = dit.attrs[name].get_thing()
            if isinstance(conf_lang, d_Lang):
                # for each lang in the conf file
                local_lang = inter.body.find_attr(name)
                if local_lang is not None:
                    # If they exit both places, merge them
                    local_lang.set_value(conf_lang)
                else:
                    # or just put the conf lang here
                    inter.body.attrs[name] = conf_lang


def _make(inter: InterpretContext) -> d_Func:
    class_: d_Class = inter.curr_tok.thing  # type: ignore
    make = class_.find_attr(MAKE)
    if make is None:
        raise d_SyntaxError(f"Class '{class_.name}' does not define a Make", inter)
    elif isinstance(make, d_Func):
        func: d_Func = make
        inst = d_Instance()
        inst.is_null = False
        inst.parent = class_
        func.add_attr(Declarable(class_, THIS), inst, use_ref=True)
        return func
    else:
        raise NotImplementedError


def _return(inter: InterpretContext) -> NoReturn:
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    if not isinstance(inter.body, d_Func):
        raise d_SyntaxError("'return' outside of function", inter)
    inter.advance_tokens()
    value = _expression_dispatch(inter)
    if value is None:
        raise NotImplementedError
    try:
        raise ReturnController(value, inter.body, orig_loc)
    except d_TypeMismatchError as mis:
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
        if arg is None:
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
        raise d_SyntaxError("Expected a name or filepath string for import", inter)

    if gra == d_Grammar.WORD:
        # import SomeName from "someFilePath.dit";
        if inter.body.find_attr(inter.next_tok.word, scope_mode=True):
            raise d_SyntaxError(
                f"'{inter.next_tok.word}' has already been declared", inter
            )
        name = inter.next_tok.word
        inter.advance_tokens()
        if inter.next_tok.grammar != d_Grammar.FROM:
            raise d_SyntaxError("Expected 'from'", inter)
        inter.advance_tokens()

    dit = _import_or_pull(inter, orig_loc)
    dit.name = name  # type: ignore

    # handled slightly differently from other bodies.
    # import always ends with a semicolon, even with a name.
    anon = _handle_anon(inter, dit, orig_loc)
    if anon is not None:
        return anon  # type: ignore
    else:
        # Thus, this explicit call to _terminal.
        _terminal(inter)


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
            raise d_SyntaxError("Expected name to pull from linked dit", inter)
        # pull NAME ...
        target = inter.next_tok.word
        loc = copy.deepcopy(inter.next_tok.loc)
        replacement = None
        inter.advance_tokens()
        if inter.next_tok.grammar == d_Grammar.AS:
            # pull NAME as ...
            inter.advance_tokens(False)
            if inter.next_tok.grammar != d_Grammar.WORD:
                raise d_SyntaxError("Expected name to replace target name", inter)
            replacement = inter.next_tok.word
            loc = inter.next_tok.loc
            inter.advance_tokens()

        name = replacement if replacement is not None else target
        result = inter.body.find_attr(name, True)
        if result is not None:
            if isinstance(result, d_Lang):
                # Langauges can overwrite langs already in this dit
                # lang someLang {{}}
                # pull someLang from LINK
                langs.append(result)
            else:
                raise d_SyntaxError(f"'{name}' has already been declared", inter, loc)
        else:
            langs.append(None)
        targets.append((target, replacement))

        if inter.next_tok.grammar == d_Grammar.FROM:
            break
        elif inter.next_tok.grammar == d_Grammar.COMMA:
            continue
        else:
            raise d_SyntaxError("Expected 'from' or ',' to follow target", inter)

    inter.advance_tokens()
    dit = _import_or_pull(inter, orig_loc)
    for (target, replacement), lang in zip(targets, langs):
        result = dit.find_attr(target)
        if result is None:
            raise d_SyntaxError(f"'{target}' is not a valid member of this dit", inter)
        result.name = replacement if replacement is not None else target
        if lang is not None:
            # explicit call to set_value, to activate Priority comparisons
            lang.set_value(result)
        else:
            inter.body.attrs[result.name] = result


def _import_or_pull(inter: InterpretContext, orig_loc: CodeLocation) -> d_Dit:
    # The next token is always the link. We just need to get the dit and return it.
    # import LINK
    # import NAMESPACE from LINK
    # pull ... from LINK
    dit = d_Dit()
    dit.is_null = False
    if inter.next_tok.grammar in [d_Grammar.NULL, d_Grammar.VALUE_NULL]:
        raise d_SyntaxError("Cannot import from null", inter)
    elif inter.next_tok.grammar not in STRINGABLES:
        raise d_SyntaxError("Expected a filepath string for import", inter)

    value = _expression_dispatch(inter)
    if inter.dec.name is not None and not inter.equaling:
        dit.path = inter.dec.name
        inter.dec.name = None  # type: ignore
    elif value is None:
        raise NotImplementedError
    elif isinstance(value, d_Str):
        dit.path = value.str_
    else:
        raise d_SyntaxError(f"Expected str value, not {value.public_type}", inter)

    dit.finalize()
    try:
        interpret(dit)
    except d_DitError as err:
        err.add_trace(dit.path, orig_loc, "import")
        raise
    return dit


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
    # class/lang NAME {{}}
    # class/lang {{}}; <- Anonymous version
    lang = None
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    clang_name = "class" if isinstance(clang, d_Class) else "lang"

    inter.advance_tokens(False)
    if inter.next_tok.grammar not in [d_Grammar.WORD, d_Grammar.BAR_BRACE_LEFT]:
        raise d_SyntaxError(f"Expected name or body to follow {clang_name}", inter)

    if inter.next_tok.grammar == d_Grammar.WORD:
        result = inter.body.find_attr(inter.next_tok.word, scope_mode=True)
        if result is not None:
            if isinstance(result, d_Lang):
                # Langs are allowed to be redeclared
                # lang someLang {{}}
                # lang someLang {{}}
                lang = result
            else:
                raise d_SyntaxError(
                    f"'{inter.next_tok.word}' has already been declared", inter
                )
        clang.name = inter.next_tok.word
        inter.advance_tokens()  # get {{
        if inter.next_tok.grammar != d_Grammar.BAR_BRACE_LEFT:
            raise d_SyntaxError(f"Expected a {clang_name} body", inter)

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
        if func.return_list and func.return_ is None:
            # sig ... listOf ...
            if gra == d_Grammar.VOID:
                raise d_SyntaxError("Cannot have listOf void", inter)
            elif gra not in TYPES and gra not in DOTABLES:
                raise d_SyntaxError(
                    "Expected type to follow listOf", inter, dotable_loc
                )
            elif gra in DOTABLES:
                dotable_loc = copy.deepcopy(inter.next_tok.loc)

        if gra == d_Grammar.FUNC:
            return _func(inter)
        elif gra == d_Grammar.EOF or None not in switches:
            raise d_SyntaxError("Expected 'func' to follow sig", inter)
        elif thing is not None:
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
            if func.return_ is not None:
                raise d_SyntaxError("Unexpected 'listOf' after type", inter)
            func.return_list = True
        else:
            raise d_SyntaxError("Unrecognized token for signature", inter)


def _sig_thing_handler(inter: InterpretContext, func: d_Func) -> None:
    thing = _expression_dispatch(inter)
    if thing is None:
        raise NotImplementedError
    elif isinstance(thing, d_Lang):
        if func.lang is not None:
            raise d_SyntaxError("Language was already assigned", inter)
        func.lang = thing
    elif isinstance(thing, d_Class):
        _sig_assign_return(inter, func)
        func.return_ = thing
    else:
        mes = (
            "Expected Class or Lang, "
            f"'{thing.name}' is of type '{thing.public_type}'"
        )
        raise d_SyntaxError(mes, inter, inter.terminal_loc)


def _sig_assign_return(inter: InterpretContext, func: d_Func) -> None:
    if func.return_ is not None:
        raise d_SyntaxError("Return type was already assigned", inter)
    func.return_list = False if func.return_list is None else func.return_list


def _func(inter: InterpretContext) -> Optional[d_Func]:
    # func test(Str right, Str left) {{}}
    # func () {{}}
    orig_loc = copy.deepcopy(inter.next_tok.loc)
    func = _sig_or_func(inter)
    if func.return_ is None:
        func.return_ = d_Grammar.VOID
    if func.return_list is None:
        func.return_list = False
    if func.lang is None:
        func.lang = b_Ditlang
    inter.advance_tokens(False)
    if inter.next_tok.grammar == d_Grammar.WORD:
        # func someName
        result: d_Thing = inter.body.find_attr(inter.next_tok.word, scope_mode=True)  # type: ignore
        if result:
            raise d_SyntaxError(f"'{result.name}' has already been declared", inter)
        else:
            func.name = inter.next_tok.word
            # Advance only if the name was there
            # If no name, then this is an anonymous function
            inter.advance_tokens()

    if inter.next_tok.grammar != d_Grammar.PAREN_LEFT:
        # func Ditlang void someName(
        raise d_SyntaxError("Expected parameter list", inter)

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
                param_type = _token_to_type(inter.next_tok)
            else:
                mes = (
                    "Expected class for parameter type, "
                    f"'{result.name}' is of type '{result.public_type}'"
                )
                raise d_SyntaxError(mes, inter, inter.terminal_loc)
        elif inter.next_tok.grammar in PRIMITIVES:
            # someName(d_String
            param_type = _token_to_type(inter.next_tok)
        else:
            raise d_SyntaxError("Expected parameter type", inter)

        inter.advance_tokens(False)
        if inter.next_tok.grammar != d_Grammar.WORD:
            raise d_SyntaxError("Expected parameter name", inter)
        else:
            # someName(d_String someParam
            param_name = inter.next_tok.word
            result: d_Thing = inter.body.find_attr(param_name, scope_mode=True)  # type: ignore
            if result:
                raise d_SyntaxError(f"'{param_name}' has already been declared", inter)
            elif param_name in [p.name for p in func.parameters]:
                raise d_SyntaxError(
                    f"'{param_name}' is already a parameter name", inter
                )
        func.parameters.append(Declarable(param_type, param_name, param_list))

        inter.advance_tokens()
        _trailing_comma(inter, d_Grammar.PAREN_RIGHT)

    if inter.next_tok.grammar != d_Grammar.BAR_BRACE_LEFT:
        raise d_SyntaxError("Expected function body", inter)

    _bar_brace_left(inter, func)
    func.finalize()
    inter.declaring_func = None  # type: ignore
    return _handle_anon(inter, func, orig_loc)  # type: ignore


def _sig_or_func(inter: InterpretContext) -> d_Func:
    # sig Python Str ...
    # OR
    # func hello() {{}}
    if inter.declaring_func is None:
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
    if anon_body.name is not None:
        # traditional statement, stop here
        if lang is not None and isinstance(anon_body, d_Lang):
            # a language is being redeclared, must call set_value to
            # activate priority comparison stuff
            lang.set_value(anon_body)
        else:
            inter.body.attrs[anon_body.name] = anon_body
        inter.named_statement = True
        return None
    else:
        # anonymous expression, need to dispatch it
        inter.anon_tok = Token(anon_body.grammar, orig_loc, thing=anon_body)
        return _expression_dispatch(inter)  # type: ignore


def _missing_terminal(inter: InterpretContext, message: str) -> NoReturn:
    tok = inter.curr_tok
    target = tok.loc
    line = inter.char_feed.get_line(target)

    if isinstance(tok.grammar.value, str):
        length = len(tok.grammar.value)  # class, Str, =
    elif tok.thing is not None:
        length = len(tok.thing.name)  # Object names
    else:
        length = len(tok.word)  # New Names

    # Shift locaton to end of token
    target.pos += length
    target.col += length

    err = d_SyntaxError(message)
    err.set_origin(inter.body.path, target, line)
    raise err


def _trigger_eof_err(inter: InterpretContext) -> NoReturn:
    inter.char_feed.pop()
    raise d_CriticalError("EOF reached, but failed to trigger")


def _not_implemented(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("This keyword is reserved for later development", inter)


def _illegal_statement(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("Illegal start of statement", inter)


def _illegal_expression(inter: InterpretContext) -> NoReturn:
    raise d_SyntaxError("Illegal start of expression", inter)


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
    d_Grammar.INSTANCE:               _not_implemented,
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
    d_Grammar.PRIMITIVE_INSTANCE:     _primitive,
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
    d_Grammar.VALUE_INSTANCE:         _value_instance,
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
    d_Grammar.INSTANCE:               _not_implemented,
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
    d_Grammar.PRIMITIVE_INSTANCE:     _illegal_expression,
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
    d_Grammar.VALUE_INSTANCE:         _value_instance,
    d_Grammar.VALUE_FUNC:             _value_function,
    d_Grammar.VALUE_DIT:              _value_dit,
    d_Grammar.VALUE_LANG:             _value_lang,
    d_Grammar.EOF:                    _trigger_eof_err,
}
# fmt: on
