from .base import Node

class ExpressionStmt(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"ExpressionStmt({self.expr!r})"


class MultiAssign(Node):
    def __init__(self, names, values, is_local=False):
        self.names = names
        self.values = values
        self.is_local = is_local

    def __repr__(self):
        return (
            f"MultiAssign("
            f"{self.names!r}, "
            f"{self.values!r}, "
            f"local={self.is_local}"
            f")"
        )


class Block(Node):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({self.statements!r})"


class If(Node):
    def __init__(self, condition, then_branch, else_branch):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def __repr__(self):
        return f"If({self.condition!r}, {self.then_branch!r}, {self.else_branch!r})"


class While(Node):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"While({self.condition!r}, {self.body!r})"


class Param(Node):
    def __init__(self, name, type_name, default=None, variadic=False):
        self.name = name
        self.type_name = type_name
        self.default = default
        self.variadic = variadic

    def __repr__(self):
        prefix = "..." if self.variadic else ""
        return f"Param({prefix}{self.name}: {self.type_name} = {self.default!r})"


class FunDecl(Node):
    def __init__(self, name, params, body, is_local=False, return_type=None):
        self.name = name
        self.params = params
        self.body = body
        self.is_local = is_local
        self.return_type = return_type

    def __repr__(self):
        return f"FunDecl({self.name}, {self.params!r}, local={self.is_local})"


class Return(Node):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Return({self.value!r})"


class ClassDecl(Node):
    def __init__(self, name, superclass, interfaces, body, is_local=False):
        self.name = name
        self.superclass = superclass      # str or None
        self.interfaces = interfaces      # list[str]
        self.body = body                  # list[FunDecl | Assign | ClassDecl]
        self.is_local = is_local

    def __repr__(self):
        return f"ClassDecl({self.name}, extends={self.superclass}, implements={self.interfaces}, local={self.is_local})"


class Import(Node):
    def __init__(self, path, alias):
        self.path = path    # str, the raw string literal (a file path)
        self.alias = alias  # str or None

    def __repr__(self):
        return f"Import({self.path!r}, as={self.alias})"


class Break(Node):
    def __repr__(self):
        return "Break()"


class Continue(Node):
    def __repr__(self):
        return "Continue()"


class For(Node):
    def __init__(self, variable, start, end, step, body, key=None, value=None, iterable=None):
        self.variable = variable
        self.start = start
        self.end = end
        self.step = step
        self.body = body

        self.key = key
        self.value = value
        self.iterable = iterable

    def __repr__(self):
        if self.iterable is not None:
            return f"For({self.key!r}, {self.value!r} in {self.iterable!r})"

        return f"For({self.variable!r} = {self.start!r}->{self.end!r}; {self.step!r})"


class Getter(Node):
    def __init__(self, name, body):
        self.name = name
        self.body = body


class Setter(Node):
    def __init__(self, name, param, body):
        self.name = name
        self.param = param
        self.body = body


class OperatorDecl(Node):
    def __init__(self, operator, params, body):
        self.operator = operator
        self.params = params
        self.body = body


class EnumMember(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"EnumMember({self.name}, {self.args!r})"


class EnumDecl(Node):
    def __init__(self, name, members, body, is_local=False):
        self.name = name
        self.members = members
        self.body = body
        self.is_local = is_local

    def __repr__(self):
        return (
            f"EnumDecl("
            f"{self.name}, "
            f"{self.members!r}, "
            f"local={self.is_local}"
            f")"
        )


class SwitchCase(Node):
    def __init__(self, values, body):
        self.values = values
        self.body = body

    def __repr__(self):
        return f"SwitchCase({self.values!r}, {self.body!r})"


class Switch(Node):
    def __init__(self, value, cases, default=None):
        self.value = value
        self.cases = cases
        self.default = default

    def __repr__(self):
        return (
            f"Switch("
            f"{self.value!r}, "
            f"{self.cases!r}, "
            f"default={self.default!r}"
            f")"
        )