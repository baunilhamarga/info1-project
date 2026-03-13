from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from ast_imp import (
    AExp,
    Assign,
    BExp,
    BoolConst,
    Cmd,
    EXIT_LABEL,
    If,
    Skip,
    While,
    entry_label,
    pretty_aexp,
    pretty_bexp,
)
from ast_imp import Seq as SeqCmd


@dataclass(frozen=True)
class EdgeAction:
    kind: str  # "skip" or "assign"
    var: str | None = None
    expr: AExp | None = None

    def pretty(self) -> str:
        if self.kind == "skip":
            return "skip"
        if self.kind == "assign":
            assert self.var is not None and self.expr is not None
            return f"{self.var} := {pretty_aexp(self.expr)}"
        raise ValueError(f"Unknown action kind: {self.kind}")


@dataclass(frozen=True)
class CFGEdge:
    src: str
    dst: str
    guard: BExp
    action: EdgeAction

    def pretty(self) -> str:
        return f"{self.src} --[{pretty_bexp(self.guard)} / {self.action.pretty()}]--> {self.dst}"


@dataclass
class CFG:
    entry: str
    exit: str
    edges: List[CFGEdge]

    def outgoing(self, label: str) -> List[CFGEdge]:
        return [e for e in self.edges if e.src == label]

    def nodes(self) -> List[str]:
        ns = {self.entry, self.exit}
        for e in self.edges:
            ns.add(e.src)
            ns.add(e.dst)
        return sorted(ns)


TRUE_GUARD = BoolConst(True)


def build_cfg(cmd: Cmd) -> CFG:
    edges, entry = _build_with_next(cmd, EXIT_LABEL)
    return CFG(entry=entry, exit=EXIT_LABEL, edges=edges)


def _build_with_next(cmd: Cmd, next_label: str) -> Tuple[List[CFGEdge], str]:
    if isinstance(cmd, Skip):
        edge = CFGEdge(cmd.label, next_label, TRUE_GUARD, EdgeAction("skip"))
        return [edge], cmd.label

    if isinstance(cmd, Assign):
        edge = CFGEdge(cmd.label, next_label, TRUE_GUARD, EdgeAction("assign", cmd.var, cmd.expr))
        return [edge], cmd.label

    if isinstance(cmd, SeqCmd):
        edges2, entry2 = _build_with_next(cmd.second, next_label)
        edges1, entry1 = _build_with_next(cmd.first, entry2)
        return edges1 + edges2, entry1

    if isinstance(cmd, If):
        edges_t, entry_t = _build_with_next(cmd.then_branch, next_label)
        edges_e, entry_e = _build_with_next(cmd.else_branch, next_label)
        head = [
            CFGEdge(cmd.label, entry_t, cmd.cond, EdgeAction("skip")),
            CFGEdge(cmd.label, entry_e, _neg(cmd.cond), EdgeAction("skip")),
        ]
        return head + edges_t + edges_e, cmd.label

    if isinstance(cmd, While):
        body_edges, body_entry = _build_with_next(cmd.body, cmd.label)
        head = [
            CFGEdge(cmd.label, body_entry, cmd.cond, EdgeAction("skip")),
            CFGEdge(cmd.label, next_label, _neg(cmd.cond), EdgeAction("skip")),
        ]
        return head + body_edges, cmd.label

    raise TypeError(f"Unknown command: {cmd!r}")


def _neg(b: BExp) -> BExp:
    from ast_imp import Not
    return Not(b)


def cfg_to_text(cfg: CFG) -> str:
    lines = [f"entry = {cfg.entry}", f"exit = {cfg.exit}", "edges:"]
    for e in cfg.edges:
        lines.append(f"  {e.pretty()}")
    return "\n".join(lines)
