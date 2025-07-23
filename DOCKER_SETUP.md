# Docker Setup for Discord MCP HTTP API

This document explains how to run the Discord HTTP API in a Docker container.

## Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Discord credentials
# At minimum, set:
# - DISCORD_TOKEN=your-discord-bot-token
# - DEFAULT_SERVER_ID=your-discord-server-id
```

### 2. Build and Run with Docker Compose
```bash
# Build and start the Discord HTTP API
docker-compose up -d discord-http-api

# Check status
docker-compose ps

# View logs
docker-compose logs -f discord-http-api
```

### 3. Test the Container
```bash
# Health check
curl http://localhost:9090/health

# List channels  
curl http://localhost:9090/channels

# Send test message
curl -X POST http://localhost:9090/test
```

## Docker Compose Services

### Discord HTTP API
- **Port**: 9090
- **Container**: `discord-http-api`
- **Health Check**: Built-in HTTP health endpoint
- **Restart Policy**: `unless-stopped`

### PostgreSQL (Optional)
- **Port**: 5434 (to avoid conflicts with existing containers)
- **Container**: `superagent-postgres-docker`
- **Credentials**: `superagent/superagent`
- **Database**: `superagent`

## Manual Docker Commands

### Build Image
```bash
docker build -t discord-http-api .
```

### Run Container
```bash
docker run -d \
  --name discord-http-api \
  -p 9090:9090 \
  -e DISCORD_TOKEN="your-token" \
  -e DEFAULT_SERVER_ID="your-server-id" \
  discord-http-api
```

## Network Configuration

The containers use a bridge network `superagent-network` for internal communication.

### Container-to-Container Access
- Discord API: `http://discord-http-api:9090`
- PostgreSQL: `postgresql://superagent:superagent@postgres:5432/superagent`

### Host Access
- Discord API: `http://localhost:9090`
- PostgreSQL: `postgresql://superagent:superagent@localhost:5434/superagent`

## Development Workflow

### Development with Live Reload
```bash
# Mount source code for development
docker run -d \
  --name discord-http-api-dev \
  -p 9090:9090 \
  -v $(pwd):/app \
  -e DISCORD_TOKEN="your-token" \
  -e DEFAULT_SERVER_ID="your-server-id" \
  python:3.11-slim \
  bash -c "cd /app && pip install -r requirements.txt && pip install fastapi uvicorn[standard] && python discord_http_api.py"
```

### Debug Container
```bash
# Run with shell access
docker-compose run --rm discord-http-api bash

# Or connect to running container
docker-compose exec discord-http-api bash
```

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs discord-http-api
```

### Test Discord Connection
```bash
# Check Discord bot token validity
curl -H "Authorization: Bot YOUR_TOKEN" https://discord.com/api/v10/users/@me

# Test from inside container
docker-compose exec discord-http-api curl http://localhost:9090/health
```

### Container Resource Usage
```bash
docker stats discord-http-api
```

## Integration with Claude Code Containers

When spawning Claude Code containers, they can access the Discord API via:

```python
# Environment variable in Claude Code container
DISCORD_HTTP_URL=http://discord-http-api:9090

# Usage in container
import aiohttp

async def send_discord_message(channel_id: str, content: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://discord-http-api:9090/messages",
            json={"channel_id": channel_id, "content": content}
        ) as resp:
            return await resp.json()
```

## Production Considerations

### Security
- Use Docker secrets for sensitive environment variables
- Consider network policies for container-to-container communication
- Implement proper logging and monitoring

### Scaling
- The Discord HTTP API can be scaled horizontally
- Use a load balancer for multiple instances
- Consider Redis for shared session state if needed

### Monitoring
```bash
# Health monitoring
docker-compose exec discord-http-api curl http://localhost:9090/health

# Resource monitoring
docker stats $(docker-compose ps -q)
```