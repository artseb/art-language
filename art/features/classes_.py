"""Class declarations: fields, methods (with overloading), static
fields, getters/setters, operator overloads, and nested classes.
`extends`/`implements` are parsed here too since they only ever appear
as part of a class header."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType, register_keyword
from ..parser.registry import decl_parser
from ..interpreter.registry import exec_handler
from ..runtime import Environment, LangClass
from .base import Node
from .functions import FunDecl
from .basics import ExpressionStmt
from .variables import Assign

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("class", TokenType.CLASS)
register_keyword("extends", TokenType.EXTENDS)
register_keyword("implements", TokenType.IMPLEMENTS)
register_keyword("get", TokenType.GET)
register_keyword("set", TokenType.SET)
register_keyword("operator", TokenType.OPERATOR)
register_keyword("static", TokenType.STATIC)

_VALID_OPERATORS = {
    TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL,
    TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL,
    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
}


class ClassDecl(Node):
    def __init__(self, name, superclass, interfaces, body, is_local=False):
        self.name = name
        self.superclass = superclass      # str or None
        self.interfaces = interfaces      # list[str]
        self.body = body                  # list[FunDecl | Assign | ClassDecl | Getter | Setter | OperatorDecl]
        self.is_local = is_local

    def __repr__(self):
        return f"ClassDecl({self.name}, extends={self.superclass}, implements={self.interfaces}, local={self.is_local})"


class Getter(Node):
    def __init__(self, name, body):
        self.name = name
        self.body = body


class Setter(Node):
    def __init__(self, name, param, body):
        self.name = name
        self.param = param
        self.body = body


class OperatorDecl(Node):
    def __init__(self, operator, params, body):
        self.operator = operator
        self.params = params
        self.body = body


# ---------- parsing ----------

@decl_parser(TokenType.CLASS)
def _parse_class_decl(parser: "Parser", is_local, in_class):
    parser._consume(TokenType.CLASS, "Expected 'class'")
    name = parser._consume(TokenType.IDENTIFIER, "Expected class name").lexeme

    superclass = None
    if parser._match(TokenType.EXTENDS):
        superclass = parser._consume(TokenType.IDENTIFIER, "Expected superclass name").lexeme

    interfaces = []
    if parser._match(TokenType.IMPLEMENTS):
        interfaces.append(parser._consume(TokenType.IDENTIFIER, "Expected interface name").lexeme)
        while parser._match(TokenType.COMMA):
            interfaces.append(parser._consume(TokenType.IDENTIFIER, "Expected interface name").lexeme)

    parser._consume(TokenType.LBRACE, "Expected '{' before class body")
    body = []
    while not parser._check(TokenType.RBRACE) and not parser._at_end():
        body.append(parser._declaration(in_class=True))
    parser._consume(TokenType.RBRACE, "Expected '}' after class body")

    return ClassDecl(name, superclass, interfaces, body, is_local)


@decl_parser(TokenType.STATIC)
def _parse_static_decl(parser: "Parser", is_local, in_class):
    static_token = parser._consume(TokenType.STATIC, "Expected 'static'")
    if not in_class:
        raise parser._error("'static' fields are only allowed inside a class body.", static_token)

    name = parser._consume(TokenType.IDENTIFIER, "Expected static field name.").lexeme
    parser._consume(TokenType.EQUAL, f"Static field '{name}' must be initialized, e.g. 'static {name} = 0'.")
    value = parser._expression()

    return ExpressionStmt(Assign(name, value, is_local=False, is_static=True))


@decl_parser(TokenType.GET)
def _parse_getter(parser: "Parser", is_local, in_class):
    getter_token = parser._consume(TokenType.GET, "Expected 'get'")
    if not in_class:
        raise parser._error("Getter declarations are only allowed inside classes.", getter_token)

    name = parser._consume(TokenType.IDENTIFIER, "Expected getter name.")
    parser._consume(TokenType.LPAREN, "Expected '(' after getter name.")
    parser._consume(TokenType.RPAREN, "Expected ')' after getter name.")
    body = parser._block()

    return Getter(name.lexeme, body)


@decl_parser(TokenType.SET)
def _parse_setter(parser: "Parser", is_local, in_class):
    setter_token = parser._consume(TokenType.SET, "Expected 'set'")
    if not in_class:
        raise parser._error("Setter declarations are only allowed inside classes.", setter_token)

    name = parser._consume(TokenType.IDENTIFIER, "Expected setter name.")
    parser._consume(TokenType.LPAREN, "Expected '(' after setter name.")
    param = parser._param()
    parser._consume(TokenType.RPAREN, "Expected ')' after setter parameter.")
    body = parser._block()

    return Setter(name.lexeme, param, body)


@decl_parser(TokenType.OPERATOR)
def _parse_operator_decl(parser: "Parser", is_local, in_class):
    operator_token = parser._consume(TokenType.OPERATOR, "Expected 'operator'")
    if not in_class:
        raise parser._error("Operator declarations are only allowed inside classes.", operator_token)

    op_token = parser._advance()

    if op_token.type not in _VALID_OPERATORS:
        raise parser._error(
            f"Invalid overloaded operator {op_token.lexeme!r}. "
            f"Supported operators: ==, !=, <, <=, >, >=, +, -, *, /.",
            op_token,
        )

    parser._consume(TokenType.LPAREN, "Expected '(' after operator.")
    param = parser._param()
    parser._consume(TokenType.RPAREN, "Expected ')' after operator parameter.")
    body = parser._block()

    return OperatorDecl(op_token.lexeme, [param], body)


# ---------- interpreting ----------

def _build_class(interp: "Interpreter", node: ClassDecl, env):
    superclass = None

    if node.superclass is not None:
        superclass = env.get(node.superclass)
        if not isinstance(superclass, LangClass):
            raise LangRuntimeError(f"'{node.superclass}' is not a class")

    class_env = Environment(env)
    klass = LangClass(node.name, superclass, node.interfaces, class_env)
    class_env.define("__class", klass)

    for member in node.body:
        if isinstance(member, FunDecl):
            interp._register_overload(
                klass.methods, member.name, member.params, member.body,
                class_env, member.return_type,
            )
        elif isinstance(member, ExpressionStmt) and isinstance(member.expr, Assign):
            assign = member.expr
            if assign.is_static:
                # Static fields are shared by the class itself, not
                # copied per-instance, so they're evaluated once, right
                # here, instead of being deferred to instantiation.
                klass.static_fields[assign.name] = interp._eval(assign.value, class_env)
            else:
                klass.field_inits[assign.name] = assign.value
        elif isinstance(member, ClassDecl):
            nested = _build_class(interp, member, class_env)
            klass.nested_classes[member.name] = nested
            class_env.define(member.name, nested)
        elif isinstance(member, Getter):
            klass.getters[member.name] = member
        elif isinstance(member, Setter):
            klass.setters[member.name] = member
        elif isinstance(member, OperatorDecl):
            interp._register_overload(
                klass.operators, member.operator, member.params, member.body,
                class_env, display_name=f"{klass.name}.{member.operator}",
            )
        else:
            raise LangRuntimeError(f"Unsupported class member: {type(member).__name__}")

    return klass


@exec_handler(ClassDecl)
def _exec_class_decl(interp: "Interpreter", node: ClassDecl, env):
    klass = _build_class(interp, node, env)

    if node.is_local:
        env.define(node.name, klass)
    else:
        env.assign_existing_or_global(node.name, klass)
