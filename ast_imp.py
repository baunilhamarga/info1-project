from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Union

# ---------- Basic types ----------

State = Dict[str, int]
Path = Tuple[str, ...]

# ---------- Arithmetic expressions ----------

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


# ---------- Boolean expressions ----------

class BExp:
    pass

@dataclass(frozen=True)
class BTrue(BExp):
    pass

@dataclass(frozen=True)
class BFalse(BExp):
    pass

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


# ---------- Commands ----------

class Cmd:
    pass

@dataclass(frozen=True)
class Skip(Cmd):
    label: str

@dataclass(frozen=True)
class Assign(Cmd):
    label: str
    var: str
    expr: AExp

@dataclass(frozen=True)
class Seq(Cmd):
    first: Cmd
    second: Cmd

@dataclass(frozen=True)
class If(Cmd):
    label: str
    cond: BExp
    then_branch: Cmd
    else_branch: Cmd

@dataclass(frozen=True)
class While(Cmd):
    label: str
    cond: BExp
    body: Cmd


# ---------- Utilities for Q1 ----------

def labels(cmd: Cmd) -> list[str]:
    if isinstance(cmd, Skip):
        return [cmd.label]
    if isinstance(cmd, Assign):
        return [cmd.label]
    if isinstance(cmd, Seq):
        return labels(cmd.first) + labels(cmd.second)
    if isinstance(cmd, If):
        return [cmd.label] + labels(cmd.then_branch) + labels(cmd.else_branch)
    if isinstance(cmd, While):
        return [cmd.label] + labels(cmd.body)
    raise TypeError(f"Unknown command: {cmd}")

def is_well_formed(cmd: Cmd) -> bool:
    labs = labels(cmd)
    return len(labs) == len(set(labs))


# ---------- Expression evaluation ----------

def eval_aexp(a: AExp, sigma: State) -> int:
    if isinstance(a, Int):
        return a.value
    if isinstance(a, Var):
        if a.name not in sigma:
            raise KeyError(f"Undefined variable: {a.name}")
        return sigma[a.name]
    if isinstance(a, Add):
        return eval_aexp(a.left, sigma) + eval_aexp(a.right, sigma)
    if isinstance(a, Sub):
        return eval_aexp(a.left, sigma) - eval_aexp(a.right, sigma)
    if isinstance(a, Mul):
        return eval_aexp(a.left, sigma) * eval_aexp(a.right, sigma)
    raise TypeError(f"Unknown arithmetic expression: {a}")

def eval_bexp(b: BExp, sigma: State) -> bool:
    if isinstance(b, BTrue):
        return True
    if isinstance(b, BFalse):
        return False
    if isinstance(b, Eq):
        return eval_aexp(b.left, sigma) == eval_aexp(b.right, sigma)
    if isinstance(b, Le):
        return eval_aexp(b.left, sigma) <= eval_aexp(b.right, sigma)
    if isinstance(b, Not):
        return not eval_bexp(b.value, sigma)
    if isinstance(b, Or):
        return eval_bexp(b.left, sigma) or eval_bexp(b.right, sigma)
    if isinstance(b, And):
        return eval_bexp(b.left, sigma) and eval_bexp(b.right, sigma)
    raise TypeError(f"Unknown boolean expression: {b}")


# ---------- SOS configurations ----------

@dataclass(frozen=True)
class Config:
    cmd: Cmd
    sigma: State
    path: Path = ()

@dataclass(frozen=True)
class Final:
    sigma: State
    path: Path


StepResult = Union[Config, Final]


# ---------- Small-step SOS with paths ----------

def step(cfg: Config) -> StepResult:
    c, sigma, path = cfg.cmd, cfg.sigma, cfg.path

    # (A)
    if isinstance(c, Assign):
        sigma2 = dict(sigma)
        sigma2[c.var] = eval_aexp(c.expr, sigma)
        return Config(Skip(c.label), sigma2, path)

    # (Sa)
    if isinstance(c, Skip):
        return Final(sigma, path + (c.label,))

    # (SS) and (SnoS)
    if isinstance(c, Seq):
        if isinstance(c.first, Skip):
            # consume the skip label and continue with second command
            return Config(c.second, sigma, path + (c.first.label,))
        next_first = step(Config(c.first, sigma, path))
        if isinstance(next_first, Final):
            # practical derived rule for sequencing
            return Config(c.second, next_first.sigma, next_first.path)
        return Config(Seq(next_first.cmd, c.second), next_first.sigma, next_first.path)

    # (IT) / (IF)
    if isinstance(c, If):
        if eval_bexp(c.cond, sigma):
            return Config(c.then_branch, sigma, path + (c.label,))
        return Config(c.else_branch, sigma, path + (c.label,))

    # (WT) / (WF)
    if isinstance(c, While):
        if eval_bexp(c.cond, sigma):
            return Config(Seq(c.body, c), sigma, path + (c.label,))
        return Config(Skip(c.label), sigma, path)

    raise TypeError(f"Unknown command: {c}")


def run(cmd: Cmd, sigma: State, max_steps: int = 10_000) -> Final:
    if not is_well_formed(cmd):
        raise ValueError("Program is not well formed: duplicated labels")

    current = Config(cmd, dict(sigma), ())
    for _ in range(max_steps):
        nxt = step(current)
        if isinstance(nxt, Final):
            return nxt
        current = nxt

    raise RuntimeError("Maximum number of steps reached (possible non-termination)")