from typing import Any, List
from .ast import *
from .utils import *
from .tokenizer import TokenType
from importlib import import_module

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        def print_wrapper(*x):
            print(*[self.unwrap(v) for v in x])
            return str(NoneLiteral())
        self.globals.define('print', print_wrapper)
        self.globals.define('import', import_module)

        def type_fn(x: Any) -> str:
            x = self.unwrap(x)
            type_x = type(x)
            if type_x == str:
                return "string"
            elif type_x == int or type_x == float:
                return "number"
            elif type_x == bool:
                return "boolean"
            elif type_x == None:
                return "none"
            elif type_x == Callable:
                return str(x)
            elif type_x == Array:
                return f"array"
            return "unknown"

        self.globals.define('typeof', type_fn)
        self.env = self.globals

    def is_truthy(self, result: Any) -> bool:
        return result == True or result == 1 or not not result

    def interpret(self, expr: Expr) -> Any:
        return self.evaluate(expr)

    def evaluate(self, expr: Expr) -> Any:
        method_name = f"visit_{type(expr).__name__.lower()}"
        method = getattr(self, method_name, None)
        if not method:
            raise RuntimeError(f"No visit method for {type(expr).__name__}")
        return method(expr)

    def unwrap(self, value: Reference | Any):
        if isinstance(value, Reference):
            return self.unwrap(value.get())
        return value

    def resolve_reference(self, expr: Expr):
        if isinstance(expr, Variable):
            name = expr.name.value
            env = self.env

            # if current value is already a reference, return that instead
            if name in self.env.values:
                value = env.get(name)
                if isinstance(value, Reference):
                    return value

            def getter():
                return env.get(name)

            def setter(value: Any):
                env.assign(name, value)
                return NoneLiteral()

            return Reference(getter, setter)

        elif isinstance(expr, IndexAccess):
            array = self.unwrap(self.evaluate(expr.collection))
            if not isinstance(array, Array):
                raise RuntimeError("Index assignment only allowed on arrays")
            index = self.unwrap(self.evaluate(expr.index))
            if not (0 <= index < len(array)):
                raise IndexError("Index out of bounds")

            def getter():
                return array[index]

            def setter(value):
                array[index] = value
                return NoneLiteral()

            return Reference(getter, setter)
        else:
            raise RuntimeError("Invalid assignment target")

    def visit_literal(self, expr: Literal):
        return expr.value.value

    def visit_variable(self, expr: Variable):
        return self.resolve_reference(expr)

    def visit_assign(self, expr: Assign):
        ref = self.evaluate(expr.target)
        if not isinstance(ref, Reference):
            raise RuntimeError("Invalid assignment target")
        value = self.evaluate(expr.value)
        ref.set(value)
        return value
    
    def visit_binary(self, expr: Binary):
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        t = expr.op.type

        match t:
            case TokenType.PLUS:
                return self.unwrap(left) + self.unwrap(right)
            case TokenType.MINUS:
                return self.unwrap(left) - self.unwrap(right)
            case TokenType.STAR:
                return self.unwrap(left) * self.unwrap(right)
            case TokenType.SLASH:
                return self.unwrap(left) / self.unwrap(right)
            case TokenType.PERCENT:
                return self.unwrap(left) % self.unwrap(right)
            case TokenType.EQUAL_EQUAL:
                return self.unwrap(left) == self.unwrap(right)
            case TokenType.BANG_EQUAL:
                return self.unwrap(left) != self.unwrap(right)
            case TokenType.GREATER:
                return self.unwrap(left) > self.unwrap(right)
            case TokenType.GREATER_EQUAL:
                return self.unwrap(left) >= self.unwrap(right)
            case TokenType.LESS:
                return self.unwrap(left) < self.unwrap(right)
            case TokenType.LESS_EQUAL:
                return self.unwrap(left) <= self.unwrap(right)
            case TokenType.AND:
                return self.unwrap(left) & self.unwrap(right)
            case TokenType.OR:
                return self.unwrap(left) | self.unwrap(right)
            case TokenType.XOR:
                return self.unwrap(left) ^ self.unwrap(right)
            case TokenType.LEFT_SHIFT:
                return self.unwrap(left) << self.unwrap(right)
            case TokenType.RIGHT_SHIFT:
                return self.unwrap(left) >> self.unwrap(right)
            case TokenType.OR_OR:
                return self.is_truthy(self.unwrap(left)) or self.is_truthy(self.unwrap(right))
            case TokenType.AND_AND:
                return self.is_truthy(self.unwrap(left)) and self.is_truthy(self.unwrap(right))

        raise RuntimeError(f"Unknown binary operator {t}")

    def visit_unary(self, expr: Unary):
        right = self.evaluate(expr.right)
        t = expr.op.type

        if t == TokenType.MINUS:
            return -right
        if t == TokenType.BANG:
            return not right

        raise RuntimeError(f"Unknown unary operator {t}")

    def visit_grouping(self, expr: Grouping):
        if expr.expr:
            return self.evaluate(expr.expr)
        return NoneLiteral()

    def visit_block(self, expr: Block):
        return self.execute_block(expr.expressions, Environment(self.env))

    def execute_block(self, statements: List[Expr], env: Environment):
        previous = self.env
        try:
            self.env = env
            result = None
            for stmt in statements:
                result = self.evaluate(stmt)
            return result
        finally:
            self.env = previous

    def visit_if(self, expr: If):
        if self.evaluate(expr.condition):
            return self.evaluate(expr.then_branch)
        elif expr.else_branch:
            return self.evaluate(expr.else_branch)
        return None

    def visit_for(self, expr: For):
        previous = self.env
        self.env = Environment(previous)
        try:
            result = None
            if expr.initializer:
                self.evaluate(expr.initializer)
            while self.evaluate(expr.condition) if expr.condition else True:
                result = self.evaluate(expr.body)
                if expr.increment:
                    self.evaluate(expr.increment)
            return result
        finally:
            self.env = previous

    def visit_ternary(self, expr: Ternary):
        if self.evaluate(expr.condition):
            return self.evaluate(expr.true_case)
        else:
            return self.evaluate(expr.false_case)

    def visit_function(self, expr: Function):
        def fn_callable(closure: Environment, *args):
            if not expr.vararg and len(args) != len(expr.params):
                raise RuntimeError("Argument count mismatch")
            
            local_env = Environment(closure)
            n_params = len(expr.params) - (1 if expr.vararg else 0)
            for param_token, arg in zip(expr.params[:n_params], args):
                local_env.define(param_token.value, arg)

            if expr.vararg:
                local_env.define(expr.params[-1].value, Array(args[n_params:]))
            try:
                return self.execute_block(
                    expr.body.expressions if isinstance(expr.body, Block) else [expr.body],
                    local_env
                )
            except ReturnException as r:
                return r.value or NoneLiteral()
            
        name = expr.name
        callable = Callable(self.env, fn_callable, len(expr.params))
        if name:
            self.env.define(name.value, callable)
        return callable

    def visit_return(self, expr: Return):
        value = self.evaluate(expr.value) if expr.value else None
        raise ReturnException(value)

    def visit_call(self, expr: Call):
        callee = self.unwrap(self.evaluate(expr.callee))
        args = [self.evaluate(arg) for arg in expr.args]
        if not callable(callee):
            raise RuntimeError("Attempted to call non-callable object")
        if isinstance(callee, StructValue):
            kwargs = {}
            for key, value in expr.kwargs.items():
                kwargs[key] = self.evaluate(value)
            return callee(*args, **kwargs)
        return callee(*args)
    
    def visit_indexaccess(self, expr: IndexAccess):
        return self.resolve_reference(expr)

    def visit_arrayliteral(self, expr: ArrayLiteral):
        values = Array([])
        for value in expr.values:
            values.append(self.evaluate(value))
        return values

    def visit_get(self, expr: Get):
        obj = self.unwrap(self.evaluate(expr.object))

        if isinstance(obj, Array):
            match expr.name.value:
                case "size":
                    return obj.size
                case "push":
                    return obj.append
                case "pop":
                    return obj.pop
            raise RuntimeError(f"Undefined property '{expr.name.value}' on Array")

        if hasattr(obj, expr.name.value):
            def getter():
                return getattr(obj, expr.name.value)
            def setter(value):
                obj.__setattr__(expr.name.value, value)

            return Reference(getter, setter)

        raise RuntimeError(f"Undefined property '{expr.name.value}'")
    
    def visit_structdef(self, expr: StructDef):
        fields = {}
        for name, value in expr.properties:
            fields[name.value] = self.evaluate(value) if value else NoneLiteral()

        name = expr.name
        struct_def = StructValue(name.value, fields)
        if name:
            self.env.define(name.value, struct_def)
        return struct_def
    