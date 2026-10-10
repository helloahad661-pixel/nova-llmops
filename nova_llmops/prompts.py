"""Versioned prompt registry. Prompts are data, not string literals scattered
through code. JSON file on disk, dict in memory."""
import json
import pathlib


class PromptRegistry:
    def __init__(self, path=None):
        self.path = pathlib.Path(path) if path else None
        self._prompts = {}
        if self.path and self.path.exists():
            self._prompts = json.loads(self.path.read_text())

    def register(self, name, version, template):
        self._prompts.setdefault(name, {})[str(version)] = template
        self._save()

    def get(self, name, version="latest"):
        versions = self._prompts.get(name)
        if not versions:
            raise KeyError("unknown prompt: %s" % name)
        if version == "latest":
            version = max(versions, key=lambda v: [int(x) for x in
                                                   str(v).split(".")])
        return versions[str(version)]

    def render(self, prompt_name, version="latest", **vars):
        return self.get(prompt_name, version).format(**vars)

    def _save(self):
        if self.path:
            self.path.write_text(json.dumps(self._prompts, indent=2))
