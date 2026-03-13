from __future__ import annotations

from ast_imp import Add, Assign, Eq, If, Int, Le, Not, Seq, Sub, Var, While, seq


def ex_abs():
    # if X <= 0 then X := -X else X := X
    return If(
        "1",
        Le(Var("X"), Int(0)),
        Assign("2", "X", Sub(Int(0), Var("X"))),
        Assign("3", "X", Var("X")),
    )


def ex_sum_to_n():
    # Y := 0; while X != 0 do (Y := Y + X; X := X - 1)
    return seq(
        Assign("1", "Y", Int(0)),
        While(
            "2",
            Not(Eq(Var("X"), Int(0))),
            seq(
                Assign("3", "Y", Add(Var("Y"), Var("X"))),
                Assign("4", "X", Sub(Var("X"), Int(1))),
            ),
        ),
    )


def ex_gcd_subtractive():
    # while X != Y do if X <= Y then Y := Y - X else X := X - Y
    return While(
        "1",
        Not(Eq(Var("X"), Var("Y"))),
        If(
            "2",
            Le(Var("X"), Var("Y")),
            Assign("3", "Y", Sub(Var("Y"), Var("X"))),
            Assign("4", "X", Sub(Var("X"), Var("Y"))),
        ),
    )
