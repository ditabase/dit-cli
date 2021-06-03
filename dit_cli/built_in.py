import os
from typing import List

import dit_cli.settings
from dit_cli.grammar import d_Grammar
from dit_cli.oop import Declarable, d_Dit, d_Func, d_Lang

b_Ditlang = d_Lang()
b_Ditlang.name = "Ditlang"
b_Ditlang.is_built_in = True


def d_print(func: d_Func) -> None:
    # TODO: The entire print stack is subject to change since we're switching to always
    # JSON serialization. We might just be able to use JSON.encode, or something similar
    # The first attribute is the parameter we want.
    key, val = next(iter(func.attrs.items()))
    val = val.get_thing()
    print(val)


b_print = d_Func()
b_print.name = "print"
b_print.parameters = [Declarable(d_Grammar.PRIMITIVE_THING, "value")]
b_print.is_built_in = True
b_print.py_func = d_print
b_print.is_null = False
b_print.lang = b_Ditlang


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
b_get_config.lang = b_Ditlang


BUILT_INS = [b_print, b_get_config, b_Ditlang]
