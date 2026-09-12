"""
Self-registration for statement/expression handlers.

The old interpreter was one class with a `_exec_<NodeType>` or
`_eval_<NodeType>` method per AST node, all in a single ~1000-line file.
The dispatch *shape* (look up a handler by node type) was already fine;
what didn't scale was cramming every handler's body into that one file.

Here, each handler is a plain function living in whichever file under
`statements/` or `expressions/` owns that concern, and it registers
itself for the node type(s) it handles with a decorator:

    # interpreter/statements/control_flow.py
    @exec_handler(If)
    def _exec_if(interp, node, env):
        ...

`interp._exec(node, env)` / `interp._eval(node, env)` then just look the
node's type up in these tables - same O(1) dispatch as before, but any
file can contribute handlers, and adding a new node type never means
touching this file or the core Interpreter class.
"""

EXEC_HANDLERS = {}
EVAL_HANDLERS = {}


def exec_handler(*node_classes):
    """Register a statement handler: fn(interp, node, env) -> None."""
    def decorator(fn):
        for node_class in node_classes:
            if node_class in EXEC_HANDLERS:
                raise RuntimeError(
                    f"Exec handler for {node_class.__name__} already "
                    f"registered (duplicate from {fn.__module__}.{fn.__name__})"
                )
            EXEC_HANDLERS[node_class] = fn
        return fn
    return decorator


def eval_handler(*node_classes):
    """Register an expression handler: fn(interp, node, env) -> value."""
    def decorator(fn):
        for node_class in node_classes:
            if node_class in EVAL_HANDLERS:
                raise RuntimeError(
                    f"Eval handler for {node_class.__name__} already "
                    f"registered (duplicate from {fn.__module__}.{fn.__name__})"
                )
            EVAL_HANDLERS[node_class] = fn
        return fn
    return decorator
