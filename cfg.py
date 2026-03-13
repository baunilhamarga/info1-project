from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple
from graphviz import Digraph
from turtle import dot

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


def cfg_to_graphviz(cfg: CFG, *, name: str = "cfg") -> Digraph:
    """
    Convert a CFG into a Graphviz Digraph.

    Rendering conventions:
    - one node per program label;
    - the exit node is displayed as '_';
    - each edge is labelled with:
          guard
          action
    """
    dot = Digraph(name=name, format="pdf")
    dot.attr(rankdir="TB", splines="true", nodesep="0.5", ranksep="0.6")
    dot.attr(
        "node",
        shape="circle",
        fontname="Helvetica",
        fontsize="12",
        width="0.55",
        height="0.55",
        margin="0.03",
    )
    dot.attr("edge", fontname="Helvetica", fontsize="10")

    for node in cfg.nodes():
        visible = "_" if node == EXIT_LABEL else str(node)
        attrs = {}

        if node == cfg.entry:
            attrs.update(style="filled", fillcolor="lightgrey")

        if node == cfg.exit:
            attrs.update(peripheries="2")

        dot.node(str(node), visible, **attrs)

    for edge in cfg.edges:
        edge_label = f"{pretty_bexp(edge.guard)}\\n{edge.action.pretty()}"
        dot.edge(str(edge.src), str(edge.dst), label=edge_label)

    return dot


def cmd_to_graphviz(cmd: Cmd, *, name: str = "cfg") -> Digraph:
    """Convenience wrapper: build the CFG, then render it."""
    return cfg_to_graphviz(build_cfg(cmd), name=name)