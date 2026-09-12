from ..features import FunDecl, ExpressionStmt, Assign, ClassDecl, Getter, Setter, OperatorDecl
from ..errors import LangRuntimeError
from ..runtime import Environment, LangClass, LangInstance, LangTable


class ClassMixin:
    def _build_class(self, node, env):
        superclass = None

        if node.superclass is not None:
            superclass = env.get(node.superclass)

            if not isinstance(superclass, LangClass):
                raise LangRuntimeError(
                    f"'{node.superclass}' is not a class"
                )

        class_env = Environment(env)
        klass = LangClass(node.name, superclass, node.interfaces, class_env)

        class_env.define("__class", klass)

        for member in node.body:
            if isinstance(member, FunDecl):
                self._register_overload(
                    klass.methods, member.name, member.params, member.body,
                    class_env, member.return_type,
                )
            elif isinstance(member, ExpressionStmt) and isinstance(member.expr, Assign):
                assign = member.expr
                if assign.is_static:
                    klass.static_fields[assign.name] = self._eval(assign.value, class_env)
                else:
                    klass.field_inits[assign.name] = assign.value
            elif isinstance(member, ClassDecl):
                nested = self._build_class(member, class_env)

                klass.nested_classes[member.name] = nested
                class_env.define(member.name, nested)
            elif isinstance(member, Getter):
                klass.getters[member.name] = member
            elif isinstance(member, Setter):
                klass.setters[member.name] = member
            elif isinstance(member, OperatorDecl):
                self._register_overload(
                    klass.operators, member.operator, member.params,
                    member.body, class_env,
                    display_name=f"{klass.name}.{member.operator}",
                )

            else:
                raise LangRuntimeError(
                    f"Unsupported class member: {type(member).__name__}"
                )

        return klass

    def _instantiate(self, klass: LangClass, args):
        instance = LangInstance(klass)

        for name, init_expr in klass.find_field_inits():
            instance.fields[name] = self._eval(init_expr, klass.closure)

        constructor = klass.methods.get(klass.name)

        if constructor is not None:
            self._call_function(
                constructor,
                args,
                this=instance,
            )

        return instance

    def _make_immutable(self, value, seen=None):
        if seen is None:
            seen = set()

        value_id = id(value)

        if value_id in seen:
            return

        seen.add(value_id)

        if isinstance(value, LangTable):
            for item in value.array:
                self._make_immutable(item, seen)

            for key, item in value.map.items():
                self._make_immutable(key, seen)
                self._make_immutable(item, seen)

            value.make_immutable()
            return

        if isinstance(value, LangInstance):
            value.is_enum_member = True

            for field_value in value.fields.values():
                self._make_immutable(field_value, seen)

            return
