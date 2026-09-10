# ART

A small dynamically-typed scripting language (Java-style classes, Lua-style
tables, Kotlin-style `fun` declarations) with a tree-walking interpreter
written in Python.

```
python3 run.py path/to/script.art
```

Set `ART_DEBUG=1` to get a full Python traceback for genuine interpreter
bugs instead of the short "Internal interpreter error" summary.