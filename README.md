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

## Quick Setup Guide

### Prerequisites
- Python 3.10 or higher
- UV package manager (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Discord Developer account
- Claude Desktop (for MCP integration)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/glindberg2000/mcp-discord.git
cd mcp-discord

# Switch to the fix-fstring branch (contains important fixes)
git checkout fix-fstring-syntax

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies (Python 3.13+ specific)
uv pip install audioop-lts  # Only if using Python 3.13+

# Install the package
uv pip install -e .
```

### Step 2: Create Discord Bot

1. **Go to Discord Developer Portal**: https://discord.com/developers/applications
2. **Create New Application**:
   - Click "New Application"
   - Name: "MCP Discord Bot" (or your preferred name)
   - Click "Create"

3. **Set up Bot**:
   - Go to "Bot" section in left sidebar
   - Click "Add Bot" if not already added
   - Under "Token", click "Reset Token" and **copy the bot token**
   - Enable "SERVER MEMBERS INTENT" and "MESSAGE CONTENT INTENT"

4. **Configure Permissions**:
   - Go to "OAuth2" → "URL Generator"
   - Scopes: Select "bot"
   - Bot Permissions: Select these permissions:
     - ✅ Send Messages
     - ✅ Read Message History
     - ✅ Manage Messages
     - ✅ Manage Channels
     - ✅ Manage Roles
     - ✅ Kick Members
     - ✅ Ban Members
     - ✅ Add Reactions
     - ✅ Use Slash Commands

5. **Invite Bot to Server**:
   - Copy the generated OAuth URL
   - Open URL in browser to invite bot to your Discord server

6. **Get Server ID**:
   - Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
   - Right-click your server name → "Copy Server ID"

### Step 3: Configure Environment

Create a `.env` file in the mcp-discord directory:

```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here
DEFAULT_SERVER_ID=your_server_id_here
```

**Example:**
```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here
DEFAULT_SERVER_ID=your_server_id_here
```

**Important:** The `.env` file is automatically added to `.gitignore` to prevent accidentally committing sensitive credentials.

### Step 4: Test Bot Connection

Test that your bot can connect successfully:

```bash
# Test with environment variables
export DISCORD_TOKEN="your_bot_token"
export DEFAULT_SERVER_ID="your_server_id"
python test_bot.py your_bot_token
```

**Quick test:**
```bash
# Test the MCP server directly
export DISCORD_TOKEN="your_bot_token"
export DEFAULT_SERVER_ID="your_server_id"
export PATH="$HOME/.local/bin:$PATH"
uv run mcp-discord --help
```

If successful, you should see the MCP server help output without any token errors.

### Step 5: Configure Claude Desktop

Configure Claude Desktop to use the MCP Discord server:

**Configuration file locations:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Configuration format:**
```json
{
  "mcpServers": {
    "discord": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "your_bot_token",
        "DEFAULT_SERVER_ID": "your_server_id"
      }
    }
  }
}
```

**Example for macOS:**
```json
{
  "mcpServers": {
    "discord": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "your_bot_token",
        "DEFAULT_SERVER_ID": "your_server_id"
      }
    }
  }
}
```

### Step 6: Verify Setup

1. **Restart Claude Desktop** after updating the configuration
2. **Check bot status**: Bot should appear online in your Discord server
3. **Test basic functionality**: Try sending a message through Claude Desktop

### Troubleshooting

**Common Issues:**
- **"DISCORD_TOKEN environment variable is required"**: Make sure your .env file is in the correct location and contains the token
- **"Invalid bot token"**: Double-check the token from Discord Developer Portal
- **"Bot not appearing online"**: Ensure bot has proper permissions and is invited to the server
- **"UV command not found"**: Add UV to your PATH: `export PATH="$HOME/.local/bin:$PATH"`

**Getting Help:**
- Check the bot's permissions in your Discord server
- Verify the bot token is correct and not expired
- Ensure all required intents are enabled in Discord Developer Portal

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
