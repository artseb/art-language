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
