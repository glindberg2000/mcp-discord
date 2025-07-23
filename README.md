# Discord MCP HTTP Bridge

A **stateless** Discord HTTP API that enables multi-bot interactions via Model Context Protocol (MCP) over HTTP transport. Perfect for containerized architectures where multiple Claude Code containers need Discord access with different bot identities.

## 🚀 Features

- **🔄 Completely Stateless**: Creates fresh Discord clients per request - no caching or persistent connections
- **🤖 Multi-Bot Support**: Handle multiple Discord bot tokens simultaneously with separate identities
- **📡 HTTP Transport**: RESTful API compatible with MCP HTTP protocol
- **🐳 Container Ready**: Dockerized deployment with health checks
- **🔐 Secure**: Tokens passed per request, never stored server-side
- **⚡ Efficient**: Proper cleanup after each operation

## 📋 Quick Start

### 1. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the stateless Discord API
python discord_http_stateless.py

# Server runs on http://localhost:9091
```

### 2. Docker Deployment

```bash
# Build and start
docker-compose up -d discord-http-api

# Check health
curl http://localhost:9091/health
```

### 3. Send Messages

```bash
# Send message from Bot 1
curl -X POST http://localhost:9091/messages \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "YOUR_CHANNEL_ID",
    "content": "Hello from Bot 1!",
    "discord_token": "YOUR_BOT_1_TOKEN"
  }'

# Send message from Bot 2  
curl -X POST http://localhost:9091/messages \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "YOUR_CHANNEL_ID", 
    "content": "Hello from Bot 2!",
    "discord_token": "YOUR_BOT_2_TOKEN"
  }'
```

## 🔗 API Endpoints

### Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "stateless": true,
  "timestamp": "2025-07-23T00:58:45.929694"
}
```

### Send Message
```
POST /messages
```
Body:
```json
{
  "channel_id": "1234567890",
  "content": "Hello Discord!",
  "discord_token": "your_bot_token_here"
}
```

### Send Test Message
```
POST /test
```
Body:
```json
{
  "discord_token": "your_bot_token_here"
}
```

### List Channels
```
POST /channels
```
Body:
```json
{
  "discord_token": "your_bot_token_here"
}
```

## 🧪 Testing Multi-Bot Setup

Use the provided test client to verify multiple Discord bot identities:

```bash
# Set up environment variables
export DISCORD_TOKEN="your_first_bot_token"
export DISCORD_TOKEN2="your_second_bot_token"

# Run multi-bot test
python test_mcp_http_client.py
```

Expected output shows messages from different Discord applications:
```
🔵 Testing MCP Client 1 (Bot Token: ...abcd1234)
✅ Initialized MCP Discord client (Bot Token: ...abcd1234)
✅ Test message: Test message sent! Message ID: 1397376915706216558

🟢 Testing MCP Client 2 (Bot Token: ...efgh5678)  
✅ Initialized MCP Discord client (Bot Token: ...efgh5678)
✅ Test message: Test message sent! Message ID: 1397376918445232259
```

## 🏗️ Architecture

### Stateless Design
```
┌─────────────────┐    HTTP     ┌──────────────────────┐
│   Client App    │ ──────────► │  Stateless Discord   │
│  (Claude Code)  │             │      HTTP API        │
└─────────────────┘             └──────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────────┐
                                │  Fresh Discord       │
                                │  Client Per Request  │
                                │  (Auto-cleanup)      │
                                └──────────────────────┘
```

### Request Flow
1. **Client sends HTTP request** with Discord token in body
2. **Server creates fresh Discord client** for that specific token
3. **Operation executes** (send message, list channels, etc.)
4. **Discord client closes** automatically after operation
5. **Response returned** to client with results

### Key Differences from Stateful Approach
| Stateful (❌ Old) | Stateless (✅ New) |
|---|---|
| Caches bot instances | Creates fresh clients per request |
| Token mixing issues | Perfect token isolation |
| Memory leaks possible | Automatic cleanup |
| Single bot identity | Multiple bot identities work correctly |

