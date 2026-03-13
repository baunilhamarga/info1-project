from ast_imp import *

p = Assign("1", "X", Add(Var("X"), Int(1)))
res = run(p, {"X": 3})
print(res.sigma)   # {'X': 4}
print(res.path)    # ('1',)

p = If(
    "1",
    Le(Var("X"), Int(0)),
    Assign("2", "Y", Int(0)),
    Assign("3", "Y", Int(1)),
)
print(run(p, {"X": -2, "Y": 99}))
print(run(p, {"X": 5, "Y": 99}))
# Expected paths are ('1', '2') and ('1', '3').

p = While(
    "1",
    Not(Eq(Var("X"), Int(0))),
    Assign("2", "X", Sub(Var("X"), Int(1))),
)
res = run(p, {"X": 3})
print(res.sigma)   # {'X': 0}
print(res.path)    # ('1', '2', '1', '2', '1', '2', '1')