"""The grammar's fallback forms: evaluating an expression for its side
effects, `return`, and local variable declarations (`local x = 1`,
`local a, b = 1, 2`).

Var-decl doesn't get a STMT_PARSERS/DECL_PARSERS entry because it has
no leading keyword of its own to key a table on - parser/core.py's
`_declaration()` recognizes it by lookahead (`local` already consumed,
or a bare `identifier =` / `identifier ,`) and calls `parse_var_decl`
directly. Everything downstream of that (the AST it builds, the exec
handler) still lives here with its siblings.
"""
from typing import TYPE_CHECKING

from ..tokens import TokenType, register_keyword
from ..parser.registry import stmt_parser
from ..interpreter.registry import exec_handler
from .base import Node
from .literals import Literal
from .variables import Assign

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("return", TokenType.RETURN)
register_keyword("local", TokenType.LOCAL)


class ExpressionStmt(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"ExpressionStmt({self.expr!r})"


class Return(Node):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Return({self.value!r})"


class MultiAssign(Node):
    def __init__(self, names, values, is_local=False):
        self.names = names
        self.values = values
        self.is_local = is_local

    def __repr__(self):
        return f"MultiAssign({self.names!r}, {self.values!r}, local={self.is_local})"


# ---------- parsing ----------

def parse_var_decl(parser: "Parser", is_local=False):
    names = [parser._consume(TokenType.IDENTIFIER, "Expected variable name").lexeme]

    while parser._match(TokenType.COMMA):
        names.append(parser._consume(TokenType.IDENTIFIER, "Expected variable name after ','").lexeme)

    values = []
    if parser._match(TokenType.EQUAL):
        values.append(parser._expression())
        while parser._match(TokenType.COMMA):
            values.append(parser._expression())

    if len(names) == 1:
        value = values[0] if values else Literal(None)
        return ExpressionStmt(Assign(names[0], value, is_local))

    return MultiAssign(names, values, is_local)


@stmt_parser(TokenType.RETURN)
def _parse_return_stmt(parser: "Parser"):
    parser._advance()
    value = None
    if not parser._check(TokenType.RBRACE):
        value = parser._expression()
    return Return(value)


# ---------- interpreting ----------

@exec_handler(ExpressionStmt)
def _exec_expression_stmt(interp: "Interpreter", node: ExpressionStmt, env):
    interp._eval(node.expr, env)


@exec_handler(Return)
def _exec_return(interp: "Interpreter", node: Return, env):
    from ..errors import ReturnSignal
    value = None
    if node.value is not None:
        value = interp._eval(node.value, env)
    raise ReturnSignal(value)


@exec_handler(MultiAssign)
def _exec_multi_assign(interp: "Interpreter", node: MultiAssign, env):
    values = []
    for expr in node.values:
        value = interp._eval(expr, env)
        if isinstance(value, tuple):
            values.extend(value)
        else:
            values.append(value)

    for index, name in enumerate(node.names):
        value = values[index] if index < len(values) else None

        if name == "_":
            continue

        if node.is_local:
            env.define(name, value)
        else:
            env.assign_existing_or_global(name, value)
