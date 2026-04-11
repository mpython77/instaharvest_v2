# Tools & Plugins

## Built-in Tools (161)

The agent automatically selects the right tool for each task from its extensive library of 161 built-in tools, organized into 10 specialized categories:

### 1. Instagram Core Tools
Get profiles, parse posts, extract reels, stories, and comments.

### 2. Media & Social Tools
Follow, like, comment, and send Direct Messages (DMs) seamlessly.

### 3. Analytics & Growth Tools
Compare multiple accounts, calculate engagement rates, and find peak posting times.

### 4. Automation & Monitoring Tools
Schedule future posts, auto-greet new followers, and monitor target accounts.

### 5. Bulk & Pipeline Tools
Export data directly to SQLite databases, JSONL pipelines, and bulk download user media.

### 6. Network & Web Tools
Run DuckDuckGo internet searches and send authenticated HTTP API requests.

### 7. Auth & Context Tools
Securely authenticate, validate sessions, perform checkups, and cycle proxies.

### 8. File I/O Tools
Sandboxed tools to read CSV/JSON, save output logs, and manage local directory file structures.

### 9. Utility & Transformation Tools
Parse complex JSON objects, transform CSV to JSON, perform numeric calculations, and merge files.

### 10. `run_InstaHarvest v2_code`
Execute custom Python code in a secure sandbox with direct access to the `ig` client when standard tools aren't enough.

---

## Custom Plugins

Register your own functions as agent tools using `PluginManager`:

```python
from instaharvest_v2.agent import InstaAgent

agent = InstaAgent(ig=ig, provider="gemini", api_key="...")

# Register a custom tool
def translate(args):
    text = args.get("text", "")
    target = args.get("target_language", "en")
    # Your translation logic here
    return f"Translated: {text}"

agent.register_tool(
    name="translate",
    handler=translate,
    description="Translate text between languages",
    schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate"},
            "target_language": {"type": "string", "description": "Target language code"},
        },
    },
)

# Now the agent can use your tool!
result = agent.ask("Translate 'Hello World' to Spanish")
```

### Auto-Schema

If you don't provide a schema, `PluginManager` auto-generates one from your function signature:

```python
def sentiment(text: str, detailed: bool = False):
    """Analyze text sentiment."""
    return {"score": 0.8, "label": "positive"}

# Schema auto-generated from type hints
agent.register_tool("sentiment", sentiment, "Analyze sentiment")
```

### Plugin Management

```python
# List registered plugins
plugins = agent.plugins.list_plugins()

# Check if plugin exists
agent.plugins.has("translate")  # True

# Remove a plugin
agent.plugins.unregister("translate")

# Plugin count
agent.plugins.count  # 0
```
