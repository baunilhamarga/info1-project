# IMP operational semantics project

Operational Semantics project for the CentraleSupélec's course "Analysis of algorithms and programs" (Parcours Recherche - Info 1)

- Q1: AST, environments, utility functions
- Q2: small-step SOS interpreter with execution paths
- Q3: unit tests
- Q4: CFG construction
- Q5: bounded path coverage
- Q6: decision / condition coverage
- Q7: symbolic execution tree
- Q8: test generation from symbolic paths (bounded finite-domain solver)
- Q9: comparison between concrete and symbolic execution
- Q10: lexer + parser for a textual IMP syntax

## Files

- `ast_imp.py`: abstract syntax tree and utility functions
- `eval_imp.py`: arithmetic / boolean evaluation
- `sos.py`: concrete small-step semantics
- `cfg.py`: control-flow graph
- `coverage.py`: path, decision, and condition coverage
- `symbolic.py`: symbolic execution and bounded solving
- `parser_imp.py`: lexer + parser
- `examples.py`: example programs
- `test_imp.py`: unit tests
- `main.py`: small CLI driver

## Run tests

```bash
python -m unittest test_imp.py
```

## Run on a file

```bash
python main.py input.imp --k 5
```

## Example input file

```text
sigma X = 3, Y = 0

1 : Y := 0 ;
while 2 : not (X = 0) do
begin
    3 : Y := Y + X ;
    4 : X := X - 1
end
```
