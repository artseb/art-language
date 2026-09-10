from ..ast import ExpressionStmt
from ..runtime import Environment


class SwitchMixin:
    def _find_switch_case(self, node, env):
        value = self._eval(node.value, env)

        for case in node.cases:
            for case_value in case.values:
                evaluated = self._eval(case_value, env)
                if self._values_equal(value, evaluated):
                    return case.body

        return node.default

    def _eval_switch_body(self, body, env):
        block_env = Environment(env)
        result = None

        for stmt in body.statements:
            if isinstance(stmt, ExpressionStmt):
                result = self._eval(stmt.expr, block_env)
            else:
                self._exec(stmt, block_env)

        return result
