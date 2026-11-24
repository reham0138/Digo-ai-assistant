# Digo AI Assistant

A local-first starter with one reusable AI core and independently runnable Store and Delivery assistant services. Each service has a narrow role, its own policy, and only its own integrations.

## Architecture

- `shared/ai_core`: reusable Ollama client, conversation models, prompt loader, tool registry, response validation, and `AssistantRuntime`.
- `services/store_assistant`: shopping and product-advice assistant.
- `services/delivery_assistant`: food ordering and delivery assistant, with a focused web-search tool for food nutrition questions.

Both services can use the same local Ollama server. Their prompts, routes, and business integrations remain separate.

## Intent understanding and tool execution

The runtime does not use fixed keyword lists to route user requests. When a service has registered tools, the model receives the user's message, the service policy, and the descriptions/schemas of only those tools. Ollama returns a JSON action plan constrained by a JSON schema:

- `respond`: return the model's direct answer.
- `use_tool`: validate the selected tool name and arguments, then execute only that registered handler.

This is application-level tool selection using structured output; it does not depend on native model tool-calling support. Tool results are returned by their handler, so integrations must format and attribute retrieved facts themselves. The runtime does not let the model generate SQL or execute arbitrary code.

When no tools are registered, the runtime keeps the ordinary text-generation path.

## Current capabilities and limits

Both services expose:
- `GET /health` for a health check.
- `POST /chat` for assistant responses.

The chat runtime accepts a bounded history supplied by the caller (up to 12 messages). It does not persist conversations between requests.

### Store Assistant

- Handles shopping guidance, product selection, and general product questions.
- Does not have a live product catalogue or inventory connection yet.
- Must not invent current prices, discounts, stock, or branch availability.
- No store data tools are registered until a trusted store backend and its schema are available.

### Delivery Assistant

- Handles food, meals, menus, delivery, pickup, and food-ordering guidance.
- The model selects the registered `nutrition_search` tool for nutrition questions based on intent, not a fixed list of phrases.
- Nutrition search results are shown with source links and are explicitly estimates; values depend on portion size and preparation.
- If nutrition search is unavailable or returns no usable results, the API reports that instead of generating nutrition numbers.
- Live restaurant, menu, order, delivery-fee, and availability data are not connected yet. The assistant must not invent these facts.

The nutrition search uses DuckDuckGo's lightweight public HTML search endpoint. It requires outbound internet access from the API server. Search snippets are indicative and should be checked against the linked source; this is not a clinical nutrition database.

## Requirements

- Python 3.11+
- Ollama installed and running locally
- A model pulled in Ollama (default: `gemma3:1b`)

## Setup (PowerShell)

Use the Python version installed on your machine:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Start Ollama in a separate terminal if it is not already running:

```powershell
ollama pull gemma3:1b
ollama serve
```

## Run the services

Store Assistant:

```powershell
uvicorn services.store_assistant.app.main:app --reload --port 8001
```

Delivery Assistant (in a second terminal):

```powershell
uvicorn services.delivery_assistant.app.main:app --reload --port 8002
```

API documentation:
- Store: http://127.0.0.1:8001/docs
- Delivery: http://127.0.0.1:8002/docs

## Chat request examples

Store:

```json
{
  "message": "Help me choose a laptop",
  "branch_id": "branch-1",
  "history": []
}
```

Delivery:

```json
{
  "message": "I want to find something for dinner",
  "history": []
}
```

Nutrition lookup:

```json
{
  "message": "How many calories are in a serving of chicken shawarma?",
  "history": []
}
```

A follow-up request can send the previous user/assistant messages in `history`. Keep the history relevant and do not send more than 12 messages.

## Design rules

1. The frontend calls the relevant assistant service; it does not call Ollama or business data sources directly.
2. Store and Delivery must not share business tools or data access implicitly.
3. LLM output is not a source of truth for product prices, stock, restaurant availability, delivery fees, or order status.
4. External factual lookups must use a dedicated integration and show where the information came from.
5. Never commit `.env`, credentials, or private user data.

## Tests

Run the automated tests from the repository root:

```powershell
python -m pytest -v
```
