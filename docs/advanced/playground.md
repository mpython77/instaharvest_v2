# Web Playground

InstaHarvest v2 provides a FastAPI browser interface (`instaharvest_v2.agent.web`) for AI Agent chat, parallel multi-agent tasks, and direct Instagram API lookups.

## Quick Start

```bash
pip install "instaharvest-v2[web]"
python -m instaharvest_v2.agent.web
# Opens http://127.0.0.1:8899
```

### CLI Options

```bash
python -m instaharvest_v2.agent.web [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--port` | `8899` | Server port |
| `--host` | `127.0.0.1` | Server host |
| `--provider` | `gemini` | AI provider (`openai`, `gemini`, `claude`, etc.) |
| `--model` | `None` | AI model override |
| `--api-key` | env | AI API key |
| `--env` | `.env` | Path to `.env` file |
| `--permission` | `full_access` | Permission level (`ask_every`, `ask_once`, `full_access`) |

### Requirements

- `fastapi` — web framework
- `uvicorn` — ASGI server
- `.env` file with Instagram credentials (optional for public/anonymous mode)
- AI provider API key env var (e.g., `GEMINI_API_KEY` or `OPENAI_API_KEY`) for AI Chat

---

## API Endpoints

### AI Agent & System

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Web Chat HTML UI |
| `POST` | `/api/ask` | Ask `InstaAgent` a question (`{"message": "..."}`) |
| `POST` | `/api/parallel` | Run parallel tasks via `AgentCoordinator` (`{"tasks": [...]}`) |
| `GET` | `/api/history` | Get recent agent conversation history |
| `POST` | `/api/reset` | Reset agent conversation history |
| `GET` | `/api/info` | Provider info, history length, session/proxy counts |

### Direct Instagram Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/feed/user/{user_id}?count=12` | Fetch public user feed (`ig.public.get_feed`) |
| `GET` | `/api/feed/tagged/{user_id}?count=12` | Fetch tagged posts (`ig.graphql.get_tagged_posts`) |
| `GET` | `/api/media/likers/{media_pk}` | Fetch post likers (`ig.media.get_likers_parsed`) |
| `GET` | `/api/user/info/{username}` | Fetch user profile info (`ig.users.get_by_username`) |

---

## Programmatic Usage

```python
from instaharvest_v2.agent.web import create_app
import uvicorn

app = create_app(
    env_path=".env",
    provider="gemini",
    permission_level="ask_once",
)

# Add custom FastAPI routes on top of the app
@app.get("/api/custom/health")
async def custom_health():
    return {"status": "ok"}

uvicorn.run(app, host="127.0.0.1", port=8899)
```
