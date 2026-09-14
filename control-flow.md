# Control Flow

## Conditions

```art
if (health > 0) {
    print("alive")
} else {
    print("dead")
}
```

## While

```art
while (condition) {
    doSomething()
}
```

## For

ART supports `for` loops, including iteration over values.

## Break and Continue

`break` exits a loop. `continue` skips to the next iteration.

## Switch

`switch` supports multiple cases and an optional `else` branch.

```art
switch (state) {
    case Idle:
        print("idle")
    case Running:
        print("running")
    else:
        print("other")
}
```

A switch can also be used as an expression and produce a value.