#!/usr/bin/env python3
"""
Test MCP client connecting to Discord HTTP API
This simulates how Claude Code containers would use the Discord MCP over HTTP
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, Any


class MCPDiscordHTTPClient:
    """MCP-style client for Discord HTTP API"""
    
    def __init__(self, base_url: str = "http://localhost:9090", token: str = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {"Authorization": f"Bot {token}"} if token else {}
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize MCP connection (like MCP protocol initialization)"""
        async with aiohttp.ClientSession() as session:
            # Test the connection with a simple test call
            async with session.post(
                f"{self.base_url}/test",
                headers={"Authorization": f"Bot {self.token}"}
            ) as resp:
                result = await resp.json()
                
            if result.get("success"):
                print(f"✅ Initialized MCP Discord client (Bot Token: ...{self.token[-8:]})")
                print(f"   - Test message sent successfully: {result.get('message_id', 'unknown')}")
                return {"status": "connected", "test_message_id": result.get("message_id")}
            else:
                raise Exception(f"Failed to initialize: {result}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available Discord tools (MCP tools/list)"""
        # Simulate MCP tools/list response
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "send_message",
                        "description": "Send a message to a Discord channel",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "channel_id": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["channel_id", "content"]
                        }
                    },
                    {
                        "name": "list_channels", 
                        "description": "List all accessible Discord channels",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "test_message",
                        "description": "Send a test message",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Discord tool (MCP tools/call)"""
        async with aiohttp.ClientSession() as session:
            if name == "send_message":
                async with session.post(
                    f"{self.base_url}/messages",
                    json={
                        "channel_id": arguments["channel_id"],
                        "content": arguments["content"]
                    },
                    headers=self.headers
                ) as resp:
                    result = await resp.json()
                    
                return {
                    "jsonrpc": "2.0", 
                    "id": 1,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Message sent successfully. ID: {result.get('message_id', 'unknown')}"
                            }
                        ]
                    }
                }
            
            elif name == "list_channels":
                async with session.post(
                    f"{self.base_url}/channels", 
                    json={"token": self.token}
                ) as resp:
                    result = await resp.json()
                    
                channels = result.get("channels", [])
                channel_list = "\n".join([f"#{ch['name']} ({ch['id']})" for ch in channels])
                
                return {
                    "jsonrpc": "2.0",
                    "id": 1, 
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Available channels ({len(channels)}):\n{channel_list}"
                            }
                        ]
                    }
                }
            
            elif name == "test_message":
                async with session.post(
                    f"{self.base_url}/test",
                    headers=self.headers
                ) as resp:
                    result = await resp.json()
                    
                return {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "content": [
                            {
                                "type": "text", 
                                "text": f"Test message sent! Message ID: {result.get('message_id', 'unknown')}"
                            }
                        ]
                    }
                }
            
            else:
                raise ValueError(f"Unknown tool: {name}")


async def test_mcp_discord_clients():
    """Test multiple MCP clients with different Discord tokens"""
    print("🤖 Testing MCP Discord HTTP Clients with Multiple Tokens")
    print("=" * 60)
    
    # Get tokens from environment
    token1 = os.getenv("DISCORD_TOKEN")
    token2 = os.getenv("DISCORD_TOKEN2") 
    
    if not token1:
        print("❌ DISCORD_TOKEN not set")
        return
    
    if not token2:
        print("⚠️  DISCORD_TOKEN2 not set, testing with single token only")
        token2 = None
    
    # Test Client 1
    print(f"\n🔵 Testing MCP Client 1 (Bot Token: ...{token1[-8:]})")
    print("-" * 40)
    
    client1 = MCPDiscordHTTPClient(token=token1)
    
    try:
        # Initialize
        await client1.initialize()
        
        # List tools
        tools_resp = await client1.list_tools()
        tools = tools_resp["result"]["tools"]
        print(f"✅ Available tools: {[t['name'] for t in tools]}")
        
        # List channels
        channels_result = await client1.call_tool("list_channels", {})
        print(f"✅ Channels: {channels_result['result']['content'][0]['text'][:100]}...")
        
        # Send test message
        test_result = await client1.call_tool("test_message", {})
        print(f"✅ Test message: {test_result['result']['content'][0]['text']}")
        
    except Exception as e:
        print(f"❌ Client 1 failed: {e}")
    
    # Test Client 2 if available
    if token2:
        print(f"\n🟢 Testing MCP Client 2 (Bot Token: ...{token2[-8:]})")
        print("-" * 40)
        
        client2 = MCPDiscordHTTPClient(token=token2)
        
        try:
            # Initialize 
            await client2.initialize()
            
            # Send test message 
            test_result = await client2.call_tool("test_message", {})
            print(f"✅ Test message: {test_result['result']['content'][0]['text']}")
            
            # Send custom message to show it's a different bot
            channels_result = await client2.call_tool("list_channels", {})
            channels_text = channels_result['result']['content'][0]['text']
            
            # Extract first channel ID
            lines = channels_text.split('\n')
            if len(lines) > 1:
                first_channel_line = lines[1]  # Skip header
                channel_id = first_channel_line.split('(')[1].split(')')[0]
                
                custom_result = await client2.call_tool("send_message", {
                    "channel_id": channel_id,
                    "content": "🤖 This message is from Bot 2 - different Discord application!"
                })
                print(f"✅ Custom message: {custom_result['result']['content'][0]['text']}")
            
        except Exception as e:
            print(f"❌ Client 2 failed: {e}")
    
    print("\n✅ MCP Discord HTTP Client tests completed!")
    print("Check Discord to see messages from different bot applications")


async def test_claude_code_container_usage():
    """Simulate how a Claude Code container would use this"""
    print("\n🐳 Simulating Claude Code Container Usage")
    print("-" * 40)
    
    # This is how a Claude Code container would use it
    token = os.getenv("DISCORD_TOKEN") 
    if not token:
        print("❌ No token available for container simulation")
        return
    
    # Container gets token from its environment and uses HTTP API
    container_client = MCPDiscordHTTPClient(token=token)
    
    try:
        await container_client.initialize()
        
        # Container sends status update
        result = await container_client.call_tool("send_message", {
            "channel_id": "1395578179531309089",  # Your #general channel
            "content": "🐳 Claude Code container started and connected to Discord via HTTP MCP!"
        })
        
        print(f"✅ Container sent status: {result['result']['content'][0]['text']}")
        
    except Exception as e:
        print(f"❌ Container simulation failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_mcp_discord_clients())
    asyncio.run(test_claude_code_container_usage())