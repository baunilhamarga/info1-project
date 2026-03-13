from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from ast_imp import BExp, BoolConst, Cmd, Eq, If, Le, Not, Or, And, Path, State, While
from cfg import CFG, CFGEdge, build_cfg
from sos import run_with_trace


LabelPath = Tuple[str, ...]


def enumerate_cfg_label_paths(cfg: CFG, k: int) -> Set[LabelPath]:
    if k <= 0:
        raise ValueError("k must be strictly positive")

    results: Set[LabelPath] = set()

    def dfs(current_label: str, prefix: List[str], depth: int) -> None:
        if depth > k:
            return
        if current_label == cfg.exit:
            results.add(tuple(prefix))
            return
        for edge in cfg.outgoing(current_label):
            dfs(edge.dst, prefix + [edge.src], depth + 1)

    dfs(cfg.entry, [], 0)
    return results


def covered_prefixes_from_execution_path(path: Path, k: int) -> Set[LabelPath]:
    covered: Set[LabelPath] = set()
    for i in range(1, min(len(path), k) + 1):
        covered.add(tuple(path[:i]))
    return covered


@dataclass(frozen=True)
class PathCoverageReport:
    all_paths: Set[LabelPath]
    covered_paths: Set[LabelPath]
    uncovered_paths: Set[LabelPath]
    coverage_rate: float


def path_coverage(cmd: Cmd, test_set: Sequence[State], k: int) -> PathCoverageReport:
    cfg = build_cfg(cmd)
    all_paths = enumerate_cfg_label_paths(cfg, k)
    covered_paths: Set[LabelPath] = set()

    for sigma in test_set:
        trace = run_with_trace(cmd, sigma)
        covered_paths |= covered_prefixes_from_execution_path(trace.path, k)

    covered_paths = covered_paths & all_paths
    uncovered_paths = all_paths - covered_paths
    rate = 1.0 if not all_paths else len(covered_paths) / len(all_paths)
    return PathCoverageReport(
        all_paths=all_paths,
        covered_paths=covered_paths,
        uncovered_paths=uncovered_paths,
        coverage_rate=rate,
    )


def atomic_conditions(b: BExp) -> Set[str]:
    if isinstance(b, (Eq, Le)):
        return {repr(b)}
    if isinstance(b, BoolConst):
        return set()
    if isinstance(b, Not):
        return atomic_conditions(b.value)
    if isinstance(b, (Or, And)):
        return atomic_conditions(b.left) | atomic_conditions(b.right)
    raise TypeError(f"Unknown boolean expression: {b!r}")


def decisions_in_program(cmd: Cmd) -> Dict[str, str]:
    if isinstance(cmd, If):
        result = {cmd.label: repr(cmd.cond)}
        result.update(decisions_in_program(cmd.then_branch))
        result.update(decisions_in_program(cmd.else_branch))
        return result
    if isinstance(cmd, While):
        result = {cmd.label: repr(cmd.cond)}
        result.update(decisions_in_program(cmd.body))
        return result
    from ast_imp import Skip, Assign, Seq
    if isinstance(cmd, (Skip, Assign)):
        return {}
    if isinstance(cmd, Seq):
        result = decisions_in_program(cmd.first)
        result.update(decisions_in_program(cmd.second))
        return result
    raise TypeError(f"Unknown command: {cmd!r}")


def conditions_in_program(cmd: Cmd) -> Set[str]:
    if isinstance(cmd, If):
        return atomic_conditions(cmd.cond) | conditions_in_program(cmd.then_branch) | conditions_in_program(cmd.else_branch)
    if isinstance(cmd, While):
        return atomic_conditions(cmd.cond) | conditions_in_program(cmd.body)
    from ast_imp import Skip, Assign, Seq
    if isinstance(cmd, (Skip, Assign)):
        return set()
    if isinstance(cmd, Seq):
        return conditions_in_program(cmd.first) | conditions_in_program(cmd.second)
    raise TypeError(f"Unknown command: {cmd!r}")


@dataclass(frozen=True)
class DecisionConditionCoverageReport:
    uncovered_decisions: Dict[str, Set[bool]]
    uncovered_conditions: Dict[str, Set[bool]]


def uncovered_decisions_and_conditions(cmd: Cmd, test_set: Sequence[State]) -> DecisionConditionCoverageReport:
    all_decisions = decisions_in_program(cmd)
    all_conditions = conditions_in_program(cmd)

    decision_seen: Dict[str, Set[bool]] = {label: set() for label in all_decisions}
    cond_seen: Dict[str, Set[bool]] = {cond: set() for cond in all_conditions}

    for sigma in test_set:
        trace = run_with_trace(cmd, sigma)
        for event in trace.decisions:
            if event.label in decision_seen:
                decision_seen[event.label].add(event.value)
        for event in trace.atomic_conditions:
            if event.condition_repr in cond_seen:
                cond_seen[event.condition_repr].add(event.value)

    uncovered_decisions = {label: {True, False} - seen for label, seen in decision_seen.items() if {True, False} - seen}
    uncovered_conditions = {cond: {True, False} - seen for cond, seen in cond_seen.items() if {True, False} - seen}
    return DecisionConditionCoverageReport(
        uncovered_decisions=uncovered_decisions,
        uncovered_conditions=uncovered_conditions,
    )
