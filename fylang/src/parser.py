from typing import List
from .tokenizer import Token, TokenType
from .utils import NoneLiteral
from .ast import *
from .types import *

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def next(self) -> Token:
        return self.tokens[self.pos + 1]

    def at_end(self) -> bool:
        return self.peek().type == TokenType.EOF

    def advance(self):
        if not self.at_end():
            self.pos += 1
        return self.previous()

    def match(self, *types):
        if self.peek().type in types:
            self.advance()
            return self.previous()
        return None

    def expect(self, token_type: TokenType, value=None, message: str | None = None):
        tok = self.match(token_type)
        if not tok or (value and tok.value != value):
            raise SyntaxError(
                (message or f"Expected {value or token_type.name}")
                + f" at position {self.peek().position}"
            )
        return tok

    def parse(self):
        exprs = []
        while not self.at_end():
            if self.peek().type != TokenType.SEMICOLON:
                exprs.append(self.parse_expression())
            self.expect(TokenType.SEMICOLON)
        return Block(exprs)

    def parse_expression(self):
        return self.parse_decl()

    def parse_decl(self):
        if self.peek().type == TokenType.IDENTIFIER:
            if self.next().type == TokenType.COLON:
                name = self.advance()
                self.advance()
                type = self.parse_type()
                initializer = None
                if self.match(TokenType.EQUAL):
                    initializer = self.parse_assignment()
                return VariableDecl(name, type, initializer)
            elif self.next().type == TokenType.COLON_EQUAL:
                name = self.advance()
                self.advance()
                initializer = self.parse_assignment()
                return AutoDeclAssign(name, initializer)

        return self.parse_return()

    def parse_type(self):
        if self.match(TokenType.LEFT_BRACE):
            fields = {}
            if self.peek().type != TokenType.RIGHT_BRACE:
                while True:
                    name = self.expect(
                        TokenType.IDENTIFIER,
                        message="Expected field name in struct type",
                    )
                    self.expect(
                        TokenType.COLON, message="Expected ':' after struct field name"
                    )

                    field_type = self.parse_type()
                    fields[name.value] = field_type

                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RIGHT_BRACE)
            return StructType(fields)

        if self.match(TokenType.LEFT_PAREN):
            varargs = None
            inner_types = []
            if self.peek().type != TokenType.RIGHT_PAREN:
                while True:
                    if self.match(TokenType.DOT_DOT_DOT):
                        varargs = VarArgs(None, ArrayType(self.parse_type()))
                        break
                    else:
                        inner_types.append(self.parse_type())
                    if not self.match(TokenType.COMMA):
                        break

            self.expect(
                TokenType.RIGHT_PAREN,
                message=(
                    f"Variable arguments type must be the only or the last parameter in the type"
                    if varargs
                    else None
                ),
            )

            if self.match(TokenType.ARROW):
                return_type = self.parse_type()
                typ: BaseType = FunctionType(inner_types, return_type, varargs)
            else:
                if len(inner_types) != 1:
                    raise SyntaxError(
                        "Parenthesized type must contain a single type unless followed by '->' for function types"
                    )
                typ = inner_types[0]

        else:
            if self.match(
                TokenType.STRING_KW,
                TokenType.NUMBER_KW,
                TokenType.BOOLEAN_KW,
                TokenType.ANY_KW,
                TokenType.NONE,
                TokenType.IDENTIFIER,
            ):
                typ = Type(self.previous())
            else:
                raise SyntaxError(f"Unexpected token in type: {self.peek().type.name}")

        while self.match(TokenType.LEFT_SQUARE):
            self.expect(TokenType.RIGHT_SQUARE)
            typ = ArrayType(typ)

        return typ

    def parse_return(self):
        if self.match(TokenType.RETURN):
            value = None
            if self.peek().type != TokenType.SEMICOLON:
                value = self.parse_expression()
            return Return(value)

        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_if_while()

        if self.match(
            TokenType.EQUAL,
            TokenType.PLUS_EQUAL,
            TokenType.MINUS_EQUAL,
            TokenType.SLASH_EQUAL,
            TokenType.STAR_EQUAL,
            TokenType.COLON_EQUAL,
        ):
            equals = self.previous()
            value = self.parse_assignment()

            if equals.type != TokenType.EQUAL:
                base_op, base_value = {
                    TokenType.PLUS_EQUAL.name: (TokenType.PLUS, "+"),
                    TokenType.MINUS_EQUAL.name: (TokenType.MINUS, "-"),
                    TokenType.STAR_EQUAL.name: (TokenType.STAR, "*"),
                    TokenType.SLASH_EQUAL.name: (TokenType.SLASH, "/"),
                }[equals.type.name]
                value = Binary(expr, Token(base_op, base_value, equals.position), value)

            return Assign(expr, value)

        return expr

    def parse_if_while(self):
        if self.match(TokenType.IF):
            condition = self.parse_expression()
            then_branch = self.parse_expression()
            else_branch = None
            if self.match(TokenType.ELSE):
                else_branch = self.parse_expression()
            return If(condition, then_branch, else_branch)

        if self.match(TokenType.FOR):
            initializer = condition = increment = None
            if self.peek().type != TokenType.LEFT_BRACE:
                if self.peek().type != TokenType.SEMICOLON:
                    initializer = self.parse_expression()
                self.expect(TokenType.SEMICOLON)
                if self.peek().type != TokenType.SEMICOLON:
                    condition = self.parse_assignment()
                self.expect(TokenType.SEMICOLON)
                if self.peek().type != TokenType.SEMICOLON:
                    increment = self.parse_assignment()
                self.expect(TokenType.SEMICOLON)

            body = self.parse_expression()
            return For(initializer, condition, increment, body)

        return self.parse_ternary()

    def parse_ternary(self):
        expr = self.parse_logical_or()

        if self.match(TokenType.QUESTION):
            true_case = self.parse_expression()
            self.expect(TokenType.COLON)
            false_case = self.parse_ternary()
            return Ternary(expr, true_case, false_case)

        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while self.match(TokenType.OR_OR):
            op = self.previous()
            right = self.parse_logical_and()
            expr = Binary(expr, op, right)
        return expr

    def parse_logical_and(self):
        expr = self.parse_bitwise()
        while self.match(TokenType.AND_AND):
            op = self.previous()
            right = self.parse_bitwise()
            expr = Binary(expr, op, right)
        return expr

    def parse_bitwise(self):
        expr = self.parse_equality()
        while self.match(
            TokenType.AND,
            TokenType.OR,
            TokenType.XOR,
            TokenType.LEFT_SHIFT,
            TokenType.RIGHT_SHIFT,
        ):
            op = self.previous()
            right = self.parse_equality()
            expr = Binary(expr, op, right)
        return expr

    def parse_equality(self):
        expr = self.parse_comparison()
        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            op = self.previous()
            right = self.parse_comparison()
            expr = Binary(expr, op, right)
        return expr

    def parse_comparison(self):
        expr = self.parse_term()

        while self.match(
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        ):
            op = self.previous()
            right = self.parse_term()
            expr = Binary(expr, op, right)

        return expr

    def parse_term(self):
        expr = self.parse_factor()

        while self.match(TokenType.MINUS, TokenType.PLUS):
            op = self.previous()
            right = self.parse_factor()
            expr = Binary(expr, op, right)

        return expr

    def parse_factor(self):
        expr = self.parse_unary()

        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.previous()
            right = self.parse_unary()
            expr = Binary(expr, op, right)

        return expr

    def parse_unary(self):
        if self.match(TokenType.BANG, TokenType.MINUS, TokenType.BANG):
            op = self.previous()
            right = self.parse_unary()
            return Unary(op, right)

        return self.parse_call()

    def parse_call(self):
        expr = self.parse_primary()

        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr = self.finish_call(expr)
            elif self.match(TokenType.LEFT_SQUARE):
                index = self.parse_expression()
                self.expect(TokenType.RIGHT_SQUARE)
                expr = IndexAccess(expr, index)
            elif self.match(TokenType.DOT):
                name = self.expect(TokenType.IDENTIFIER)
                expr = Get(name, expr)
            else:
                break

        return expr

    def finish_call(self, callee: Expr):
        args = []
        kwargs = {}

        if self.peek().type != TokenType.RIGHT_PAREN:
            while True:
                if (
                    self.peek().type == TokenType.IDENTIFIER
                    and self.next().type == TokenType.EQUAL
                ):
                    name = self.advance()
                    self.advance()
                    value = self.parse_expression()
                    kwargs[name.value] = value
                else:
                    args.append(self.parse_expression())

                if not self.match(TokenType.COMMA):
                    break

        self.expect(TokenType.RIGHT_PAREN)

        return Call(callee, args, kwargs)

    def parse_primary(self):
        if self.match(TokenType.STRUCT):
            self.expect(TokenType.LEFT_BRACE)

            fields = []
            while not self.match(TokenType.RIGHT_BRACE):
                if (
                    self.peek().type == TokenType.IDENTIFIER
                    and self.next().type == TokenType.COLON
                ):
                    field_name = self.advance()
                    self.advance()
                    field_type = self.parse_type()
                    initializer = None
                    if self.match(TokenType.EQUAL):
                        initializer = self.parse_assignment()
                    fields.append(VariableDecl(field_name, field_type, initializer))
                else:
                    raise SyntaxError(
                        f"Struct fields must be variable declarations at position {self.peek().position}"
                    )

                self.expect(TokenType.SEMICOLON)

            return StructDef(fields)
        if self.match(TokenType.FUNCTION):
            self.expect(TokenType.LEFT_PAREN)
            varargs = None
            params, types = [], []
            if self.peek().type != TokenType.RIGHT_PAREN:
                while True:
                    if self.match(TokenType.DOT_DOT_DOT):
                        params.append(self.expect(TokenType.IDENTIFIER))
                        self.expect(TokenType.COLON)
                        varargs = VarArgs(params[-1], ArrayType(self.parse_type()))
                        break
                    else:
                        params.append(self.expect(TokenType.IDENTIFIER))
                        self.expect(TokenType.COLON)
                        types.append(self.parse_type())
                    if not self.match(TokenType.COMMA):
                        break

            self.expect(
                TokenType.RIGHT_PAREN,
                message=(
                    f"Variable arguments must be the only or the last parameter"
                    if varargs
                    else None
                ),
            )
            return_type = None
            if self.match(TokenType.COLON):
                return_type = self.parse_type()
            self.expect(TokenType.ARROW)

            body = self.parse_assignment()

            return Function(params, types, return_type, body, varargs)
        if self.match(
            TokenType.NUMBER, TokenType.STRING, TokenType.BOOLEAN, TokenType.NONE
        ):

            def num_cast(x):
                try:
                    return int(x)
                except ValueError:
                    return float(x)

            literal_cast = {
                TokenType.NUMBER.name: num_cast,
                TokenType.STRING.name: lambda x: x[1:-1],
                TokenType.NONE.name: lambda _: NoneLiteral(),
                TokenType.BOOLEAN.name: lambda x: True if x == "true" else False,
            }
            literal = self.previous()
            return Literal(
                Token(
                    literal.type,
                    literal_cast[literal.type.name](literal.value),
                    literal.position,
                )
            )
        if self.match(TokenType.IDENTIFIER):
            return Variable(self.previous())
        if self.match(TokenType.LEFT_SQUARE):
            exprs = []
            if not self.peek().type == TokenType.RIGHT_SQUARE:
                exprs.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    exprs.append(self.parse_expression())

            self.expect(TokenType.RIGHT_SQUARE)
            return ArrayLiteral(exprs)
        if self.match(TokenType.LEFT_PAREN):
            expr = None
            if self.peek().type != TokenType.RIGHT_PAREN:
                expr = self.parse_expression()
            self.expect(TokenType.RIGHT_PAREN)
            return Grouping(expr)
        if self.match(TokenType.LEFT_BRACE):
            exprs = []
            while self.peek().type != TokenType.RIGHT_BRACE:
                exprs.append(self.parse_expression())
                self.expect(TokenType.SEMICOLON)

            self.expect(TokenType.RIGHT_BRACE)
            return Block(exprs)

        unexpected = self.peek()
        raise SyntaxError(
            f"Unexpected token {unexpected.value or unexpected.type.value} at position {self.peek().position}"
        )
