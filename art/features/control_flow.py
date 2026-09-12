"""Loops and branches: `if`, `while`, `for` (both the C-style
`for (local i = 0 -> 10; 1)` and table-iteration `for (local k, v in t)`
forms), `break`/`continue`, and the plain `{ ... }` block."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType, register_keyword
from ..parser.registry import stmt_parser
from ..interpreter.registry import exec_handler
from ..interpreter.signals import BreakSignal, ContinueSignal
from ..runtime import Environment, LangTable
from .base import Node
from .literals import Literal

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("if", TokenType.IF)
register_keyword("else", TokenType.ELSE)
register_keyword("while", TokenType.WHILE)
register_keyword("for", TokenType.FOR)
register_keyword("in", TokenType.IN)
register_keyword("break", TokenType.BREAK)
register_keyword("continue", TokenType.CONTINUE)


class Block(Node):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({self.statements!r})"


class If(Node):
    def __init__(self, condition, then_branch, else_branch):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def __repr__(self):
        return f"If({self.condition!r}, {self.then_branch!r}, {self.else_branch!r})"


class While(Node):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"While({self.condition!r}, {self.body!r})"


class Break(Node):
    def __repr__(self):
        return "Break()"


class Continue(Node):
    def __repr__(self):
        return "Continue()"


class For(Node):
    def __init__(self, variable, start, end, step, body, key=None, value=None, iterable=None):
        self.variable = variable
        self.start = start
        self.end = end
        self.step = step
        self.body = body
        self.key = key
        self.value = value
        self.iterable = iterable

    def __repr__(self):
        if self.iterable is not None:
            return f"For({self.key!r}, {self.value!r} in {self.iterable!r})"
        return f"For({self.variable!r} = {self.start!r}->{self.end!r}; {self.step!r})"


# ---------- parsing ----------

@stmt_parser(TokenType.LBRACE)
def _parse_block_stmt(parser: "Parser"):
    return parser._block()


@stmt_parser(TokenType.IF)
def _parse_if_stmt(parser: "Parser"):
    parser._consume(TokenType.IF, "Expected 'if'")
    return _finish_if(parser)


def _finish_if(parser: "Parser"):
    """Everything after the leading `if` token has already been
    consumed - shared by the top-level `if` statement and by
    `else if (...)`, which consumes its own `if` via `_match` before
    getting here."""
    parser._consume(TokenType.LPAREN, "Expected '(' after if")
    condition = parser._expression()
    parser._consume(TokenType.RPAREN, "Expected ')' after if condition")

    then_branch = parser._statement()
    else_branch = None

    if parser._match(TokenType.ELSE):
        if parser._match(TokenType.IF):
            else_branch = _finish_if(parser)
        else:
            else_branch = parser._statement()

    return If(condition, then_branch, else_branch)


@stmt_parser(TokenType.WHILE)
def _parse_while_stmt(parser: "Parser"):
    parser._consume(TokenType.WHILE, "Expected 'while'")
    parser._consume(TokenType.LPAREN, "Expected '(' after while")
    condition = parser._expression()
    parser._consume(TokenType.RPAREN, "Expected ')' after while condition")
    body = parser._statement()
    return While(condition, body)


@stmt_parser(TokenType.BREAK)
def _parse_break(parser: "Parser"):
    parser._advance()
    return Break()


@stmt_parser(TokenType.CONTINUE)
def _parse_continue(parser: "Parser"):
    parser._advance()
    return Continue()


@stmt_parser(TokenType.FOR)
def _parse_for_stmt(parser: "Parser"):
    parser._consume(TokenType.FOR, "Expected 'for'")
    parser._consume(TokenType.LPAREN, "Expected '(' after for")
    parser._consume(TokenType.LOCAL, "Expected 'local' after '('")

    first_name = parser._consume(TokenType.IDENTIFIER, "Expected variable name after 'local'").lexeme

    if parser._match(TokenType.COMMA):
        value_name = parser._consume(TokenType.IDENTIFIER, "Expected value variable after ','").lexeme
        parser._consume(TokenType.IN, "Expected 'in' after loop variables")
        iterable = parser._expression()
        parser._consume(TokenType.RPAREN, "Expected ')' after for loop")
        body = parser._statement()

        return For(
            variable=None, start=None, end=None, step=None, body=body,
            key=first_name, value=value_name, iterable=iterable,
        )

    parser._consume(TokenType.EQUAL, "Expected '=' after loop variable")
    start = parser._expression()

    parser._consume(TokenType.ARROW, "Expected '->' after loop start")
    end = parser._expression()

    step = Literal(1)
    if parser._match(TokenType.SEMICOLON):
        step = parser._expression()

    parser._consume(TokenType.RPAREN, "Expected ')' after for loop")
    body = parser._statement()

    return For(variable=first_name, start=start, end=end, step=step, body=body)


# ---------- interpreting ----------

@exec_handler(Block)
def _exec_block(interp: "Interpreter", node: Block, env):
    block_env = Environment(env)
    for stmt in node.statements:
        interp._exec(stmt, block_env)


@exec_handler(If)
def _exec_if(interp: "Interpreter", node: If, env):
    if interp._truthy(interp._eval(node.condition, env)):
        interp._exec(node.then_branch, env)
    elif node.else_branch is not None:
        interp._exec(node.else_branch, env)


@exec_handler(While)
def _exec_while(interp: "Interpreter", node: While, env):
    while interp._truthy(interp._eval(node.condition, env)):
        try:
            interp._exec(node.body, env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break


@exec_handler(Break)
def _exec_break(interp: "Interpreter", node: Break, env):
    raise BreakSignal()


@exec_handler(Continue)
def _exec_continue(interp: "Interpreter", node: Continue, env):
    raise ContinueSignal()


@exec_handler(For)
def _exec_for(interp: "Interpreter", node: For, env):
    if node.iterable is None:
        start = interp._eval(node.start, env)
        end = interp._eval(node.end, env)
        step = interp._eval(node.step, env)

        if step == 0:
            raise LangRuntimeError("For loop step cannot be zero")

        loop_env = Environment(env)
        loop_env.define(node.variable, start)

        while True:
            current = loop_env.get(node.variable)

            if step > 0 and current > end:
                break
            if step < 0 and current < end:
                break

            try:
                interp._exec(node.body, loop_env)
            except ContinueSignal:
                pass
            except BreakSignal:
                break

            current = loop_env.get(node.variable)
            loop_env.assign_existing_or_global(node.variable, current + step)

        return

    table = interp._eval(node.iterable, env)
    if not isinstance(table, LangTable):
        raise LangRuntimeError(f"Cannot iterate over {table!r}")

    loop_env = Environment(env)

    for index, value in enumerate(table.array, start=1):
        loop_env.define(node.key, index)
        loop_env.define(node.value, value)
        try:
            interp._exec(node.body, loop_env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break

    for key, value in table.map.items():
        loop_env.define(node.key, key)
        loop_env.define(node.value, value)
        try:
            interp._exec(node.body, loop_env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break
