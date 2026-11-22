from services.store_assistant.app.agents.store_agent import (
    is_live_store_data_query,
    is_store_related,
)


def test_live_product_data_queries_are_detected():
    assert is_live_store_data_query("What products are available?")
    assert is_live_store_data_query("كم سعر المنتج؟")
    assert is_live_store_data_query("Is this item in stock?")


def test_general_product_advice_stays_in_scope():
    assert is_store_related("Help me choose a laptop for university")
    assert not is_live_store_data_query("Help me choose a laptop for university")
