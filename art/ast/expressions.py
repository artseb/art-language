from .base import Node

class Literal(Node):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Literal({self.value!r})"

class Variable(Node):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Variable({self.name})"

class Assign(Node):
    def __init__(self, name, value, is_local=False, is_static=False):
        self.name = name
        self.value = value
        self.is_local = is_local
        self.is_static = is_static

    def __repr__(self):
        return f"Assign({self.name}, {self.value!r}, local={self.is_local})"

class Binary(Node):
    def __init__(self, left, op, right):
        super().__init__(op)
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"Binary({self.left!r} {self.op.lexeme} {self.right!r})"

class Unary(Node):
    def __init__(self, op, right):
        super().__init__(op)
        self.op = op
        self.right = right

    def __repr__(self):
        return f"Unary({self.op.lexeme}{self.right!r})"

class Call(Node):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def __repr__(self):
        return f"Call({self.callee!r}, {self.args!r})"

class Get(Node):
    def __init__(self, obj, name):
        self.obj = obj
        self.name = name

    def __repr__(self):
        return f"Get({self.obj!r}.{self.name})"

class Set(Node):
    def __init__(self, obj, name, value):
        self.obj = obj
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Set({self.obj!r}.{self.name} = {self.value!r})"


class TableLiteral(Node):
    def __init__(self, entries):
        self.entries = entries

    def __repr__(self):
        return f"TableLiteral({self.entries!r})"

class Index(Node):
    def __init__(self, obj, index):
        self.obj = obj
        self.index = index

    def __repr__(self):
        return f"Index({self.obj!r}[{self.index!r}])"


class IndexSet(Node):
    def __init__(self, obj, index, value):
        self.obj = obj
        self.index = index
        self.value = value

    def __repr__(self):
        return f"IndexSet({self.obj!r}[{self.index!r}] = {self.value!r})"

class Lambda(Node):
    def __init__(self, params, body, return_type=None):
        self.params = params
        self.body = body
        self.return_type = return_type

    def __repr__(self):
        return f"Lambda({self.params!r}, {self.body!r}, {self.return_type!r})"

class Super(Node):
    def __init__(self):
        pass

    def __repr__(self):
        return "Super()"