import os
import asyncio
import logging
import argparse
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps

import discord
from discord.ext import commands
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent, EmptyResult
from mcp.server.stdio import stdio_server
from .event_waiter import wait_for_message

# Load environment variables from .env file (fallback only)
# Environment variables should be provided via MCP server configuration
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")

# Discord bot setup - will be set in main() function
DISCORD_TOKEN = None
DEFAULT_SERVER_ID = None

# Initialize MCP server
app = Server("discord-server")

# --- Agent Status Tracking ---
# (Moved to bot instances)


# Bot factory function to create isolated instances
def create_bot_instance(token: str):
    """Create a new Discord bot instance with the given token."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Store bot-specific data
    bot.discord_client = None
    bot.agent_status = {"status": "offline", "details": None}

    @bot.event
    async def on_ready():
        bot.discord_client = bot
        logger.info(f"Logged in as {bot.user.name}")
        logger.info(f"Bot is ready and connected to Discord!")

    @bot.event
    async def on_disconnect():
        bot.discord_client = None
        logger.warning("Bot disconnected from Discord")

    @bot.event
    async def on_error(event, *args, **kwargs):
        logger.error(f"Discord bot error in event {event}: {args} {kwargs}")

    return bot


# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the current bot instance from the context
        bot = getattr(func, "_bot_instance", None)
        if not bot or not bot.discord_client:
            logger.error("Discord client not ready - bot may not be connected")
            raise RuntimeError("Discord client not ready")
        if not bot.discord_client.is_ready():
            logger.error("Discord client is not ready - connection may be in progress")
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)

    return wrapper


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Discord tools."""
    return [
        # Server Information Tools
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID. If not provided, the default server ID will be used.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_members",
            description="Get a list of members in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID. If not provided, the default server ID will be used.",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                },
                "required": [],
            },
        ),
        # Role Management Tools
        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "user_id": {"type": "string", "description": "User to add role to"},
                    "role_id": {"type": "string", "description": "Role ID to add"},
                },
                "required": ["user_id", "role_id"],
            },
        ),
        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from",
                    },
                    "role_id": {"type": "string", "description": "Role ID to remove"},
                },
                "required": ["user_id", "role_id"],
            },
        ),
        # Channel Management Tools
        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "name": {"type": "string", "description": "Channel name"},
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete",
                    },
                    "reason": {"type": "string", "description": "Reason for deletion"},
                },
                "required": ["channel_id"],
            },
        ),
        Tool(
            name="create_thread",
            description="Create a new thread in a text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of the text channel to create thread in",
                    },
                    "name": {"type": "string", "description": "Name of the thread"},
                    "message_id": {
                        "type": "string",
                        "description": "Optional message ID to start the thread from. If not provided, creates a public thread.",
                    },
                    "auto_archive_duration": {
                        "type": "number",
                        "description": "Duration in minutes before the thread will archive. Must be one of: 60, 1440, 4320, 10080",
                        "enum": [60, 1440, 4320, 10080],
                    },
                },
                "required": ["channel_id", "name"],
            },
        ),
        Tool(
            name="set_channel_permissions",
            description="Set permissions for a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of the channel to set permissions for",
                    },
                    "role_id": {
                        "type": "string",
                        "description": "ID of the role to set permissions for. Use 'everyone' for the @everyone role.",
                    },
                    "allow_view": {
                        "type": "boolean",
                        "description": "Allow or deny viewing the channel",
                    },
                    "modify_everyone": {
                        "type": "boolean",
                        "description": "Also modify @everyone permissions",
                    },
                    "everyone_can_view": {
                        "type": "boolean",
                        "description": "If modify_everyone is true, controls whether @everyone can view the channel",
                    },
                },
                "required": ["channel_id", "role_id"],
            },
        ),
        Tool(
            name="create_category",
            description="Create a new category in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "name": {"type": "string", "description": "Category name"},
                    "position": {
                        "type": "number",
                        "description": "Optional position of the category",
                    },
                    "restricted_role_id": {
                        "type": "string",
                        "description": "Optional: If provided, only this role can view the category and its channels",
                    },
                    "everyone_can_view": {
                        "type": "boolean",
                        "description": "Optional: Controls whether @everyone can view this category. Default is true.",
                    },
                },
                "required": ["name"],
            },
        ),
        # Message Reaction Tools
        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to",
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)",
                    },
                },
                "required": ["channel_id", "message_id", "emoji"],
            },
        ),
        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to",
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)",
                        },
                        "description": "List of emojis to add as reactions",
                    },
                },
                "required": ["channel_id", "message_id", "emojis"],
            },
        ),
        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from",
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)",
                    },
                },
                "required": ["channel_id", "message_id", "emoji"],
            },
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID",
                    },
                    "content": {"type": "string", "description": "Message content"},
                },
                "required": ["channel_id", "content"],
            },
        ),
        Tool(
            name="read_messages",
            description="Read recent messages from a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["channel_id"],
            },
        ),
        Tool(
            name="get_user_info",
            description="Get information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Discord user ID"}
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation (optional)",
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320,  # Max 4 weeks
                    },
                },
                "required": ["channel_id", "message_id"],
            },
        ),
        Tool(
            name="create_role",
            description="Create a new role in the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "name": {"type": "string", "description": "Name of the role"},
                    "color": {
                        "type": "string",
                        "description": "Color of the role in hex format (e.g., '#FF0000' for red)",
                    },
                    "hoist": {
                        "type": "boolean",
                        "description": "Whether the role should be displayed separately in the member list",
                    },
                    "mentionable": {
                        "type": "boolean",
                        "description": "Whether the role can be mentioned by anyone",
                    },
                    "permissions": {
                        "type": "string",
                        "description": "Permissions as an integer (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="delete_role",
            description="Delete a role from the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "role_id": {
                        "type": "string",
                        "description": "ID of the role to delete",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deleting the role",
                    },
                },
                "required": ["role_id"],
            },
        ),
        Tool(
            name="list_roles",
            description="List all roles in the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="kick_user",
            description="Kick a user from the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "user_id": {"type": "string", "description": "ID of user to kick"},
                    "reason": {
                        "type": "string",
                        "description": "Reason for kicking the user (optional)",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="ban_user",
            description="Ban a user from the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID. If not provided, the default server ID will be used.",
                    },
                    "user_id": {"type": "string", "description": "ID of user to ban"},
                    "delete_message_days": {
                        "type": "number",
                        "description": "Number of days worth of messages to delete (0-7)",
                        "minimum": 0,
                        "maximum": 7,
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for banning the user (optional)",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="wait_for_message",
            description="Wait for a Discord message matching filters (channel, DM, mention, sender, content, timeout)",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID to filter (optional)",
                    },
                    "dm_only": {
                        "type": "boolean",
                        "description": "Only match DMs (optional)",
                    },
                    "mention_only": {
                        "type": "boolean",
                        "description": "Only match messages mentioning the bot (optional)",
                    },
                    "sender_id": {
                        "type": "string",
                        "description": "Only match messages from this user ID (optional)",
                    },
                    "content_regex": {
                        "type": "string",
                        "description": "Regex to match message content (optional)",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (optional)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_unread_messages",
            description="Get unread messages in a channel since a given message ID (optional). Returns messages newer than since_message_id, up to limit. Supports filtering by sender, mention, DM, and content regex.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID",
                    },
                    "since_message_id": {
                        "type": "string",
                        "description": "Only return messages after this message ID (optional)",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "sender_id": {
                        "type": "string",
                        "description": "Only return messages from this user ID (optional)",
                    },
                    "mention_only": {
                        "type": "boolean",
                        "description": "Only return messages mentioning the bot (optional)",
                    },
                    "dm_only": {
                        "type": "boolean",
                        "description": "Only return DMs (optional)",
                    },
                    "content_regex": {
                        "type": "string",
                        "description": "Regex to match message content (optional)",
                    },
                },
                "required": ["channel_id"],
            },
        ),
        # --- Agent Status Tool ---
        Tool(
            name="set_agent_status",
            description="Set the agent's status (available, working, offline, etc.) and update Discord presence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Agent status: available, working, offline, etc.",
                    },
                    "details": {
                        "type": "string",
                        "description": "Optional custom status message or activity.",
                    },
                },
                "required": ["status"],
            },
        ),
        Tool(
            name="check_connection",
            description="Check the Discord bot connection status and return diagnostic information.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        
        # File Operations
        Tool(
            name="send_file",
            description="Upload a file to a Discord channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID where the file should be sent",
                    },
                    "file_path": {
                        "type": "string", 
                        "description": "Local file path to upload",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional custom filename (defaults to original filename)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Optional message text to send with the file",
                    },
                },
                "required": ["channel_id", "file_path"],
            },
        ),
        Tool(
            name="send_file_from_bytes",
            description="Upload a file from bytes data to Discord channel",
            inputSchema={
                "type": "object", 
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID where the file should be sent",
                    },
                    "file_data": {
                        "type": "string",
                        "description": "Base64 encoded file data",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename for the uploaded file",
                    },
                    "content": {
                        "type": "string", 
                        "description": "Optional message text to send with the file",
                    },
                },
                "required": ["channel_id", "file_data", "filename"],
            },
        ),
        Tool(
            name="get_message_attachments", 
            description="Get list of attachments from a specific message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID",
                    },
                    "message_id": {
                        "type": "string", 
                        "description": "Discord message ID",
                    },
                },
                "required": ["channel_id", "message_id"],
            },
        ),
        Tool(
            name="download_attachment",
            description="Download an attachment from a Discord message to local storage",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Discord message ID",
                    },
                    "attachment_filename": {
                        "type": "string",
                        "description": "Filename of the attachment to download",
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Local path where the file should be saved (optional, defaults to downloads/filename)",
                    },
                },
                "required": ["channel_id", "message_id", "attachment_filename"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle Discord tool calls."""
    
    # Get the bot instance from the app
    bot = getattr(app, 'bot_instance', None)
    if not bot or not bot.discord_client:
        return [TextContent(type="text", text="Error: Discord client not ready")]
    
    discord_client = bot.discord_client

    if name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        return [
            TextContent(
                type="text", text=f"Message sent successfully. Message ID: {message.id}"
            )
        ]

    elif name == "read_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 10)), 100)
        fetch_users = arguments.get(
            "fetch_reaction_users", False
        )  # Only fetch users if explicitly requested
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = []
            for reaction in message.reactions:
                emoji_str = (
                    str(reaction.emoji.name)
                    if hasattr(reaction.emoji, "name") and reaction.emoji.name
                    else (
                        str(reaction.emoji.id)
                        if hasattr(reaction.emoji, "id")
                        else str(reaction.emoji)
                    )
                )
                reaction_info = {"emoji": emoji_str, "count": reaction.count}
                logger.error(f"Emoji: {emoji_str}")
                reaction_data.append(reaction_info)
            messages.append(
                {
                    "id": str(message.id),
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "reactions": reaction_data,  # Add reactions to message dict
                }
            )
        return [
            TextContent(
                type="text",
                text=f"Retrieved {len(messages)} messages:\n\n"
                + "\n".join(
                    [
                        f"ID: {m['id']}\n{m['author']} ({m['timestamp']}): {m['content']}\n"
                        + (
                            f"Reactions: {', '.join('{}({})'.format(r['emoji'], r['count']) for r in m['reactions'])}"
                            if m["reactions"]
                            else "Reactions: No reactions"
                        )
                        for m in messages
                    ]
                ),
            )
        ]

    elif name == "get_user_info":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        user_info = {
            "id": str(user.id),
            "name": user.name,
            "discriminator": user.discriminator,
            "bot": user.bot,
            "created_at": user.created_at.isoformat(),
        }
        return [
            TextContent(
                type="text",
                text=f"User information:\n"
                + f"Name: {user_info['name']}#{user_info['discriminator']}\n"
                + f"ID: {user_info['id']}\n"
                + f"Bot: {user_info['bot']}\n"
                + f"Created: {user_info['created_at']}",
            )
        ]

    elif name == "moderate_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))

        # Delete the message - Message.delete() doesn't accept a reason parameter
        await message.delete()

        # Handle timeout if specified
        if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
            if isinstance(message.author, discord.Member):
                duration = discord.utils.utcnow() + datetime.timedelta(
                    minutes=arguments["timeout_minutes"]
                )
                await message.author.timeout(
                    duration, reason=arguments.get("reason", "User timed out via MCP")
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Message deleted and user timed out for {arguments['timeout_minutes']} minutes.",
                    )
                ]

        return [TextContent(type="text", text="Message deleted successfully.")]

    # Server Information Tools
    elif name == "get_server_info":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))

        # Get basic guild info
        info = {
            "name": guild.name,
            "id": str(guild.id),
            "owner_id": str(guild.owner_id),
            "member_count": guild.member_count,
            "created_at": guild.created_at.isoformat(),
            "description": guild.description,
            "premium_tier": guild.premium_tier,
            "explicit_content_filter": str(guild.explicit_content_filter),
        }

        # Fetch all channels to get categories and channels
        channels = await guild.fetch_channels()

        # Separate categories and channels
        categories = []
        text_channels = []
        voice_channels = []

        for channel in channels:
            if isinstance(channel, discord.CategoryChannel):
                categories.append(
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "position": channel.position,
                    }
                )
            elif isinstance(channel, discord.TextChannel):
                text_channels.append(
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "category_id": (
                            str(channel.category_id) if channel.category_id else "None"
                        ),
                        "topic": channel.topic or "No topic",
                    }
                )
            elif isinstance(channel, discord.VoiceChannel):
                voice_channels.append(
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "category_id": (
                            str(channel.category_id) if channel.category_id else "None"
                        ),
                    }
                )

        # Sort channels by position
        categories.sort(key=lambda x: x["position"])

        # Create formatted output
        output = [f"Server Information:"]
        for k, v in info.items():
            output.append(f"{k}: {v}")

        output.append("\nCategories:")
        for cat in categories:
            output.append(f"  {cat['name']} (ID: {cat['id']})")

        output.append("\nText Channels:")
        for chan in text_channels:
            output.append(
                f"  #{chan['name']} (ID: {chan['id']}, Category: {chan['category_id']})"
            )

        output.append("\nVoice Channels:")
        for chan in voice_channels:
            output.append(
                f"  🔊 {chan['name']} (ID: {chan['id']}, Category: {chan['category_id']})"
            )

        return [TextContent(type="text", text="\n".join(output))]

    elif name == "list_members":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        limit = min(int(arguments.get("limit", 100)), 1000)

        members = []
        async for member in guild.fetch_members(limit=limit):
            members.append(
                {
                    "id": str(member.id),
                    "name": member.name,
                    "nick": member.nick,
                    "joined_at": (
                        member.joined_at.isoformat() if member.joined_at else None
                    ),
                    "roles": [
                        str(role.id) for role in member.roles[1:]
                    ],  # Skip @everyone
                }
            )

        return [
            TextContent(
                type="text",
                text=f"Server Members ({len(members)}):\n"
                + "\n".join(
                    f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})"
                    for m in members
                ),
            )
        ]

    # Role Management Tools
    elif name == "add_role":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))

        await member.add_roles(role, reason="Role added via MCP")
        return [
            TextContent(
                type="text", text=f"Added role {role.name} to user {member.name}"
            )
        ]

    elif name == "remove_role":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))

        await member.remove_roles(role, reason="Role removed via MCP")
        return [
            TextContent(
                type="text", text=f"Removed role {role.name} from user {member.name}"
            )
        ]

    # Channel Management Tools
    elif name == "create_text_channel":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        category = None
        if "category_id" in arguments:
            try:
                # Properly fetch the category instead of using get_channel which only checks cache
                category = await discord_client.fetch_channel(
                    int(arguments["category_id"])
                )
                if not isinstance(category, discord.CategoryChannel):
                    logger.warning(
                        f"Channel {arguments['category_id']} is not a category channel"
                    )
                    category = None
            except Exception as e:
                logger.error(f"Error fetching category: {str(e)}")
                category = None

        channel = await guild.create_text_channel(
            name=arguments["name"],
            category=category,
            topic=arguments.get("topic"),
            reason="Channel created via MCP",
        )

        return [
            TextContent(
                type="text",
                text=f"Created text channel #{channel.name} (ID: {channel.id})",
            )
        ]

    elif name == "delete_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        await channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
        return [TextContent(type="text", text=f"Deleted channel successfully")]

    elif name == "create_thread":
        try:
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))

            # Check if this is a text channel that can have threads
            if not isinstance(channel, discord.TextChannel):
                return [
                    TextContent(
                        type="text",
                        text="Error: The specified channel is not a text channel. Only text channels can have threads.",
                    )
                ]

            thread_name = arguments["name"]
            auto_archive_duration = int(
                arguments.get("auto_archive_duration", 1440)
            )  # Default: 1 day

            # Create thread based on whether a message_id is provided
            if "message_id" in arguments:
                # Create a thread from a message
                message = await channel.fetch_message(int(arguments["message_id"]))
                thread = await message.create_thread(
                    name=thread_name, auto_archive_duration=auto_archive_duration
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Created thread #{thread.name} (ID: {thread.id}) from message in channel #{channel.name}",
                    )
                ]
            else:
                # Create a public thread not connected to a message
                thread = await channel.create_thread(
                    name=thread_name,
                    auto_archive_duration=auto_archive_duration,
                    type=discord.ChannelType.public_thread,
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Created public thread #{thread.name} (ID: {thread.id}) in channel #{channel.name}",
                    )
                ]
        except discord.Forbidden:
            return [
                TextContent(
                    type="text",
                    text="Error: The bot does not have permissions to create threads in this channel.",
                )
            ]
        except discord.HTTPException as e:
            return [TextContent(type="text", text=f"Error creating thread: {str(e)}")]

    elif name == "set_channel_permissions":
        try:
            channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
            role_id_str = arguments["role_id"]

            # Get guild
            guild = channel.guild
            if not guild:
                guild = await discord_client.fetch_guild(channel.guild_id)

            # For @everyone role, use the default role
            if role_id_str.lower() == "everyone":
                role = guild.default_role
                logger.info("Using @everyone role for permission settings")
            else:
                # Get the specified role by ID
                try:
                    role_id = int(role_id_str)
                    role = guild.get_role(role_id)

                    # If the role isn't in the cache, look it up more directly
                    if not role:
                        roles = await guild.fetch_roles()
                        for r in roles:
                            if r.id == role_id:
                                role = r
                                break
                except ValueError:
                    # If role_id isn't a valid number and not 'everyone'
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Invalid role ID '{role_id_str}'. Must be a valid role ID or 'everyone'.",
                        )
                    ]

            if not role:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Role with ID {role_id_str} not found in the server.",
                    )
                ]

            # Set if we allow or deny viewing the channel for the role
            allow_view = arguments.get("allow_view", True)

            # Set up permissions for the specified role
            if allow_view:
                await channel.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )
                permission_state = "can now see"
            else:
                await channel.set_permissions(role, view_channel=False)
                permission_state = "can no longer see"

            # Handle @everyone permissions if specified and this isn't already the everyone role
            result_text = f"Updated permissions: Role {role.name} {permission_state} the channel #{channel.name}."

            if arguments.get("modify_everyone", False) and role != guild.default_role:
                everyone_role = guild.default_role
                everyone_can_view = arguments.get("everyone_can_view", False)

                if everyone_can_view:
                    await channel.set_permissions(everyone_role, view_channel=True)
                    result_text += " @everyone can now see the channel."
                else:
                    await channel.set_permissions(everyone_role, view_channel=False)
                    result_text += " @everyone can no longer see the channel."

            return [TextContent(type="text", text=result_text)]
        except discord.Forbidden:
            return [
                TextContent(
                    type="text",
                    text="Error: The bot does not have permissions to modify channel permissions.",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text", text=f"Error setting channel permissions: {str(e)}"
                )
            ]

    elif name == "create_category":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        position = arguments.get("position")

        try:
            # Determine visibility permissions
            everyone_can_view = arguments.get("everyone_can_view", True)
            restricted_role_id = arguments.get("restricted_role_id")

            # Set up permission overwrites
            overwrites = {}

            # Handle @everyone permissions
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=everyone_can_view
            )

            # Handle restricted role permissions if provided
            if restricted_role_id:
                role = guild.get_role(int(restricted_role_id))
                if not role:
                    roles = await guild.fetch_roles()
                    for r in roles:
                        if r.id == int(restricted_role_id):
                            role = r
                            break

                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )
                else:
                    logger.warning(f"Could not find role with ID {restricted_role_id}")

            # Create the category with specified permissions
            category = await guild.create_category(
                name=arguments["name"],
                overwrites=overwrites,
                position=position,
                reason="Category created via MCP",
            )

            # Create a default text channel in the category to make it more visible
            text_channel = await guild.create_text_channel(
                name=f"{arguments['name']}-general",
                category=category,
                reason="Default channel for new category",
            )

            # Generate appropriate success message
            if restricted_role_id and not everyone_can_view:
                msg = f"Created restricted category {category.name} (ID: {category.id}) with default channel #{text_channel.name}. Only specified roles can view it."
            elif not everyone_can_view:
                msg = f"Created hidden category {category.name} (ID: {category.id}) with default channel #{text_channel.name}. @everyone cannot view it."
            else:
                msg = f"Created category {category.name} (ID: {category.id}) with default channel #{text_channel.name}"

            return [TextContent(type="text", text=msg)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating category: {str(e)}")]

    # Message Reaction Tools
    elif name == "add_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.add_reaction(arguments["emoji"])
        return [
            TextContent(
                type="text", text=f"Added reaction {arguments['emoji']} to message"
            )
        ]

    elif name == "add_multiple_reactions":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        for emoji in arguments["emojis"]:
            await message.add_reaction(emoji)
        return [
            TextContent(
                type="text",
                text=f"Added reactions: {', '.join(arguments['emojis'])} to message",
            )
        ]

    elif name == "remove_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.remove_reaction(arguments["emoji"], discord_client.user)
        return [
            TextContent(
                type="text", text=f"Removed reaction {arguments['emoji']} from message"
            )
        ]

    # Role Management Tools
    elif name == "create_role":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))

        try:
            # Set up role creation parameters
            params = {"name": arguments["name"], "reason": "Role created via MCP"}

            # Handle optional parameters
            if "color" in arguments:
                color_str = arguments["color"].lstrip("#")
                color_int = int(color_str, 16)
                params["colour"] = discord.Colour(color_int)

            if "hoist" in arguments:
                params["hoist"] = arguments["hoist"]

            if "mentionable" in arguments:
                params["mentionable"] = arguments["mentionable"]

            if "permissions" in arguments:
                permissions_int = int(arguments["permissions"])
                params["permissions"] = discord.Permissions(permissions=permissions_int)

            # Create the role
            role = await guild.create_role(**params)

            return [
                TextContent(
                    type="text", text=f"Created role {role.name} (ID: {role.id})"
                )
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating role: {str(e)}")]

    elif name == "delete_role":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))
        role_id = int(arguments["role_id"])

        try:
            # Find the role
            role = guild.get_role(role_id)
            if not role:
                roles = await guild.fetch_roles()
                for r in roles:
                    if r.id == role_id:
                        role = r
                        break

            if not role:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Role with ID {role_id} not found in the server.",
                    )
                ]

            # Delete the role
            role_name = role.name
            await role.delete(reason=arguments.get("reason", "Role deleted via MCP"))

            return [
                TextContent(
                    type="text", text=f"Deleted role {role_name} (ID: {role_id})"
                )
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Error deleting role: {str(e)}")]

    elif name == "list_roles":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))

        try:
            # Fetch all roles from the guild
            roles = await guild.fetch_roles()

            # Format role information
            role_info = []
            for role in roles:
                role_info.append(
                    {
                        "id": str(role.id),
                        "name": role.name,
                        "color": str(role.color),
                        "position": role.position,
                        "hoisted": role.hoist,
                        "mentionable": role.mentionable,
                    }
                )

            # Sort roles by position (higher positions are higher in the hierarchy)
            role_info.sort(key=lambda r: r["position"], reverse=True)

            # Format the output
            result = "Server Roles:\n"
            for role in role_info:
                result += f"- {role['name']} (ID: {role['id']}, Position: {role['position']})\n"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing roles: {str(e)}")]

    # User Management Tools
    elif name == "kick_user":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))

        try:
            # Get the member from the guild
            member = await guild.fetch_member(int(arguments["user_id"]))

            # Kick the member
            reason = arguments.get("reason", "Kicked via MCP")
            await member.kick(reason=reason)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully kicked user {member.name}#{member.discriminator} (ID: {member.id}) from the server.",
                )
            ]
        except discord.errors.NotFound:
            return [
                TextContent(
                    type="text",
                    text=f"User with ID {arguments['user_id']} not found in the server.",
                )
            ]
        except discord.errors.Forbidden:
            return [
                TextContent(
                    type="text",
                    text="Bot doesn't have permission to kick this user. Make sure the bot's role is higher than the user's role.",
                )
            ]

    elif name == "ban_user":
        server_id = arguments.get("server_id", DEFAULT_SERVER_ID)
        if not server_id:
            return [
                TextContent(
                    type="text",
                    text="Error: No server ID provided and no default server ID set. Set DEFAULT_SERVER_ID environment variable or provide server_id in the request.",
                )
            ]

        guild = await discord_client.fetch_guild(int(server_id))

        try:
            # Get optional parameters
            reason = arguments.get("reason", "Banned via MCP")
            delete_message_days = min(int(arguments.get("delete_message_days", 0)), 7)

            # Ban the user
            await guild.ban(
                discord.Object(id=int(arguments["user_id"])),
                reason=reason,
                delete_message_days=delete_message_days,
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully banned user with ID {arguments['user_id']} from the server. Deleted messages from the past {delete_message_days} days.",
                )
            ]
        except discord.errors.NotFound:
            return [
                TextContent(
                    type="text", text=f"User with ID {arguments['user_id']} not found."
                )
            ]
        except discord.errors.Forbidden:
            return [
                TextContent(
                    type="text",
                    text="Bot doesn't have permission to ban this user. Make sure the bot's role is higher than the user's role.",
                )
            ]

    elif name == "wait_for_message":
        # Parse arguments
        channel = (
            int(arguments["channel_id"])
            if "channel_id" in arguments and arguments["channel_id"]
            else None
        )
        dm_only = bool(arguments.get("dm_only", False))
        mention_only = bool(arguments.get("mention_only", False))
        sender = (
            int(arguments["sender_id"])
            if "sender_id" in arguments and arguments["sender_id"]
            else None
        )
        content_regex = arguments.get("content_regex")
        timeout = (
            float(arguments["timeout"])
            if "timeout" in arguments and arguments["timeout"]
            else None
        )
        try:
            msg = await wait_for_message(
                discord_client,
                channel=channel,
                dm_only=dm_only,
                mention_only=mention_only,
                sender=sender,
                content_regex=content_regex,
                timeout=timeout,
            )
            return [TextContent(type="text", text=f"Received message: {msg}")]
        except TimeoutError:
            return [
                TextContent(type="text", text="Timeout: No matching message received.")
            ]

    elif name == "get_unread_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 20)), 100)
        since_message_id = arguments.get("since_message_id")
        sender_id = arguments.get("sender_id")
        mention_only = bool(arguments.get("mention_only", False))
        dm_only = bool(arguments.get("dm_only", False))
        content_regex = arguments.get("content_regex")
        messages = []
        if since_message_id:
            after_obj = discord.Object(id=int(since_message_id))
            async for message in channel.history(
                limit=limit, after=after_obj, oldest_first=True
            ):
                messages.append(message)
            # Sort messages by timestamp ascending (oldest to newest)
            messages.sort(key=lambda m: m.created_at)
        else:
            async for message in channel.history(limit=limit):
                messages.append(message)
            # Sort messages by timestamp descending (newest to oldest)
            messages.sort(key=lambda m: m.created_at, reverse=True)
        # Apply filtering
        filtered = []
        for message in messages:
            if sender_id and str(message.author.id) != str(sender_id):
                continue
            if mention_only and discord_client.user not in message.mentions:
                continue
            if dm_only and message.guild is not None:
                continue
            if content_regex:
                import re

                if not re.search(content_regex, message.content):
                    continue
            filtered.append(
                {
                    "id": str(message.id),
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                }
            )
        return [
            TextContent(
                type="text",
                text=f"Unread messages ({len(filtered)}):\n\n"
                + "\n".join(
                    [
                        f"ID: {m['id']}\n{m['author']} ({m['timestamp']}): {m['content']}"
                        for m in filtered
                    ]
                ),
            )
        ]

    elif name == "set_agent_status":
        status = arguments["status"].lower()
        details = arguments.get("details")
        bot.agent_status["status"] = status
        bot.agent_status["details"] = details
        # Map status to Discord presence with human-friendly messages
        activity = None
        discord_status = discord.Status.online
        if status in ("available", "waiting"):
            activity = discord.Game(details or "Ready for tasks")
            discord_status = discord.Status.online
        elif status == "working":
            activity = discord.Game(details or "Working")
            discord_status = discord.Status.online
        elif status == "offline":
            activity = discord.Game(details or "Offline")
            discord_status = discord.Status.invisible
        else:
            activity = discord.Game(details or status.capitalize())
            discord_status = discord.Status.online
        await discord_client.change_presence(status=discord_status, activity=activity)
        return [
            TextContent(
                type="text",
                text=f"Agent status set to '{status}'{' with details: ' + details if details else ''}.",
            )
        ]

    elif name == "check_connection":
        # Check Discord connection status
        connection_info = {
            "discord_client_exists": discord_client is not None,
            "discord_client_ready": (
                discord_client.is_ready() if discord_client else False
            ),
            "bot_user": (
                str(discord_client.user)
                if discord_client and discord_client.user
                else None
            ),
            "guilds_count": len(discord_client.guilds) if discord_client else 0,
            "agent_status": bot.agent_status,
        }

        status_text = f"Discord Connection Status:\n"
        status_text += (
            f"- Discord client exists: {connection_info['discord_client_exists']}\n"
        )
        status_text += (
            f"- Discord client ready: {connection_info['discord_client_ready']}\n"
        )
        status_text += f"- Bot user: {connection_info['bot_user']}\n"
        status_text += f"- Connected to {connection_info['guilds_count']} servers\n"
        status_text += f"- Agent status: {connection_info['agent_status']['status']}"

        if connection_info["agent_status"]["details"]:
            status_text += f" ({connection_info['agent_status']['details']})"

        return [TextContent(type="text", text=status_text)]

    # File Operations
    elif name == "send_file":
        import os
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        file_path = arguments["file_path"]
        filename = arguments.get("filename")
        content = arguments.get("content", "")
        
        try:
            if not os.path.exists(file_path):
                return [TextContent(type="text", text=f"Error: File not found at path: {file_path}")]
            
            discord_file = discord.File(file_path, filename=filename)
            message = await channel.send(content=content, file=discord_file)
            
            return [TextContent(
                type="text", 
                text=f"File uploaded successfully. Message ID: {message.id}, Filename: {filename or os.path.basename(file_path)}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error uploading file: {str(e)}")]

    elif name == "send_file_from_bytes":
        import io
        import base64
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        file_data = arguments["file_data"]
        filename = arguments["filename"]
        content = arguments.get("content", "")
        
        try:
            # Decode base64 data
            bytes_data = base64.b64decode(file_data)
            file_obj = io.BytesIO(bytes_data)
            
            discord_file = discord.File(file_obj, filename=filename)
            message = await channel.send(content=content, file=discord_file)
            
            return [TextContent(
                type="text",
                text=f"File uploaded successfully from bytes. Message ID: {message.id}, Filename: {filename}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error uploading file from bytes: {str(e)}")]

    elif name == "get_message_attachments":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message_id = arguments["message_id"]
        
        try:
            message = await channel.fetch_message(int(message_id))
            attachments = []
            
            for att in message.attachments:
                attachments.append({
                    "filename": att.filename,
                    "url": att.url,
                    "size": att.size,
                    "content_type": getattr(att, 'content_type', 'unknown')
                })
            
            if attachments:
                attachment_text = f"Found {len(attachments)} attachments:\n"
                for att in attachments:
                    attachment_text += f"- {att['filename']} ({att['size']} bytes, {att['content_type']})\n"
                    attachment_text += f"  URL: {att['url']}\n"
            else:
                attachment_text = "No attachments found in this message."
            
            return [TextContent(type="text", text=attachment_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting message attachments: {str(e)}")]

    elif name == "download_attachment":
        import os
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message_id = arguments["message_id"]
        attachment_filename = arguments["attachment_filename"]
        save_path = arguments.get("save_path")
        
        try:
            message = await channel.fetch_message(int(message_id))
            
            # Find the attachment
            target_attachment = None
            for attachment in message.attachments:
                if attachment.filename == attachment_filename:
                    target_attachment = attachment
                    break
            
            if not target_attachment:
                return [TextContent(
                    type="text", 
                    text=f"Error: Attachment '{attachment_filename}' not found in message"
                )]
            
            # Set default save path if not provided
            if not save_path:
                # Create downloads directory in the working directory
                downloads_dir = os.path.abspath("downloads")
                os.makedirs(downloads_dir, exist_ok=True)
                save_path = os.path.join(downloads_dir, attachment_filename)
            else:
                # Make save_path absolute and ensure directory exists
                save_path = os.path.abspath(save_path)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Download the attachment
            await target_attachment.save(fp=save_path, use_cached=False)  # use_cached=False for non-images
            
            return [TextContent(
                type="text",
                text=f"Attachment downloaded successfully:\n- Filename: {attachment_filename}\n- Saved to: {save_path}\n- Absolute path: {os.path.abspath(save_path)}\n- Size: {target_attachment.size} bytes"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error downloading attachment: {str(e)}")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Discord MCP Server")
    parser.add_argument("--token", help="Discord bot token")
    parser.add_argument("--server-id", help="Default Discord server ID")

    # Parse known args (ignore unknown args that might be passed by uv)
    args, unknown = parser.parse_known_args()

    # Use command line args if provided, otherwise fall back to environment variables
    global DISCORD_TOKEN, DEFAULT_SERVER_ID

    # Get token from command line args or environment variables
    token = args.token or os.getenv("DISCORD_TOKEN")
    server_id = args.server_id or os.getenv("DEFAULT_SERVER_ID")

    # Validate that we have a token
    if not token:
        raise ValueError("DISCORD_TOKEN is required. Provide via --token argument or DISCORD_TOKEN environment variable.")

    # Set global variables
    DISCORD_TOKEN = token
    DEFAULT_SERVER_ID = server_id

    # Create a new bot instance for this process using the factory
    bot = create_bot_instance(token)

    # Store the bot instance in the app for access by tools
    app.bot_instance = bot

    # Start Discord bot and wait for it to be ready
    bot_task = asyncio.create_task(bot.start(token))
    
    # Wait for the bot to be ready (with timeout)
    try:
        await asyncio.wait_for(bot.wait_until_ready(), timeout=30.0)
        logger.info("Discord bot is ready, starting MCP server")
    except asyncio.TimeoutError:
        logger.warning("Discord bot connection timeout, starting MCP server anyway")
    except Exception as e:
        logger.error(f"Error waiting for Discord bot: {e}")

    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
