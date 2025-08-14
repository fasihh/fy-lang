# pyright: ignore[reportShadowedImports]
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from .tokenizer import Token

@dataclass
class Expr:
    pass


@dataclass
class If(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Optional[Expr]


@dataclass
class For(Expr):
    initializer: Optional[Expr]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Expr


@dataclass
class Block(Expr):
    expressions: List[Expr]


@dataclass
class Binary(Expr):
    left: Expr
    op: Token
    right: Expr


@dataclass
class Variable(Expr):
    name: Token


@dataclass
class Literal(Expr):
    value: Token


@dataclass
class ArrayLiteral(Expr):
    values: List[Expr]


@dataclass
class IndexAccess(Expr):
    collection: Expr
    index: Expr


@dataclass
class Assign(Expr):
    target: Expr
    value: Expr


@dataclass
class Ternary(Expr):
    condition: Expr
    true_case: Expr
    false_case: Expr


@dataclass
class Unary(Expr):
    op: Token
    right: Expr


@dataclass
class Function(Expr):
    params: List[Token]
    body: Expr
    vararg: Optional[VarArgs]


@dataclass
class Return(Expr):
    value: Optional[Expr]


@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr]
    kwargs: Dict[str, Expr]


@dataclass
class Get(Expr):
    name: Token
    object: Expr


@dataclass
class Grouping(Expr):
    expr: Optional[Expr]


@dataclass
class StructDef(Expr):
    name: Optional[Token]
    properties: List[Tuple[Token, Expr]]
