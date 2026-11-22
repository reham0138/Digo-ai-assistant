"""Delivery restaurant/meal retrieval adapter placeholder.

This adapter will be connected to the delivery project's trusted API/data
source after its data contract is reviewed.
"""


class RestaurantSearch:
    async def search(self, query: str) -> list[dict]:
        raise NotImplementedError("Delivery retrieval integration is not implemented yet.")
