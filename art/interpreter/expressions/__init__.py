"""Importing this subpackage runs every handler module below once,
registering their @eval_handler(...)-decorated functions into
interpreter.registry.EVAL_HANDLERS. Add a new expression type by adding
a new file here (or a new handler to an existing one) - nothing else
needs to import it by name."""
from . import literals  # noqa: F401
from . import variables  # noqa: F401
from . import operators  # noqa: F401
from . import access  # noqa: F401
from . import calls  # noqa: F401
from . import switch  # noqa: F401
