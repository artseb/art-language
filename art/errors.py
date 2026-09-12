class ArtError(Exception):
    """Base class for all ART errors. Carries an optional source location
    (line/column) so every stage of the pipeline can report *where*
    something went wrong, not just what."""

    stage = "Error"

    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._format())

    def _format(self):
        if self.line is not None:
            where = f"line {self.line}"
            if self.column is not None:
                where += f", column {self.column}"
            return f"{self.stage} ({where}): {self.message}"
        return f"{self.stage}: {self.message}"

    def __str__(self):
        return self._format()


class LexError(ArtError):
    """Raised when source code cannot be tokenized."""
    stage = "Lex error"


class ParseError(ArtError):
    """Raised when tokens cannot be parsed into valid ART syntax.

    Always constructed as ``ParseError(message, token)`` - message first,
    token second - so line/column are filled in automatically and the
    argument order can never be accidentally swapped (a real bug in the
    previous version, which had a second, incompatible ParseError class
    defined locally in parser.py with the arguments the other way round).
    """
    stage = "Parse error"

    def __init__(self, message, token=None):
        line = token.line if token is not None else None
        column = token.column if token is not None else None
        self.token = token
        super().__init__(message, line, column)


class ReturnSignal(Exception):
    """Used internally to unwind the stack on `return`. Not an error."""
    def __init__(self, value):
        self.value = value


class LangRuntimeError(ArtError):
    """Raised when otherwise-valid ART code fails during execution
    (undefined variables, bad types, division by zero, failed imports,
    stack overflow from runaway recursion, etc.)."""
    stage = "Runtime error"

    def __init__(self, message, token=None):
        line = token.line if token is not None else None
        column = token.column if token is not None else None
        self.token = token
        super().__init__(message, line, column)
