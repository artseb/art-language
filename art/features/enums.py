"""`enum Name { A, B(1, 2) fun Name(x) { ... } }` - a fixed set of
named, immutable instances of a hidden class, optionally constructed
with arguments via that class's constructor."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType, register_keyword
from ..parser.registry import decl_parser
from ..interpreter.registry import exec_handler
from ..runtime import Environment, LangClass, LangInstance, LangEnum, LangTable
from .base import Node
from .functions import FunDecl, _parse_fun_decl

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("enum", TokenType.ENUM)


class EnumMember(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"EnumMember({self.name}, {self.args!r})"


class EnumDecl(Node):
    def __init__(self, name, members, body, is_local=False):
        self.name = name
        self.members = members
        self.body = body
        self.is_local = is_local

    def __repr__(self):
        return f"EnumDecl({self.name}, {self.members!r}, local={self.is_local})"


# ---------- parsing ----------

@decl_parser(TokenType.ENUM)
def _parse_enum_decl(parser: "Parser", is_local, in_class):
    parser._consume(TokenType.ENUM, "Expected 'enum'")
    name = parser._consume(TokenType.IDENTIFIER, "Expected enum name.")
    parser._consume(TokenType.LBRACE, "Expected '{' before enum body.")

    members = []
    member_names = set()

    while not parser._check(TokenType.RBRACE) and not parser._at_end():
        # If we encounter a function, the enum members are finished.
        if parser._check(TokenType.FUN):
            break

        member = parser._consume(TokenType.IDENTIFIER, "Expected enum member name.")

        if member.lexeme in member_names:
            raise parser._error(f"Duplicate enum member '{member.lexeme}'", member)
        if member.lexeme in ("name", "enum"):
            raise parser._error(f"'{member.lexeme}' is reserved for enum member metadata", member)

        member_names.add(member.lexeme)

        args = []
        if parser._match(TokenType.LPAREN):
            if not parser._check(TokenType.RPAREN):
                args.append(parser._expression())
                while parser._match(TokenType.COMMA):
                    args.append(parser._expression())
            parser._consume(TokenType.RPAREN, "Expected ')' after enum member arguments.")

        members.append(EnumMember(member.lexeme, args))
        parser._match(TokenType.COMMA)  # comma between enum members

    # Parse the enum's methods/constructor.
    body = []
    while not parser._check(TokenType.RBRACE) and not parser._at_end():
        if parser._check(TokenType.FUN):
            body.append(_parse_fun_decl(parser, False, False))
        else:
            raise parser._error("Expected function declaration in enum body.")

    parser._consume(TokenType.RBRACE, "Expected '}' after enum body.")
    return EnumDecl(name.lexeme, members, body, is_local)


# ---------- interpreting ----------

def _make_immutable(value, seen=None):
    """Recursively freeze an enum member (and anything it holds) so it
    can't be mutated after construction. Only enums need this - a class
    or table used any other way is deliberately mutable."""
    if seen is None:
        seen = set()

    value_id = id(value)
    if value_id in seen:
        return
    seen.add(value_id)

    if isinstance(value, LangTable):
        for item in value.array:
            _make_immutable(item, seen)
        for key, item in value.map.items():
            _make_immutable(key, seen)
            _make_immutable(item, seen)
        value.make_immutable()
        return

    if isinstance(value, LangInstance):
        value.is_enum_member = True
        for field_value in value.fields.values():
            _make_immutable(field_value, seen)


@exec_handler(EnumDecl)
def _exec_enum_decl(interp: "Interpreter", node: EnumDecl, env):
    class_env = Environment(env)
    klass = LangClass(node.name, None, [], class_env)
    klass.is_enum = True
    class_env.define("__class", klass)

    for member in node.body:
        if isinstance(member, FunDecl):
            interp._register_overload(
                klass.methods, member.name, member.params, member.body,
                class_env, member.return_type,
            )

    enum = LangEnum(node.name, klass)

    for member in node.members:
        instance = LangInstance(klass)
        constructor = klass.methods.get(node.name)

        if constructor is not None:
            args = [interp._eval(arg, env) for arg in member.args]
            interp._call_function(constructor, args, this=instance)
        elif member.args:
            raise LangRuntimeError(
                f"Enum '{node.name}' has no constructor for member '{member.name}'"
            )

        instance.enum_name = node.name
        instance.enum_member_name = member.name
        _make_immutable(instance)

        enum.add_member(member.name, instance)

    if node.is_local:
        env.define(node.name, enum)
    else:
        env.assign_existing_or_global(node.name, enum)
