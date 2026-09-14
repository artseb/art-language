# ART

ART is a small, dynamically typed programming language designed to be simple to write, flexible to use, and capable of supporting larger projects.

It is currently written in Python and runs through a tree-walking interpreter.

## Features

ART currently supports:

* Variables and multiple-variable declarations
* Local variables
* Tables with array and key-value entries
* Functions
* Lambda functions
* Function overloading
* Classes and objects
* Inheritance
* Static members
* Getters and setters
* Nested classes
* Operator overloading
* Enums
* `if` / `else`
* `while` and `for` loops
* `break` and `continue`
* `switch` statements and expressions
* Imports and modules
* String utilities
* Mathematical functions
* Exponentiation
* A syntax checker for scripts

ART is still actively evolving, so some of these systems may change as the language develops.

## Example

A small ART program can look like this:

```art
class Player {
    local name
    local health = 100

    fun init(name) {
        this.name = name
    }

    fun damage(amount) {
        health = health - amount
    }

    fun isAlive() {
        return health > 0
    }
}

local player = Player("Seb")

player.damage(25)

if (player.isAlive()) {
    print(player.name + " is still alive")
}
```

The goal is to keep programs readable without requiring large amounts of boilerplate.

## Local Variables

ART uses `local` to explicitly define variables that belong to the current scope.

This provides a simple way to control variable scope without relying on separate public/private declarations.

```art
name = "Seb" // still valid, global
local health = 100
```

Variables can also be declared together:

```art
local x, y = 20, 10
```

both being `local` ^

`_` can be used when a returned value should be discarded.

## Functions

Functions are first-class values and can be stored, passed around, and called dynamically.

```art
fun add(a, b) {
    return a + b
}

print(add(10, 20))
```

Functions can also have multiple overloads, allowing different implementations to exist for different argument combinations.

## Classes

ART supports object-oriented programming through classes.

Classes can contain fields, functions, static members, getters, setters, and nested classes.

```art
class Enemy {
    local health = 100
    static maxHealth = 100

    fun damage(amount) {
        health = health - amount
    }

    set health(amount) {
        if (amount > maxHealth) {
            health = maxHealth
        } else if (amount < 0) {
            health = 0
        } else {
            health = amount
        }
    }
}
```

Classes can also inherit from other classes and implement interfaces.

## Tables

Tables are ART's general-purpose collection type.

They can contain indexed values, key-value pairs, or a mixture of both.

```art
numbers = [10, 20, 30]

local player = {
    name = "Seb",
    health = 100
}
```

Tables are useful for everything from simple lists to structured data.

## Operator Overloading

Operators can be implemented by user-defined types.

This allows custom objects to define how operations such as:

```text
+
-
*
/
==
```

behave when used with them.

This is particularly useful for mathematical types, data structures, and other objects that naturally support operators.

## Enums

ART supports enums for representing a fixed set of named values.

```art
enum State {
    Idle,
    Running,
    Dead
}
```

## Control Flow

ART provides the standard control-flow tools needed for scripting and general programming:

* `if` / `else`
* `while`
* `for`
* `break`
* `continue`
* `switch`

`switch` can also be used as an expression when a value needs to be produced.

## Modules

ART supports importing code from other files, allowing projects to be separated into multiple modules instead of keeping everything in one script.

## Standard Library

ART currently includes basic functionality for:

* Mathematics
* Strings
* Input/output
* Control flow utilities

The standard library is still growing alongside the language itself.

## Development

ART is currently implemented in Python.

This was intentional during the early development of the language because Python makes it practical to experiment with the lexer, parser, interpreter, runtime, and language features quickly.

However, Python is not the intended final implementation.

Python is significantly slower than languages commonly used when performance is important, particularly for applications such as games and other real-time software. Because of this, one of the long-term goals of ART is to move the language's implementation to a compiled language.

The exact language has not been decided yet. The current candidates are:

* C
* C++
* C#

The roadmap may refer to this generally as a conversion to C, but this means the broader C-family of languages rather than a final decision to use C specifically.

The Python implementation therefore serves as the foundation for designing and testing the language before moving toward a faster implementation.

## Editor Support

ART includes a semi-working VS Code extension with support for:

* Live syntax diagnostics
* Outline support
* Snippets
* Running ART files

The extension is located in:

```text
editors/vscode/
```

## Syntax Checking

ART includes a standalone syntax checker that can parse a script without running it.

```text
python tools/art_check.py path/to/script.art
```

This is also used by the VS Code extension to provide diagnostics while editing.

## Project Structure

```text
art/
├── features/       Language features
├── builtins/       Built-in functionality
├── runtime/        Runtime objects and execution
├── interpreter/    Interpreter implementation
└── tokens.py       Token definitions

std/                Standard library
editors/vscode/     VS Code extension
tools/              Development tools
run.py              ART entry point
ROADMAP.md          Development roadmap
```

## Roadmap

ART is still under development.

The long-term goal is to evolve ART from a small interpreted language into a more complete programming language with a faster implementation and a larger ecosystem.

Planned development includes:

* Continuing to expand the language
* Improving the runtime
* Expanding the standard library
* Improving tooling
* Improving editor support
* Experimenting with a compiled implementation
* Eventually moving away from the Python implementation for performance

The roadmap is intentionally subject to change as the language develops.

## Philosophy

ART is primarily an experiment in designing a programming language that is enjoyable to use while still providing enough functionality for serious projects.

The focus is on keeping the language flexible without making every feature unnecessarily complicated.

It is not intended to copy the design of any single existing language. Its syntax and behavior are being developed independently as the project evolves.