"""Token/cost/latency log in SQLite. Reads open read-only (mode=ro)."""
import pathlib
import sqlite3
import time

# USD per 1M tokens (input, output). SAMPLE rates — edit for your contracts.
PRICES = {
    "fake-small": (0.10, 0.30),
    "fake-large": (1.00, 3.00),
}

SCHEMA = ("CREATE TABLE IF NOT EXISTS calls("
          "id INTEGER PRIMARY KEY, ts REAL, provider TEXT, model TEXT,"
          "input_tokens INTEGER, output_tokens INTEGER,"
          "latency REAL, ok INTEGER)")


class CostLog:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        con = sqlite3.connect(str(self.path))
        try:
            con.execute(SCHEMA)
            con.commit()
        finally:
            con.close()

    def record(self, provider, model, input_tokens, output_tokens,
               latency, ok=True):
        con = sqlite3.connect(str(self.path), timeout=10)
        try:
            con.execute("INSERT INTO calls(ts,provider,model,input_tokens,"
                        "output_tokens,latency,ok) VALUES (?,?,?,?,?,?,?)",
                        (time.time(), provider, model, input_tokens,
                         output_tokens, latency, int(bool(ok))))
            con.commit()
        finally:
            con.close()

    def _read(self):
        uri = "file:%s?mode=ro" % self.path.as_posix()
        con = sqlite3.connect(uri, uri=True, timeout=10)
        try:
            return con.execute("SELECT provider,model,input_tokens,"
                               "output_tokens,latency,ok FROM calls").fetchall()
        finally:
            con.close()

    def report(self):
        rows = self._read()
        by_model = {}
        for prov, model, i, o, lat, ok in rows:
            m = by_model.setdefault(model, {"calls": 0, "failures": 0,
                                            "in_tok": 0, "out_tok": 0,
                                            "latency": 0.0})
            m["calls"] += 1
            m["failures"] += 0 if ok else 1
            m["in_tok"] += i
            m["out_tok"] += o
            m["latency"] += lat
        out = {"total_calls": len(rows), "models": {}}
        for model, m in by_model.items():
            pi, po = PRICES.get(model, (0.0, 0.0))
            cost = (m["in_tok"] * pi + m["out_tok"] * po) / 1e6
            m["est_cost_usd"] = round(cost, 6)
            m["avg_latency"] = round(m["latency"] / m["calls"], 3)
            out["models"][model] = m
        out["total_est_cost_usd"] = round(sum(m["est_cost_usd"] for m in
                                             out["models"].values()), 6)
        return out
