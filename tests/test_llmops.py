"""Tests: router failover, cost log, evals, prompt registry. Stdlib only —
no network, no API keys. Run: python -m unittest discover -s tests -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from nova_llmops.router import Router, FakeProvider, ProviderError
from nova_llmops.costs import CostLog
from nova_llmops.evals import run_evals
from nova_llmops.prompts import PromptRegistry


class TestRouter(unittest.TestCase):
    def test_first_healthy_provider_wins(self):
        r = Router([FakeProvider("a", reply="from-a")]).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(r["text"], "from-a")
        self.assertEqual(r["provider"], "a")

    def test_fails_over_to_next_provider(self):
        r = Router([FakeProvider("down", fail=True),
                    FakeProvider("up", reply="backup")]).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(r["text"], "backup")
        self.assertEqual(r["provider"], "up")

    def test_all_down_raises_with_every_error(self):
        with self.assertRaises(ProviderError) as ctx:
            Router([FakeProvider("x", fail=True),
                    FakeProvider("y", fail=True)]).chat([{"role": "user", "content": "hi"}])
        self.assertIn("x", str(ctx.exception))
        self.assertIn("y", str(ctx.exception))

    def test_attempts_are_logged(self):
        with tempfile.TemporaryDirectory() as d:
            log = CostLog(Path(d) / "c.db")
            Router([FakeProvider("a", reply="hi")], log=log).chat([{"role": "user", "content": "hi"}])
            self.assertEqual(log.report()["total_calls"], 1)


class TestCosts(unittest.TestCase):
    def test_report_math(self):
        with tempfile.TemporaryDirectory() as d:
            log = CostLog(Path(d) / "c.db")
            log.record("p", "fake-small", 1_000_000, 1_000_000, 0.5)
            rep = log.report()
            self.assertEqual(rep["total_calls"], 1)
            self.assertAlmostEqual(rep["total_est_cost_usd"], 0.10 + 0.30)
            self.assertEqual(rep["models"]["fake-small"]["failures"], 0)

    def test_read_path_is_read_only(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.db"
            CostLog(p)
            ro = sqlite3.connect("file:%s?mode=ro" % p.as_posix(), uri=True)
            try:
                with self.assertRaises(Exception):
                    ro.execute("CREATE TABLE nope(x)")
            finally:
                ro.close()


class TestEvals(unittest.TestCase):
    def test_pass_and_fail_counted(self):
        router = Router([FakeProvider("a", reply="Hello there")])
        out = run_evals(router, [
            {"name": "says-hello", "prompt": "hi", "expect": "hello"},
            {"name": "says-bye", "prompt": "hi", "expect": "goodbye"},
        ])
        self.assertEqual((out["passed"], out["failed"]), (1, 1))

    def test_dead_router_fails_cases_not_crashes(self):
        router = Router([FakeProvider("x", fail=True)])
        out = run_evals(router, [{"name": "n", "prompt": "hi", "expect": "x"}])
        self.assertEqual(out["failed"], 1)


class TestPrompts(unittest.TestCase):
    def test_register_render_latest(self):
        with tempfile.TemporaryDirectory() as d:
            reg = PromptRegistry(Path(d) / "p.json")
            reg.register("greet", "1.0", "Hello {name}")
            reg.register("greet", "2.0", "Hello {name}, welcome!")
            self.assertEqual(reg.render("greet", name="Sam"), "Hello Sam, welcome!")
            self.assertEqual(reg.render("greet", version="1.0", name="Sam"), "Hello Sam")

    def test_unknown_prompt_raises(self):
        with self.assertRaises(KeyError):
            PromptRegistry().render("nope")


if __name__ == "__main__":
    unittest.main()
