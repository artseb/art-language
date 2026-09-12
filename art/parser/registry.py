"""
Self-registration for the parser, mirroring interpreter/registry.py.

A hand-written recursive-descent parser doesn't dispatch as cleanly as
a tree-walking interpreter does (grammar rules have to be tried in a
specific order, and some only apply given surrounding context like
"are we inside a class body"), but the parts that genuinely are "which
single leading token am I looking at" decisions - starting a statement,
starting a primary expression, a declaration keyword, a postfix `.`/`(`/`[`
- work exactly the same way: register a parser function per TokenType,
look it up by the token actually seen, done.

Five tables, one per decision point in art/parser/core.py:

  STMT_PARSERS      - `_statement()`: if/while/for/break/continue/switch/...
  DECL_PARSERS       - `_declaration()`: class/fun/enum/get/set/operator/static/import
  PRIMARY_PARSERS   - `_primary()`: literals, identifiers, lambdas, switch-as-expr, ...
  POSTFIX_PARSERS   - `_call()`'s postfix loop: `(args)`, `.name`, `[index]`
  ASSIGN_BUILDERS   - `_assignment()`: what `target = value` builds, keyed by
                       the type of the already-parsed left-hand expression
                       (Variable -> Assign, Get -> Set, Index -> IndexSet)

Handlers registered in STMT_PARSERS/DECL_PARSERS/PRIMARY_PARSERS/POSTFIX_PARSERS
are responsible for consuming their own leading token(s) - the dispatcher
only peeks to decide *which* handler to call.
"""

STMT_PARSERS = {}
DECL_PARSERS = {}
PRIMARY_PARSERS = {}
POSTFIX_PARSERS = {}
ASSIGN_BUILDERS = {}


def _make_registrar(table, label):
    def register(*keys):
        def decorator(fn):
            for key in keys:
                if key in table:
                    raise RuntimeError(
                        f"{label} for {key!r} already registered "
                        f"(duplicate from {fn.__module__}.{fn.__name__})"
                    )
                table[key] = fn
            return fn
        return decorator
    return register


stmt_parser = _make_registrar(STMT_PARSERS, "Statement parser")
decl_parser = _make_registrar(DECL_PARSERS, "Declaration parser")
primary_parser = _make_registrar(PRIMARY_PARSERS, "Primary parser")
postfix_parser = _make_registrar(POSTFIX_PARSERS, "Postfix parser")
assignment_target = _make_registrar(ASSIGN_BUILDERS, "Assignment target builder")
