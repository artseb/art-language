from .tokens import Token, TokenType, KEYWORDS
from .errors import LexError

# Importing this populates tokens.KEYWORDS: every feature module
# registers the keyword string(s) it owns (see art/features/*.py and
# tokens.register_keyword). This import has to happen somewhere before
# tokenizing runs, and the lexer is the first thing that ever needs
# KEYWORDS, so it happens right here rather than depending on the
# parser or interpreter having been imported first.
from . import features as _features  # noqa: F401


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1

    def tokenize(self):
        while not self._at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    # --- helpers ---

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
        self._advance()
        return True

    def _add_token(self, type_, literal=None):
        text = self.source[self.start:self.current]
        self.tokens.append(Token(
            type_,
            text,
            literal,
            self.start_line,
            self.start_column,
        ))

    # --- core scanning ---

    def _scan_token(self):
        c = self._advance()

        if c in " \r\t":
            return
        if c == "\n":
            # _advance() already moved the line/column counters past the
            # newline; nothing else to do.
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
            "^": TokenType.CARET,
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

        if c == "'":
            self._string()
            return

        if c.isdigit():
            self._number()
            return

        if c.isalpha() or c == "_":
            self._identifier()
            return

        raise LexError(f"Unexpected character {c!r}", self.start_line, self.start_column)

    _ESCAPES = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        '"': '"',
        "\\": "\\",
        "0": "\0",
        "$": "$",
    }

    def _string(self):
        """Scan a string literal, which is an interpolated string as soon
        as it contains a `${ ... }` hole. Interpolation is resolved in
        two stages: here the hole's source text is only *found* (matching
        braces, skipping over nested string literals) and stashed
        verbatim, along with where it started; the parser is what turns
        that text into an expression (see features/literals.py). The
        lexer deliberately doesn't recurse into the parser itself - it
        has no business knowing the expression grammar."""
        start_line = self.line
        chars = []
        parts = []  # ("text", str) | ("expr", source, line, column)

        def flush_text():
            if chars:
                parts.append(("text", "".join(chars)))
                chars.clear()

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
                        self.column - 2,
                    )
                continue

            if ch == "$" and self._peek_next() == "{":
                flush_text()
                parts.append(self._interpolation())
                continue

            chars.append(self._advance())

        if self._at_end():
            raise LexError("Unterminated string", start_line)

        self._advance()  # closing "

        if not any(part[0] == "expr" for part in parts):
            self._add_token(TokenType.STRING, "".join(chars))
            return
 
        flush_text()
        self._add_token(TokenType.INTERP_STRING, parts)
 
    def _interpolation(self):
        """Consume one `${ ... }` hole and return its raw source."""
        self._advance()  # '$'
        self._advance()  # '{'
 
        expr_line, expr_column = self.line, self.column
        start = self.current
        depth = 1
 
        while depth > 0:
            if self._at_end():
                raise LexError("Unterminated interpolation (missing '}')", expr_line, expr_column)
 
            ch = self._peek()
 
            if ch in "\"'":
                # A nested string can contain braces of its own, so skip
                # it wholesale rather than counting through it.
                quote = self._advance()
                while not self._at_end() and self._peek() != quote:
                    if self._peek() == "\\":
                        self._advance()
                    self._advance()
                if self._at_end():
                    raise LexError("Unterminated string inside interpolation", expr_line)
                self._advance()  # closing quote
                continue
 
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    source = self.source[start:self.current]
                    self._advance()  # '}'
                    if not source.strip():
                        raise LexError("Empty interpolation '${}'", expr_line, expr_column)
                    return ("expr", source, expr_line, expr_column)
 
            self._advance()

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