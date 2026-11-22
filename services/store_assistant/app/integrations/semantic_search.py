"""Store semantic-search adapter placeholder.

Implement only after confirming the semantic-search engine request/response
contract and preparing a stable product DTO. Do not send browser-supplied
prices or stock as authoritative catalogue data.
"""


class StoreSemanticSearch:
    async def search(self, query: str, products: list[dict]) -> list[dict]:
        raise NotImplementedError("Semantic-search contract integration is the next task.")
