#!/bin/bash
# Setup script for Discord MCP HTTP server

echo "🚀 Setting up Discord MCP HTTP Server..."

# Check if mcp-discord exists
if [ ! -d "mcp-discord" ]; then
    echo "📦 Cloning mcp-discord repository..."
    git clone https://github.com/glindberg2000/mcp-discord.git
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements_http.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << EOL
# Discord Configuration
DISCORD_TOKEN=your-discord-bot-token-here
DEFAULT_SERVER_ID=your-discord-server-id-here

# PostgreSQL Configuration (for memory)
POSTGRES_URL=postgresql://postgres:superagent@localhost:5433/superagent

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic Configuration (for Claude Code containers)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
EOL
    echo "⚠️  Please edit .env file with your actual tokens and IDs"
fi

echo "✅ Setup complete!"
echo ""
echo "To start the HTTP server:"
echo "  python discord_mcp_http_native.py"
echo ""
echo "To test the server:"
echo "  python test_discord_http.py [channel_id]"
echo ""
echo "To start with custom port:"
echo "  python discord_mcp_http_native.py --port 8080"

# Make scripts executable
chmod +x discord_mcp_http_native.py
chmod +x test_discord_http.py
chmod +x discord_mcp_http_wrapper.py