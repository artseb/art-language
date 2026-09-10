from .tokens import Token, TokenType, KEYWORDS
from .errors import LexError

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1

    def tokenize(self):
        while not self._at_end():
            self.start = self.current
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, "", None, self.line))
        return self.tokens

    def _at_end(self):
        return self.current >= len(self.source)

    def _advance(self):
        char = self.source[self.current]
        self.current += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def _peek(self):
        if self._at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self):
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _match(self, expected):
        if self._at_end() or self.source[self.current] != expected:
            return False
        self.current += 1
        return True

    def _add_token(self, type_, literal=None):
        start_line = self.line
        start_column = self.column
        text = self.source[self.start:self.current]
        self.tokens.append(Token(
            type_, 
            text, 
            literal, 
            start_line,
            start_column
        ))

    # --- core scanning ---

    def _scan_token(self):
        c = self._advance()

        if c in " \r\t":
            return
        if c == "\n":
            self.line += 1
            return

        # line comments
        if c == "/" and self._peek() == "/":
            while self._peek() != "\n" and not self._at_end():
                self._advance()
            return

        # block comments (support nesting so a commented-out block
        # containing another /* */ doesn't get cut off early)
        if c == "/" and self._peek() == "*":
            self._advance()  # consume '*'
            depth = 1
            start_line = self.line
            while depth > 0:
                if self._at_end():
                    raise LexError("Unterminated block comment", start_line)
                if self._peek() == "/" and self._peek_next() == "*":
                    self._advance()
                    self._advance()
                    depth += 1
                    continue
                if self._peek() == "*" and self._peek_next() == "/":
                    self._advance()
                    self._advance()
                    depth -= 1
                    continue
                self._advance()
            return

        simple = {
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ",": TokenType.COMMA,
            ":": TokenType.COLON,
            ";": TokenType.SEMICOLON,
            "+": TokenType.PLUS,
            "*": TokenType.STAR,
        }
        if c in simple:
            self._add_token(simple[c])
            return

        if c == ".":
            if self._match(".") and self._match("."):
                self._add_token(TokenType.ELLIPSIS)
            else:
                self._add_token(TokenType.DOT)
            return

        if c == "-":
            if self._match(">"):
                self._add_token(TokenType.ARROW)
            else:
                self._add_token(TokenType.MINUS)
            return

        if c == "/":
            self._add_token(TokenType.SLASH)
            return

        if c == "=":
            self._add_token(TokenType.EQUAL_EQUAL if self._match("=") else TokenType.EQUAL)
            return
        if c == "!":
            self._add_token(TokenType.BANG_EQUAL if self._match("=") else TokenType.BANG)
            return
        if c == "<":
            self._add_token(TokenType.LESS_EQUAL if self._match("=") else TokenType.LESS)
            return
        if c == ">":
            self._add_token(TokenType.GREATER_EQUAL if self._match("=") else TokenType.GREATER)
            return

        if c == '"':
            self._string()
            return

        if c.isdigit():
            self._number()
            return

        if c.isalpha() or c == "_":
            self._identifier()
            return

        raise LexError(f"Unexpected character {c!r}", self.line, self.column)

    _ESCAPES = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        '"': '"',
        "\\": "\\",
        "0": "\0",
    }

    def _string(self):
        start_line = self.line
        chars = []

        while self._peek() != '"' and not self._at_end():
            ch = self._peek()

            if ch == "\n":
                # ART strings are single-line; a bare newline almost
                # always means a missing closing quote further up.
                raise LexError(
                    "Unterminated string (newline before closing '\"')",
                    self.line,
                )

            if ch == "\\":
                self._advance()  # consume backslash
                if self._at_end():
                    raise LexError("Unterminated string", start_line)

                esc = self._advance()
                if esc in self._ESCAPES:
                    chars.append(self._ESCAPES[esc])
                else:
                    raise LexError(
                        f"Unknown escape sequence '\\{esc}' in string",
                        self.line,
                        self.column,
                    )
                continue

            chars.append(self._advance())

        if self._at_end():
            raise LexError("Unterminated string", start_line)

        self._advance()  # closing "
        self._add_token(TokenType.STRING, "".join(chars))

    def _number(self):
        while self._peek().isdigit():
            self._advance()

        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()

        value = float(self.source[self.start:self.current])
        self._add_token(TokenType.NUMBER, value)

    def _identifier(self):
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        text = self.source[self.start:self.current]
        type_ = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add_token(type_)