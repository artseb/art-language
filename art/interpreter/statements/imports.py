"""`import "file.art" [as Alias]`. The actual file-loading/caching lives
on the interpreter itself (see interpreter/modules.py) since it's
recursive - this is just the statement handler that binds the result to
a name in the current scope."""
from ...ast import Import
from ...runtime import LangModule
from ..registry import exec_handler


@exec_handler(Import)
def _exec_import(interp, node, env):
    """import "file.art"        -> binds a module named after the file;
                                    members are reached as file.method(...)
       import "file.art" as Foo -> binds it as Foo instead; Foo.method(...)

    This replaced an older, more surprising form where a plain
    `import "file.art"` (no `as`) silently merged every top-level name
    from the file directly into the importing scope, which made it
    very easy to accidentally shadow a local name and to lose track of
    where an identifier actually came from.
    """
    module_env = interp._load_module(node.path)
    name = interp._module_bind_name(node.path, node.alias)

    module = LangModule(name, dict(module_env.values))
    env.define(name, module)