## 🔧 Configuration

### Environment Variables (Optional)
The server is completely stateless and doesn't require environment variables. Tokens are passed with each request.

```bash
# For testing only
DISCORD_TOKEN=your_primary_bot_token
DISCORD_TOKEN2=your_secondary_bot_token
DEFAULT_SERVER_ID=your_discord_server_id
```

### MCP Configuration
```json
{
  "mcpServers": {
    "discord-stateless": {
      "transport": {
        "type": "http",
        "url": "http://localhost:9091"
      },
      "description": "Stateless Discord MCP Server supporting multiple bot tokens"
    }
  }
}
```

## 🐳 Container Deployment

### Docker Compose (Recommended)
```yaml
services:
  discord-http-api:
    build: .
    container_name: discord-stateless-api
    ports:
      - "9091:9091"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/health"]
```

### Standalone Docker
```bash
# Build image
docker build -t discord-stateless-api .

# Run container
docker run -d \
  --name discord-stateless \
  -p 9091:9091 \
  discord-stateless-api
```

## 📝 Usage Examples

### Claude Code Integration
```python
import aiohttp

class ClaudeCodeDiscordClient:
    def __init__(self, api_url="http://discord-api:9091", bot_token="..."):
        self.api_url = api_url
        self.bot_token = bot_token
    
    async def send_status(self, message):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/messages", json={
                "channel_id": "1234567890",
                "content": message,
                "discord_token": self.bot_token
            }) as resp:
                return await resp.json()

# Usage in Claude Code container
client = ClaudeCodeDiscordClient(bot_token=os.getenv("CLAUDE_BOT_TOKEN"))
await client.send_status("🤖 Claude Code container started!")
```

### Multi-Agent System
```python
# Different agents use different Discord identities
agents = {
    "research_agent": "BOT_TOKEN_1",
    "coding_agent": "BOT_TOKEN_2", 
    "testing_agent": "BOT_TOKEN_3"
}

for agent_name, token in agents.items():
    await send_message(
        channel_id="1234567890",
        content=f"Agent {agent_name} is online!",
        discord_token=token
    )
```

## 🔍 Troubleshooting

### Bot Identity Issues
If you see the same Discord user for different tokens:
1. **Verify tokens are from different Discord applications** (not regenerated tokens)
2. **Check server logs** for "Created fresh Discord client" messages
3. **Use test endpoint** to verify bot identities

### Permission Errors
```json
{
  "success": false,
  "error": "Bot doesn't have permission to send messages in this channel"
}
```
**Solution**: Ensure bot has `Send Messages` permission in target channel.

### Connection Issues
```json
{
  "success": false, 
  "error": "Invalid Discord token"
}
```
**Solution**: Verify bot token is valid and bot is invited to the server.

## 📊 Performance

- **No memory leaks**: Fresh clients prevent connection accumulation
- **Efficient**: Quick client creation/cleanup cycle
- **Scalable**: Handles multiple concurrent requests
- **Resource-friendly**: No persistent Discord connections

## 🛠️ Development

### Running Tests
```bash
# Test multiple bot identities
python test_mcp_http_client.py

# Test single bot functionality  
curl -X POST http://localhost:9091/test \
  -H "Content-Type: application/json" \
  -d '{"discord_token": "YOUR_TOKEN"}'
```

### Adding New Endpoints
1. Add endpoint to `discord_http_stateless.py`
2. Use `execute_with_client()` wrapper for Discord operations
3. Ensure proper error handling and cleanup
4. Update API documentation

## 🚀 Next Steps

This stateless Discord API is designed for integration with:
- **Claude Code containers** with individual Discord bot identities
- **Multi-agent orchestrators** managing different Discord personalities  
- **Microservice architectures** requiring Discord functionality
- **MCP-based applications** needing HTTP transport

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**Built for the SuperAgent multi-agent system** 🤖  
**Perfect for containerized Claude Code deployments** 🐳  
**Enabling true multi-bot Discord interactions** 🚀