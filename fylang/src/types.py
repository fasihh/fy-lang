# pyright: ignore[reportShadowedImports]
from dataclasses import dataclass
from .tokenizer import TokenType, Token
from typing import List, Optional, Dict

@dataclass
class BaseType:
    def __eq__(self, a: "BaseType"):
        pass

    def __str__(self):
        return "base_type"

@dataclass
class Type(BaseType):
    type: Token

    @classmethod
    def number(cls):
        return cls(Token(TokenType.NUMBER_KW, "number", -1))
    
    @classmethod
    def string(cls):
        return cls(Token(TokenType.STRING_KW, "string", -1))
    
    @classmethod
    def boolean(cls):
        return cls(Token(TokenType.BOOLEAN_KW, "boolean", -1))
    
    @classmethod
    def none(cls):
        return cls(Token(TokenType.NONE, "none", -1))

    @classmethod
    def any(cls):
        return cls(Token(TokenType.ANY_KW, "any", -1))

    def __eq__(self, a: "Type"):
        return isinstance(a, Type) and self.type.type == a.type.type

    def __str__(self):
        return self.type.value
    
    def __repr__(self):
        return str(self)

@dataclass
class VarArgs:
    name: Optional[Token]
    type: "ArrayType"

    def __eq__(self, a: "VarArgs"):
        return isinstance(a, VarArgs) and self.type == a.type

@dataclass
class FunctionType(BaseType):
    param_types: List[BaseType]
    return_type: BaseType
    varargs: Optional[VarArgs] = None

    def __eq__(self, a: "FunctionType"):
        return (
            isinstance(a, FunctionType) and
            len(a.param_types) == len(self.param_types) and
            all(x == y for x, y in zip(self.param_types, a.param_types)) and
            self.return_type == a.return_type and
            self.varargs == a.varargs
        )
    
    def __str__(self):
        params = [str(param) for param in self.param_types] + ([f"...{self.varargs.type.elements_type}"] if self.varargs else [])
        return f"({', '.join(params)}) -> {str(self.return_type or Type.none())}"
    
    def __repr__(self):
        return str(self)
    
@dataclass
class ArrayType(BaseType):
    elements_type: Optional[BaseType]

    def __eq__(self, a: "ArrayType"):
        return isinstance(a, ArrayType) and self.elements_type == a.elements_type
    
    def __str__(self):
        current = str(self.elements_type)
        if isinstance(self.elements_type, FunctionType):
            current = f"({current})"
        return f"{current}[]"
    

@dataclass
class StructType(BaseType):
    properties: Dict[str, BaseType]

    def __eq__(self, a: "StructType"):
        return isinstance(a, StructType) and self.properties == a.properties

    def __str__(self):
        kv = lambda key, value: f"{key}: {value}"
        return f"{{ {'; '.join([kv(key, value) for key, value in self.properties.items()])} }}"
    
@dataclass
class StructTypeInst(StructType):
    @classmethod
    def of(cls, obj: StructType):
        return cls(obj.properties)

    def __eq__(self, a: "StructTypeInst"):
        return isinstance(a, StructTypeInst) and self.properties == a.properties()