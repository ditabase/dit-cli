import os
from typing import List

import dit_cli.settings
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


def d_str(thing: d_Thing) -> str:
    if thing.is_null:
        return "null"
    elif isinstance(thing, d_String):
        return _ser_str(thing.string_value)
    elif isinstance(thing, d_List):
        return _ser_list(thing)
    elif isinstance(thing, d_Thing):  # type: ignore
        return _ser_obj(thing)
    else:
        raise CriticalError("Unrecognized argument for str()")


def d_print(func: d_Func) -> None:
    # TODO: The entire print stack is subject to change since we're switching to always
    # JSON serialization. We might just be able to use JSON.encode, or something similar
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
        return d_Grammar.NULL.value
    elif isinstance(thing, d_List):
        if len(thing.list_value) == 0:
            return "[]"
        value = "["
        for i in thing.list_value:
            # Serialize any depth of list by recursing
            value += _ser_list(i)
            value += ","
        # Replace last comma with ]
        value = value[:-1] + "]"
        return value
    elif isinstance(thing, d_String):
        return _ser_str(thing.string_value)
    elif isinstance(thing, d_Thing):  # type: ignore
        return _ser_obj(thing)
    else:
        raise CriticalError("Unrecognized argument for _ser_list()")


def _ser_str(str_: str) -> str:
    return str_


def _ser_obj(obj: d_Thing) -> str:
    raise NotImplementedError


def _get_config(func: d_Func) -> List[d_Dit]:
    path = os.path.abspath(dit_cli.settings.DIT_FILEPATH)
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
