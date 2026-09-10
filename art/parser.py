from .lexer import Token, TokenType
from .ast import *
from .errors import ParseError


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

    def _declaration(self, in_class=False):
        if self._check(TokenType.IMPORT):
            return self._import_decl()

        if self._check(TokenType.STATIC):
            return self._static_decl(in_class)

        is_local = self._match(TokenType.LOCAL)

        if self._check(TokenType.CLASS):
            return self._class_decl(is_local)

        if self._check(TokenType.FUN):
            return self._fun_decl(is_local)

        if is_local and self._check(TokenType.IDENTIFIER):
            return self._var_decl(is_local)

        if (
            self._check(TokenType.IDENTIFIER)
            and (
                self._check_next(TokenType.EQUAL)
                or self._check_next(TokenType.COMMA)
            )
        ):
            return self._var_decl(is_local)

        if self._match(TokenType.GET):
            if not in_class:
                raise self._error("Getter declarations are only allowed inside classes.", self._previous())

            name = self._consume(TokenType.IDENTIFIER, "Expected getter name.")
            self._consume(TokenType.LPAREN, "Expected '(' after getter name.")
            self._consume(TokenType.RPAREN, "Expected ')' after getter name.")
            body = self._block()

            return Getter(name.lexeme, body)
        if self._match(TokenType.SET):
            if not in_class:
                raise self._error(
                    "Setter declarations are only allowed inside classes.",
                    self._previous(),
                )

            name = self._consume(TokenType.IDENTIFIER, "Expected setter name.")
            self._consume(TokenType.LPAREN, "Expected '(' after setter name.")

            param = self._param()

            self._consume(TokenType.RPAREN, "Expected ')' after setter parameter.")
            body = self._block()

            return Setter(name.lexeme, param, body)

        if self._match(TokenType.OPERATOR):
            if not in_class:
                raise self._error(
                    "Operator declarations are only allowed inside classes.",
                    self._previous(),
                )

            operator_token = self._advance()

            valid_operators = {
                TokenType.EQUAL_EQUAL,
                TokenType.BANG_EQUAL,
                TokenType.LESS,
                TokenType.LESS_EQUAL,
                TokenType.GREATER,
                TokenType.GREATER_EQUAL,
                TokenType.PLUS,
                TokenType.MINUS,
                TokenType.STAR,
                TokenType.SLASH
            }

            if operator_token.type not in valid_operators:
                raise self._error(
                    f"Invalid overloaded operator {operator_token.lexeme!r}. "
                    f"Supported operators: ==, !=, <, <=, >, >=, +, -, *, /.",
                    operator_token,
                )

            self._consume(
                TokenType.LPAREN,
                "Expected '(' after operator."
            )

            param = self._param()

            self._consume(
                TokenType.RPAREN,
                "Expected ')' after operator parameter."
            )

            body = self._block()

            return OperatorDecl(operator_token.lexeme, [param], body)

        if self._match(TokenType.ENUM):
            return self._enum_decl(is_local)

        if is_local:
            raise ParseError(
                "Expected 'class', 'fun', or a variable after 'local'",
                self._peek()
            )

        return self._statement()

    def _import_decl(self):
        self._consume(TokenType.IMPORT, "Expected 'import'")
        path_token = self._consume(TokenType.STRING, "Expected a string path after 'import'")
        alias = None
        if self._match(TokenType.AS):
            alias = self._consume(TokenType.IDENTIFIER, "Expected alias name after 'as'").lexeme
        return Import(path_token.literal, alias)

    def _static_decl(self, in_class):
        static_token = self._consume(TokenType.STATIC, "Expected 'static'")

        if not in_class:
            raise self._error(
                "'static' fields are only allowed inside a class body.",
                static_token,
            )

        name = self._consume(TokenType.IDENTIFIER, "Expected static field name.").lexeme
        self._consume(
            TokenType.EQUAL,
            f"Static field '{name}' must be initialized, e.g. 'static {name} = 0'.",
        )
        value = self._expression()

        return ExpressionStmt(Assign(name, value, is_local=False, is_static=True))

    def _class_decl(self, is_local):
        self._consume(TokenType.CLASS, "Expected 'class'")
        name = self._consume(TokenType.IDENTIFIER, "Expected class name").lexeme

        superclass = None
        if self._match(TokenType.EXTENDS):
            superclass = self._consume(TokenType.IDENTIFIER, "Expected superclass name").lexeme

        interfaces = []
        if self._match(TokenType.IMPLEMENTS):
            interfaces.append(self._consume(TokenType.IDENTIFIER, "Expected interface name").lexeme)
            while self._match(TokenType.COMMA):
                interfaces.append(self._consume(TokenType.IDENTIFIER, "Expected interface name").lexeme)

        self._consume(TokenType.LBRACE, "Expected '{' before class body")
        body = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            body.append(self._declaration(in_class=True))
        self._consume(TokenType.RBRACE, "Expected '}' after class body")

        return ClassDecl(name, superclass, interfaces, body, is_local)

    def _fun_decl(self, is_local):
        self._consume(TokenType.FUN, "Expected 'fun'")
        name = self._consume(TokenType.IDENTIFIER, "Expected function name").lexeme

        params = self._parse_param_list("function")
        return_type = self._parse_optional_return_type()
        body = self._block()
        return FunDecl(name, params, body, is_local, return_type)

    def _parse_param_list(self, context):
        """Parse a parenthesized, comma-separated parameter list, shared by
        named functions (`fun name(...)`) and lambdas (`fun (...)`).
        `context` is only used to make error messages ("function" /
        "anonymous function") say where the problem is.
        """
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

    def _var_decl(self, is_local=False):
        names = [
            self._consume(
                TokenType.IDENTIFIER,
                "Expected variable name"
            ).lexeme
        ]

        while self._match(TokenType.COMMA):
            names.append(
                self._consume(
                    TokenType.IDENTIFIER,
                    "Expected variable name after ','"
                ).lexeme
            )

        values = []

        if self._match(TokenType.EQUAL):
            values.append(self._expression())

            while self._match(TokenType.COMMA):
                values.append(self._expression())

        if len(names) == 1:
            value = values[0] if values else Literal(None)

            return ExpressionStmt(
                Assign(
                    names[0],
                    value,
                    is_local
                )
            )

        return MultiAssign(
            names,
            values,
            is_local
        )

    def _enum_decl(self, is_local=False):
        name = self._consume(
            TokenType.IDENTIFIER,
            "Expected enum name."
        )

        self._consume(
            TokenType.LBRACE,
            "Expected '{' before enum body."
        )

        members = []
        member_names = set()

        while not self._check(TokenType.RBRACE) and not self._at_end():
            # If we encounter a function, the enum members are finished.
            if self._check(TokenType.FUN):
                break

            member = self._consume(
                TokenType.IDENTIFIER,
                "Expected enum member name."
            )

            if member.lexeme in member_names:
                raise ParseError(
                    f"Duplicate enum member '{member.lexeme}'",
                    member
                )

            if member.lexeme in ("name", "enum"):
                raise ParseError(
                    f"'{member.lexeme}' is reserved for enum member metadata",
                    member
                )

            member_names.add(member.lexeme)

            args = []

            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())

                    while self._match(TokenType.COMMA):
                        args.append(self._expression())

                self._consume(
                    TokenType.RPAREN,
                    "Expected ')' after enum member arguments."
                )

            members.append(EnumMember(member.lexeme, args))

            # Comma between enum members.
            self._match(TokenType.COMMA)

        # Parse the enum's methods/constructor.
        body = []

        while not self._check(TokenType.RBRACE) and not self._at_end():
            if self._check(TokenType.FUN):
                body.append(self._fun_decl(False))
            else:
                raise self._error("Expected function declaration in enum body.")

        self._consume(
            TokenType.RBRACE,
            "Expected '}' after enum body."
        )

        return EnumDecl(
            name.lexeme,
            members,
            body,
            is_local
        )

    # ---------- statements ----------

    def _statement(self):
        if self._match(TokenType.IF):
            return self._if_stmt()
        if self._match(TokenType.WHILE):
            return self._while_stmt()
        if self._match(TokenType.RETURN):
            return self._return_stmt()
        if self._match(TokenType.BREAK):
            return Break()
        if self._match(TokenType.FOR):
            return self._for_stmt()
        if self._match(TokenType.CONTINUE):
            return Continue()
        if self._check(TokenType.LBRACE):
            return self._block()
        if self._match(TokenType.SWITCH):
            return self._switch_expr()

        expr = self._expression()
        return ExpressionStmt(expr)

    def _for_stmt(self):
        self._consume(TokenType.LPAREN, "Expected '(' after for")
        self._consume(TokenType.LOCAL, "Expected 'local' after '('")

        first_name = self._consume(
            TokenType.IDENTIFIER,
            "Expected variable name after 'local'"
        ).lexeme

        if self._match(TokenType.COMMA):
            value_name = self._consume(
                TokenType.IDENTIFIER,
                "Expected value variable after ','"
            ).lexeme

            self._consume(TokenType.IN, "Expected 'in' after loop variables")
            iterable = self._expression()

            self._consume(TokenType.RPAREN, "Expected ')' after for loop")
            body = self._statement()

            return For(
                variable=None,
                start=None,
                end=None,
                step=None,
                body=body,
                key=first_name,
                value=value_name,
                iterable=iterable,
            )
        self._consume(
            TokenType.EQUAL,
            "Expected '=' after loop variable"
        )
        start = self._expression()

        self._consume(TokenType.ARROW, "Expected '->' after loop start")
        end = self._expression()

        step = Literal(1)
        if self._match(TokenType.SEMICOLON):
            step = self._expression()

        self._consume(TokenType.RPAREN, "Expected ')' after for loop")
        body = self._statement()

        return For(
            variable=first_name,
            start=start,
            end=end,
            step=step,
            body=body,
        )

    def _if_stmt(self):
        self._consume(TokenType.LPAREN, "Expected '(' after if")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')' after if condition")

        then_branch = self._statement()
        else_branch = None

        if self._match(TokenType.ELSE):
            if self._match(TokenType.IF):
                else_branch = self._if_stmt()
            else:
                else_branch = self._statement()

        return If(condition, then_branch, else_branch)

    def _while_stmt(self):
        self._consume(TokenType.LPAREN, "Expected '(' after while")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')' after while condition")
        body = self._statement()
        return While(condition, body)

    def _return_stmt(self):
        value = None
        if not self._check(TokenType.RBRACE):
            value = self._expression()
        return Return(value)

    def _block(self):
        self._consume(TokenType.LBRACE, "Expected '{'")
        statements = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            statements.append(self._declaration())
        self._consume(TokenType.RBRACE, "Expected '}' after block")
        return Block(statements)

    def _switch_expr(self):
        self._consume(
            TokenType.LPAREN,
            "Expected '(' after switch"
        )

        value = self._expression()

        self._consume(
            TokenType.RPAREN,
            "Expected ')' after switch value"
        )

        self._consume(
            TokenType.LBRACE,
            "Expected '{' before switch body"
        )

        cases = []
        else_body = None
        found_else = False

        while not self._check(TokenType.RBRACE) and not self._at_end():
            if self._match(TokenType.CASE):
                if found_else:
                    raise ParseError(
                        "Case cannot appear after 'else' in switch",
                        self._previous()
                    )

                values = [self._expression()]

                while self._match(TokenType.COMMA):
                    values.append(self._expression())

                self._consume(
                    TokenType.COLON,
                    "Expected ':' after case values"
                )

                body = []

                while (
                    not self._check(TokenType.CASE)
                    and not self._check(TokenType.ELSE)
                    and not self._check(TokenType.RBRACE)
                    and not self._at_end()
                ):
                    body.append(self._declaration())

                cases.append(
                    SwitchCase(
                        values,
                        Block(body)
                    )
                )

            elif self._match(TokenType.ELSE):
                if found_else:
                    raise ParseError(
                        "Duplicate 'else' in switch",
                        self._previous()
                    )

                found_else = True

                self._consume(
                    TokenType.COLON,
                    "Expected ':' after 'else'"
                )

                body = []

                while (
                    not self._check(TokenType.CASE)
                    and not self._check(TokenType.RBRACE)
                    and not self._at_end()
                ):
                    body.append(self._declaration())

                else_body = Block(body)

            else:
                raise ParseError(
                    "Expected 'case' or 'else' in switch",
                    self._peek()
                )

        self._consume(
            TokenType.RBRACE,
            "Expected '}' after switch body"
        )

        return Switch(value, cases, else_body)

    # ---------- expressions ----------

    def _expression(self):
        return self._assignment()

    def _assignment(self):
        expr = self._or()

        if self._match(TokenType.EQUAL):
            value = self._assignment()
            if isinstance(expr, Variable):
                return Assign(expr.name, value, is_local=False)
            if isinstance(expr, Get):
                return Set(expr.obj, expr.name, value)
            elif isinstance(expr, Index):
                return IndexSet(
                    expr.obj,
                    expr.index,
                    value,
                )
            raise ParseError("Invalid assignment target", self._previous())

        return expr

    def _or(self):
        expr = self._and()

        while self._match(TokenType.OR):
            op = self._previous()
            right = self._and()
            expr = Binary(expr, op, right)

        return expr

    def _and(self):
        expr = self._equality()

        while self._match(TokenType.AND):
            op = self._previous()
            right = self._equality()
            expr = Binary(expr, op, right)

        return expr

    def _equality(self):
        expr = self._comparison()

        while self._match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            op = self._previous()
            right = self._comparison()
            expr = Binary(expr, op, right)

        return expr

    def _comparison(self):
        expr = self._term()
        while self._match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            op = self._previous()
            right = self._term()
            expr = Binary(expr, op, right)
        return expr

    def _term(self):
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._previous()
            right = self._factor()
            expr = Binary(expr, op, right)
        return expr

    def _factor(self):
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            op = self._previous()
            right = self._unary()
            expr = Binary(expr, op, right)
        return expr

    def _unary(self):
        if self._match(TokenType.BANG, TokenType.MINUS):
            op = self._previous()
            right = self._unary()
            return Unary(op, right)
        return self._call()

    def _call(self):
        expr = self._primary()
        while True:
            if self._match(TokenType.LPAREN):
                args = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._expression())
                self._consume(TokenType.RPAREN, "Expected ')' after arguments")
                expr = Call(expr, args)
            elif self._match(TokenType.DOT):
                if self._check(TokenType.IDENTIFIER) or self._check(TokenType.ENUM):
                    name = self._advance().lexeme
                else:
                    raise ParseError(
                        "Expected property name after '.'",
                        self._peek()
                    )

                expr = Get(expr, name)
            elif self._match(TokenType.LBRACKET):
                index = self._expression()
                self._consume(TokenType.RBRACKET, "Expected ']' after index.")
                expr = Index(expr, index)
            else:
                break
        return expr

    def _primary(self):
        if self._match(TokenType.NUMBER):
            return Literal(self._previous().literal)
        if self._match(TokenType.STRING):
            return Literal(self._previous().literal)
        if self._match(TokenType.TRUE):
            return Literal(True)
        if self._match(TokenType.FALSE):
            return Literal(False)
        if self._match(TokenType.NIL):
            return Literal(None)
        if self._match(TokenType.IDENTIFIER):
            return Variable(self._previous().lexeme)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        if self._match(TokenType.LBRACKET):
            return self._table_literal()
        if self._match(TokenType.FUN):
            return self._lambda()
        if self._match(TokenType.SUPER):
            return Super()
        if self._match(TokenType.SWITCH):
            return self._switch_expr()

        raise ParseError(f"Unexpected token {self._peek().lexeme!r}", self._peek())

    def _table_literal(self):
        entries = []
        if not self._check(TokenType.RBRACKET):
            entries.append(self._table_entry())
            while self._match(TokenType.COMMA):
                entries.append(self._table_entry())
        self._consume(TokenType.RBRACKET, "Expected ']' after table literal")
        return TableLiteral(entries)

    def _table_entry(self):
        # Use _equality() (not _expression()) so the '=' below isn't
        # swallowed by assignment parsing -- table entries own their '='.
        expr = self._equality()
        if self._match(TokenType.EQUAL):
            value = self._equality()
            return (expr, value)
        return (None, expr)

    def _lambda(self):
        params = self._parse_param_list("anonymous function")
        return_type = self._parse_optional_return_type()
        body = self._block()
        return Lambda(params, body, return_type)

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