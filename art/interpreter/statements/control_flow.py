"""Loops, branches, and the statement forms that unwind the stack
(break/continue/switch-as-statement)."""
from ...ast import Block, If, While, Break, Continue, For, Switch
from ...errors import LangRuntimeError
from ...runtime import Environment, LangTable
from ..registry import exec_handler
from ..signals import BreakSignal, ContinueSignal


@exec_handler(Block)
def _exec_block(interp, node, env):
    block_env = Environment(env)
    for stmt in node.statements:
        interp._exec(stmt, block_env)


@exec_handler(If)
def _exec_if(interp, node, env):
    if interp._truthy(interp._eval(node.condition, env)):
        interp._exec(node.then_branch, env)
    elif node.else_branch is not None:
        interp._exec(node.else_branch, env)


@exec_handler(While)
def _exec_while(interp, node, env):
    while interp._truthy(interp._eval(node.condition, env)):
        try:
            interp._exec(node.body, env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break


@exec_handler(Break)
def _exec_break(interp, node, env):
    raise BreakSignal()


@exec_handler(Continue)
def _exec_continue(interp, node, env):
    raise ContinueSignal()


@exec_handler(For)
def _exec_for(interp, node, env):
    if node.iterable is None:
        start = interp._eval(node.start, env)
        end = interp._eval(node.end, env)
        step = interp._eval(node.step, env)

        if step == 0:
            raise LangRuntimeError("For loop step cannot be zero")

        loop_env = Environment(env)
        loop_env.define(node.variable, start)

        while True:
            current = loop_env.get(node.variable)

            if step > 0 and current > end:
                break
            if step < 0 and current < end:
                break

            try:
                interp._exec(node.body, loop_env)
            except ContinueSignal:
                pass
            except BreakSignal:
                break

            current = loop_env.get(node.variable)
            loop_env.assign_existing_or_global(
                node.variable,
                current + step
            )

        return

    table = interp._eval(node.iterable, env)

    if not isinstance(table, LangTable):
        raise LangRuntimeError(
            f"Cannot iterate over {table!r}"
        )

    loop_env = Environment(env)

    for index, value in enumerate(table.array, start=1):
        loop_env.define(node.key, index)
        loop_env.define(node.value, value)

        try:
            interp._exec(node.body, loop_env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break

    for key, value in table.map.items():
        loop_env.define(node.key, key)
        loop_env.define(node.value, value)

        try:
            interp._exec(node.body, loop_env)
        except ContinueSignal:
            continue
        except BreakSignal:
            break


@exec_handler(Switch)
def _exec_switch(interp, node, env):
    body = interp._find_switch_case(node, env)
    if body is not None:
        interp._exec(body, env)
