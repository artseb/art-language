from ..errors import LangRuntimeError
from .functions import BoundMethod

class LangClass:
    def __init__(self, name, superclass, interfaces, closure):
        self.is_enum = False

        self.name = name
        self.superclass = superclass
        self.interfaces = interfaces
        self.closure = closure

        self.methods = {}
        self.field_inits = {}
        self.nested_classes = {}

        self.getters = {}
        self.setters = {}

        self.operators = {}

        # `static x = ...` fields: one shared value per class (not per
        # instance), evaluated once when the class is declared.
        self.static_fields = {}

    def find_method(self, name):
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def find_getter_owner(self, name):
        if name in self.getters:
            return self
        if self.superclass is not None:
            return self.superclass.find_getter_owner(name)
        return None

    def find_setter_owner(self, name):
        if name in self.setters:
            return self
        if self.superclass is not None:
            return self.superclass.find_setter_owner(name)
        return None

    def find_field_inits(self):
        """Collect field initializers up the inheritance chain (base first)."""
        chain = []
        if self.superclass is not None:
            chain.extend(self.superclass.find_field_inits())
        chain.extend(self.field_inits.items())
        return chain

    def find_static_owner(self, name):
        """Return the class (self or an ancestor) that owns static field
        `name`, or None if no class in the chain declares it."""
        if name in self.static_fields:
            return self
        if self.superclass is not None:
            return self.superclass.find_static_owner(name)
        return None

    def get_static(self, name):
        owner = self.find_static_owner(name)
        if owner is None:
            raise LangRuntimeError(f"Class '{self.name}' has no static field '{name}'")
        return owner.static_fields[name]

    def set_static(self, name, value):
        owner = self.find_static_owner(name) or self
        owner.static_fields[name] = value

    def __repr__(self):
        return f"<class {self.name}>"


class LangInstance:
    def __init__(self, klass: LangClass):
        self.klass = klass
        self.fields = {}
        self.is_enum_member = False

    def get(self, name):
        if name in self.fields:
            return self.fields[name]

        method = self.klass.find_method(name)
        if method is not None:
            return BoundMethod(self, method)

        static_owner = self.klass.find_static_owner(name)
        if static_owner is not None:
            return static_owner.static_fields[name]

        raise LangRuntimeError(f"Undefined property '{name}' on instance of {self.klass.name}")

    def set(self, name, value):
        self.fields[name] = value

    def __repr__(self):
        return f"<{self.klass.name} instance>"
