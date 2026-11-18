"""Optional fixed-endpoint generators; configuration never enables generation."""
import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.services.rag.prompts import SYSTEM


@dataclass(frozen=True)
class Generated:
    text: str
    input_tokens: int | None
    output_tokens: int | None


def token_count(value):
    return value if type(value) is int and 0 <= value <= 1_000_000_000 else None


class Generator(Protocol):
    async def generate(self, question, sources) -> Generated: ...


class OpenAIResponses:
    def __init__(self, model, key):
        self.model, self.key = model, key

    async def generate(self, question, sources):
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            for attempt in range(2):
                response = await client.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {self.key}"}, json={
                    "model": self.model, "store": False, "max_output_tokens": 800,
                    "instructions": SYSTEM, "input": json.dumps({"question": question, "excerpts": sources})})
                if response.status_code not in {429, 503} or attempt:
                    break
            response.raise_for_status()
            data = response.json()
        if data.get("status") != "completed":
            raise ValueError("Incomplete generation")
        answer = "\n".join(part["text"] for item in data.get("output", []) if item.get("type") == "message"
                           for part in item.get("content", []) if part.get("type") == "output_text")
        usage = data.get("usage") or {}
        return Generated(answer, token_count(usage.get("input_tokens")), token_count(usage.get("output_tokens")))


class Ollama:
    def __init__(self, model):
        self.model = model

    async def generate(self, question, sources):
        # Loopback only, no custom URL, proxies or redirects. Does not pull models.
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
            response = await client.post("http://127.0.0.1:11434/api/chat", json={"model": self.model, "stream": False,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps({"question": question, "excerpts": sources})}],
                "options": {"num_predict": 800, "num_ctx": 8192}})
            response.raise_for_status()
            data = response.json()
        if not data.get("done"):
            raise ValueError("Incomplete generation")
        return Generated(data["message"]["content"], token_count(data.get("prompt_eval_count")), token_count(data.get("eval_count")))
