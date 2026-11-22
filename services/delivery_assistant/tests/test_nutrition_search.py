from services.delivery_assistant.app.agents.delivery_agent import (
    is_delivery_related,
    is_live_delivery_data_query,
    is_nutrition_query,
)
from services.delivery_assistant.app.integrations.nutrition_search import (
    _DuckDuckGoLiteParser,
)


def test_nutrition_queries_are_in_delivery_scope():
    assert is_nutrition_query("How many calories are in shawarma?")
    assert is_nutrition_query("كم سعرة حرارية في الفلافل؟")
    assert is_delivery_related("calories in a cheeseburger")


def test_live_restaurant_queries_are_not_sent_to_the_llm():
    assert is_live_delivery_data_query("what restaurants are available?")
    assert is_live_delivery_data_query("what the restaurants available in the website")
    assert is_live_delivery_data_query("شو المطاعم الموجودة؟")


def test_unrelated_queries_remain_out_of_scope():
    assert not is_delivery_related("Explain how neural networks work")


def test_search_parser_extracts_title_snippet_and_source():
    html = """
    <tr><td><a class="result-link" href="https://example.com/nutrition">
    Chicken nutrition facts</a></td></tr>
    <tr><td class="result-snippet">About 250 calories per serving.</td></tr>
    """
    parser = _DuckDuckGoLiteParser()
    parser.feed(html)

    assert parser.results == [{
        "url": "https://example.com/nutrition",
        "title": "Chicken nutrition facts",
        "snippet": "About 250 calories per serving.",
    }]
