from __future__ import annotations

import argparse
from pprint import pprint

from cfg import build_cfg, cfg_to_text, cmd_to_graphviz
from coverage import path_coverage, uncovered_decisions_and_conditions
from parser_imp import parse_file
from sos import run, run_with_trace
from symbolic import build_symbolic_execution_tree, compare_concrete_and_symbolic, symbolic_tree_to_text
from graphviz.backend import ExecutableNotFound



def main() -> None:
    parser = argparse.ArgumentParser(description="IMP project runner")
    parser.add_argument("file", help="input file containing sigma and an IMP program")
    parser.add_argument("--max-steps", type=int, default=10_000)
    parser.add_argument("--k", type=int, default=5, help="bound for path / symbolic exploration")
    parser.add_argument("--render", action="store_true", help="render the CFG as a PDF")
    args = parser.parse_args()

    sigma, cmd = parse_file(args.file)

    print("=== Parsed environment ===")
    pprint(sigma)

    print("\n=== Concrete execution ===")
    result = run(cmd, sigma, max_steps=args.max_steps)
    print("final state:", result.sigma)
    print("path:", ".".join(result.path))

    print("\n=== CFG ===")
    cfg = build_cfg(cmd)
    print(cfg_to_text(cfg))
    if args.render:
        dot = cmd_to_graphviz(cmd, name="cfg")
        try:
            dot.graph_attr.update({'margin': '0', 'pad': '0'})
            dot.render("cfg", format="pdf", cleanup=True, quiet=True)
            print("PDF written to cfg.pdf")
        except ExecutableNotFound:
            dot.save("cfg.gv")
            print("Graphviz 'dot' executable not found.")
            print("I saved the DOT source as cfg.gv instead.")

    print("\n=== Bounded path coverage for singleton test set ===")
    report = path_coverage(cmd, [sigma], args.k)
    print("all paths:", sorted(report.all_paths))
    print("covered paths:", sorted(report.covered_paths))
    print("coverage rate:", report.coverage_rate)

    print("\n=== Decision / condition coverage for singleton test set ===")
    dc = uncovered_decisions_and_conditions(cmd, [sigma])
    print("uncovered decisions:", dc.uncovered_decisions)
    print("uncovered conditions:", dc.uncovered_conditions)

    print("\n=== Symbolic execution tree ===")
    tree = build_symbolic_execution_tree(cmd, args.k)
    print(symbolic_tree_to_text(tree))

    print("\n=== Concrete vs symbolic ===")
    pprint(compare_concrete_and_symbolic(cmd, sigma))


if __name__ == "__main__":
    main()
