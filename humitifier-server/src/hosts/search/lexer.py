"""Tokenizer for advanced search queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import GROUP_CLOSE, GROUP_OPEN, LogicalOperator, TokenType


@dataclass(frozen=True)
class Token:
    """A lexical token with type, value, and character position."""

    type: TokenType
    value: Any
    position: int


def tokenize(query: str) -> list[Token]:
    """Tokenize a search query string into a list of Tokens.

    Raises:
        ValueError: For unterminated strings or unexpected characters, with position.
    """
    tokens: list[Token] = []
    i = 0
    n = len(query)

    while i < n:
        char = query[i]

        # Whitespace
        if char.isspace():
            i += 1
            continue

        # Quoted strings (both ' and " supported)
        if char in ('"', "'"):
            quote = char
            start_pos = i
            i += 1
            chars: list[str] = []
            closed = False
            while i < n:
                c = query[i]
                if c == "\\":
                    if i + 1 < n:
                        chars.append(query[i + 1])
                        i += 2
                    else:
                        chars.append("\\")
                        i += 1
                elif c == quote:
                    closed = True
                    i += 1
                    break
                else:
                    chars.append(c)
                    i += 1

            if not closed:
                raise ValueError(
                    f"Unterminated string literal starting at position {start_pos}"
                )

            # Quoted literals are ALWAYS strings
            tokens.append(Token(TokenType.STRING, "".join(chars), start_pos))
            continue

        # Single and multi-character delimiters/punctuation
        if char == GROUP_OPEN:
            tokens.append(Token(TokenType.LBRACE, GROUP_OPEN, i))
            i += 1
            continue

        if char == GROUP_CLOSE:
            tokens.append(Token(TokenType.RBRACE, GROUP_CLOSE, i))
            i += 1
            continue

        if char == "(":
            tokens.append(Token(TokenType.LPAREN, "(", i))
            i += 1
            continue

        if char == ")":
            tokens.append(Token(TokenType.RPAREN, ")", i))
            i += 1
            continue

        if char == ",":
            tokens.append(Token(TokenType.COMMA, ",", i))
            i += 1
            continue

        # Comparison operators (symbolic)
        if char in (">", "<"):
            start_pos = i
            if i + 1 < n and query[i + 1] == "=":
                op = query[i : i + 2]
                i += 2
            else:
                op = char
                i += 1
            tokens.append(Token(TokenType.OPERATOR, op, start_pos))
            continue

        if char == "=":
            tokens.append(Token(TokenType.OPERATOR, "=", i))
            i += 1
            continue

        # Numbers: optional leading minus followed by digits
        if char.isdigit() or (char == "-" and i + 1 < n and query[i + 1].isdigit()):
            start_pos = i
            if char == "-":
                i += 1
            while i < n and query[i].isdigit():
                i += 1
            if i < n and query[i] == "." and i + 1 < n and query[i + 1].isdigit():
                i += 1
                while i < n and query[i].isdigit():
                    i += 1
                num_val: Any = float(query[start_pos:i])
            else:
                num_val = int(query[start_pos:i])
            tokens.append(Token(TokenType.NUMBER, num_val, start_pos))
            continue

        # Identifiers and keyword tokens
        if char.isalpha() or char == "_":
            start_pos = i
            while i < n and (query[i].isalnum() or query[i] in "_.[]-"):
                i += 1
            word = query[start_pos:i]
            word_upper = word.upper()

            if word_upper == "AND":
                tokens.append(Token(TokenType.LOGICAL, LogicalOperator.AND, start_pos))
            elif word_upper == "OR":
                tokens.append(Token(TokenType.LOGICAL, LogicalOperator.OR, start_pos))
            elif word_upper == "CONTAINS":
                tokens.append(Token(TokenType.OPERATOR, "CONTAINS", start_pos))
            elif word_upper == "TRUE":
                tokens.append(Token(TokenType.BOOLEAN, True, start_pos))
            elif word_upper == "FALSE":
                tokens.append(Token(TokenType.BOOLEAN, False, start_pos))
            else:
                tokens.append(Token(TokenType.IDENT, word, start_pos))
            continue

        # Any unrecognized character
        raise ValueError(f"Unexpected character '{char}' at position {i}")

    return tokens
