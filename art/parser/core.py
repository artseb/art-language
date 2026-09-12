"""The Parser itself: token-stream primitives and the grammar's fixed
skeleton (the handful of decision points that need lookahead or
context rather than a single-token dispatch). Everything that CAN be
decided by "which token am I looking at" is a registered handler living
in art/features/*.py instead - see registry.py for the five tables and
why each one exists.

Adding a new statement/declaration/primary-expression/postfix form
never touches this file: register a handler in the right feature file
and it's live.
"""
from ..errors import ParseError
from ..tokens import TokenType
from ..ast.base import Param
from .registry import (
    STMT_PARSERS, DECL_PARSERS, PRIMARY_PARSERS, POSTFIX_PARSERS, ASSIGN_BUILDERS,
    primary_parser,
)

# Importing this runs every feature module once, which is what actually
# populates the tables above (and tokens.KEYWORDS, and the interpreter's
# EXEC_HANDLERS/EVAL_HANDLERS) - see art/features/__init__.py.
from .. import features as _features  # noqa: F401  (registration side effect)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def _error(self, message, token=None):
        """Build a ParseError anchored at `token` (defaults to the current
        token). Centralizing this means the (message, token) argument
        order can't get flipped by accident at a call site."""
        return ParseError(message, token if token is not None else self._peek())

    # ---------- entry point ----------

    def parse(self):
        statements = []
        while not self._at_end():
            statements.append(self._declaration())
        return statements

    # ---------- declarations ----------
    #
    # This is the one grammar rule that can't be reduced to "look up the
    # next token in a table": `local`, `static`, and the in-class-only
    # forms are modifiers/context checks layered in front of the actual
    # decision, and a bare `local var-decl` has no leading keyword of its
    # own to key a table on (it's "identifier followed by '=' or ','",
    # a lookahead pattern, not a token type). Everything that DOES have
    # a single unambiguous leading keyword still goes through DECL_PARSERS.

    def _declaration(self, in_class=False):
        if self._check(TokenType.IMPORT):
            return DECL_PARSERS[TokenType.IMPORT](self, False, in_class)

        if self._check(TokenType.STATIC):
            return DECL_PARSERS[TokenType.STATIC](self, False, in_class)

        is_local = self._match(TokenType.LOCAL)

        if self._check(TokenType.CLASS):
            return DECL_PARSERS[TokenType.CLASS](self, is_local, in_class)

        if self._check(TokenType.FUN):
            return DECL_PARSERS[TokenType.FUN](self, is_local, in_class)

        if is_local and self._check(TokenType.IDENTIFIER):
            from ..features.basics import parse_var_decl
            return parse_var_decl(self, is_local)

        if (
            self._check(TokenType.IDENTIFIER)
            and (
                self._check_next(TokenType.EQUAL)
                or self._check_next(TokenType.COMMA)
            )
        ):
            from ..features.basics import parse_var_decl
            return parse_var_decl(self, is_local)

        for token_type in (TokenType.GET, TokenType.SET, TokenType.OPERATOR, TokenType.ENUM):
            if self._check(token_type):
                return DECL_PARSERS[token_type](self, is_local, in_class)

        if is_local:
            raise ParseError(
                "Expected 'class', 'fun', or a variable after 'local'",
                self._peek()
            )

        return self._statement()

    # ---------- statements ----------

    def _statement(self):
        handler = STMT_PARSERS.get(self._peek().type)
        if handler is not None:
            return handler(self)

        expr = self._expression()
        return self._wrap_expression_statement(expr)

    def _wrap_expression_statement(self, expr):
        from ..features.basics import ExpressionStmt
        return ExpressionStmt(expr)

    def _block(self):
        from ..features.control_flow import Block
        self._consume(TokenType.LBRACE, "Expected '{'")
        statements = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            statements.append(self._declaration())
        self._consume(TokenType.RBRACE, "Expected '}' after block")
        return Block(statements)

    # ---------- shared function-signature grammar ----------
    #
    # Used by plain functions, lambdas, setters, and operator overloads -
    # genuinely cross-feature, not any one construct's business.

    def _parse_param_list(self, context):
        """Parse a parenthesized, comma-separated parameter list.
        `context` only affects error messages ("function" / "anonymous
        function")."""
        self._consume(TokenType.LPAREN, f"Expected '(' to start the {context} parameter list")

        params = []
        has_default = False

        if not self._check(TokenType.RPAREN):
            while True:
                param = self._param()

                if has_default and param.default is None and not param.variadic:
                    raise self._error(
                        "Required parameter cannot follow a parameter with a default value",
                        self._previous(),
                    )

                if param.default is not None:
                    has_default = True

                params.append(param)

                if param.variadic:
                    if self._check(TokenType.COMMA):
                        raise self._error(
                            "Variadic parameter must be the last parameter",
                            self._peek(),
                        )
                    break

                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RPAREN, f"Expected ')' after {context} parameters")
        return params

    def _parse_optional_return_type(self):
        if self._match(TokenType.ARROW):
            return self._consume(
                TokenType.IDENTIFIER,
                "Expected return type after '->'"
            ).lexeme
        return None

    def _param(self):
        variadic = self._match(TokenType.ELLIPSIS)

        name = self._consume(
            TokenType.IDENTIFIER,
            "Expected parameter name"
        ).lexeme

        type_name = None

        if self._match(TokenType.COLON):
            type_name = self._consume(
                TokenType.IDENTIFIER,
                "Expected type name"
            ).lexeme

        default = None

        if self._match(TokenType.EQUAL):
            if variadic:
                raise ParseError(
                    "Variadic parameter cannot have a default value",
                    self._previous()
                )

            default = self._expression()

        return Param(name, type_name, default, variadic)

    # ---------- expressions ----------

    def _expression(self):
        return self._assignment()

    def _assignment(self):
        from ..features.operators import parse_or
        expr = parse_or(self)

        if self._match(TokenType.EQUAL):
            value = self._assignment()  # right-associative: a = b = c

            builder = ASSIGN_BUILDERS.get(type(expr))
            if builder is None:
                raise ParseError("Invalid assignment target", self._previous())

            return builder(expr, value)

        return expr

    def _call(self):
        """Primary expression, followed by however many postfix
        `(args)` / `.name` / `[index]` forms follow it. The loop is
        generic; each punctuation's meaning is a registered handler."""
        expr = self._primary()
        while True:
            handler = POSTFIX_PARSERS.get(self._peek().type)
            if handler is None:
                break
            expr = handler(self, expr)
        return expr

    def _primary(self):
        handler = PRIMARY_PARSERS.get(self._peek().type)
        if handler is not None:
            return handler(self)

        raise ParseError(f"Unexpected token {self._peek().lexeme!r}", self._peek())

    # ---------- token helpers ----------

    def _match(self, *types):
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _check(self, type_):
        if self._at_end():
            return False
        return self._peek().type == type_

    def _check_next(self, type_):
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].type == type_

    def _advance(self):
        if not self._at_end():
            self.current += 1
        return self._previous()

    def _at_end(self):
        return self._peek().type == TokenType.EOF

    def _peek(self):
        return self.tokens[self.current]

    def _previous(self):
        return self.tokens[self.current - 1]

    def _consume(self, type_, message):
        if self._check(type_):
            return self._advance()
        raise ParseError(message, self._peek())


@primary_parser(TokenType.LPAREN)
def _parse_grouping(parser):
    """`(expr)` - not a feature of its own (no AST node, just
    precedence grouping), so it's registered here rather than being
    homeless or forcing an arbitrary feature file to own it."""
    parser._advance()  # consume '('
    expr = parser._expression()
    parser._consume(TokenType.RPAREN, "Expected ')' after expression")
    return expr
