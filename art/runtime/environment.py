from ..errors import LangRuntimeError


class Environment:
    def __init__(self, enclosing=None):
        self.values = {}
        self.enclosing = enclosing

    def define(self, name, value):
        self.values[name] = value

    def get(self, name):
        scope = self
        while scope is not None:
            if name in scope.values:
                return scope.values[name]
            scope = scope.enclosing

        raise LangRuntimeError(
            f"Undefined variable '{name}' "
            f"(did you forget 'local {name} = ...'?)"
        )

    def has(self, name):
        scope = self
        while scope is not None:
            if name in scope.values:
                return True
            scope = scope.enclosing
        return False

    def assign_existing_or_global(self, name, value):
        scope = self
        while scope is not None:
            if name in scope.values:
                scope.values[name] = value
                return
            scope = scope.enclosing

        # ART's current behavior: assignment to a name that doesn't exist
        # anywhere in the scope chain creates it in the global scope.
        root = self
        while root.enclosing is not None:
            root = root.enclosing
        root.values[name] = value
