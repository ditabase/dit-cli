from dit_cli.grammar import d_Grammar
from dit_cli.interpret_context import CharFeed, InterpretContext
from dit_cli.oop import d_Func
from dit_cli.settings import CodeLocation

SHAPES = [
    d_Grammar.TRI_LEFT,
    d_Grammar.TRI_RIGHT,
    d_Grammar.CIR_LEFT,
    d_Grammar.CIR_RIGHT,
]

DIT_SHAPES = [
    d_Grammar.TRI_RIGHT,
    d_Grammar.CIR_LEFT,
]

GUEST_SHAPES = [
    d_Grammar.TRI_LEFT,
    d_Grammar.CIR_RIGHT,
]


class PreProcessContext:
    def __init__(self, func: d_Func) -> None:
        self.char_feed = CharFeed(func.view, CodeLocation(0, 0, 0))
        self.depth: int = 0
        self.func: d_Func = func
        self.prev_loc: int = 0


def preprocess(func: d_Func) -> None:
    """Converts func.view into a prepared GuestLang function and writes it to a file."""
    # <|return (|parseFloat(<|num1;|>) + parseFloat(<|num2|>)|);|>
    # turns into...
    # exe_ditlang("return " + parseFloat(exe_ditlang('num1')) +
    #                         parseFloat(exe_ditlang('num2')) + ";")

    # A triangle <||> expression always calls back to Ditlang to be executed.
    # This means it can contain any code in any style or order.
    # A circle (||) expression guestLang code, and must equate to a string
    # A circle can only be inside a triangle. A circle must contat the dit code on
    # either side and execute the entire resulting string as dit code.
    if len(func.view) == 0:
        return
    func.code = bytearray()
    proc = PreProcessContext(func)

    _recurse_section(proc)
    function_wrap_left = func.lang.get_prop("function_wrap_left")
    function_wrap_right = func.lang.get_prop("function_wrap_right")
    export_string = func.lang.get_prop("export_string")
    output: str = (
        function_wrap_left
        + func.code.decode()
        + "\n"
        + function_wrap_right
        + "\n\n"
        + export_string
    )
    file_extension = func.lang.get_prop("file_extension")
    func.guest_func_path = (
        "/tmp/dit/" + func.lang.name + "_func_" + func.name + "." + file_extension
    )
    open(func.guest_func_path, "w").write(output)


def _recurse_section(proc: PreProcessContext) -> None:
    while True:

        proc.char_feed.pop()
        if proc.char_feed.eof():
            proc.func.code += proc.func.view[proc.prev_loc : proc.char_feed.loc.pos]
            return

        cur = proc.char_feed.current() + proc.char_feed.peek()
        if cur == d_Grammar.TRI_LEFT.value:
            if _in_guest_lang(proc.depth):
                add_section(proc, "triangle_expr_left")
                proc.depth += 1
            else:
                raise NotImplementedError
        elif cur == d_Grammar.TRI_RIGHT.value:
            if not _in_guest_lang(proc.depth):
                add_section(proc, "triangle_expr_right")
                proc.depth -= 1
            else:
                raise NotImplementedError
        elif cur == d_Grammar.CIR_LEFT.value:
            if not _in_guest_lang(proc.depth):
                add_section(proc, "circle_expr_left")
                proc.depth += 1
            else:
                raise NotImplementedError
        elif cur == d_Grammar.CIR_RIGHT.value:
            if _in_guest_lang(proc.depth):
                add_section(proc, "circle_expr_right")
                proc.depth -= 1
            else:
                raise NotImplementedError


def add_section(proc: PreProcessContext, prop: str):
    proc.func.code += (
        bytes(proc.func.view[proc.prev_loc : proc.char_feed.loc.pos])
        + _get_dit_line_ender(proc, prop)
        + proc.func.lang.get_prop(prop).encode()
        + _get_lang_line_ender(proc, prop)
    )
    proc.prev_loc = proc.char_feed.loc.pos + 2


def _get_dit_line_ender(proc: PreProcessContext, prop: str) -> bytes:
    # The last statement in a triangle expression is not required to have a semicolon.
    # This is so that short statements don't look overly cluttered.
    # A ! will be treated as a correct line ender, whether or not a semi was present.
    # <|counter|> --> counter!
    # <|counter;|> --> counter;!
    # Both are correct.
    return d_Grammar.POINT.value.encode() if prop == "triangle_expr_right" else b""


def _get_lang_line_ender(proc: PreProcessContext, prop: str) -> bytes:
    # Some languages can have explicit line enders added after
    if prop == "triangle_expr_right" and proc.depth == 1:
        if proc.func.lang.get_prop("add_line_enders") == "true":
            return proc.func.lang.get_prop("line_ender").encode()

    return b""


def _in_guest_lang(depth: int) -> bool:
    # Suppose a guest func with very deep shape expressions.
    # The numbers note the depth of the expression.
    # { 0 <| 1 (|2 <|3 (|4 <|5|> 4|) 3|> 2|) 1 |> 0 } EOF
    # 0, 2, 4 etc are a guestlang. 1, 3, 5 etc are Ditlang
    # so we're in a guestLang if the depth is even
    return depth % 2 == 0
