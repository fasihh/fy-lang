from .tokenizer import TokenType
from .ast import *
from .utils import TypeEnv
from .types import *

class TypeChecker:
    def __init__(self):
        self.env = TypeEnv()
        self.env.define(
            "print",
            FunctionType(
                [],
                Type.none(),
                VarArgs(Token(TokenType.IDENTIFIER, "x", -1), ArrayType(Type.any())),
            ),
        )
        self.env.define("to_number", FunctionType([Type.any()], Type.number()))
        self.env.define("to_any", FunctionType([Type.any()], Type.any()))
        self.env.define("typeof", FunctionType([Type.any()], Type.string()))
        self.current_return_type = None

    def check(self, node):
        method = getattr(self, f"visit_{type(node).__name__.lower()}", None)
        if not method:
            raise NotImplementedError(f"No type check method for {type(node).__name__}")
        return method(node)

    def type_compatible(self, a: BaseType, b: BaseType):
        if isinstance(a, Type) and isinstance(b, Type):
            if a.type.type == TokenType.ANY_KW or b.type.type == TokenType.ANY_KW:
                return True
            return a.type.type == b.type.type
        elif isinstance(a, FunctionType) and isinstance(b, FunctionType):
            if len(a.param_types) != len(b.param_types):
                return False
            for x, y in zip(a.param_types, b.param_types):
                if x != y:
                    return False
            return a.return_type == b.return_type and a.varargs == b.varargs
        elif isinstance(a, ArrayType) and isinstance(b, ArrayType):
            return a.elements_type == b.elements_type
        elif isinstance(a, StructType) and isinstance(b, StructType):
            return a.properties == b.properties
        return False

    def visit_literal(self, expr: Literal):
        match expr.value.type:
            case TokenType.STRING:
                return Type.string()
            case TokenType.BOOLEAN:
                return Type.boolean()
            case TokenType.NUMBER:
                return Type.number()
            case TokenType.NONE:
                return Type.none()
        raise TypeError(f"Unknown literal type: {expr.value}")

    def visit_variabledecl(self, expr: VariableDecl):
        if expr.name.value in self.env.vars:
            raise TypeError(
                f"Redeclaring '{expr.name.value}' in the same scope again is not allowed"
            )
        self.env.define(expr.name.value, expr.type)
        if expr.initializer:
            init_type = self.check(expr.initializer)
            if (
                isinstance(init_type, ArrayType)
                and isinstance(expr.type, ArrayType)
                and not init_type.elements_type
            ):
                init_type.elements_type = expr.type.elements_type

            if expr.type != Type.any() and not self.type_compatible(
                init_type, expr.type
            ):
                raise TypeError(
                    f"Type mismatch: expected '{expr.type}', got '{init_type}'"
                )
        return expr.type

    def visit_autodeclassign(self, expr: AutoDeclAssign):
        self.env.define(expr.name.value, Type.any())
        init_type = self.check(expr.initializer)
        self.env.vars[expr.name.value] = init_type
        return init_type

    def visit_variable(self, expr: Variable):
        var_type = self.env.lookup(expr.name.value)
        if not var_type:
            raise TypeError(f"Undefined variable '{expr.name.value}'")
        expr.type = var_type
        return var_type

    def visit_assign(self, expr: Assign):
        var_type: Type = self.check(expr.target)
        value_type: Type = self.check(expr.value)
        if var_type == Type.any() or var_type == value_type:
            return var_type
        raise TypeError(f"Cannot assign '{value_type}' type to '{var_type}' type")

    def visit_binary(self, expr: Binary):
        left = self.check(expr.left)
        right = self.check(expr.right)
        t = expr.op.type

        error = TypeError(
            f"Invalid use of {t.name} operator between types '{left}' and '{right}'"
        )
        if isinstance(left, FunctionType) or isinstance(right, FunctionType):
            raise error

        left: Type = left
        right: Type = right
        if left == Type.any() or right == Type.any():
            return Type.any()

        match t:
            case TokenType.PLUS:
                if left == right and (left == Type.string() or left == Type.number()):
                    return left
            case TokenType.MINUS | TokenType.STAR | TokenType.SLASH | TokenType.PERCENT:
                if left == right and left == Type.number():
                    return left
            case TokenType.EQUAL_EQUAL | TokenType.BANG_EQUAL:
                if left == right:
                    return Type.boolean()
            case (
                TokenType.GREATER
                | TokenType.GREATER_EQUAL
                | TokenType.LESS
                | TokenType.LESS_EQUAL
            ):
                if left == right and left == Type.number():
                    return Type.boolean()
            case (
                TokenType.AND
                | TokenType.OR
                | TokenType.XOR
                | TokenType.LEFT_SHIFT
                | TokenType.RIGHT_SHIFT
            ):
                if left == right and left == Type.number():
                    return left
            case TokenType.OR_OR | TokenType.AND_AND:
                if left == right and left == Type.boolean():
                    return left
            case _:
                raise RuntimeError(f"Unknown binary operator {t}")

        raise error

    def visit_unary(self, expr: Unary):
        right = self.check(expr.right)
        t = expr.op.type

        error = TypeError(f"Invalid use of {t.name} operator with type '{right}'")
        if isinstance(right, FunctionType):
            raise error

        right: Type = right
        if t == TokenType.MINUS and right == Type.number():
            return right

        if t == TokenType.BANG and right in (
            Type.number(),
            Type.none(),
            Type.boolean(),
            Type.any(),
        ):
            return Type.boolean()

        raise error

    def visit_grouping(self, expr: Grouping):
        return self.check(expr.expr)

    def check_block(self, statements: List[Expr], env: TypeEnv):
        previous = self.env
        try:
            self.env = env
            result = Type.none()
            for stmt in statements:
                result = self.check(stmt)
            return result
        finally:
            self.env = previous

    def visit_block(self, expr: Block):
        return self.check_block(expr.expressions, TypeEnv(self.env))

    def visit_if(self, expr: If):
        self.check(expr.condition)
        self.check(expr.then_branch)
        if expr.else_branch:
            self.check(expr.else_branch)
        return Type.any()

    def visit_for(self, expr: For):
        if expr.initializer:
            self.check(expr.initializer)
        if expr.condition:
            self.check(expr.condition)
        if expr.increment:
            self.check(expr.increment)
        return self.check(expr.body)

    def visit_ternary(self, expr: Ternary):
        self.check(expr.condition)
        true_case = self.check(expr.true_case)
        false_case = self.check(expr.false_case)
        return true_case == false_case

    def visit_function(self, expr: Function):
        self.env = TypeEnv(self.env)
        for param_name, param_type in zip(expr.params, expr.param_types):
            self.env.define(param_name.value, param_type)
        if expr.vararg:
            self.env.define(expr.vararg.name.value, expr.vararg.type)

        old_return_type = self.current_return_type
        self.current_return_type = expr.return_type or Type.none()

        body = self.check(expr.body)
        if not expr.return_type:
            expr.return_type = body

        if (
            isinstance(expr.return_type, ArrayType)
            and isinstance(body, ArrayType)
            and not body.elements_type
        ):
            body.elements_type = expr.return_type.elements_type

        if expr.return_type != Type.any() and expr.return_type != body:
            raise TypeError(
                f"Expected type '{expr.return_type}', got type '{body}' from function"
            )

        func_type = FunctionType(expr.param_types, expr.return_type, expr.vararg)

        self.current_return_type = old_return_type
        self.env = self.env.parent
        return func_type

    def visit_return(self, expr: Return):
        if self.current_return_type is None:
            raise TypeError("'return' outside of a function")
        if expr.value:
            value: BaseType = self.check(expr.value)
            if (
                self.current_return_type != Type.any()
                and value != self.current_return_type
            ):
                raise TypeError(
                    f"Return type mismatch: expected '{self.current_return_type}', got '{value}'"
                )
            return self.current_return_type
        return Type.none()

    def visit_call(self, expr: Call):
        callee = self.check(expr.callee)
        if callee == Type.any():
            return Type.any()
        if isinstance(callee, FunctionType):
            arg_types = [self.check(arg) for arg in expr.args]
            fixed_params = callee.param_types

            if callee.varargs:
                if len(arg_types) < len(fixed_params):
                    raise TypeError(
                        f"Expected at least {len(fixed_params)} args, got {len(arg_types)}"
                    )

                for arg_type, param_type in zip(arg_types, fixed_params):
                    if param_type != Type.any() and arg_type != param_type:
                        raise TypeError(
                            f"Expected argument of type '{param_type}', got '{arg_type}'"
                        )

                varargs_type = callee.varargs.type.elements_type
                for extra_arg in arg_types[len(fixed_params) :]:
                    if varargs_type != Type.any() and varargs_type != extra_arg:
                        raise TypeError(
                            f"Expected argument of type '{varargs_type}', got '{extra_arg}'"
                        )
            else:
                if len(arg_types) != len(fixed_params):
                    raise TypeError(
                        f"Expected {len(fixed_params)} args, got {len(arg_types)}"
                    )

                for arg_type, param_type in zip(arg_types, fixed_params):
                    if param_type != Type.any() and arg_type != param_type:
                        raise TypeError(
                            f"Expected argument of type '{param_type}', got '{arg_type}'"
                        )

            return callee.return_type
        elif isinstance(callee, StructType):
            arg_types = [self.check(arg) for arg in expr.args]

            field_names = list(callee.properties.keys())
            field_types = list(callee.properties.values())

            if len(arg_types) > len(field_types):
                raise TypeError(
                    f"Struct init expected at most {len(field_types)} args, got {len(arg_types)}"
                )

            for i, arg_type in enumerate(arg_types):
                declared_type = field_types[i]
                if declared_type != Type.any() and not self.type_compatible(arg_type, declared_type):
                    raise TypeError(
                        f"Struct field '{field_names[i]}' type mismatch: "
                        f"expected '{declared_type}', got '{arg_type}'"
                    )

            if expr.kwargs:
                for kw_name, kw_expr in expr.kwargs.items():
                    if kw_name not in callee.properties:
                        raise TypeError(f"Unknown struct field '{kw_name}'")
                    declared_type = callee.properties[kw_name]
                    kw_type = self.check(kw_expr)
                    if declared_type != Type.any() and not self.type_compatible(kw_type, declared_type):
                        raise TypeError(
                            f"Struct field '{kw_name}' type mismatch: "
                            f"expected '{declared_type}', got '{kw_type}'"
                        )

            return StructTypeInst.of(callee)

        raise TypeError(f"{callee} is not a callable")

    def visit_indexaccess(self, expr: IndexAccess):
        collection = self.check(expr.collection)
        if self.check(expr.index) != Type.number():
            raise TypeError("Array index must be a number")
        if isinstance(collection, ArrayType):
            return collection.elements_type
        raise TypeError(f"'{collection}' is not accessable")

    def visit_arrayliteral(self, expr: ArrayLiteral):
        type = None
        for value in expr.values:
            val_type = self.check(value)
            if type is None:
                type = val_type
            elif val_type != type:
                return ArrayType(Type.any())
        return ArrayType(type)

    def visit_get(self, expr: Get):
        name = expr.name
        obj = self.check(expr.object)
        err = TypeError(f"Undefined property '{name.value}'")

        if isinstance(obj, ArrayType):
            match name.value:
                case "push":
                    return FunctionType([obj.elements_type], Type.none())
                case "pop":
                    return FunctionType([], Type.none())
                case "size":
                    return FunctionType([], Type.number())
            raise err

        if isinstance(obj, StructType):
            if name.value not in obj.properties:
                raise err
            return obj.properties[name.value]

        raise err
    
    def visit_structdef(self, expr: StructDef):
        struct_env = TypeEnv(self.env)
        properties: Dict[str, BaseType] = {}

        for field in expr.fields:
            if field.name.value in properties:
                raise TypeError(f"Duplicate field '{field.name.value}' in struct")
            struct_env.define(field.name.value, field.type)
            properties[field.name.value] = field.type

        previous_env = self.env
        try:
            self.env = struct_env
            for field in expr.fields:
                if field.initializer:
                    default_type = self.check(field.initializer)
                    declared_type = properties[field.name.value]
                    if declared_type != Type.any() and not self.type_compatible(default_type, declared_type):
                        raise TypeError(
                            f"Field '{field.name.value}' default type mismatch: "
                            f"expected '{declared_type}', got '{default_type}'"
                        )
        finally:
            self.env = previous_env

        return StructType(properties)
