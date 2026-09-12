# ART

A small dynamically-typed scripting language (Java-style classes, Lua-style
tables, Kotlin-style `fun` declarations) with a tree-walking interpreter
written in Python.

```
python3 run.py path/to/script.art
```

Set `ART_DEBUG=1` to get a full Python traceback for genuine interpreter
bugs instead of the short "Internal interpreter error" summary.

## Editor support

[`editors/vscode`](editors/vscode) is a VS Code extension for ART:
syntax highlighting, live lex/parse diagnostics, outline, go-to-definition,
hover, completion, snippets and an `ART: Run File` command. See its
[README](editors/vscode/README.md) for installation.

## Tools

```
python3 tools/art_check.py path/to/script.art   # or --stdin
```

Lexes and parses a script - without running it - and prints any problem as
JSON. This is what the editor extension uses for diagnostics, and it works
as a standalone syntax check in CI.