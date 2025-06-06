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

### Agent Status Management
- `set_agent_status`: Set the agent's status (available, working, offline, etc.) and update Discord presence for visibility

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

## Agent Usage Notes (Cursor/AI Agents)

- The MCP Discord server provides stateless tools for message and backlog handling.
- **Agents (like Cursor or your own bots) are responsible for:**
  - Tracking the last seen message ID (per channel or context).
  - Calling `get_unread_messages` with the last seen message ID to fetch all unread messages (up to 100 at a time).
  - Paginating if there are more than 100 unread messages (call again with the new last seen ID).
  - After processing the backlog, use `wait_for_message` for real-time events.
- The MCP server does **not** maintain agent state or run loops for you; it only responds to explicit tool calls.
- This pattern is robust, humanlike, and works for all agent types.

**Example agent workflow:**
1. On startup, load last seen message ID (if any).
2. Call `get_unread_messages` with that ID to fetch backlog.
3. Process all messages, update last seen ID.
4. Call `wait_for_message` to wait for new messages.
5. On new message, repeat from step 2.

This approach ensures no missed or double-processed messages and is compatible with Cursor and other AI agent frameworks.

## Agent Status Management

The `set_agent_status` tool allows agents to set their current status and update the bot's Discord presence accordingly. This is useful for both internal agent state tracking and for making the agent's state visible to Discord users.

**Parameters:**
- `status` (string): The agent's status (e.g., `available`, `waiting`, `working`, `offline`, or custom)
- `details` (string, optional): Custom status message or activity (shown in Discord)

**Example usage:**
```json
{
  "status": "waiting"
}
```

**Status mapping:**
- `available` or `waiting`: Online, activity "Ready for tasks"
- `working`: Online, activity "Working"
- `offline`: Invisible, activity "Offline"
- Custom: Online, activity set to custom value (details or status)

The bot's presence is always clear and human-friendly, making it easy for users to see if the agent is ready, working, or offline.

Agents should call this tool when entering waiting mode (set to `available` or `waiting`), when working (set to `working`), or when going offline (set to `offline`).

## License

MIT License - see LICENSE file for details.
