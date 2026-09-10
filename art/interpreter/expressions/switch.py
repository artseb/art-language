"""`switch` used as an expression (its value is the last expression
evaluated in the matched case body). See interpreter/switching.py for
the case-matching/body-evaluation logic shared with the statement form
in statements/control_flow.py."""
from ...ast import Switch
from ..registry import eval_handler


@eval_handler(Switch)
def _eval_switch(interp, node, env):
    body = interp._find_switch_case(node, env)
    if body is not None:
        return interp._eval_switch_body(body, env)
    return None
