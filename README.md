# IMP Operational Semantics Project

Python implementation of a small IMP language toolkit developed for the CentraleSupelec course "Analysis of Algorithms and Programs" (`Info 1`).

The repository covers the full workflow around a tiny imperative language:

- abstract syntax trees and well-formedness checks
- arithmetic and boolean expression evaluation
- concrete small-step operational semantics
- control-flow graph construction
- bounded path, decision, and condition coverage
- symbolic execution and bounded test generation
- parsing from a textual IMP syntax

## Repository Contents

| File | Purpose |
| --- | --- |
| `ast_imp.py` | IMP AST definitions, labels, pretty-printers, and helpers |
| `eval_imp.py` | Evaluation of arithmetic and boolean expressions |
| `sos.py` | Concrete small-step execution and trace generation |
| `cfg.py` | Control-flow graph construction and Graphviz export |
| `coverage.py` | Path, decision, and condition coverage utilities |
| `symbolic.py` | Symbolic execution tree construction and bounded solving |
| `parser_imp.py` | Lexer/parser for the textual IMP syntax |
| `examples.py` | Small example IMP programs |
| `test_imp.py` | Unit test suite |
| `main.py` | CLI entry point for running the analysis pipeline |

## Requirements

- Python 3.10+
- `graphviz` Python package if you want CFG rendering
- Graphviz system binaries if you want `--render` to produce a PDF directly

Install the optional dependency with:

```bash
pip install graphviz
```

If the Graphviz executable is not installed, the project still saves the CFG as a `.gv` file instead of rendering a PDF.

## Running the Project

Run the full pipeline on an IMP input file:

```bash
python main.py input.imp --k 5
```

Useful CLI options:

- `--k`: bound used for path exploration and symbolic execution
- `--max-steps`: safety bound for concrete execution
- `--render`: render the bundled subtractive GCD CFG to `gcd_cfg.pdf` or save `gcd_cfg.gv` if Graphviz is unavailable

Example:

```bash
python main.py input2.imp --k 8 --max-steps 2000
```

The CLI prints:

- the parsed initial environment
- final concrete state and traversed label path
- the control-flow graph
- bounded path coverage
- uncovered decisions and conditions
- the symbolic execution tree
- a comparison between concrete and symbolic execution

## Running Tests

```bash
python -m unittest test_imp.py
```

## IMP Input Format

Input files contain:

1. an optional initial state introduced by `sigma`
2. a labeled IMP program

Example:

```text
sigma X = 3, Y = 0

1 : Y := 0 ;
while 2 : not (X = 0) do
begin
    3 : Y := Y + X ;
    4 : X := X - 1
end
```

### Supported commands

- assignment: `1 : X := X + 1`
- skip: `2 : skip`
- sequencing: `c1 ; c2`
- conditional:

```text
if 1 : X <= 0 then
    2 : Y := 0
else
    3 : Y := 1
```

- loop:

```text
while 1 : not (X = 0) do
begin
    2 : X := X - 1
end
```

### Supported expressions

- arithmetic: integers, variables, `+`, `-`, `*`
- boolean: `=`, `<=`, `not`, `and`, `or`, `true`, `false`

Comments starting with `#` are ignored by the parser.

## Example Programs in Code

`examples.py` includes a few small benchmark-style programs:

- absolute value
- sum from `1` to `n`
- subtractive GCD

These are useful for testing the CFG, coverage, and symbolic execution modules directly from Python.

## Notes

- Labels should be unique across a program.
- Concrete execution uses bounded small-step evaluation to avoid non-terminating runs.
- Coverage and symbolic generation are bounded analyses, so results depend on the chosen `k`.
