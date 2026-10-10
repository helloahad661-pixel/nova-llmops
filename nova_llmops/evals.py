"""Tiny eval runner: prompts in, pass rate out. Expectations are substrings
(or callables taking the reply text). No network, no keys — bring any router.
"""
from .router import ProviderError


def run_evals(router, cases):
    """cases: [{name, prompt, expect}]. Returns {passed, failed, results}."""
    results = []
    for c in cases:
        try:
            r = router.chat([{"role": "user", "content": c["prompt"]}])
            text = r.get("text", "")
            exp = c["expect"]
            ok = exp(text) if callable(exp) else exp.lower() in text.lower()
            results.append({"name": c["name"], "ok": bool(ok),
                            "provider": r.get("provider"), "reply": text})
        except ProviderError as e:
            results.append({"name": c["name"], "ok": False,
                            "provider": None, "reply": "ERROR: %s" % e})
    passed = sum(1 for r in results if r["ok"])
    return {"passed": passed, "failed": len(results) - passed,
            "results": results}


def demo_cases():
    return [
        {"name": "greeting", "prompt": "Say hello",
         "expect": "hello"},
        {"name": "checkin-time", "prompt": "What time is check-in?",
         "expect": lambda t: any(w in t.lower() for w in ["check-in", "3pm", "3 pm"])},
    ]
