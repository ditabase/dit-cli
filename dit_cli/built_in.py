import os
from typing import List

import dit_cli.config
from dit_cli.exceptions import CriticalError
from dit_cli.grammar import d_Grammar
from dit_cli.oop import (
    Declarable,
    d_Dit,
    d_Func,
    d_Lang,
    d_List,
    d_Ref,
    d_String,
    d_Thing,
)

JAVASCRIPT = {
    "name": "Javascript",
    "path": "/usr/bin/node",
    "socket": "dit_cli/client_daemons/js_daemon.js",
    "function_string": "function run() {@@CODE}\\n",
    "call_string": "module.exports: {\\nrun\\n};",
    "null_type": "null",
    "str_open": '"',
    "str_close": '"',
    "str_escape": "\\",
    "str_newline": "\\n",
    "str_tab": "\\t",
    "list_open": "[",
    "list_delimiter": ",",
    "list_close": "]",
    "obj_open": "{",
    "obj_colon": ":",
    "obj_delimiter": ",",
    "obj_close": "}",
}

PRINT = {
    "name": "Print",
    "path": None,
    "socket": None,
    "function_string": None,
    "call_string": None,
    "null_type": "null",
    "str_open": None,
    "str_close": None,
    "str_escape": "\\",
    "str_newline": "\\n",
    "str_tab": "\\t",
    "list_open": "[",
    "list_delimiter": ",",
    "list_close": "]",
    "obj_open": "{",
    "obj_colon": ":",
    "obj_delimiter": ",",
    "obj_close": "}",
}

LANG = PRINT


def d_str(thing: d_Thing) -> str:
    if thing.is_null:
        return LANG["null_type"]
    elif isinstance(thing, d_String):
        return _ser_str(thing.string_value)
    elif isinstance(thing, d_List):
        return _ser_list(thing)
    elif isinstance(thing, d_Thing):  # type: ignore
        return _ser_obj(thing)
    else:
        raise CriticalError("Unrecognized argument for str()")


def d_print(func: d_Func) -> None:
    # The first attribute is the parameter we want.
    val = func.attrs[0]
    if isinstance(val, d_Ref):
        val = val.target
    print(d_str(val))


b_print = d_Func()
b_print.name = "print"
b_print.parameters = [Declarable(d_Grammar.PRIMITIVE_THING, "value")]
b_print.is_built_in = True
b_print.py_func = d_print
b_print.is_null = False


def _ser_list(thing: d_Thing) -> str:
    if thing.is_null:
        return LANG["null_type"]
    elif isinstance(thing, d_List):
        if len(thing.list_value) == 0:
            return LANG["list_open"] + LANG["list_close"]
        value = LANG["list_open"]
        for i in thing.list_value:
            # Serialize any depth of list by recursing
            value += _ser_list(i)
            value += LANG["list_delimiter"]
        # Replace last comma with ]
        value = value[:-1] + LANG["list_close"]
        return value
    elif isinstance(thing, d_String):
        return _ser_str(thing.string_value)
    elif isinstance(thing, d_Thing):  # type: ignore
        return _ser_obj(thing)
    else:
        raise CriticalError("Unrecognized argument for _ser_list()")


def _ser_str(str_: str) -> str:
    if LANG["str_escape"] in str_:
        str_ = str_.replace(LANG["str_escape"], LANG["str_escape"] + LANG["str_escape"])

    if "\n" in str_:
        str_ = str_.replace("\n", LANG["str_newline"])

    if "\t" in str_:
        str_ = str_.replace("\t", LANG["str_tab"])

    if LANG["str_open"] is not None:
        if LANG["str_open"] in str_:
            str_ = str_.replace(LANG["str_open"], LANG["str_escape"] + LANG["str_open"])

    if LANG["str_open"] != LANG["str_close"] and LANG["str_close"] in str_:
        str_ = str_.replace(LANG["str_close"], LANG["str_escape"] + LANG["str_close"])

    if LANG["str_open"] is not None:
        str_ = LANG["str_open"] + str_

    if LANG["str_close"] is not None:
        str_ = str_ + LANG["str_close"]

    return str_


def _ser_obj(obj: d_Thing) -> str:
    raise NotImplementedError


def _get_config(func: d_Func) -> List[d_Dit]:
    path = os.path.abspath(dit_cli.config.DIT_FILEPATH)
    directory = os.path.dirname(path)
    dits: List[d_Dit] = []
    while True:
        if os.path.isfile(directory + "/.ditconf"):
            dit = d_Dit()
            dit.path = directory + "/.ditconf"
            dit.is_null = False
            dit.name = "ditconf"
            dit.finalize()
            dits.append(dit)

        if directory == "/":
            break
        directory = os.path.dirname(directory)
    return dits


b_get_config = d_Func()
b_get_config.name = "getConfig"
b_get_config.parameters = []
b_get_config.is_built_in = True
b_get_config.py_func = _get_config
b_get_config.is_null = False


b_Ditlang = d_Lang()
b_Ditlang.name = "Ditlang"
b_Ditlang.is_built_in = True


BUILT_INS = [b_print, b_get_config, b_Ditlang]
