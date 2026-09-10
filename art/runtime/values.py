from .tables import LangTable
from .classes import LangInstance
from ..errors import LangRuntimeError


TYPE_NAMES = {
    float: ("Int", "Number", "Float"),
    str: ("String",),
    bool: ("Bool", "Boolean"),
    LangTable: ("Table",),
}


def runtime_type_matches(value, type_name):
    if type_name is None:
        return True

    for py_type, names in TYPE_NAMES.items():
        if isinstance(value, py_type) and type_name in names:
            return True

    if isinstance(value, LangInstance):
        klass = value.klass

        while klass is not None:
            if klass.name == type_name:
                return True

            klass = klass.superclass

    return False


def stringify(value):
    if value is None:
        return "nil"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

        return str(value)

    return str(value)


class LangEnum:
    def __init__(self, name, klass):
        self.name = name
        self.klass = klass
        self.members = {}

    def get(self, name):
        if name not in self.members:
            raise LangRuntimeError(
                f"Enum '{self.name}' has no member '{name}'"
            )
        return self.members[name]

    def add_member(self, name, instance):
        self.members[name] = instance

    def get_members(self):
        table = LangTable()

        for name, instance in self.members.items():
            table.set(name, instance)

        table.make_immutable()
        return table

    def __repr__(self):
        return f"<enum {self.name}>"