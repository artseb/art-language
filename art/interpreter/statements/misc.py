"""Leftover statement forms that don't fit a bigger theme: evaluating an
expression for its side effects, and `return`. (`print` used to live
here as a bespoke AST node/parser special-case; it's now an ordinary
builtin function call - see art/builtins/io.py - so there's no handler
for it at all anymore.)"""
from ...ast import ExpressionStmt, Return
from ...errors import ReturnSignal
from ..registry import exec_handler


@exec_handler(ExpressionStmt)
def _exec_expression_stmt(interp, node, env):
    interp._eval(node.expr, env)


@exec_handler(Return)
def _exec_return(interp, node, env):
    value = None
    if node.value is not None:
        value = interp._eval(node.value, env)
    raise ReturnSignal(value)
