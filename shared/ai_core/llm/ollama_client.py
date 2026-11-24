"""Small async client for a locally hosted Ollama instance."""
from __future__ import annotations

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = httpx.Timeout(timeout_seconds)

    async def _post(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Ollama returned an invalid response payload.")
        return data

    async def generate(self, prompt: str, system: str | None = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        data = await self._post("/api/generate", payload)
        result = data.get("response")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Ollama returned an empty or invalid response.")
        return result.strip()

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: str | None = None,
    ) -> str:
        """Generate JSON constrained by an Ollama-supported JSON schema."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        data = await self._post("/api/chat", payload)
        message = data.get("message")
        result = message.get("content") if isinstance(message, dict) else None
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Ollama returned an empty or invalid structured response.")
        return result.strip()
