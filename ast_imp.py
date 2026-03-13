from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

State = Dict[str, int]
Path = Tuple[str, ...]
Label = str
EXIT_LABEL = "_exit"


# =========================
# Arithmetic expressions
# =========================

class AExp:
    pass


@dataclass(frozen=True)
class Int(AExp):
    value: int


@dataclass(frozen=True)
class Var(AExp):
    name: str


@dataclass(frozen=True)
class Add(AExp):
    left: AExp
    right: AExp


@dataclass(frozen=True)
class Sub(AExp):
    left: AExp
    right: AExp


@dataclass(frozen=True)
class Mul(AExp):
    left: AExp
    right: AExp


# =========================
# Boolean expressions
# =========================

class BExp:
    pass


@dataclass(frozen=True)
class BoolConst(BExp):
    value: bool


@dataclass(frozen=True)
class Eq(BExp):
    left: AExp
    right: AExp


@dataclass(frozen=True)
class Le(BExp):
    left: AExp
    right: AExp


@dataclass(frozen=True)
class Not(BExp):
    value: BExp


@dataclass(frozen=True)
class Or(BExp):
    left: BExp
    right: BExp


@dataclass(frozen=True)
class And(BExp):
    left: BExp
    right: BExp


# =========================
# Commands
# =========================

class Cmd:
    pass


@dataclass(frozen=True)
class Skip(Cmd):
    label: Label


@dataclass(frozen=True)
class Assign(Cmd):
    label: Label
    var: str
    expr: AExp


@dataclass(frozen=True)
class Seq(Cmd):
    first: Cmd
    second: Cmd


@dataclass(frozen=True)
class If(Cmd):
    label: Label
    cond: BExp
    then_branch: Cmd
    else_branch: Cmd


@dataclass(frozen=True)
class While(Cmd):
    label: Label
    cond: BExp
    body: Cmd


# =========================
# Smart constructors
# =========================

def seq(*cmds: Cmd) -> Cmd:
    if not cmds:
        raise ValueError("seq() expects at least one command")
    result = cmds[-1]
    for cmd in reversed(cmds[:-1]):
        result = Seq(cmd, result)
    return result


# =========================
# Observers / utility functions
# =========================

def vars_aexp(a: AExp) -> Set[str]:
    if isinstance(a, Int):
        return set()
    if isinstance(a, Var):
        return {a.name}
    if isinstance(a, (Add, Sub, Mul)):
        return vars_aexp(a.left) | vars_aexp(a.right)
    raise TypeError(f"Unknown arithmetic expression: {a!r}")


def vars_bexp(b: BExp) -> Set[str]:
    if isinstance(b, BoolConst):
        return set()
    if isinstance(b, (Eq, Le)):
        return vars_aexp(b.left) | vars_aexp(b.right)
    if isinstance(b, Not):
        return vars_bexp(b.value)
    if isinstance(b, (Or, And)):
        return vars_bexp(b.left) | vars_bexp(b.right)
    raise TypeError(f"Unknown boolean expression: {b!r}")


def vars_cmd(c: Cmd) -> Set[str]:
    if isinstance(c, Skip):
        return set()
    if isinstance(c, Assign):
        return {c.var} | vars_aexp(c.expr)
    if isinstance(c, Seq):
        return vars_cmd(c.first) | vars_cmd(c.second)
    if isinstance(c, If):
        return vars_bexp(c.cond) | vars_cmd(c.then_branch) | vars_cmd(c.else_branch)
    if isinstance(c, While):
        return vars_bexp(c.cond) | vars_cmd(c.body)
    raise TypeError(f"Unknown command: {c!r}")


def labels(c: Cmd) -> List[Label]:
    if isinstance(c, Skip):
        return [c.label]
    if isinstance(c, Assign):
        return [c.label]
    if isinstance(c, Seq):
        return labels(c.first) + labels(c.second)
    if isinstance(c, If):
        return [c.label] + labels(c.then_branch) + labels(c.else_branch)
    if isinstance(c, While):
        return [c.label] + labels(c.body)
    raise TypeError(f"Unknown command: {c!r}")


