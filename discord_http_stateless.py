#!/usr/bin/env python3
"""
Stateless Discord HTTP API
Creates fresh Discord clients per request - no caching or state storage
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-stateless-api")

# FastAPI app
app = FastAPI(title="Stateless Discord HTTP API", version="1.0.0")


class MessageRequest(BaseModel):
    """Request to send a message"""
    channel_id: str
    content: str
    discord_token: str  # Token provided per request


class MessageResponse(BaseModel):
    """Response from message operations"""
    success: bool
    message_id: Optional[str] = None
    bot_info: Optional[str] = None
    error: Optional[str] = None


class TokenRequest(BaseModel):
    """Request that includes bot token"""
    discord_token: str
    server_id: Optional[str] = None


async def create_discord_client(token: str) -> discord.Client:
    """Create a fresh Discord client for a single request"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    client = discord.Client(intents=intents)
    
    try:
        await client.login(token)
        logger.info(f"✅ Created fresh Discord client for token: ...{token[-8:]}")
        return client
    except discord.LoginFailure:
        raise HTTPException(status_code=401, detail="Invalid Discord token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to authenticate: {e}")


async def execute_with_client(token: str, operation):
    """Execute an operation with a temporary Discord client"""
    client = None
    try:
        client = await create_discord_client(token)
        result = await operation(client)
        logger.info(f"✅ Operation completed for token: ...{token[-8:]}")
        return result
    finally:
        if client:
            await client.close()
            logger.info(f"🔌 Closed Discord client for token: ...{token[-8:]}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "stateless": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/test")
async def test_message(request: TokenRequest):
    """Send a test message with token-specific identity"""
    async def test_operation(client):
        # Find first available text channel
        channel = None
        bot_name = str(client.user) if client.user else "Unknown Bot"
        
        for guild in client.guilds:
            for c in guild.channels:
                if isinstance(c, discord.TextChannel):
                    channel = c
                    break
            if channel:
                break
        
        if not channel:
            return {
                "success": False,
                "error": "No accessible text channels found",
                "bot_info": bot_name
            }
        
        # Send message with bot identity
        message_content = f"🚀 Test from {bot_name} (ID: {client.user.id}) - Stateless Discord API!"
        message = await channel.send(message_content)
        
        return {
            "success": True,
            "message_id": str(message.id),
            "bot_info": bot_name
        }
    
    try:
        result = await execute_with_client(request.discord_token, test_operation)
        return MessageResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        return MessageResponse(
            success=False,
            error=str(e)
        )


@app.post("/messages")
async def send_message(request: MessageRequest):
    """Send a message to a Discord channel with fresh client"""
    async def send_operation(client):
        try:
            channel = client.get_channel(int(request.channel_id))
            if not channel:
                channel = await client.fetch_channel(int(request.channel_id))
            
            if not channel:
                return {
                    "success": False,
                    "error": f"Channel {request.channel_id} not found or bot doesn't have access",
                    "bot_info": str(client.user)
                }
            
            # Add bot identity to message
            bot_name = str(client.user) if client.user else "Unknown Bot"
            enhanced_content = f"{request.content} [Sent by: {bot_name}]"
            
            message = await channel.send(enhanced_content)
            
            return {
                "success": True,
                "message_id": str(message.id),
                "bot_info": bot_name
            }
            
        except discord.Forbidden:
            return {
                "success": False,
                "error": "Bot doesn't have permission to send messages in this channel",
                "bot_info": str(client.user)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "bot_info": str(client.user)
            }
    
    try:
        result = await execute_with_client(request.discord_token, send_operation)
        return MessageResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        return MessageResponse(
            success=False,
            error=str(e)
        )


@app.post("/channels")
async def list_channels(request: TokenRequest):
    """List all accessible Discord channels for a bot"""
    async def list_operation(client):
        channels = []
        bot_name = str(client.user) if client.user else "Unknown Bot"
        
        for guild in client.guilds:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    channels.append({
                        "id": str(channel.id),
                        "name": channel.name,
                        "guild": guild.name
                    })
        
        return {
            "bot_info": bot_name,
            "channels": channels,
            "count": len(channels)
        }
    
    try:
        result = await execute_with_client(request.discord_token, list_operation)
        return result
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting Stateless Discord HTTP API on port 9091")
    logger.info("🔄 Creates fresh Discord clients per request")
    logger.info("📝 Tokens provided per request - no caching")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9091,
        log_level="info"
    )