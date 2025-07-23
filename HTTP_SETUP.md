# Discord MCP HTTP Transport Setup

This document explains how to use the Discord MCP server with HTTP transport for containerized environments.

## Current Status

The Discord MCP server currently uses STDIO transport, which works great for local MCP clients but isn't suitable for Docker containers or network communication.

## HTTP Transport Options

### Option 1: Use SuperAgent's Discord HTTP API (Recommended)

SuperAgent provides a standalone HTTP API that wraps Discord operations in REST endpoints:

```bash
# In SuperAgent repository
python discord_http_api.py

# Server starts on http://localhost:9090
```

**Available Endpoints:**
- `GET /health` - Check server health and Discord connection
- `GET /channels` - List all accessible Discord channels
- `POST /messages` - Send message to channel
- `GET /messages/{channel_id}` - Get recent messages
- `POST /test` - Send test message

**Usage from containers:**
```python
import aiohttp

async with aiohttp.ClientSession() as session:
    # Send message
    async with session.post(
        "http://host.docker.internal:9090/messages",
        json={"channel_id": "123456789", "content": "Hello!"}
    ) as resp:
        result = await resp.json()
```

### Option 2: Native MCP HTTP Support (Future)

The MCP protocol supports HTTP transport, but the current Discord MCP server would need modifications:

```python
# Future implementation
from mcp.server.fastapi import create_fastapi_app
import uvicorn

# Create FastAPI app from MCP server
app = create_fastapi_app(discord_mcp_server)

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Integration with SuperAgent Containers

### Environment Variables for Containers
```bash
DISCORD_HTTP_URL=http://host.docker.internal:9090
DISCORD_TOKEN=your-discord-bot-token
```

### Example Container Usage
```python
import os
import aiohttp

class DiscordHTTPClient:
    def __init__(self):
        self.base_url = os.getenv("DISCORD_HTTP_URL", "http://localhost:9090")
    
    async def send_message(self, channel_id: str, content: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                json={"channel_id": channel_id, "content": content}
            ) as resp:
                return await resp.json()
```

## Benefits of HTTP Transport

1. **Container-friendly**: Works across Docker networks
2. **Network accessible**: Can be called from any networked client
3. **Load balancable**: Can put load balancer in front
4. **Health checks**: Built-in HTTP health endpoints
5. **Debugging**: Easy to test with curl/Postman

## Migration Path

1. **Phase 1** (Current): Use SuperAgent's HTTP API alongside existing STDIO MCP
2. **Phase 2**: Add native HTTP transport to Discord MCP server
3. **Phase 3**: Container orchestration with multiple Discord MCP instances

## Testing

Test the HTTP API:
```bash
# Health check
curl http://localhost:9090/health

# List channels
curl http://localhost:9090/channels

# Send test message
curl -X POST http://localhost:9090/test
```

The HTTP transport maintains full compatibility with the existing STDIO MCP server - they can run simultaneously without conflicts.