def labels_by_kind(c: Cmd, kinds: Set[str]) -> Set[Label]:
    acc: Set[Label] = set()
    if isinstance(c, Skip):
        if "skip" in kinds:
            acc.add(c.label)
        return acc
    if isinstance(c, Assign):
        if "assign" in kinds:
            acc.add(c.label)
        return acc
    if isinstance(c, Seq):
        return labels_by_kind(c.first, kinds) | labels_by_kind(c.second, kinds)
    if isinstance(c, If):
        if "if" in kinds:
            acc.add(c.label)
        return acc | labels_by_kind(c.then_branch, kinds) | labels_by_kind(c.else_branch, kinds)
    if isinstance(c, While):
        if "while" in kinds:
            acc.add(c.label)
        return acc | labels_by_kind(c.body, kinds)
    raise TypeError(f"Unknown command: {c!r}")


def is_well_formed(c: Cmd) -> bool:
    labs = labels(c)
    return len(labs) == len(set(labs))


def duplicate_labels(c: Cmd) -> Set[Label]:
    seen: Set[Label] = set()
    dup: Set[Label] = set()
    for lab in labels(c):
        if lab in seen:
            dup.add(lab)
        seen.add(lab)
    return dup


def entry_label(c: Cmd) -> Label:
    if isinstance(c, (Skip, Assign, If, While)):
        return c.label
    if isinstance(c, Seq):
        return entry_label(c.first)
    raise TypeError(f"Unknown command: {c!r}")


# =========================
# Pretty printers
# =========================

def pretty_aexp(a: AExp) -> str:
    if isinstance(a, Int):
        return str(a.value)
    if isinstance(a, Var):
        return a.name
    if isinstance(a, Add):
        return f"({pretty_aexp(a.left)} + {pretty_aexp(a.right)})"
    if isinstance(a, Sub):
        return f"({pretty_aexp(a.left)} - {pretty_aexp(a.right)})"
    if isinstance(a, Mul):
        return f"({pretty_aexp(a.left)} * {pretty_aexp(a.right)})"
    raise TypeError(f"Unknown arithmetic expression: {a!r}")


def pretty_bexp(b: BExp) -> str:
    if isinstance(b, BoolConst):
        return "true" if b.value else "false"
    if isinstance(b, Eq):
        return f"({pretty_aexp(b.left)} = {pretty_aexp(b.right)})"
    if isinstance(b, Le):
        return f"({pretty_aexp(b.left)} <= {pretty_aexp(b.right)})"
    if isinstance(b, Not):
        return f"(not {pretty_bexp(b.value)})"
    if isinstance(b, Or):
        return f"({pretty_bexp(b.left)} or {pretty_bexp(b.right)})"
    if isinstance(b, And):
        return f"({pretty_bexp(b.left)} and {pretty_bexp(b.right)})"
    raise TypeError(f"Unknown boolean expression: {b!r}")


def _indent(text: str, level: int = 1) -> str:
    prefix = "    " * level
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def pretty_cmd(c: Cmd) -> str:
    if isinstance(c, Skip):
        return f"{c.label} : skip"
    if isinstance(c, Assign):
        return f"{c.label} : {c.var} := {pretty_aexp(c.expr)}"
    if isinstance(c, Seq):
        return f"{pretty_cmd(c.first)} ;\n{pretty_cmd(c.second)}"
    if isinstance(c, If):
        return (
            f"if {c.label} : {pretty_bexp(c.cond)} then\n"
            f"begin\n{_indent(pretty_cmd(c.then_branch))}\nend\n"
            f"else\n"
            f"begin\n{_indent(pretty_cmd(c.else_branch))}\nend"
        )
    if isinstance(c, While):
        return (
            f"while {c.label} : {pretty_bexp(c.cond)} do\n"
            f"begin\n{_indent(pretty_cmd(c.body))}\nend"
        )
    raise TypeError(f"Unknown command: {c!r}")
