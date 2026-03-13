from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ast_imp import (
    AExp,
    Add,
    And,
    BExp,
    BoolConst,
    Cmd,
    Eq,
    Le,
    Mul,
    Not,
    Or,
    Path,
    State,
    Sub,
    Var,
    vars_cmd,
)
from cfg import CFG, CFGEdge, EdgeAction, build_cfg
from eval_imp import eval_bexp


SymStore = Dict[str, AExp]


@dataclass
class SymState:
    label: str
    store: SymStore
    path_condition: List[BExp]
    label_path: Tuple[str, ...]
    depth: int
    children: List["SymState"] = field(default_factory=list)

    def pretty(self) -> str:
        store_str = ", ".join(f"{k} -> {v!r}" for k, v in sorted(self.store.items()))
        pc_str = " and ".join(repr(x) for x in self.path_condition) if self.path_condition else "true"
        return f"({self.label}, {{{store_str}}}, {pc_str}, path={self.label_path})"


def subst_aexp(a: AExp, store: SymStore) -> AExp:
    from ast_imp import Int
    if isinstance(a, Int):
        return a
    if isinstance(a, Var):
        return store.get(a.name, a)
    if isinstance(a, Add):
        return Add(subst_aexp(a.left, store), subst_aexp(a.right, store))
    if isinstance(a, Sub):
        return Sub(subst_aexp(a.left, store), subst_aexp(a.right, store))
    if isinstance(a, Mul):
        return Mul(subst_aexp(a.left, store), subst_aexp(a.right, store))
    raise TypeError(f"Unknown arithmetic expression: {a!r}")


def subst_bexp(b: BExp, store: SymStore) -> BExp:
    if isinstance(b, BoolConst):
        return b
    if isinstance(b, Eq):
        return Eq(subst_aexp(b.left, store), subst_aexp(b.right, store))
    if isinstance(b, Le):
        return Le(subst_aexp(b.left, store), subst_aexp(b.right, store))
    if isinstance(b, Not):
        return Not(subst_bexp(b.value, store))
    if isinstance(b, Or):
        return Or(subst_bexp(b.left, store), subst_bexp(b.right, store))
    if isinstance(b, And):
        return And(subst_bexp(b.left, store), subst_bexp(b.right, store))
    raise TypeError(f"Unknown boolean expression: {b!r}")


def input_symbols(cmd: Cmd) -> List[str]:
    return sorted(f"{v}0" for v in vars_cmd(cmd))


def initial_store(cmd: Cmd) -> SymStore:
    return {v: Var(f"{v}0") for v in sorted(vars_cmd(cmd))}


def satisfiable_bounded(path_condition: Sequence[BExp], input_vars: Sequence[str], lo: int = -3, hi: int = 3) -> bool:
    return find_model_bounded(path_condition, input_vars, lo=lo, hi=hi) is not None


def find_model_bounded(path_condition: Sequence[BExp], input_vars: Sequence[str], lo: int = -3, hi: int = 3) -> Optional[State]:
    domain = list(range(lo, hi + 1))
    for values in product(domain, repeat=len(input_vars)):
        sigma = dict(zip(input_vars, values))
        if all(eval_bexp(pc, sigma) for pc in path_condition):
            return sigma
    return None


def build_symbolic_execution_tree(cmd: Cmd, k: int, lo: int = -3, hi: int = 3) -> SymState:
    if k <= 0:
        raise ValueError("k must be strictly positive")

    cfg = build_cfg(cmd)
    root = SymState(
        label=cfg.entry,
        store=initial_store(cmd),
        path_condition=[],
        label_path=(),
        depth=0,
    )
    inputs = input_symbols(cmd)
    _expand_symbolic(cfg, root, k, inputs, lo, hi)
    return root


def _expand_symbolic(cfg: CFG, node: SymState, k: int, inputs: Sequence[str], lo: int, hi: int) -> None:
    if node.depth >= k or node.label == cfg.exit:
        return

    for edge in cfg.outgoing(node.label):
        child = symbolic_step(node, edge)
        if satisfiable_bounded(child.path_condition, inputs, lo=lo, hi=hi):
            node.children.append(child)
            _expand_symbolic(cfg, child, k, inputs, lo, hi)


def symbolic_step(state: SymState, edge: CFGEdge) -> SymState:
    new_pc = list(state.path_condition)
    guard = subst_bexp(edge.guard, state.store)
    if not (isinstance(guard, BoolConst) and guard.value is True):
        new_pc.append(guard)

    new_store = dict(state.store)
    if edge.action.kind == "assign":
        assert edge.action.var is not None and edge.action.expr is not None
        new_store[edge.action.var] = subst_aexp(edge.action.expr, state.store)

    return SymState(
        label=edge.dst,
        store=new_store,
        path_condition=new_pc,
        label_path=state.label_path + (edge.src,),
        depth=state.depth + 1,
    )


def collect_symbolic_paths(root: SymState) -> List[SymState]:
    leaves: List[SymState] = []

    def visit(node: SymState) -> None:
        if not node.children:
            leaves.append(node)
            return
        for child in node.children:
            visit(child)

    visit(root)
    return leaves


def generate_test_for_label_path(cmd: Cmd, k: int, label_path: Tuple[str, ...], lo: int = -3, hi: int = 3) -> Optional[State]:
    root = build_symbolic_execution_tree(cmd, k, lo=lo, hi=hi)
    inputs = input_symbols(cmd)

    for leaf in collect_symbolic_paths(root):
        if leaf.label_path == label_path:
            model = find_model_bounded(leaf.path_condition, inputs, lo=lo, hi=hi)
            if model is None:
                return None
            return {name[:-1]: value for name, value in model.items() if name.endswith("0")}
    return None


def compare_concrete_and_symbolic(cmd: Cmd, sigma: State, lo: int = -5, hi: int = 5) -> Dict[str, object]:
    from sos import run

    concrete = run(cmd, sigma)
    root = build_symbolic_execution_tree(cmd, max(1, len(concrete.path)), lo=lo, hi=hi)
    matching_leaf = None
    for leaf in collect_symbolic_paths(root):
        if leaf.label_path == concrete.path:
            matching_leaf = leaf
            break

    initial_sigma = {f"{k}0": v for k, v in sigma.items()}
    symbolic_matches = False
    if matching_leaf is not None:
        symbolic_matches = all(eval_bexp(pc, initial_sigma) for pc in matching_leaf.path_condition)

    return {
        "concrete_path": concrete.path,
        "concrete_final_state": concrete.sigma,
        "found_symbolic_path": matching_leaf is not None,
        "symbolic_condition_satisfied_by_input": symbolic_matches,
        "symbolic_path_condition": None if matching_leaf is None else matching_leaf.path_condition,
    }


def symbolic_tree_to_text(root: SymState) -> str:
    lines: List[str] = []

    def visit(node: SymState, indent: int) -> None:
        prefix = "  " * indent
        lines.append(prefix + node.pretty())
        for child in node.children:
            visit(child, indent + 1)

    visit(root, 0)
    return "\n".join(lines)
