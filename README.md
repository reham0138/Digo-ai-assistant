# Shared AI Assistant

A local-first AI platform with one reusable AI Core and independently runnable Store and Delivery assistant services.

## Architecture

- `shared/ai_core`: reusable Ollama client, conversation abstractions, prompt loading, tool registry, and response validation.
- `services/store_assistant`: independent FastAPI service for shopping/product assistance.
- `services/delivery_assistant`: independent FastAPI service for restaurant/meal/order assistance.
- Each service has its own configuration, routes, agent instructions, and integrations.
- Both services may use the same local Ollama server while keeping business logic and conversation state isolated.

## Initial scope

This scaffold intentionally starts with health endpoints and a minimal chat orchestration boundary. Product/restaurant retrieval integrations will be implemented and tested separately before connecting real project data.

## Requirements

- Python 3.11+
- Ollama installed locally
- A model pulled in Ollama (for example `gemma3:1b`)

## Setup (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Start Ollama separately, then pull a model if needed:

```powershell
ollama pull gemma3:1b
ollama serve
```

Run Store Assistant:

```powershell
$env:ASSISTANT_SERVICE="store"
uvicorn services.store_assistant.app.main:app --reload --port 8001
```

Run Delivery Assistant in a second terminal:

```powershell
$env:ASSISTANT_SERVICE="delivery"
uvicorn services.delivery_assistant.app.main:app --reload --port 8002
```

Health checks:
- http://127.0.0.1:8001/health
- http://127.0.0.1:8002/health

API docs:
- http://127.0.0.1:8001/docs
- http://127.0.0.1:8002/docs

## Important design rules

1. The frontend calls the relevant assistant service; it does not call Ollama or the semantic-search engine directly.
2. Store and Delivery services must not share business tools or data access implicitly.
3. LLM output is not a source of truth for product prices, stock, restaurant availability, or order status.
4. A service must validate any IDs and factual claims against its own trusted integration before returning them.
5. Do not put API keys, credentials, or private user data in prompts or commit `.env`.

## Next implementation milestones

1. Verify both services start and pass health checks.
2. Implement and test the Store semantic-search integration against mock product data.
3. Add the shared Ollama client and bounded prompt handling.
4. Implement Delivery retrieval independently.
5. Add frontend adapters only after service contracts are stable.
