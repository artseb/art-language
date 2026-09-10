"""Literal values: numbers/strings/booleans/nil (already collapsed to a
plain Python value by the parser) and table literals `[1, 2, "k" = v]`."""
from ...ast import Literal, TableLiteral
from ...runtime import LangTable
from ..registry import eval_handler


@eval_handler(Literal)
def _eval_literal(interp, node, env):
    return node.value


@eval_handler(TableLiteral)
def _eval_table_literal(interp, node, env):
    table = LangTable()
    for key_expr, value_expr in node.entries:
        value = interp._eval(value_expr, env)
        if key_expr is None:
            table.append(value)
        else:
            key = interp._eval(key_expr, env)
            table.set(key, value)
    return table
