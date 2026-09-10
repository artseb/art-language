"""Binary and unary operators, including operator-overload dispatch to a
class's `operator ==` etc. methods and the numeric-operand type checks."""
from ...ast import Binary, Unary
from ...errors import LangRuntimeError
from ...runtime import LangInstance, stringify
from ..registry import eval_handler

_ARITHMETIC_OPS = {"+", "-", "*", "/"}
_COMPARISON_OPS = {"<", "<=", ">", ">="}


def _check_numeric_operands(interp, op, left, right, token):
    if not isinstance(left, (int, float)) or isinstance(left, bool):
        raise LangRuntimeError(
            f"Operator '{op}' expects a number on the left, got {interp._type_name(left)}",
            token,
        )
    if not isinstance(right, (int, float)) or isinstance(right, bool):
        raise LangRuntimeError(
            f"Operator '{op}' expects a number on the right, got {interp._type_name(right)}",
            token,
        )


@eval_handler(Binary)
def _eval_binary(interp, node, env):
    op_token = node.op
    op = op_token.lexeme
    left = interp._eval(node.left, env)

    if op == "and":
        if not interp._truthy(left):
            return left
        return interp._eval(node.right, env)

    if op == "or":
        if interp._truthy(left):
            return left
        return interp._eval(node.right, env)

    right = interp._eval(node.right, env)

    if isinstance(left, LangInstance):
        operator = left.klass.operators.get(op)

        if operator is not None:
            return interp._call_function(operator, [right], this=left)

    if op == "!=" and isinstance(left, LangInstance):
        operator = left.klass.operators.get("==")

        if operator is not None:
            result = interp._call_function(operator, [right], this=left)
            return not interp._truthy(result)

    if op == "+" and (isinstance(left, str) or isinstance(right, str)):
        return stringify(left) + stringify(right)

    if op in _ARITHMETIC_OPS or op in _COMPARISON_OPS:
        _check_numeric_operands(interp, op, left, right, op_token)

    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise LangRuntimeError("Division by zero", op_token)
        return left / right
    if op == "==":
        return interp._values_equal(left, right)
    if op == "!=":
        return not interp._values_equal(left, right)
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right

    raise LangRuntimeError(f"Unknown binary operator '{op}'", op_token)


@eval_handler(Unary)
def _eval_unary(interp, node, env):
    op_token = node.op
    op = op_token.lexeme
    right = interp._eval(node.right, env)

    if op == "-":
        if not isinstance(right, (int, float)) or isinstance(right, bool):
            raise LangRuntimeError(
                f"Unary '-' expects a number, got {interp._type_name(right)}",
                op_token,
            )
        return -right
    if op == "!":
        return not interp._truthy(right)

    raise LangRuntimeError(f"Unknown unary operator '{op}'", op_token)
