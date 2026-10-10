"""Provider router with failover. No third-party deps, no API keys needed."""
import time


class ProviderError(Exception):
    pass


class Provider:
    """Implement chat(messages) -> dict(text, input_tokens, output_tokens).
    Raise ProviderError when the backend is down, rate-limited, or failing.
    """
    name = "base"
    model = "unknown"

    def chat(self, messages):
        raise NotImplementedError


class FakeProvider(Provider):
    """Deterministic stand-in for tests and demos. Fails when told to."""

    def __init__(self, name, reply="ok", fail=False, in_tok=10, out_tok=5):
        self.name = name
        self.model = name
        self._reply = reply
        self._fail = fail
        self._in, self._out = in_tok, out_tok

    def chat(self, messages):
        if self._fail:
            raise ProviderError("%s is down" % self.name)
        return {"text": self._reply, "input_tokens": self._in,
                "output_tokens": self._out}


class Router:
    """Try providers in order. First success wins; all attempts are logged."""

    def __init__(self, providers, log=None):
        self.providers = list(providers)
        self.log = log

    def chat(self, messages, retries=1):
        errors = []
        for p in self.providers:
            for _ in range(max(1, retries)):
                t0 = time.monotonic()
                try:
                    r = p.chat(messages)
                    if self.log is not None:
                        self.log.record(provider=p.name, model=p.model,
                                        input_tokens=r.get("input_tokens", 0),
                                        output_tokens=r.get("output_tokens", 0),
                                        latency=time.monotonic() - t0, ok=True)
                    r["provider"] = p.name
                    return r
                except ProviderError as e:
                    errors.append("%s: %s" % (p.name, e))
                except Exception as e:  # never let one backend kill the call
                    errors.append("%s: unexpected %r" % (p.name, e))
        raise ProviderError("all providers failed: %s" % " | ".join(errors))
