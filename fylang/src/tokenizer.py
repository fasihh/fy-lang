import re
from typing import List, Any
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
  LEFT_PAREN = auto()
  RIGHT_PAREN = auto()
  LEFT_SQUARE = auto()
  RIGHT_SQUARE = auto()
  LEFT_BRACE = auto()
  RIGHT_BRACE = auto()
  COMMA = auto()
  DOT = auto()
  MINUS = auto()
  PLUS = auto()
  SEMICOLON = auto()
  SLASH = auto()
  STAR = auto()
  QUESTION = auto()
  COLON = auto()
  PERCENT = auto()

  BANG = auto()
  BANG_EQUAL = auto()
  EQUAL = auto()
  EQUAL_EQUAL = auto()
  GREATER = auto()
  GREATER_EQUAL = auto()
  LESS = auto()
  LESS_EQUAL = auto()
  AND_AND = auto()
  OR_OR = auto()
  LEFT_SHIFT = auto()
  RIGHT_SHIFT = auto()
  ARROW = auto()

  PLUS_EQUAL = auto()
  MINUS_EQUAL = auto()
  STAR_EQUAL = auto()
  SLASH_EQUAL = auto()
  COLON_EQUAL = auto()

  DOT_DOT_DOT = auto()

  IDENTIFIER = auto()
  STRING = auto()
  NUMBER = auto()
  BOOLEAN = auto()
  
  AND = auto()
  STRUCT = auto()
  ELSE = auto()
  FALSE = auto()
  FUNCTION = auto()
  FOR = auto()
  IF = auto()
  NONE = auto()
  OR = auto()
  RETURN = auto()
  TRUE = auto()
  XOR = auto()
  BREAK = auto()
  CONTINUE = auto()

  EOF = auto()


@dataclass
class Token:
  type: TokenType
  value: Any
  position: int


KEYWORDS = {
  "and": TokenType.AND,
  "struct": TokenType.STRUCT,
  "else": TokenType.ELSE,
  "false": TokenType.FALSE,
  "fn": TokenType.FUNCTION,
  "for": TokenType.FOR,
  "if": TokenType.IF,
  "none": TokenType.NONE,
  "or": TokenType.OR,
  "return": TokenType.RETURN,
  "true": TokenType.TRUE,
  "xor": TokenType.XOR,
  "break": TokenType.BREAK,
  "continue": TokenType.CONTINUE,
}


TOKEN_REGEX = re.compile(
    r"""
    (?P<WHITESPACE>[ \t\n]+)
  | (?P<COMMENT>//.*)

  | (?P<PLUS_EQUAL>\+=)
  | (?P<MINUS_EQUAL>-=)
  | (?P<STAR_EQUAL>\*=)
  | (?P<SLASH_EQUAL>/=)
  | (?P<COLON_EQUAL>:=)
  
  | (?P<ARROW>->)
  | (?P<BANG_EQUAL>!=)
  | (?P<EQUAL_EQUAL>==)
  | (?P<GREATER_EQUAL>>=)
  | (?P<LESS_EQUAL><=)
  | (?P<AND_AND>&&)
  | (?P<OR_OR>\|\|)
  | (?P<LEFT_SHIFT><<)
  | (?P<RIGHT_SHIFT>>>)

  | (?P<DOT_DOT_DOT>\.\.\.)

  | (?P<LEFT_SQUARE>\[)
  | (?P<RIGHT_SQUARE>\])
  | (?P<LEFT_PAREN>\()
  | (?P<RIGHT_PAREN>\))
  | (?P<LEFT_BRACE>{)
  | (?P<RIGHT_BRACE>})
  | (?P<COMMA>,)
  | (?P<DOT>\.)
  | (?P<MINUS>-)
  | (?P<PLUS>\+)
  | (?P<SEMICOLON>;)
  | (?P<SLASH>/)
  | (?P<STAR>\*)
  | (?P<QUESTION>\?)
  | (?P<COLON>:)
  | (?P<PERCENT>%)
  | (?P<BANG>!)
  | (?P<EQUAL>=)
  | (?P<GREATER>>)
  | (?P<LESS><)


  | (?P<STRING>(?:"(\\.|[^"])*"|'(\\.|[^'])*'))
  | (?P<NUMBER>\b\d+(\.\d+)?\b)
  | (?P<BOOLEAN>true|false)
  | (?P<IDENTIFIER>\b[a-zA-Z_][a-zA-Z0-9_]*\b)
    """,
    re.VERBOSE,
)


def tokenize(code: str) -> List[Token]:
  tokens = []
  for match in TOKEN_REGEX.finditer(code):
    kind = match.lastgroup
    value = match.group()
    start = match.start()

    if kind in ("WHITESPACE", "COMMENT"):
      continue

    if kind == "IDENTIFIER" and value in KEYWORDS:
      token_type = KEYWORDS[value]
    else:
      token_type = TokenType[kind]

    tokens.append(Token(token_type, value, start))

  tokens.append(Token(TokenType.EOF, "", len(code)))
  return tokens
