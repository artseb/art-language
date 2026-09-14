# Runtime Architecture

ART is currently implemented as a tree-walking interpreter written in Python.

The implementation is separated into several major stages and systems:

- Lexer: converts source text into tokens.
- Parser: converts tokens into the language's syntax structures.
- Features: implements individual language constructs.
- Interpreter: evaluates parsed structures.
- Runtime: represents values, environments, functions, classes, instances, modules, and tables.
- Builtins: exposes functionality implemented by the host runtime.
- Standard library: provides functionality written in ART itself.

## Current Implementation

Python was chosen because it makes language experimentation and iteration practical during development.

It is not intended to be the final implementation. ART is planned to eventually move toward a faster implementation using a language from the C family; the exact choice between C, C++, and C# has not been made.

The current Python interpreter is therefore both the implementation people can use today and the foundation for developing the language itself.