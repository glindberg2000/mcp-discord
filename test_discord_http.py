#!/usr/bin/env python3
"""
Test script for Discord MCP HTTP server
"""

import asyncio
import aiohttp
import json
import sys
from typing import Optional


class DiscordMCPClient:
    """Simple client to test the Discord MCP HTTP server"""
    
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self):
        """Check server health"""
        async with self.session.get(f"{self.base_url}/health") as resp:
            return await resp.json()
    
    async def server_info(self):
        """Get server info"""
        async with self.session.get(f"{self.base_url}/info") as resp:
            return await resp.json()
    
    async def list_tools(self):
        """List available tools via MCP"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        async with self.session.post(
            f"{self.base_url}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        ) as resp:
            result = await resp.json()
            return result.get("result", {}).get("tools", [])
    
    async def send_message(self, channel_id: str, content: str):
        """Send a message to Discord"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "send_message",
                "arguments": {
                    "channel_id": channel_id,
                    "content": content
                }
            },
            "id": 2
        }
        
        async with self.session.post(
            f"{self.base_url}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        ) as resp:
            return await resp.json()


async def main():
    """Run tests"""
    # Get channel ID from command line or environment
    channel_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    async with DiscordMCPClient() as client:
        print("Testing Discord MCP HTTP Server...")
        print("-" * 50)
        
        # Health check
        try:
            health = await client.health_check()
            print(f"✅ Health Check: {health}")
        except Exception as e:
            print(f"❌ Health Check Failed: {e}")
            return
        
        # Server info
        try:
            info = await client.server_info()
            print(f"✅ Server Info: {json.dumps(info, indent=2)}")
        except Exception as e:
            print(f"❌ Server Info Failed: {e}")
        
        # List tools
        try:
            tools = await client.list_tools()
            print(f"✅ Available Tools: {len(tools)}")
            for tool in tools[:5]:  # Show first 5
                print(f"   - {tool.get('name', 'Unknown')}")
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")
        except Exception as e:
            print(f"❌ List Tools Failed: {e}")
        
        # Send test message if channel ID provided
        if channel_id:
            try:
                result = await client.send_message(
                    channel_id,
                    "🚀 Test message from Discord MCP HTTP server!"
                )
                print(f"✅ Message Sent: {result}")
            except Exception as e:
                print(f"❌ Send Message Failed: {e}")
        else:
            print("\n💡 Tip: Provide a channel ID as argument to test sending messages")
            print("   python test_discord_http.py <channel_id>")


if __name__ == "__main__":
    asyncio.run(main())