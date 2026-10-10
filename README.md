# nova-llmops

Small LLMOps starter kit: route LLM calls across providers with failover,
log every call's tokens, cost and latency to SQLite, version your prompts,
and eval them — all with zero third-party dependencies and no API keys.

```bash
python -m unittest discover -s tests -v   # 10 tests, no network, no keys
```

## What's inside

| Module | What it does |
|---|---|
| `router.py` | Tries providers in order, first success wins. Every attempt logged. Dead backends never kill the call — their errors are collected, not raised. |
| `costs.py` | SQLite log of provider, model, tokens, latency, ok/fail. Reads open **read-only** (`mode=ro`). `report()` totals calls, failures, average latency and estimated USD per model. |
| `evals.py` | Runs `{name, prompt, expect}` cases through any router, counts pass/fail. Expectations are substrings or callables. A dead router fails cases, never crashes the run. |
| `prompts.py` | Versioned prompt registry backed by a JSON file. `render(name, version="latest", **vars)` — prompts as data, not string literals. |

## Try it (no keys needed)

```python
from nova_llmops.router import Router, FakeProvider
from nova_llmops.costs import CostLog
from nova_llmops.evals import run_evals, demo_cases

log = CostLog("calls.db")
router = Router([FakeProvider("primary", fail=True),
                 FakeProvider("backup", reply="Check-in is at 3pm")],
                log=log)
print(run_evals(router, demo_cases()))
print(log.report())
```

Swap `FakeProvider` for a real backend by implementing `chat(messages)` —
return `{"text", "input_tokens", "output_tokens"}`, raise `ProviderError`
on failure. Price your own models in `costs.PRICES` (the table ships with
clearly-marked sample rates).

Part of [Nova](https://github.com/helloahad661-pixel/Nova), my macOS assistant system — `laya_agent` looks after this piece.
