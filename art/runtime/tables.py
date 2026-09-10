from ..errors import LangRuntimeError


class LangTable:
    def __init__(self):
        self.array = []
        self.map = {}
        self.immutable = False

    def append(self, value):
        if self.immutable:
            raise LangRuntimeError("Cannot modify an immutable table")
        self.array.append(value)

    def get(self, key):
        # NOTE: reading from an immutable table is always fine, immutability
        # only restricts writes (append/set below). A previous version of
        # this method incorrectly blocked reads too, which made it
        # impossible to ever read back an enum's fields or its .members
        # table once it had been frozen.
        if isinstance(key, float) and key.is_integer():
            key = int(key)

        if isinstance(key, int):
            index = key - 1

            if index < 0 or index >= len(self.array):
                raise LangRuntimeError(
                    f"Table index {key} out of bounds"
                )

            return self.array[index]

        if key in self.map:
            return self.map[key]

        raise LangRuntimeError(
            f"Key {key!r} does not exist in table"
        )

    def set(self, key, value):
        if self.immutable:
            raise LangRuntimeError("Cannot modify an immutable table")

        if isinstance(key, float) and key.is_integer():
            key = int(key)

        if isinstance(key, int):
            index = key - 1

            if index < 0 or index >= len(self.array):
                raise LangRuntimeError(
                    f"Table index {key} out of bounds"
                )

            self.array[index] = value
            return

        self.map[key] = value

    def make_immutable(self):
        self.immutable = True

    def __repr__(self):
        return self._render(set())

    def _render(self, seen):
        # Tables can reference themselves (directly or through a cycle of
        # other tables/instances), which would otherwise blow the Python
        # call stack the moment someone tried to print() one.
        if id(self) in seen:
            return "[...]"
        seen = seen | {id(self)}

        entries = []

        for index, value in enumerate(self.array, start=1):
            entries.append(f"{index} = {self._render_value(value, seen)}")

        for key, value in self.map.items():
            entries.append(f"{key!r} = {self._render_value(value, seen)}")

        return "[" + ", ".join(entries) + "]"

    @staticmethod
    def _render_value(value, seen):
        if isinstance(value, LangTable):
            return value._render(seen)
        return repr(value)