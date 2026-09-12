"""`import "file.art" [as Alias]`. The actual file-loading/caching is
engine machinery shared across recursive imports - see
interpreter/modules.py - this file is just the AST node, the grammar
for the statement, and binding the loaded module to a name."""
from typing import TYPE_CHECKING

from ..tokens import TokenType, register_keyword
from ..parser.registry import decl_parser
from ..interpreter.registry import exec_handler
from ..runtime import LangModule
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("import", TokenType.IMPORT)
register_keyword("as", TokenType.AS)


class Import(Node):
    """import "path/to/file.art" [as Alias]"""
    def __init__(self, path, alias):
        self.path = path    # str, the raw string literal (a file path)
        self.alias = alias  # str or None

    def __repr__(self):
        return f"Import({self.path!r}, as={self.alias})"


# ---------- parsing ----------

@decl_parser(TokenType.IMPORT)
def _parse_import_decl(parser: "Parser", is_local, in_class):
    parser._consume(TokenType.IMPORT, "Expected 'import'")
    path_token = parser._consume(TokenType.STRING, "Expected a string path after 'import'")
    alias = None
    if parser._match(TokenType.AS):
        alias = parser._consume(TokenType.IDENTIFIER, "Expected alias name after 'as'").lexeme
    return Import(path_token.literal, alias)


# ---------- interpreting ----------

@exec_handler(Import)
def _exec_import(interp: "Interpreter", node: Import, env):
    """import "file.art"        -> binds a module named after the file;
                                    members are reached as file.method(...)
       import "file.art" as Foo -> binds it as Foo instead; Foo.method(...)
    """
    module_env = interp._load_module(node.path)
    name = interp._module_bind_name(node.path, node.alias)

    module = LangModule(name, dict(module_env.values))
    env.define(name, module)
