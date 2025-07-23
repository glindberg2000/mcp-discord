#!/usr/bin/env python3
"""
HTTP API for Discord operations using the existing enhanced_discord_agent
This provides a simple REST API for Discord operations
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-http-api")

# Import our existing Discord functionality
# from llm_providers import LLMProvider, LLMFactory  # Not needed for basic Discord API


class MessageRequest(BaseModel):
    """Request to send a message"""
    channel_id: str
    content: str
    thread_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Response from message operations"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class ChannelInfo(BaseModel):
    """Discord channel information"""
    id: str
    name: str
    type: str
    guild_id: Optional[str] = None


class DiscordBot:
    """Simplified Discord bot for HTTP operations"""
    
    def __init__(self, token: str, server_id: Optional[str] = None):
        self.token = token
        self.server_id = server_id
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.ready = False
        
        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.bot.user}")
            self.ready = True
    
    async def start(self):
        """Start the bot in the background"""
        asyncio.create_task(self.bot.start(self.token))
        
        # Wait for bot to be ready
        for _ in range(30):  # 30 second timeout
            if self.ready:
                break
            await asyncio.sleep(1)
        
        if not self.ready:
            raise RuntimeError("Discord bot failed to connect")
    
    async def send_message(self, channel_id: str, content: str, 
                          thread_id: Optional[str] = None) -> str:
        """Send a message to a Discord channel"""
        try:
            # Get the channel
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                # Try fetching it
                channel = await self.bot.fetch_channel(int(channel_id))
            
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
            
            # If thread_id provided, get the thread
            if thread_id:
                thread = channel.get_thread(int(thread_id))
                if thread:
                    channel = thread
            
            # Send the message
            message = await channel.send(content)
            return str(message.id)
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def list_channels(self) -> List[ChannelInfo]:
        """List all accessible channels"""
        channels = []
        
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    channels.append(ChannelInfo(
                        id=str(channel.id),
                        name=channel.name,
                        type="text",
                        guild_id=str(guild.id)
                    ))
        
        return channels
    
    async def get_recent_messages(self, channel_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from a channel"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(channel_id))
            
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    "id": str(message.id),
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "channel_id": str(message.channel.id)
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            raise


# Create FastAPI app
app = FastAPI(
    title="Discord HTTP API",
    description="HTTP API for Discord operations",
    version="1.0.0"
)

# Global bot instance
discord_bot: Optional[DiscordBot] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Discord bot on startup"""
    global discord_bot
    
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not set")
        raise ValueError("DISCORD_TOKEN required")
    
    server_id = os.getenv("DEFAULT_SERVER_ID")
    
    discord_bot = DiscordBot(token, server_id)
    await discord_bot.start()
    
    logger.info("Discord HTTP API started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "discord_connected": discord_bot is not None and discord_bot.ready,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/channels")
async def list_channels():
    """List all accessible Discord channels"""
    if not discord_bot:
        raise HTTPException(status_code=503, detail="Discord bot not initialized")
    
    try:
        channels = await discord_bot.list_channels()
        return {"channels": channels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/messages")
async def send_message(request: MessageRequest):
    """Send a message to a Discord channel"""
    if not discord_bot:
        raise HTTPException(status_code=503, detail="Discord bot not initialized")
    
    try:
        message_id = await discord_bot.send_message(
            request.channel_id,
            request.content,
            request.thread_id
        )
        
        return MessageResponse(
            success=True,
            message_id=message_id
        )
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return MessageResponse(
            success=False,
            error=str(e)
        )


@app.get("/messages/{channel_id}")
async def get_messages(channel_id: str, limit: int = 10):
    """Get recent messages from a channel"""
    if not discord_bot:
        raise HTTPException(status_code=503, detail="Discord bot not initialized")
    
    try:
        messages = await discord_bot.get_recent_messages(channel_id, limit)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test")
async def test_message():
    """Send a test message to the default channel"""
    if not discord_bot:
        raise HTTPException(status_code=503, detail="Discord bot not initialized")
    
    # Try to find #general or first available channel
    channels = await discord_bot.list_channels()
    
    general_channel = None
    for channel in channels:
        if channel.name == "general":
            general_channel = channel
            break
    
    if not general_channel and channels:
        general_channel = channels[0]
    
    if not general_channel:
        raise HTTPException(status_code=404, detail="No channels found")
    
    request = MessageRequest(
        channel_id=general_channel.id,
        content="🚀 Discord HTTP API is working! This is a test message."
    )
    
    return await send_message(request)


if __name__ == "__main__":
    import sys
    
    # Allow port override
    port = 9090
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )