# Tooling

## Running ART

The repository entry point is `run.py`.

```text
python run.py path/to/script.art
```

## Syntax Checker

ART includes a standalone checker that lexes and parses a script without executing it.

```text
python tools/art_check.py path/to/script.art
```

It is also used by the VS Code extension for diagnostics.

## VS Code

The repository contains a VS Code extension under `editors/vscode/`.

It currently provides syntax support, diagnostics, outline information, snippets, and the ability to run ART files.