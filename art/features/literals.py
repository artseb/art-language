"""Literal values (numbers/strings/true/false/nil - the parser already
collapses these to a plain Python value), interpolated strings
(`"Hello, ${name}"`), and table literals `[1, 2, "k" = v]`."""
from typing import TYPE_CHECKING

from ..errors import ParseError
from ..tokens import TokenType, register_keyword
from ..parser.registry import primary_parser
from ..interpreter.registry import eval_handler
from ..runtime import LangTable
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("true", TokenType.TRUE)
register_keyword("false", TokenType.FALSE)
register_keyword("nil", TokenType.NIL)


class Literal(Node):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Literal({self.value!r})"


class Interpolation(Node):
    """`"a ${b} c"`. `parts` is a list of plain strings and expression
    nodes; evaluating joins them with the same formatting `print` uses,
    so `"${5}"` is "5" rather than "5.0" and an instance with a
    `toString()` speaks for itself."""
    def __init__(self, parts):
        self.parts = parts

    def __repr__(self):
        return f"Interpolation({self.parts!r})"


class TableLiteral(Node):
    """Unified array/dict literal. `entries` is a list of
    (key_or_None, value_expr) pairs - key_or_None is None for plain
    array-style entries (`[1, 2, 3]`) and an expr for dict-style
    entries (`["key" = "value"]`)."""
    def __init__(self, entries):
        self.entries = entries

    def __repr__(self):
        return f"TableLiteral({self.entries!r})"


# ---------- parsing ----------

@primary_parser(TokenType.NUMBER, TokenType.STRING)
def _parse_literal_value(parser: "Parser"):
    parser._advance()
    return Literal(parser._previous().literal)


@primary_parser(TokenType.INTERP_STRING)
def _parse_interpolated_string(parser: "Parser"):
    """Each `${ ... }` hole arrives as unparsed source text (the lexer
    only matched its braces), so parse each one here as a full
    expression in its own right - which is what makes any expression,
    not just a bare variable name, legal inside a hole."""
    from ..lexer import Lexer
    from ..parser.core import Parser as ArtParser

    parser._advance()
    token = parser._previous()

    parts = []
    for part in token.literal:
        if part[0] == "text":
            parts.append(part[1])
            continue
 
        _, source, line, column = part

        # Lex the hole as if it were still sitting where it was written,
        # so an error inside it points at the real line and column
        # rather than at "line 1" of a detached fragment.
        sub_lexer = Lexer(source)
        sub_lexer.line, sub_lexer.column = line, column
        sub_parser = ArtParser(sub_lexer.tokenize())
 
        expr = sub_parser._expression()
        if not sub_parser._at_end():
            raise ParseError(
                "Expected a single expression inside '${ ... }'",
                sub_parser._peek(),
            )

        parts.append(expr)

    return Interpolation(parts)


@primary_parser(TokenType.TRUE)
def _parse_true(parser: "Parser"):
    parser._advance()
    return Literal(True)


@primary_parser(TokenType.FALSE)
def _parse_false(parser: "Parser"):
    parser._advance()
    return Literal(False)


@primary_parser(TokenType.NIL)
def _parse_nil(parser: "Parser"):
    parser._advance()
    return Literal(None)


@primary_parser(TokenType.LBRACKET)
def _parse_table_literal(parser: "Parser"):
    from .operators import parse_equality

    parser._advance()  # consume '['

    def table_entry():
        # Use parse_equality() (not the full expression grammar) so the
        # '=' below isn't swallowed by assignment parsing - table
        # entries own their own '='.
        expr = parse_equality(parser)
        if parser._match(TokenType.EQUAL):
            value = parse_equality(parser)
            return (expr, value)
        return (None, expr)

    entries = []
    if not parser._check(TokenType.RBRACKET):
        entries.append(table_entry())
        while parser._match(TokenType.COMMA):
            if parser._check(TokenType.RBRACKET):
                break  # trailing comma - `[1, 2, 3,]` is fine, not an error
            entries.append(table_entry())

    parser._consume(TokenType.RBRACKET, "Expected ']' after table literal")
    return TableLiteral(entries)


# ---------- interpreting ----------

@eval_handler(Literal)
def _eval_literal(interp: "Interpreter", node, env):
    return node.value


@eval_handler(Interpolation)
def _eval_interpolation(interp: "Interpreter", node: Interpolation, env):
    pieces = []
    for part in node.parts:
        if isinstance(part, str):
            pieces.append(part)
        else:
            pieces.append(interp.display(interp._eval(part, env)))
 
    return "".join(pieces)


@eval_handler(TableLiteral)
def _eval_table_literal(interp: "Interpreter", node, env):
    table = LangTable()
    for key_expr, value_expr in node.entries:
        value = interp._eval(value_expr, env)
        if key_expr is None:
            table.append(value)
        else:
            key = interp._eval(key_expr, env)
            table.set(key, value)
    return table