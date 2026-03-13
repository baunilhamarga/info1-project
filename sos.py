from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from ast_imp import Assign, Cmd, If, Path, Seq, Skip, State, While, duplicate_labels, is_well_formed
from eval_imp import eval_aexp, eval_bexp, eval_bexp_with_atoms


@dataclass(frozen=True)
class Config:
    cmd: Cmd
    sigma: State
    path: Path = ()


@dataclass(frozen=True)
class FinalConfig:
    sigma: State
    path: Path


@dataclass(frozen=True)
class DecisionEvent:
    label: str
    condition_repr: str
    value: bool


@dataclass(frozen=True)
class AtomicConditionEvent:
    condition_repr: str
    value: bool


@dataclass(frozen=True)
class ExecutionTrace:
    final_sigma: State
    path: Path
    decisions: Tuple[DecisionEvent, ...]
    atomic_conditions: Tuple[AtomicConditionEvent, ...]


StepResult = Union[Config, FinalConfig]


def step(cfg: Config) -> StepResult:
    c, sigma, path = cfg.cmd, cfg.sigma, cfg.path

    # (A) Assign
    if isinstance(c, Assign):
        sigma2 = dict(sigma)
        sigma2[c.var] = eval_aexp(c.expr, sigma)
        return Config(Skip(c.label), sigma2, path)

    # (Sa) Skip alone
    if isinstance(c, Skip):
        return FinalConfig(sigma, path + (c.label,))

    # (SS) and (SnoS)
    if isinstance(c, Seq):
        if isinstance(c.first, Skip):
            return Config(c.second, sigma, path + (c.first.label,))
        nxt = step(Config(c.first, sigma, path))
        if isinstance(nxt, FinalConfig):
            return Config(c.second, nxt.sigma, nxt.path)
        return Config(Seq(nxt.cmd, c.second), nxt.sigma, nxt.path)

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

    raise TypeError(f"Unknown command: {c!r}")


def run(cmd: Cmd, sigma: State, max_steps: int = 10_000) -> FinalConfig:
    if not is_well_formed(cmd):
        raise ValueError(f"Program is not well formed: duplicate labels {sorted(duplicate_labels(cmd))}")

    current = Config(cmd, dict(sigma), ())
    for _ in range(max_steps):
        nxt = step(current)
        if isinstance(nxt, FinalConfig):
            return nxt
        current = nxt
    raise RuntimeError("Maximum number of steps reached. Possible non-termination.")


def run_with_trace(cmd: Cmd, sigma: State, max_steps: int = 10_000) -> ExecutionTrace:
    if not is_well_formed(cmd):
        raise ValueError(f"Program is not well formed: duplicate labels {sorted(duplicate_labels(cmd))}")

    decisions: List[DecisionEvent] = []
    atomics: List[AtomicConditionEvent] = []

    current = Config(cmd, dict(sigma), ())
    for _ in range(max_steps):
        c = current.cmd

        if isinstance(c, If):
            value, atoms = eval_bexp_with_atoms(c.cond, current.sigma)
            decisions.append(DecisionEvent(c.label, repr(c.cond), value))
            atomics.extend(AtomicConditionEvent(cond_repr, cond_val) for cond_repr, cond_val in atoms)
        elif isinstance(c, While):
            value, atoms = eval_bexp_with_atoms(c.cond, current.sigma)
            decisions.append(DecisionEvent(c.label, repr(c.cond), value))
            atomics.extend(AtomicConditionEvent(cond_repr, cond_val) for cond_repr, cond_val in atoms)

        nxt = step(current)
        if isinstance(nxt, FinalConfig):
            return ExecutionTrace(
                final_sigma=nxt.sigma,
                path=nxt.path,
                decisions=tuple(decisions),
                atomic_conditions=tuple(atomics),
            )
        current = nxt

    raise RuntimeError("Maximum number of steps reached. Possible non-termination.")
