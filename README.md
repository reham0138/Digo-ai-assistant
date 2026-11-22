# Digo AI Assistant

A local-first starter with one reusable AI core and independently runnable Store and Delivery assistant services. The goal is to reuse the core in future projects by supplying a different system prompt and project-specific tools.

## Architecture

- `shared/ai_core`: reusable Ollama client, conversation models, prompt loader, tool registry, response validation, and `AssistantRuntime`.
- `services/store_assistant`: FastAPI service with store-specific instructions and API contracts.
- `services/delivery_assistant`: FastAPI service with delivery-specific instructions and API contracts.
- Both services can use the same local Ollama server. Their prompts, routes, and business integrations remain separate.

## Current scope

Both services expose:
- `GET /health` for a health check.
- `POST /chat` for a prompt-configured Ollama response.

The chat runtime accepts a bounded history supplied by the caller (up to 12 messages). It does not persist conversations between requests. The Store semantic-search and Delivery restaurant-search integrations are still placeholders; recommendations and operational facts are not retrieved from real project data yet.

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

A follow-up request can send the previous user/assistant messages in `history`. Keep the history relevant and do not send more than 12 messages.

## Important design rules

1. The frontend calls the relevant assistant service; it does not call Ollama or business data sources directly.
2. Store and Delivery must not share business tools or data access implicitly.
3. LLM output is not a source of truth for product prices, stock, restaurant availability, delivery fees, or order status.
4. Only trusted service integrations can supply factual catalogue, restaurant, and order data.
5. Never commit `.env`, credentials, or private user data.

## Next milestones

1. Connect Store chat to the existing semantic-search engine and validate results against trusted product data.
2. Add Store-specific tools for product and branch questions.
3. Implement Delivery restaurant/menu retrieval and its project-specific tools.
4. Add tests with mocked Ollama and mocked business integrations.
5. Integrate a frontend only after the service contracts are stable.
