"""Calling things: `callee(args...)`, `super(args...)` (the constructor
call form; `super.method()` is a Get producing a BoundMethod - see
access.py), and lambda expressions `fun(params) { ... }`.

Actually invoking a resolved callee value is `interp.call_value(...)`
in interpreter/calling.py - shared machinery, since classes, bound
methods, and native builtins all need to be callable too, not just
plain functions. This file's job is just "what ART syntax produces a
call, and what does it evaluate to"."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType
from ..parser.registry import postfix_parser, primary_parser
from ..interpreter.registry import eval_handler
from ..runtime import LangFunction
from .base import Node
from .access import Super

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser


class Call(Node):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def __repr__(self):
        return f"Call({self.callee!r}, {self.args!r})"


class Lambda(Node):
    def __init__(self, params, body, return_type=None):
        self.params = params
        self.body = body
        self.return_type = return_type

    def __repr__(self):
        return f"Lambda({self.params!r})"


# ---------- parsing ----------

@postfix_parser(TokenType.LPAREN)
def _parse_call(parser: "Parser", left):
    parser._advance()  # consume '('
    args = []
    if not parser._check(TokenType.RPAREN):
        args.append(parser._expression())
        while parser._match(TokenType.COMMA):
            args.append(parser._expression())
    parser._consume(TokenType.RPAREN, "Expected ')' after arguments")
    return Call(left, args)


@primary_parser(TokenType.FUN)
def _parse_lambda(parser: "Parser"):
    parser._advance()  # consume 'fun'
    params = parser._parse_param_list("anonymous function")
    return_type = parser._parse_optional_return_type()
    body = parser._block()
    return Lambda(params, body, return_type)


# ---------- interpreting ----------

@eval_handler(Call)
def _eval_call(interp: "Interpreter", node: Call, env):
    args = [interp._eval(a, env) for a in node.args]

    if isinstance(node.callee, Super):
        if not env.has("this"):
            raise LangRuntimeError("'super' can only be used inside a class method")
        if not env.has("__class"):
            raise LangRuntimeError("Cannot determine superclass for 'super'")

        current_class = env.get("__class")
        superclass = current_class.superclass
        if superclass is None:
            raise LangRuntimeError(f"Class '{current_class.name}' has no superclass")

        constructor = superclass.methods.get(superclass.name)
        if constructor is not None:
            interp._call_function(constructor, args, this=env.get("this"))

        return env.get("this")

    callee = interp._eval(node.callee, env)
    return interp.call_value(callee, args)


@eval_handler(Lambda)
def _eval_lambda(interp: "Interpreter", node: Lambda, env):
    func = LangFunction("<anonymous>")
    func.add_overload(node.params, node.body, env, node.return_type)
    return func
