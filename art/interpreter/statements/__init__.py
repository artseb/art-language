"""Importing this subpackage runs every handler module below once,
registering their @exec_handler(...)-decorated functions into
interpreter.registry.EXEC_HANDLERS. Add a new statement type by adding a
new file here (or a new handler to an existing one) - nothing else
needs to import it by name."""
from . import control_flow  # noqa: F401
from . import declarations  # noqa: F401
from . import imports  # noqa: F401
from . import misc  # noqa: F401
