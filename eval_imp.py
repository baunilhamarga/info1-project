from __future__ import annotations

from typing import Dict, List, Tuple

from ast_imp import (
    AExp,
    Add,
    And,
    BExp,
    BoolConst,
    Eq,
    Int,
    Le,
    Mul,
    Not,
    Or,
    State,
    Sub,
    Var,
)

AtomicEval = Tuple[str, bool]


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
    raise TypeError(f"Unknown arithmetic expression: {a!r}")


def eval_bexp(b: BExp, sigma: State) -> bool:
    if isinstance(b, BoolConst):
        return b.value
    if isinstance(b, Eq):
        return eval_aexp(b.left, sigma) == eval_aexp(b.right, sigma)
    if isinstance(b, Le):
        return eval_aexp(b.left, sigma) <= eval_aexp(b.right, sigma)
    if isinstance(b, Not):
        return not eval_bexp(b.value, sigma)
    if isinstance(b, Or):
        left = eval_bexp(b.left, sigma)
        right = eval_bexp(b.right, sigma)
        return left or right
    if isinstance(b, And):
        left = eval_bexp(b.left, sigma)
        right = eval_bexp(b.right, sigma)
        return left and right
    raise TypeError(f"Unknown boolean expression: {b!r}")


def eval_bexp_with_atoms(b: BExp, sigma: State) -> Tuple[bool, List[AtomicEval]]:
    """
    Returns:
        (value, atoms)
    where atoms records the truth value of every atomic condition (Eq / Le)
    actually evaluated during the recursive evaluation.
    """
    if isinstance(b, BoolConst):
        return b.value, []

    if isinstance(b, Eq):
        value = eval_aexp(b.left, sigma) == eval_aexp(b.right, sigma)
        return value, [(repr(b), value)]

    if isinstance(b, Le):
        value = eval_aexp(b.left, sigma) <= eval_aexp(b.right, sigma)
        return value, [(repr(b), value)]

    if isinstance(b, Not):
        v, atoms = eval_bexp_with_atoms(b.value, sigma)
        return (not v), atoms

    if isinstance(b, Or):
        lv, la = eval_bexp_with_atoms(b.left, sigma)
        rv, ra = eval_bexp_with_atoms(b.right, sigma)
        return lv or rv, la + ra

    if isinstance(b, And):
        lv, la = eval_bexp_with_atoms(b.left, sigma)
        rv, ra = eval_bexp_with_atoms(b.right, sigma)
        return lv and rv, la + ra

    raise TypeError(f"Unknown boolean expression: {b!r}")
