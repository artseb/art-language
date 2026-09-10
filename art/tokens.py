from enum import Enum, auto

class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords
    LOCAL = auto()
    STATIC = auto()
    FUN = auto()
    CLASS = auto()
    EXTENDS = auto()
    IMPLEMENTS = auto()
    IMPORT = auto()
    AS = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    BREAK = auto()
    CONTINUE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    AND = auto()
    OR = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    SUPER = auto()
    GET = auto()
    SET = auto()
    OPERATOR = auto()
    ENUM = auto()
    SWITCH = auto()
    CASE = auto()

    # Symbols
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    ELLIPSIS = auto()
    COLON = auto()
    SEMICOLON = auto()

    # Operators
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG = auto()
    BANG_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    ARROW = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

    EOF = auto()

KEYWORDS = {
    "local": TokenType.LOCAL,
    "static": TokenType.STATIC,
    "fun": TokenType.FUN,
    "class": TokenType.CLASS,
    "extends": TokenType.EXTENDS,
    "implements": TokenType.IMPLEMENTS,
    "import": TokenType.IMPORT,
    "as": TokenType.AS,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "nil": TokenType.NIL,
    "super": TokenType.SUPER,
    "get": TokenType.GET,
    "set": TokenType.SET,
    "operator": TokenType.OPERATOR,
    "enum": TokenType.ENUM,
    "switch": TokenType.SWITCH,
    "case": TokenType.CASE,
}


class Token:
    def __init__(self, type_, lexeme, literal=None, line=1, column=1):
        self.type = type_
        self.lexeme = lexeme
        self.literal = literal
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token("
            f"{self.type}, "
            f"{self.lexeme!r}, "
            f"{self.literal!r}, "
            f"line={self.line}, "
            f"column={self.column}"
            f")"
        )