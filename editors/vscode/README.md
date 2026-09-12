# ART Language for VS Code

Editor support for [ART](https://github.com/artseb/art-language), a small
dynamically-typed scripting language with a tree-walking interpreter
written in Python.

## Features

- **Syntax highlighting** for every construct the language has today:
  `class`/`extends`/`implements`, `enum`, `fun` (named, anonymous,
  overloaded), `get`/`set` accessors, `operator` overloads, `switch`/`case`,
  `for ... in`, type annotations (`name: String`, `-> Int`), variadics
  (`...rest`), tables, nested block comments and string escapes.
- **Live error checking.** Squiggles come from the real interpreter -
  the extension pipes your buffer through `tools/art_check.py`, which runs
  ART's own lexer and parser - so the message and location match exactly
  what `python3 run.py` would print. Nothing is executed while checking.
- **Outline and breadcrumbs**: classes, enums and their members, methods,
  constructors, accessors, operators, imports and locals.
- **Go to definition** and **hover** for declarations in the current file,
  plus documentation on keywords, builtins and type names.
- **Completion** of keywords, builtins and the symbols declared in the
  file, with type names offered after `:` and `->`.
- **Snippets** for the common declarations (`fun`, `class`, `classx`,
  `enum`, `for`, `switch`, `get`, `set`, `operator`, `attempt`, ...).
- **Editing conveniences**: brackets, parentheses and quotes close
  themselves (and wrap the selection when you type one over it), new lines
  keep and adjust their indentation inside blocks, block comments continue
  with `*`, and every save leaves the file ending in one empty line so no
  statement sits on the last line.
- **Run the current file** with `ART: Run File` (`Ctrl+F5` / `Cmd+F5`, or
  the play button in the editor title bar). Output goes to a terminal.

## Requirements

Python 3 and a checkout of the ART interpreter. The extension finds the
interpreter by walking up from the file you are editing, then checking the
open workspace folders, looking for a directory that contains `run.py` and
`art/lexer.py`. Point `art.interpreterPath` at your checkout if it lives
somewhere else.

Syntax highlighting and snippets work without any of that; only
diagnostics and `ART: Run File` need the interpreter.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `art.pythonPath` | `python3` | Python interpreter used to run ART. |
| `art.interpreterPath` | `""` | Path to the art-language checkout (or directly to its `run.py`). Empty means auto-detect. |
| `art.diagnostics.enabled` | `true` | Report lex and parse errors. |
| `art.diagnostics.run` | `onType` | `onType` or `onSave`. |
| `art.diagnostics.delay` | `300` | Debounce in milliseconds for `onType`. |
| `art.insertFinalNewlineOnSave` | `true` | End every saved ART file with a single empty line. |

ART files also default to 4-space indentation; override it in your
settings under `"[art]"` if you prefer something else.

## Installing from source

```bash
cd editors/vscode
npm install
npm run compile
npx @vscode/vsce package --no-dependencies   # produces art-language-<version>.vsix
code --install-extension art-language-0.1.0.vsix
```

Or press `F5` with `editors/vscode` open as the workspace folder to launch
an Extension Development Host on the repository's `examples/` directory.

## Known limitations

- Cross-file analysis is not implemented: go-to-definition, hover and
  completion see only the current file, so symbols reached through
  `import "utils.art" as Utils` are not resolved.
- Diagnostics stop at the first lex or parse error, because the
  interpreter's pipeline does - fix it and the next one appears.
- Nothing is type-checked. Type annotations are checked by the
  interpreter at call time, not by this extension.
