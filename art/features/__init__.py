"""
Every ART language construct as one file: its AST node(s), the tokens
and keywords it needs (registered into tokens.KEYWORDS as a side effect
of import), how the parser recognizes it, and how the interpreter runs
it. See art/parser/registry.py and art/interpreter/registry.py for the
five self-registration tables these files plug into.

Importing this package (from art/lexer.py, art/parser/core.py, and
art/interpreter/core.py - each needs a different piece of what gets
registered here, and importing more than once is harmless/cheap since
Python caches it) is what actually makes every feature "live". Adding
a new one means adding a new file here and importing it below -
nothing in lexer.py, parser/core.py, or interpreter/core.py ever needs
to change.
"""
from .literals import *       # noqa: F401
from .variables import *      # noqa: F401
from .operators import *      # noqa: F401
from .access import *         # noqa: F401
from .calls import *          # noqa: F401
from .functions import *      # noqa: F401
from .basics import *         # noqa: F401
from .control_flow import *   # noqa: F401
from .switch_ import *        # noqa: F401
from .classes_ import *       # noqa: F401
from .enums import *          # noqa: F401
from .imports_ import *       # noqa: F401