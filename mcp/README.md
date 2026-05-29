# canon-mcp-server

MCP server that connects AI coding assistants to your team's organizational memory in canon — active migrations, deprecated patterns, architecture decisions, prior failures, and the context behind why things are the way they are.

```json
{
  "mcpServers": {
    "canon": {
      "command": "uvx",
      "args": ["canon-mcp-server"],
      "env": {
        "CANON_API_TOKEN": "ct_...",
        "CANON_BACKEND_URL": "https://your-canon-backend.com"
      }
    }
  }
}
```
