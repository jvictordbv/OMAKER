"""Minimal Ollama client for local Qwen3, with JSON-schema output and retries."""
from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

DEFAULT_MODEL = "qwen3:8b"
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
if not DEFAULT_HOST.startswith("http"):
    DEFAULT_HOST = "http://" + DEFAULT_HOST


class LLMError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST, num_ctx: int = 8192, timeout: int = 600):
        self.model = model
        self.host = host.rstrip("/")
        self.num_ctx = num_ctx   # Ollama's default (2-4k) silently truncates long prompts
        self.timeout = timeout

    def check(self):
        """Fails early with an actionable message if Ollama or the model is missing."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
        except requests.RequestException:
            raise LLMError(f"Cannot reach Ollama at {self.host}. Install/start it (`ollama serve`).")
        names = [m.get("name", "") for m in r.json().get("models", [])]
        wanted = self.model if ":" in self.model else self.model + ":"
        if not any(n == self.model or n.startswith(wanted) for n in names):
            raise LLMError(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")

    def _post(self, payload: dict) -> str:
        r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        if r.status_code == 400 and "think" in r.text.lower() and "think" in payload:
            payload = {k: v for k, v in payload.items() if k != "think"}  # older Ollama / non-thinking model
            r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        if r.status_code != 200:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        return r.json()["message"]["content"]

    @staticmethod
    def _parse_json(content: str):
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
        return json.loads(content)

    def chat_json(self, system: str, user: str, schema: dict, temperature: float = 0.1, retries: int = 2):
        """Returns parsed JSON that follows `schema`. Retries with the parse error as feedback."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        last_err: Optional[Exception] = None
        for _ in range(retries + 1):
            content = self._post(
                {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "think": False,       # no reasoning block mixed into the answer
                    "format": schema,     # structured output enforced by Ollama
                    "options": {"temperature": temperature, "num_ctx": self.num_ctx},
                }
            )
            try:
                return self._parse_json(content)
            except json.JSONDecodeError as e:
                last_err = e
                messages += [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That was not valid JSON ({e}). Return only valid JSON that matches the schema."},
                ]
        raise LLMError(f"The model did not return valid JSON after {retries + 1} attempts: {last_err}")