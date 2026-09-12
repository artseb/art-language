"""`switch (value) { case a, b: ... else: ... }`, usable both as a
statement and as an expression (its value is the last expression
evaluated in whichever case body matched) - same AST either way, just
registered against both dispatch points below."""
from typing import TYPE_CHECKING

from ..tokens import TokenType, register_keyword
from ..parser.registry import stmt_parser, primary_parser
from ..interpreter.registry import exec_handler, eval_handler
from ..runtime import Environment
from .control_flow import Block
from .basics import ExpressionStmt
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("switch", TokenType.SWITCH)
register_keyword("case", TokenType.CASE)


class SwitchCase(Node):
    def __init__(self, values, body):
        self.values = values
        self.body = body

    def __repr__(self):
        return f"SwitchCase({self.values!r}, {self.body!r})"


class Switch(Node):
    def __init__(self, value, cases, default=None):
        self.value = value
        self.cases = cases
        self.default = default

    def __repr__(self):
        return f"Switch({self.value!r}, {self.cases!r}, default={self.default!r})"


# ---------- parsing ----------

@stmt_parser(TokenType.SWITCH)
@primary_parser(TokenType.SWITCH)
def _parse_switch(parser: "Parser"):
    parser._consume(TokenType.SWITCH, "Expected 'switch'")
    parser._consume(TokenType.LPAREN, "Expected '(' after switch")
    value = parser._expression()
    parser._consume(TokenType.RPAREN, "Expected ')' after switch value")
    parser._consume(TokenType.LBRACE, "Expected '{' before switch body")

    cases = []
    else_body = None
    found_else = False

    while not parser._check(TokenType.RBRACE) and not parser._at_end():
        if parser._match(TokenType.CASE):
            if found_else:
                raise parser._error("Case cannot appear after 'else' in switch", parser._previous())

            values = [parser._expression()]
            while parser._match(TokenType.COMMA):
                values.append(parser._expression())

            parser._consume(TokenType.COLON, "Expected ':' after case values")

            body = []
            while (
                not parser._check(TokenType.CASE)
                and not parser._check(TokenType.ELSE)
                and not parser._check(TokenType.RBRACE)
                and not parser._at_end()
            ):
                body.append(parser._declaration())

            cases.append(SwitchCase(values, Block(body)))

        elif parser._match(TokenType.ELSE):
            if found_else:
                raise parser._error("Duplicate 'else' in switch", parser._previous())
            found_else = True

            parser._consume(TokenType.COLON, "Expected ':' after 'else'")

            body = []
            while (
                not parser._check(TokenType.CASE)
                and not parser._check(TokenType.RBRACE)
                and not parser._at_end()
            ):
                body.append(parser._declaration())

            else_body = Block(body)

        else:
            raise parser._error("Expected 'case' or 'else' in switch", parser._peek())

    parser._consume(TokenType.RBRACE, "Expected '}' after switch body")
    return Switch(value, cases, else_body)


# ---------- interpreting ----------

def _find_matching_body(interp: "Interpreter", node: Switch, env):
    value = interp._eval(node.value, env)
    for case in node.cases:
        for case_value in case.values:
            evaluated = interp._eval(case_value, env)
            if interp._values_equal(value, evaluated):
                return case.body
    return node.default


@exec_handler(Switch)
def _exec_switch(interp: "Interpreter", node: Switch, env):
    body = _find_matching_body(interp, node, env)
    if body is not None:
        interp._exec(body, env)


@eval_handler(Switch)
def _eval_switch(interp: "Interpreter", node: Switch, env):
    body = _find_matching_body(interp, node, env)
    if body is None:
        return None

    block_env = Environment(env)
    result = None
    for stmt in body.statements:
        if isinstance(stmt, ExpressionStmt):
            result = interp._eval(stmt.expr, block_env)
        else:
            interp._exec(stmt, block_env)
    return result
