from __future__ import annotations

import unittest

from ast_imp import Add, Assign, BoolConst, Eq, If, Int, Le, Not, Skip, Sub, Var, While, is_well_formed, seq
from cfg import build_cfg
from coverage import path_coverage, uncovered_decisions_and_conditions
from eval_imp import eval_aexp, eval_bexp
from examples import ex_abs, ex_gcd_subtractive, ex_sum_to_n
from parser_imp import parse_text
from sos import run
from symbolic import compare_concrete_and_symbolic, generate_test_for_label_path


class TestEval(unittest.TestCase):
    def test_aexp(self):
        expr = Add(Var("X"), Sub(Int(10), Var("Y")))
        self.assertEqual(eval_aexp(expr, {"X": 2, "Y": 3}), 9)

    def test_bexp(self):
        cond = Not(Le(Var("X"), Int(0)))
        self.assertTrue(eval_bexp(cond, {"X": 1}))
        self.assertFalse(eval_bexp(cond, {"X": 0}))


class TestSOS(unittest.TestCase):
    def test_assignment(self):
        cmd = Assign("1", "X", Add(Var("X"), Int(1)))
        result = run(cmd, {"X": 3})
        self.assertEqual(result.sigma, {"X": 4})
        self.assertEqual(result.path, ("1",))

    def test_if(self):
        cmd = If("1", Le(Var("X"), Int(0)), Assign("2", "Y", Int(0)), Assign("3", "Y", Int(1)))
        res1 = run(cmd, {"X": -1, "Y": 10})
        res2 = run(cmd, {"X": 5, "Y": 10})
        self.assertEqual(res1.path, ("1", "2"))
        self.assertEqual(res2.path, ("1", "3"))

    def test_while(self):
        cmd = While("1", Not(Eq(Var("X"), Int(0))), Assign("2", "X", Sub(Var("X"), Int(1))))
        result = run(cmd, {"X": 3})
        self.assertEqual(result.sigma["X"], 0)
        self.assertEqual(result.path, ("1", "2", "1", "2", "1", "2", "1"))

    def test_well_formed(self):
        bad = seq(Assign("1", "X", Int(1)), Skip("1"))
        self.assertFalse(is_well_formed(bad))


class TestCFGAndCoverage(unittest.TestCase):
    def test_cfg(self):
        cmd = ex_abs()
        cfg = build_cfg(cmd)
        self.assertEqual(cfg.entry, "1")
        self.assertTrue(any(e.src == "1" and e.dst == "2" for e in cfg.edges))
        self.assertTrue(any(e.src == "1" and e.dst == "3" for e in cfg.edges))

    def test_path_coverage(self):
        cmd = ex_abs()
        report = path_coverage(cmd, [{"X": -2}, {"X": 3}], k=2)
        self.assertAlmostEqual(report.coverage_rate, 1.0)

    def test_decision_condition_coverage(self):
        cmd = ex_abs()
        report = uncovered_decisions_and_conditions(cmd, [{"X": -1}, {"X": 3}])
        self.assertEqual(report.uncovered_decisions, {})
        self.assertEqual(report.uncovered_conditions, {})


class TestSymbolic(unittest.TestCase):
    def test_generate_test_from_path(self):
        cmd = ex_abs()
        sigma = generate_test_for_label_path(cmd, k=2, label_path=("1", "2"), lo=-3, hi=3)
        self.assertIsNotNone(sigma)
        self.assertLessEqual(sigma["X"], 0)

    def test_compare(self):
        cmd = ex_abs()
        info = compare_concrete_and_symbolic(cmd, {"X": -2})
        self.assertEqual(info["concrete_path"], ("1", "2"))
        self.assertTrue(info["found_symbolic_path"])
        self.assertTrue(info["symbolic_condition_satisfied_by_input"])


class TestParser(unittest.TestCase):
    def test_parser(self):
        text = """
        sigma X = 3, Y = 0
        1 : X := X + 1 ;
        while 2 : not (X <= 0) do
        begin
            3 : Y := Y + X ;
            4 : X := X - 1
        end
        """
        sigma, cmd = parse_text(text)
        self.assertEqual(sigma, {"X": 3, "Y": 0})
        result = run(cmd, sigma)
        self.assertEqual(result.sigma["X"], 0)


if __name__ == "__main__":
    unittest.main()
