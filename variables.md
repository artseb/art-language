# Variables and Scope

## Global Variables

Variables do not need a declaration keyword.

```art
hello = 10
print(hello)
```

A variable created this way is available through the script's global environment.

## Local Variables

Use `local` when a variable should belong to the current scope.

```art
fun example() {
    local value = 10
    print(value)
}
```

A local variable cannot be accessed outside its scope.

## Shadowing

A local variable can have the same name as a global variable. The local value takes priority inside that scope.

```art
hello = 10

fun example() {
    local hello = 20
    print(hello)
}

example()
print(hello)
```

This prints `20` and then `10`.

## Multiple Variables

Multiple variables can be declared together.

```art
local x, y = 20, 10
```

The `_` name can be used as a discard target when a returned value is not needed.