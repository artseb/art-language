# Classes

ART supports classes and object instances.

```art
class Player {
    local health = 100

    fun damage(amount) {
        health = health - amount
    }
}
```

## Construction

A class can define an initializer and be called to create an instance.

## Inheritance

Classes can extend other classes.

## Interfaces

Classes can implement interfaces.

## Static Members

Classes can contain static members that belong to the class rather than an individual instance.

## Getters and Setters

Properties can define getter and setter behavior.

## Nested Classes

Classes can contain other class declarations.

## `this` and `super`

`this` refers to the current instance. `super` can be used when working with inherited behavior.