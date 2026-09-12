"""Binary and unary operators: the precedence ladder (or -> and ->
equality -> comparison -> term -> factor -> unary -> postfix/primary),
operator-overload dispatch to a class's `operator ==` etc. methods, and
the numeric-operand type checks. Precedence is one interlocking system,
so - unlike most other features - it isn't split further; the parsing
side and the interpreting side for +,-,*,/,and,or,==,!=,<,<=,>,>= all
live in this one file together.

`parse_or` and `parse_equality` are the two entry points other files
need: `parse_or` is "a full expression, minus assignment" (used by
parser/core.py's `_assignment()`), and `parse_equality` is a
narrower slice used by table literals (see literals.py) so that the
'=' in `["key" = value]` isn't swallowed as a comparison chain.
"""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType, register_keyword
from ..runtime import LangInstance, stringify
from ..interpreter.registry import eval_handler
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("and", TokenType.AND)
register_keyword("or", TokenType.OR)

_ARITHMETIC_OPS = {"+", "-", "*", "/"}
_COMPARISON_OPS = {"<", "<=", ">", ">="}


class Binary(Node):
    def __init__(self, left, op, right):
        super().__init__(op)
        self.left = left
        self.op = op  # Token
        self.right = right

    def __repr__(self):
        return f"Binary({self.left!r} {self.op.lexeme} {self.right!r})"


class Unary(Node):
    def __init__(self, op, right):
        super().__init__(op)
        self.op = op  # Token
        self.right = right

    def __repr__(self):
        return f"Unary({self.op.lexeme}{self.right!r})"


# ---------- parsing (precedence ladder) ----------

def parse_or(parser: "Parser"):
    expr = _parse_and(parser)
    while parser._match(TokenType.OR):
        op = parser._previous()
        right = _parse_and(parser)
        expr = Binary(expr, op, right)
    return expr


def _parse_and(parser: "Parser"):
    expr = parse_equality(parser)
    while parser._match(TokenType.AND):
        op = parser._previous()
        right = parse_equality(parser)
        expr = Binary(expr, op, right)
    return expr


def parse_equality(parser: "Parser"):
    expr = _parse_comparison(parser)
    while parser._match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
        op = parser._previous()
        right = _parse_comparison(parser)
        expr = Binary(expr, op, right)
    return expr


def _parse_comparison(parser: "Parser"):
    expr = _parse_term(parser)
    while parser._match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
        op = parser._previous()
        right = _parse_term(parser)
        expr = Binary(expr, op, right)
    return expr


def _parse_term(parser: "Parser"):
    expr = _parse_factor(parser)
    while parser._match(TokenType.PLUS, TokenType.MINUS):
        op = parser._previous()
        right = _parse_factor(parser)
        expr = Binary(expr, op, right)
    return expr


def _parse_factor(parser: "Parser"):
    expr = _parse_unary(parser)
    while parser._match(TokenType.STAR, TokenType.SLASH):
        op = parser._previous()
        right = _parse_unary(parser)
        expr = Binary(expr, op, right)
    return expr


def _parse_unary(parser: "Parser"):
    if parser._match(TokenType.BANG, TokenType.MINUS):
        op = parser._previous()
        right = _parse_unary(parser)
        return Unary(op, right)
    return parser._call()


# ---------- interpreting ----------

def _check_numeric_operands(interp: "Interpreter", op, left, right, token):
    if not isinstance(left, (int, float)) or isinstance(left, bool):
        raise LangRuntimeError(
            f"Operator '{op}' expects a number on the left, got {interp._type_name(left)}",
            token,
        )
    if not isinstance(right, (int, float)) or isinstance(right, bool):
        raise LangRuntimeError(
            f"Operator '{op}' expects a number on the right, got {interp._type_name(right)}",
            token,
        )


@eval_handler(Binary)
def _eval_binary(interp: "Interpreter", node: Binary, env):
    op_token = node.op
    op = op_token.lexeme
    left = interp._eval(node.left, env)

    if op == "and":
        if not interp._truthy(left):
            return left
        return interp._eval(node.right, env)

    if op == "or":
        if interp._truthy(left):
            return left
        return interp._eval(node.right, env)

    right = interp._eval(node.right, env)

    if isinstance(left, LangInstance):
        operator = left.klass.operators.get(op)
        if operator is not None:
            return interp._call_function(operator, [right], this=left)

    if op == "!=" and isinstance(left, LangInstance):
        operator = left.klass.operators.get("==")
        if operator is not None:
            result = interp._call_function(operator, [right], this=left)
            return not interp._truthy(result)

    if op == "+" and (isinstance(left, str) or isinstance(right, str)):
        return stringify(left) + stringify(right)

    if op in _ARITHMETIC_OPS or op in _COMPARISON_OPS:
        _check_numeric_operands(interp, op, left, right, op_token)

    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise LangRuntimeError("Division by zero", op_token)
        return left / right
    if op == "==":
        return interp._values_equal(left, right)
    if op == "!=":
        return not interp._values_equal(left, right)
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right

    raise LangRuntimeError(f"Unknown binary operator '{op}'", op_token)


@eval_handler(Unary)
def _eval_unary(interp: "Interpreter", node: Unary, env):
    op_token = node.op
    op = op_token.lexeme
    right = interp._eval(node.right, env)

    if op == "-":
        if not isinstance(right, (int, float)) or isinstance(right, bool):
            raise LangRuntimeError(
                f"Unary '-' expects a number, got {interp._type_name(right)}",
                op_token,
            )
        return -right
    if op == "!":
        return not interp._truthy(right)

    raise LangRuntimeError(f"Unknown unary operator '{op}'", op_token)
