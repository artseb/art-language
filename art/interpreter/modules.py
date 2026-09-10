import os

from ..errors import ArtError, LangRuntimeError
from ..runtime import Environment
from .. import builtins as builtins_pkg


class ModuleMixin:
    def _module_bind_name(self, rel_path, alias):
        if alias:
            return alias

        stem = os.path.splitext(os.path.basename(rel_path))[0]

        valid = bool(stem) and (stem[0].isalpha() or stem[0] == "_") \
            and all(ch.isalnum() or ch == "_" for ch in stem)

        if not valid:
            raise LangRuntimeError(
                f"Cannot import '{rel_path}': '{stem}' isn't a valid name to "
                f"bind it to. Use 'import \"{rel_path}\" as SomeName' instead."
            )

        return stem

    def _load_module(self, rel_path):
        if not rel_path.endswith(".art"):
            raise LangRuntimeError(
                f"Cannot import '{rel_path}': ART modules must be '.art' files"
            )

        base_dir_real = os.path.realpath(self.base_dir)
        candidate_real = os.path.realpath(
            os.path.join(self.base_dir, rel_path)
        )

        # Path-traversal guard: without this, a script could do
        # `import "../../../etc/passwd.art"` (or follow a symlink that
        # points outside the project) and have an arbitrary file on disk
        # read and fed straight to the lexer/parser. Confine every import
        # to the project's base directory (the folder the entry script
        # lives in).
        if os.path.commonpath([base_dir_real, candidate_real]) != base_dir_real:
            raise LangRuntimeError(
                f"Cannot import '{rel_path}': path escapes the project directory"
            )

        abs_path = candidate_real

        if abs_path in self.module_cache:
            return self.module_cache[abs_path]
        if abs_path in self._loading:
            raise LangRuntimeError(f"Circular import detected: '{rel_path}'")
        if not os.path.isfile(abs_path):
            raise LangRuntimeError(f"Cannot find module '{rel_path}' (looked at {abs_path})")

        from ..lexer import Lexer
        from ..parser import Parser

        try:
            with open(abs_path, "r") as f:
                source = f.read()
        except OSError as e:
            raise LangRuntimeError(f"Cannot read module '{rel_path}': {e}")

        self._loading.add(abs_path)
        try:
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            module_env = Environment()  # isolated global scope for the module
            builtins_pkg.install(module_env)  # print/attempt/etc. need to be visible here too
            for stmt in ast:
                self._exec(stmt, module_env)
        except ArtError as e:
            raise LangRuntimeError(f"While importing '{rel_path}': {e}")
        finally:
            self._loading.discard(abs_path)

        self.module_cache[abs_path] = module_env
        return module_env