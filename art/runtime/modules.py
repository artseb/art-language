from ..errors import LangRuntimeError

class LangModule:
    """A namespaced import: `import "utils.art" as Utils` -> Utils.helper()"""

    def __init__(self, name, exports: dict):
        self.name = name
        self.exports = exports

    def get(self, name):
        if name in self.exports:
            return self.exports[name]
        raise LangRuntimeError(f"'{name}' is not exported by module '{self.name}'")

    def __repr__(self):
        return f"<module {self.name}>"