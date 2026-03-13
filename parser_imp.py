from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ast_imp import (
    Add,
    And,
    Assign,
    BoolConst,
    Cmd,
    Eq,
    If,
    Int,
    Le,
    Mul,
    Not,
    Or,
    Seq,
    Skip,
    State,
    Sub,
    Var,
)


TOKEN_RE = re.compile(
    r"""
    \s*(
        \#.*?$ |
        := | <= |
        [(),;:=+\-*] |
        -?\d+ |
        [A-Za-z_][A-Za-z0-9_]*
    )
    """,
    re.VERBOSE | re.MULTILINE,
)


KEYWORDS = {"sigma", "if", "then", "else", "while", "do", "begin", "end", "skip", "true", "false", "not", "and", "or"}


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            if text[pos].isspace():
                pos += 1
                continue
            raise SyntaxError(f"Unexpected character at position {pos}: {text[pos]!r}")
        tok = m.group(1)
        pos = m.end()
        if tok.startswith("#"):
            continue
        tokens.append(tok)
    return tokens


@dataclass
class Parser:
    tokens: List[str]
    i: int = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def pop(self) -> str:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        self.i += 1
        return tok

    def expect(self, expected: str) -> None:
        tok = self.pop()
        if tok != expected:
            raise SyntaxError(f"Expected {expected!r}, got {tok!r}")

    def at_end(self) -> bool:
        return self.i >= len(self.tokens)

    # -------------------------
    # File level
    # -------------------------

    def parse_file(self) -> Tuple[State, Cmd]:
        sigma: State = {}
        if self.peek() == "sigma":
            sigma = self.parse_sigma()
        cmd = self.parse_command()
        if not self.at_end():
            raise SyntaxError(f"Unexpected token after program: {self.peek()!r}")
        return sigma, cmd

    def parse_sigma(self) -> State:
        self.expect("sigma")
        sigma: State = {}
        while True:
            name = self.pop()
            self.expect("=")
            value_tok = self.pop()
            if not re.fullmatch(r"-?\d+", value_tok):
                raise SyntaxError(f"Expected integer in sigma, got {value_tok!r}")
            sigma[name] = int(value_tok)
            if self.peek() != ",":
                break
            self.pop()
        return sigma

    # -------------------------
    # Commands
    # -------------------------

    def parse_command(self) -> Cmd:
        cmd = self.parse_simple_command()
        while self.peek() == ";":
            self.pop()
            if self.peek() in (None, "end", "else"):
                break
            cmd = Seq(cmd, self.parse_simple_command())
        return cmd

    def parse_block(self) -> Cmd:
        if self.peek() == "begin":
            self.pop()
            cmd = self.parse_command()
            self.expect("end")
            return cmd
        return self.parse_simple_command()

    def parse_simple_command(self) -> Cmd:
        tok = self.peek()
        if tok == "if":
            return self.parse_if()
        if tok == "while":
            return self.parse_while()
        if tok == "begin":
            self.pop()
            cmd = self.parse_command()
            self.expect("end")
            return cmd

        # labeled atomic command: l : skip | l : X := a
        label = self.pop()
        self.expect(":")
        if self.peek() == "skip":
            self.pop()
            return Skip(label)

        var = self.pop()
        self.expect(":=")
        expr = self.parse_aexp()
        return Assign(label, var, expr)

    def parse_if(self) -> Cmd:
        self.expect("if")
        label = self.pop()
        self.expect(":")
        cond = self.parse_bexp()
        self.expect("then")
        then_branch = self.parse_block()
        self.expect("else")
        else_branch = self.parse_block()
        return If(label, cond, then_branch, else_branch)

    def parse_while(self) -> Cmd:
        from ast_imp import While
        self.expect("while")
        label = self.pop()
        self.expect(":")
        cond = self.parse_bexp()
        self.expect("do")
        body = self.parse_block()
        return While(label, cond, body)

    # -------------------------
    # Arithmetic expressions
    # -------------------------

    def parse_aexp(self):
        return self.parse_aexp_add()

    def parse_aexp_add(self):
        expr = self.parse_aexp_mul()
        while self.peek() in {"+", "-"}:
            op = self.pop()
            right = self.parse_aexp_mul()
            expr = Add(expr, right) if op == "+" else Sub(expr, right)
        return expr

    def parse_aexp_mul(self):
        expr = self.parse_aexp_atom()
        while self.peek() == "*":
            self.pop()
            right = self.parse_aexp_atom()
            expr = Mul(expr, right)
        return expr

    def parse_aexp_atom(self):
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end while parsing arithmetic expression")
        if tok == "(":
            self.pop()
            expr = self.parse_aexp()
            self.expect(")")
            return expr
        if tok == "-":
            self.pop()
            return Sub(Int(0), self.parse_aexp_atom())
        if re.fullmatch(r"-?\d+", tok):
            self.pop()
            return Int(int(tok))
        self.pop()
        return Var(tok)

    # -------------------------
    # Boolean expressions
    # -------------------------

    def parse_bexp(self):
        return self.parse_or()

    def parse_or(self):
        expr = self.parse_and()
        while self.peek() == "or":
            self.pop()
            expr = Or(expr, self.parse_and())
        return expr

    def parse_and(self):
        expr = self.parse_not()
        while self.peek() == "and":
            self.pop()
            expr = And(expr, self.parse_not())
        return expr

    def parse_not(self):
        if self.peek() == "not":
            self.pop()
            return Not(self.parse_not())
        return self.parse_batom()

    def parse_batom(self):
        tok = self.peek()
        if tok == "true":
            self.pop()
            return BoolConst(True)
        if tok == "false":
            self.pop()
            return BoolConst(False)
        if tok == "(":
            # Could be a parenthesized boolean or a comparison
            save = self.i
            self.pop()
            try:
                left_a = self.parse_aexp()
                if self.peek() in {"=", "<="}:
                    op = self.pop()
                    right_a = self.parse_aexp()
                    self.expect(")")
                    return Eq(left_a, right_a) if op == "=" else Le(left_a, right_a)
                self.i = save
            except Exception:
                self.i = save

            self.expect("(")
            expr = self.parse_bexp()
            self.expect(")")
            return expr

        left = self.parse_aexp()
        op = self.pop()
        if op not in {"=", "<="}:
            raise SyntaxError(f"Expected '=' or '<=', got {op!r}")
        right = self.parse_aexp()
        return Eq(left, right) if op == "=" else Le(left, right)


def parse_text(text: str) -> Tuple[State, Cmd]:
    parser = Parser(tokenize(text))
    return parser.parse_file()


def parse_file(path: str) -> Tuple[State, Cmd]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_text(f.read())
