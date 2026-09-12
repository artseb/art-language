class Node:
    """Base class for all ART AST nodes."""

    def __init__(self, token=None):
        self.token = token

    @property
    def line(self):
        return self.token.line if self.token else None

    @property
    def column(self):
        return self.token.column if self.token else None


class Param(Node):
    """A function parameter, with optional type, default, and variadic
    flag. Lives here (rather than in whichever feature file happens to
    parse it first) because it's shared structure - functions, lambdas,
    setters, and operator overloads all build parameter lists out of it."""
    def __init__(self, name, type_name, default=None, variadic=False):
        self.name = name
        self.type_name = type_name
        self.default = default
        self.variadic = variadic

    def __repr__(self):
        prefix = "..." if self.variadic else ""
        return f"Param({prefix}{self.name}: {self.type_name} = {self.default!r})"
