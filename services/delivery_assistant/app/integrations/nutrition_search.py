"""Small web-search integration for food nutrition questions.

Search snippets are treated as unverified source material, not as authoritative
medical or dietary advice. The adapter intentionally returns a few attributed
web results instead of inventing normalized nutrition values.
"""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx


class NutritionSearchError(RuntimeError):
    """Raised when the web search provider cannot be reached or parsed."""


class _DuckDuckGoLiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._current: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result-link" in classes:
            self._capture = "title"
            self._buffer = []
            self._current = {"url": self._clean_url(attributes.get("href") or "")}
        elif tag in {"td", "div"} and "result-snippet" in classes:
            self._capture = "snippet"
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "title" and tag == "a":
            self._current["title"] = " ".join("".join(self._buffer).split())
            self._capture = None
            self._buffer = []
        elif self._capture == "snippet" and tag in {"td", "div"}:
            snippet = " ".join("".join(self._buffer).split())
            if snippet and self._current.get("title") and self._current.get("url"):
                self._current["snippet"] = snippet
                self.results.append(self._current)
                self._current = {}
            self._capture = None
            self._buffer = []

    @staticmethod
    def _clean_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(target)
        return url


class NutritionSearch:
    """Search the public web for food-specific nutrition information."""

    SEARCH_URL = "https://lite.duckduckgo.com/lite/"

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def search(self, food: str, limit: int = 3) -> list[dict[str, str]]:
        query = f"{food.strip()} calories nutrition facts per serving"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                headers={"User-Agent": "DigoFoodAssistant/1.0"},
                follow_redirects=True,
            ) as client:
                response = await client.get(self.SEARCH_URL, params={"q": query})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NutritionSearchError("Nutrition web search is unavailable.") from exc

        parser = _DuckDuckGoLiteParser()
        parser.feed(response.text)
        results = [
            result for result in parser.results
            if result.get("title") and result.get("snippet") and result.get("url", "").startswith("http")
        ]
        return results[: max(1, min(limit, 5))]
