from typing import List
from .tokenizer import Token, TokenType
from .utils import NoneLiteral
from .ast import *

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
        return self.parse_return()

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
    
    def parse_function_structure(self, name: Optional[Token], expect_message=""):
            self.expect(TokenType.LEFT_PAREN, message=expect_message)

            varargs = None
            params = []
            if self.peek().type != TokenType.RIGHT_PAREN:
                while True:
                    if self.match(TokenType.DOT_DOT_DOT):
                        params.append(self.expect(TokenType.IDENTIFIER))
                        varargs = VarArgs(params[-1])
                        break
                    else:
                        params.append(self.expect(TokenType.IDENTIFIER))
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

            self.expect(TokenType.ARROW)

            body = self.parse_assignment()

            return Function(name, params, body, varargs)

    def parse_primary(self):
        if self.match(TokenType.STRUCT):
            name = None
            if self.match(TokenType.IDENTIFIER):
                name = self.previous()

            self.expect(TokenType.LEFT_BRACE)

            properties = []
            while self.peek().type != TokenType.RIGHT_BRACE:
                field_name = self.expect(TokenType.IDENTIFIER)
                initializer = None
                if self.match(TokenType.EQUAL):
                    if self.peek().type == TokenType.FUNCTION:
                        self.advance()
                        initializer = self.parse_function_structure(None, "Functions inside 'struct' cannot be named")
                    else:
                        initializer = self.parse_if_while()
                properties.append((field_name, initializer))
                if not self.match(TokenType.COMMA):
                    break
            
            self.expect(TokenType.RIGHT_BRACE)

            return StructDef(name, properties)
        if self.match(TokenType.FUNCTION):
            return self.parse_function_structure(self.match(TokenType.IDENTIFIER))
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
                elements.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    is_tuple = True
                    while self.peek().type != TokenType.RIGHT_PAREN:
                        elements.append(self.parse_expression())
                        if not self.match(TokenType.COMMA):
                            break

            self.expect(TokenType.RIGHT_PAREN)

            if is_tuple or len(elements) > 1:
                return TupleLiteral(elements)
            else:
                return Grouping(elements[0] if elements else None)
        if self.match(TokenType.LEFT_BRACE):
            if self.peek().type == TokenType.STRING and self.next().type == TokenType.COLON:
                pairs = []
                while self.peek().type != TokenType.RIGHT_BRACE:
                    key_token = self.expect(TokenType.STRING)
                    self.expect(TokenType.COLON)
                    value_expr = self.parse_expression()
                    pairs.append((key_token, value_expr))
                    if not self.match(TokenType.COMMA):
                        break

                self.expect(TokenType.RIGHT_BRACE)
                return DictLiteral(pairs)

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
