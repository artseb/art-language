# ART Language Roadmap

A phased plan for taking ART from "hobby language with real semantics" to
"full-on language you can actually build things in." Phases are ordered
by dependency, not just importance — later phases lean on earlier ones
being solid.

---

## Phase 1 — Solidify what exists

Fix and round out features that are already half-built before layering
more on top.

- [ ] **Enforce `implements`.** Classes already parse and store
      `implements Interface`, but nothing checks that the class actually
      implements the interface's methods. Currently decorative.
- [ ] **Real `Int` vs `Float` types.** Every number is a Python `float`
      right now. This causes visible inconsistencies today (`print(5)` ->
      `5`, but `print([5])` -> `[1 = 5.0]`, since table printing doesn't
      go through the same clean-number formatting as `print`) and will
      matter a lot more for correctness and performance in the C rewrite.
- [ ] **Static methods**, to match static fields (`static fun helper() {}`).
- [ ] **Better overload-resolution errors.** A failed call should list
      the overloads that *do* exist, not just say "no match."
- [ ] **A real exception system.** `attempt()` only returns an error
      *message string* today - no exception objects, no stack trace, no
      way to distinguish error kinds without string-matching the
      message. This is foundational for everything downstream.

## Phase 2 — Standard library

Right now the entire stdlib is `print` and `attempt`. Roughly in order of
how often each gets reached for:

- [ ] **Strings**: length, split, trim, substring/slice, replace,
      indexOf, upper/lower
- [ ] **String interpolation** (`"Hello, ${name}"`) instead of `+`-chaining
- [ ] **Collections**: push/pop/insert/remove, length, sort, contains
- [ ] **Functional collection ops**: map/filter/reduce (closures already
      exist - this is where they start paying off)
- [ ] **Math**: abs, floor/ceil/round, sqrt, pow, min/max, random
- [ ] **I/O**: stdin, file read/write - design the sandboxing/permission
      model deliberately here, using the same threat model as the import
      path-traversal fix, not bolted on after the fact

## Phase 3 — Ergonomics

Doesn't expand what the language *can* do, but changes whether people
enjoy writing in it.

- [ ] Multi-line strings
- [ ] Destructuring beyond the current `MultiAssign` (pull fields
      straight out of a table/instance in one line)
- [ ] Iterators/generators (`yield`) so `for...in` works over
      user-defined types, not just built-in tables
- [ ] `const`, distinct from `local`
- [ ] Optional-chaining / nullish-coalescing operators (`?.`, `??`)
- [ ] Access modifiers (`private`/`public`) for real encapsulation

## Phase 4 — Tooling

The stuff that makes it feel like *a language*, not *a script you run*.

- [ ] REPL
- [ ] Formatter
- [ ] Test runner / assertion library
- [x] Syntax highlighting grammar (TextMate or tree-sitter) for editors
      and GitHub rendering - see `editors/vscode/syntaxes/art.tmLanguage.json`
- [ ] Language server (LSP) - big lift, do this last; unlocks
      autocomplete and go-to-definition

## Phase 5 — The C rewrite

Decisions worth making on paper *before* porting, not during:

- [ ] **Choose tree-walker vs. bytecode VM.** A bytecode VM is the
      standard path for a "real" language - meaningfully faster, and
      still very achievable (see *Crafting Interpreters* part 2, "clox,"
      as a direct blueprint). Decide now because some current design
      choices are tree-walker-shaped (`attempt()` uses Python's actual
      exception mechanism for control flow) and a VM needs a different
      model (explicit error codes, or `setjmp`/`longjmp`).
- [ ] **Choose a memory management strategy** - reference counting vs. a
      real GC. Matters more than it sounds: tables can already reference
      themselves (cycle-detection was added on the Python side), and
      closures capturing environments create exactly the kind of
      reference cycles plain refcounting can't clean up alone.
- [ ] **String interning** - property names and table keys get compared
      a lot; interning pays for itself quickly in a VM.

---

## Explicitly not on this roadmap (for now)

- Restructuring `interpreter.py`/`parser.py` into smaller files. Worth
  doing if the current size is actively slowing you down day-to-day, but
  the organizational question mostly resets once the C rewrite happens
  (naturally becomes per-concern `.c`/`.h` files, or a data-driven
  bytecode compiler instead of one big recursive-descent tree) - so
  better to spend time on Phases 1-2 above, which carry over into C,
  than on restructuring Python code that's getting thrown away.