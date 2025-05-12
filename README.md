# Discord MCP Server

A Model Context Protocol (MCP) server that provides Discord integration capabilities to AI agents like Goose, Claude Desktop, and other MCP clients.

## Features

The Discord MCP Server provides a comprehensive set of tools for interacting with Discord servers:

### Server Information
- `get_server_info`: Get detailed server information including channels, categories, and settings
- `list_members`: List server members with their roles and other details

### Message Management
- `send_message`: Send messages to any channel
- `read_messages`: Read message history with reaction information
- `add_reaction`: Add reactions to messages
- `add_multiple_reactions`: Add multiple reactions at once
- `remove_reaction`: Remove specific reactions
- `moderate_message`: Delete messages and optionally timeout users

### Channel Management
- `create_text_channel`: Create new text channels
- `delete_channel`: Delete existing channels
- `create_thread`: Create threads from messages or as standalone
- `set_channel_permissions`: Configure channel permissions for roles
- `create_category`: Create new channel categories

### Role Management
- `create_role`: Create new server roles with customizable settings
- `delete_role`: Remove existing roles
- `list_roles`: Get a list of all server roles
- `add_role`: Assign roles to users
- `remove_role`: Remove roles from users

### User Management
- `get_user_info`: Get detailed information about users
- `kick_user`: Kick users from the server
- `ban_user`: Ban users with optional message deletion

## Installation

1. Clone and set up the environment:
```
# Clone the repository
git clone https://github.com/netixc/mcp-discord.git
cd mcp-discord

# Create and activate virtual environment
uv venv
source .venv/bin/activate

### If using Python 3.13+ 
uv pip install audioop-lts

# Install the package
uv pip install -e .
```

2. Configure Claude Desktop 
    (%APPDATA%\Claude\claude_desktop_config.json on Windows, 
    ~/Library/Application Support/Claude/claude_desktop_config.json on macOS).

```
    "discord": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\PATH\\TO\\mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "your_bot_token"
        "DEFAULT_SERVER_ID": "your_default_server_id"  # Optional
      }
    }
```

## Agent Backlog Processing Pattern (Humanlike Robustness)

### Rationale
In real-world chat, instructions may be superseded, clarified, or cancelled by later messages. A human would always read the full backlog before acting, not just process messages one-by-one. To make agents robust and context-aware, our workflow mimics this behavior.

### Workflow
1. **Fetch all unread messages as a batch** using `get_unread_messages` with the last seen message ID.
2. **Pass the entire batch to the agent's decision logic** (AI or rules). The agent can:
   - Read the backlog in order (oldest to newest)
   - Notice if later messages change, clarify, or cancel earlier ones
   - Decide what to do based on the *latest* and *aggregate* context
3. **Update the last seen message ID** to the newest message in the batch (for replay/duplicate protection).
4. **Switch to real-time listening** using `wait_for_message` for new incoming messages. On receiving a new message, repeat the backlog fetch (in case of multiple new messages).

### Why This Pattern?
- Prevents agents from acting on outdated or cancelled instructions
- Handles reversals, clarifications, and corrections naturally
- Mimics how a human would catch up on a conversation
- Ensures no messages are missed, even after downtime

### Implementation Steps
- On startup/login, call `get_unread_messages` with the last seen message ID
- Pass the full list to agent logic for context-aware decision making
- Update and persist the last seen message ID after processing
- After backlog, use `wait_for_message` for real-time operation
- On new message, repeat backlog fetch and processing

This pattern is now the recommended approach for all Discord agent workflows in this repo.

## License

MIT License - see LICENSE file for details.
