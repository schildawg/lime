from enum import Enum
from typing import Any

class TokenType(Enum):
   # Special Items
   EOF = "EOF"
   ILLEGAL  = "ILLEGAL"

   # Data Types
   IDENT = "IDENT"
   INT = "INT"
   FLOAT = "FLOAT"

   # Arithmetic Symbols
   PLUS = "PLUS"
   MINUS = "MINUS"
   ASTERISK = "ASTERISK"
   SLASH = "SLASH"
   POW = "POW"
   MODULUS = "MODULUS"

   # Assignment
   EQ = "EQ"

   # Symbols
   COLON = "COLON"
   SEMICOLON = "SEMICOLON"
   ARROW = "ARROW"
   LPAREN = "LPAREN"
   RPAREN = "RPAREN"
   LBRACE = "LBRACE"
   RBRACE = "RBRACE"

   # Keywords
   LET = "LET"
   FN = "FN"
   RETURN = "RETURN"

   # Types
   TYPE = "TYPE"

class Token:
    def __init__(self, type : TokenType, literal: Any, line_no: int, position: int) -> None:
        self.type = type
        self.literal = literal
        self.line_no = line_no
        self.position = position

    def __str__(self) -> str:
        return f"Token[{self.type} : {self.literal} : Line {self.line_no} : Positionn {self.position}]"

    def __repr__(self) -> str:
        return str(self)

KEYWORDS: dict[str, TokenType] = {
    "let": TokenType.LET,
    "fn": TokenType.FN,
    "return": TokenType.RETURN
}

ALT_KEYWORDS: dict[str, TokenType] = {
    "lit": TokenType.LET,
    "be": TokenType.EQ,
    "rn": TokenType.SEMICOLON,
    "bruh": TokenType.FN,
    "pause": TokenType.RETURN,
    "snek": TokenType.ARROW
}

TYPE_KEYWORDS: list[str] = ["int", "float"]

def lookup_ident(ident: str) -> TokenType:
    tt: TokenType | None = KEYWORDS.get(ident)
    if tt is not None:
        return tt
    
    tt: TokenType | None = ALT_KEYWORDS.get(ident)
    if tt is not None:
        return tt
    
    if ident in TYPE_KEYWORDS:
        return TokenType.TYPE
    
    return TokenType.IDENT
