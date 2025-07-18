# Discord MCP Server - Global Installation

This is a global installation of the Discord MCP server for use across multiple Cursor projects.

## Setup Instructions

### For Each Project/User

1. **Create project-specific MCP config** in your project's `.cursor/mcp.json`:
   ```json
   {
     "mcpServers": {
       "discord-bot1": {
         "command": "python",
         "args": ["~/mcp-discord-global/src/discord_mcp/server.py"],
         "env": {
           "DISCORD_TOKEN": "your-bot-token-here",
           "DEFAULT_SERVER_ID": "your-server-id-here"
         }
       }
     }
   }
   ```

2. **Create AI guidance** in your project's `.cursorrules.md`:
   ```markdown
   # Project Rules
   
   - For all Discord interactions, exclusively use the @discord-bot1 tool
   - Always prefix Discord prompts with the bot name
   - This project uses bot1 for all Discord communications
   ```

3. **Restart Cursor** to apply the new MCP configuration

## Benefits

- **Shared Codebase**: All projects use the same MCP server code
- **Independent Bots**: Each project gets its own Discord bot identity
- **Easy Management**: Bot tokens managed in project configs, not scattered files
- **AI Memory**: `.cursorrules.md` ensures consistent bot usage

## Requirements

- Python 3.8+
- discord.py library
- Valid Discord bot token
- Discord server ID
