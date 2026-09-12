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

KEYWORDS = {}


def register_keyword(word, token_type):
    """Map a source-level keyword string to its TokenType. Called by each
    feature module for the keyword(s) it owns (see art/features/*.py) -
    the enum member itself still has to be declared above, since Python
    enums can't be assembled piecemeal, but which *word* triggers it is
    each feature's own business and lives with that feature, not here.
    """
    if word in KEYWORDS and KEYWORDS[word] is not token_type:
        raise RuntimeError(
            f"Keyword '{word}' is already registered to {KEYWORDS[word]}"
        )
    KEYWORDS[word] = token_type



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