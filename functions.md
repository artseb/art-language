# Functions

Functions are declared with `fun`.

```art
fun add(a, b) {
    return a + b
}

result = add(10, 20)
```

Functions can be stored in variables and passed as values.

## Lambdas

Anonymous functions can be created with `fun` expressions.

```art
add = fun(a, b) {
    return a + b
}
```

## Overloading

A function can have multiple overloads. The runtime selects an applicable overload from the call arguments.

## Return Values

Use `return` to leave a function and optionally provide a value.

## Constructors

Classes can define initialization behavior through their constructor function.