/** Static knowledge about ART: keywords, builtins and type names.
 *
 * Mirrors `register_keyword(...)` calls in art/features/*.py, the
 * `@native(...)` builtins in art/builtins/, and RUNTIME_TYPE_NAMES in
 * art/runtime/values.py.
 */

export interface Documented {
  name: string;
  signature?: string;
  documentation: string;
}

export const KEYWORDS: Documented[] = [
  { name: 'local', documentation: 'Declares a variable, function or class scoped to the current block.' },
  { name: 'static', documentation: 'Declares a field or class that belongs to the class itself rather than an instance.' },
  { name: 'fun', signature: 'fun name(params) -> Type { ... }', documentation: 'Declares a function. Omit the name for an anonymous function (a closure). Functions can be overloaded by parameter list.' },
  { name: 'class', signature: 'class Name extends Parent implements Interface { ... }', documentation: 'Declares a class. A method named after the class is its constructor.' },
  { name: 'extends', documentation: 'Inherits from another class.' },
  { name: 'implements', documentation: 'Declares that a class implements an interface.' },
  { name: 'import', signature: 'import "module.art" as Alias', documentation: 'Imports another ART file, relative to the importing file.' },
  { name: 'as', documentation: 'Names the module bound by an `import`.' },
  { name: 'return', documentation: 'Returns a value from the enclosing function.' },
  { name: 'if', signature: 'if (condition) { ... } else { ... }', documentation: 'Conditional execution.' },
  { name: 'else', documentation: 'Alternative branch of an `if`, or the default branch of a `switch`.' },
  { name: 'while', signature: 'while (condition) { ... }', documentation: 'Loops while the condition is truthy.' },
  { name: 'for', signature: 'for (local key, value in table) { ... }', documentation: 'Iterates over a table, binding key and value.' },
  { name: 'in', documentation: 'Separates the loop bindings from the iterated table in a `for` loop.' },
  { name: 'break', documentation: 'Exits the innermost loop.' },
  { name: 'continue', documentation: 'Skips to the next iteration of the innermost loop.' },
  { name: 'switch', signature: 'switch (value) { case match: ... else: ... }', documentation: 'Dispatches on a value.' },
  { name: 'case', documentation: 'A branch of a `switch`.' },
  { name: 'and', documentation: 'Logical AND. Returns the first falsy operand, otherwise the last one.' },
  { name: 'or', documentation: 'Logical OR. Returns the first truthy operand, otherwise the last one.' },
  { name: 'true', documentation: 'Boolean true.' },
  { name: 'false', documentation: 'Boolean false.' },
  { name: 'nil', documentation: 'The absence of a value.' },
  { name: 'super', signature: 'super(args)', documentation: 'Calls the parent constructor, or accesses a parent member with `super.member`.' },
  { name: 'this', documentation: 'The current instance inside a method.' },
  { name: 'get', signature: 'get name() { ... }', documentation: 'Declares a property getter.' },
  { name: 'set', signature: 'set name(value) { ... }', documentation: 'Declares a property setter.' },
  { name: 'operator', signature: 'operator <(other) { ... }', documentation: 'Overloads an operator for instances of the class.' },
  { name: 'enum', signature: 'enum Name { MEMBER(args), ... }', documentation: 'Declares an enum whose members are singleton instances.' },
];

export const BUILTINS: Documented[] = [
  {
    name: 'print',
    signature: 'print(value)',
    documentation: 'Writes the stringified value to standard output.',
  },
  {
    name: 'attempt',
    signature: 'attempt(callee, ...args) -> (result, error)',
    documentation:
      'Calls `callee` with the given arguments and captures any runtime error instead of aborting. ' +
      'Returns the result and an error message, the second of which is `nil` on success:\n\n' +
      '```art\nlocal ok, err = attempt(risky, 1, 2)\n```',
  },
];

export const TYPE_NAMES: Documented[] = [
  { name: 'Int', documentation: 'Number type name accepted in annotations.' },
  { name: 'Float', documentation: 'Number type name accepted in annotations.' },
  { name: 'Number', documentation: 'Number type name accepted in annotations.' },
  { name: 'String', documentation: 'String type name accepted in annotations.' },
  { name: 'Bool', documentation: 'Boolean type name accepted in annotations.' },
  { name: 'Boolean', documentation: 'Boolean type name accepted in annotations.' },
  { name: 'Table', documentation: 'Table type name accepted in annotations.' },
];

const byName = (items: Documented[]) =>
  new Map(items.map((item) => [item.name, item]));

export const KEYWORDS_BY_NAME = byName(KEYWORDS);
export const BUILTINS_BY_NAME = byName(BUILTINS);
export const TYPE_NAMES_BY_NAME = byName(TYPE_NAMES);
