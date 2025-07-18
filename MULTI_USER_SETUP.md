# Multi-User Discord Bot Setup Guide

This guide helps multiple users run their own Discord bots using the same mcp-discord installation.

## Quick Setup for New Users

### Step 1: Create Your Own Discord Bot

1. **Go to**: https://discord.com/developers/applications
2. **Create New Application**:
   - Click "New Application"
   - Name: "My Discord Bot" (or your preferred name)
   - Click "Create"

3. **Set up Bot**:
   - Go to "Bot" section
   - Click "Add Bot"
   - Reset Token and **copy your bot token**
   - Enable "SERVER MEMBERS INTENT" and "MESSAGE CONTENT INTENT"

4. **Configure Permissions**:
   - Go to "OAuth2" → "URL Generator"
   - Scopes: Select "bot"
   - Bot Permissions: Select needed permissions
   - Copy the generated invite URL

5. **Invite Bot to Server**:
   - Open the invite URL
   - Add bot to your Discord server

6. **Get Server ID**:
   - Enable Developer Mode in Discord
   - Right-click server name → "Copy Server ID"

### Step 2: Configure Your Environment

**IMPORTANT: Choose Your Setup Method**

**Method A: Separate Installation (Recommended)**
Each user clones their own copy of the repository:
```bash
# Clone your own copy
git clone https://github.com/glindberg2000/mcp-discord.git
cd mcp-discord

# Create your own .env file
echo "DISCORD_TOKEN=your_bot_token_here" > .env
echo "DEFAULT_SERVER_ID=your_server_id_here" >> .env
```

**Method B: Shared Installation with User-Specific .env**
If sharing the same installation directory, create a user-specific .env file:
```bash
# Create .env.yourusername file (e.g., .env.alice, .env.bob)
echo "DISCORD_TOKEN=your_bot_token_here" > .env.$(whoami)
echo "DEFAULT_SERVER_ID=your_server_id_here" >> .env.$(whoami)
```

**Option A: Environment Variables (Legacy)**
```bash
# Create your own .env file
echo "DISCORD_TOKEN=your_bot_token_here" > .env
echo "DEFAULT_SERVER_ID=your_server_id_here" >> .env
```

**Option B: Cursor MCP Configuration**
Update your `/Users/yourusername/.cursor/mcp.json`:

**IMPORTANT:** Do NOT include environment variables in the MCP config if you want to use .env files. The MCP config environment variables will override .env files.

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
      ]
    }
  }
}
```

**Alternative with environment variables (overrides .env):**
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

### Step 3: Test Your Setup

```bash
# Test your bot connection
export DISCORD_TOKEN="your_bot_token"
export DEFAULT_SERVER_ID="your_server_id"
export PATH="$HOME/.local/bin:$PATH"
uv run mcp-discord --help
```

## What Each User Gets:

✅ **Unique Bot Identity** - Each bot has its own name and avatar
✅ **Independent Permissions** - Each user controls their own bot's access
✅ **Separate Message History** - Each bot's messages are distinct
✅ **Individual Status** - Each bot can have different online/offline status

## Security Notes:

- 🔒 **Never share bot tokens** - Each user keeps their token private
- 🔒 **Use .env files** - Keeps credentials out of version control
- 🔒 **Individual permissions** - Each bot only has access you grant it

## Troubleshooting:

- **"Bot not appearing online"**: Check bot permissions and server invite
- **"Invalid token"**: Verify token from Discord Developer Portal
- **"Permission denied"**: Ensure bot has proper server permissions

## Example Workflow:

1. User A creates "BotA" → gets token "ABC123"
2. User B creates "BotB" → gets token "XYZ789"
3. Both use same mcp-discord code
4. Each configures their own .env file
5. Both bots can run simultaneously on same server
6. Each bot has its own identity and permissions 