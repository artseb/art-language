"""Named function declarations: `fun name(params) -> ReturnType { ... }`,
including overloading (multiple declarations of the same name with
different param signatures - see interpreter/calling.py's
`_register_overload`/`_resolve_overload`, shared with class methods and
enum constructors)."""
from typing import TYPE_CHECKING

from ..tokens import TokenType, register_keyword
from ..parser.registry import decl_parser
from ..interpreter.registry import exec_handler
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("fun", TokenType.FUN)


class FunDecl(Node):
    def __init__(self, name, params, body, is_local=False, return_type=None):
        self.name = name
        self.params = params
        self.body = body
        self.is_local = is_local
        self.return_type = return_type

    def __repr__(self):
        return f"FunDecl({self.name}, {self.params!r}, local={self.is_local})"


# ---------- parsing ----------

@decl_parser(TokenType.FUN)
def _parse_fun_decl(parser: "Parser", is_local, in_class):
    parser._consume(TokenType.FUN, "Expected 'fun'")
    name = parser._consume(TokenType.IDENTIFIER, "Expected function name").lexeme

    params = parser._parse_param_list("function")
    return_type = parser._parse_optional_return_type()
    body = parser._block()
    return FunDecl(name, params, body, is_local, return_type)


# ---------- interpreting ----------

@exec_handler(FunDecl)
def _exec_fun_decl(interp: "Interpreter", node: FunDecl, env):
    interp._register_overload(env.values, node.name, node.params, node.body, env, node.return_type)
