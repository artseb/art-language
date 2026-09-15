"""Native table primitives, following the same convention as
strings.py/mathlib.py: registered under a `__native_table_` prefix and
wrapped by plain ART source in std/table.art, which is the public API
(`table.push(t, v)`, or `t.push(v)` through the method sugar in
features/access.py).
 
Two groups, and which group a function is in is the whole mental model
for the collections library:
 
    mutating   - push, pop, insert, remove, clear, sort, reverse
                 (change the table in place; sort/reverse also return
                 it so calls can be chained)
    derived    - map, filter, reduce, slice, keys, values, contains,
                 indexOf, find
                 (never touch the original; build a new table or a
                 plain value)
 
Everything here works on the array part of a LangTable, except keys()/
values(), which are about the map part - the two halves of a table are
different enough that quietly mixing them into one "sequence" would
make ordering (and therefore sort/slice/indexOf) meaningless.
"""
import functools
from typing import TYPE_CHECKING
 
from . import native
from ..errors import LangRuntimeError
from ..runtime import LangTable
 
if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
 
 
def _require_table(name, value, position="argument"):
    if not isinstance(value, LangTable):
        raise LangRuntimeError(
            f"{name}() expects a table {position}, got {type(value).__name__}"
        )
    return value
 
 
def _require_mutable(name, table):
    # LangTable.append/set enforce this themselves, but the functions
    # below reach for `table.array` directly (that's the only way to
    # pop/insert/sort at all), which would otherwise walk straight past
    # an enum's frozen tables.
    if table.immutable:
        raise LangRuntimeError(f"{name}() cannot modify an immutable table")
    return table
 
 
def _require_index(name, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise LangRuntimeError(f"{name}() expects a numeric index, got {type(value).__name__}")
    return int(value)
 
 
def _values_equal(left, right):
    try:
        return bool(left == right)
    except TypeError:
        return False
 
 
@native("__native_table_push")
def _push(interp, args):
    if len(args) < 2:
        raise LangRuntimeError(f"push() expects at least 2 arguments, got {len(args)}")
 
    table = _require_mutable("push", _require_table("push", args[0]))
    for value in args[1:]:
        table.array.append(value)
    return table
 
 
@native("__native_table_pop", arity=1)
def _pop(interp, args):
    table = _require_mutable("pop", _require_table("pop", args[0]))
 
    if not table.array:
        raise LangRuntimeError("pop() called on an empty table")
 
    return table.array.pop()
 
 
@native("__native_table_insert", arity=3)
def _insert(interp, args):
    table = _require_mutable("insert", _require_table("insert", args[0]))
    index = _require_index("insert", args[1])
 
    # 1-indexed, and inserting at len+1 appends - the same "one past
    # the end is a valid position" rule every insert API needs.
    if index < 1 or index > len(table.array) + 1:
        raise LangRuntimeError(f"insert() index {index} out of bounds")
 
    table.array.insert(index - 1, args[2])
    return table
 
 
@native("__native_table_remove", arity=2)
def _remove(interp, args):
    table = _require_mutable("remove", _require_table("remove", args[0]))
    index = _require_index("remove", args[1])
 
    if index < 1 or index > len(table.array):
        raise LangRuntimeError(f"remove() index {index} out of bounds")
 
    return table.array.pop(index - 1)
 
 
@native("__native_table_clear", arity=1)
def _clear(interp, args):
    table = _require_mutable("clear", _require_table("clear", args[0]))
    table.array.clear()
    table.map.clear()
    return table
 
 
@native("__native_table_contains", arity=2)
def _contains(interp, args):
    table = _require_table("contains", args[0])
    return any(_values_equal(item, args[1]) for item in table.array)
 
 
@native("__native_table_index_of", arity=2)
def _index_of(interp, args):
    table = _require_table("indexOf", args[0])
 
    for index, item in enumerate(table.array, start=1):
        if _values_equal(item, args[1]):
            return float(index)
 
    return None  # nil, not 0: 0 would be a perfectly valid-looking index
 
 
@native("__native_table_slice", arity=3)
def _slice(interp, args):
    """Inclusive on both ends and 1-indexed, matching substring() and
    table indexing rather than Python's own slicing."""
    table = _require_table("slice", args[0])
    start = _require_index("slice", args[1])
    stop = _require_index("slice", args[2])
 
    result = LangTable()
    for item in table.array[max(start - 1, 0):max(stop, 0)]:
        result.append(item)
    return result
 
 
@native("__native_table_reverse", arity=1)
def _reverse(interp, args):
    table = _require_mutable("reverse", _require_table("reverse", args[0]))
    table.array.reverse()
    return table
 
 
@native("__native_table_keys", arity=1)
def _keys(interp, args):
    table = _require_table("keys", args[0])
 
    result = LangTable()
    for key in table.map:
        result.append(key)
    return result
 
 
@native("__native_table_values", arity=1)
def _values(interp, args):
    table = _require_table("values", args[0])
 
    result = LangTable()
    for value in table.map.values():
        result.append(value)
    return result
 
 
@native("__native_table_sort")
def _sort(interp: "Interpreter", args):
    """__native_table_sort(t) sorts in place using ART's own ordering.
    __native_table_sort(t, less) sorts using `less(a, b)` - true when
    `a` should come before `b`."""
    if len(args) not in (1, 2):
        raise LangRuntimeError(f"sort() expects 1 or 2 arguments, got {len(args)}")
 
    table = _require_mutable("sort", _require_table("sort", args[0]))
    less = args[1] if len(args) == 2 else None
 
    if less is None:
        kinds = {type(item) for item in table.array}
        if len(kinds) > 1 or not kinds <= {float, int, str}:
            raise LangRuntimeError(
                "sort() without a comparison function needs a table of "
                "all numbers or all strings; pass sort(t, fun(a, b) { ... }) otherwise"
            )
        table.array.sort()
        return table
 
    def compare(left, right):
        if interp._truthy(interp.call_value(less, [left, right])):
            return -1
        if interp._truthy(interp.call_value(less, [right, left])):
            return 1
        return 0
 
    table.array.sort(key=functools.cmp_to_key(compare))
    return table
 
 
@native("__native_table_map", arity=2)
def _map(interp: "Interpreter", args):
    table = _require_table("map", args[0])
 
    result = LangTable()
    for item in table.array:
        result.append(interp.call_value(args[1], [item]))
    return result
 
 
@native("__native_table_filter", arity=2)
def _filter(interp: "Interpreter", args):
    table = _require_table("filter", args[0])
 
    result = LangTable()
    for item in table.array:
        if interp._truthy(interp.call_value(args[1], [item])):
            result.append(item)
    return result
 
 
@native("__native_table_reduce", arity=3)
def _reduce(interp: "Interpreter", args):
    """reduce(t, fun(accumulator, item) { ... }, initial). The initial
    value is required rather than defaulting to the first element, so
    reducing an empty table is an ordinary answer instead of an error."""
    table = _require_table("reduce", args[0])
 
    accumulator = args[2]
    for item in table.array:
        accumulator = interp.call_value(args[1], [accumulator, item])
    return accumulator
 
 
@native("__native_table_find", arity=2)
def _find(interp: "Interpreter", args):
    table = _require_table("find", args[0])
 
    for item in table.array:
        if interp._truthy(interp.call_value(args[1], [item])):
            return item
 
    return None