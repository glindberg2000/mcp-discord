#!/usr/bin/env python3
"""
Simple test script to verify Discord bot connection
Usage: python test_bot.py YOUR_BOT_TOKEN
"""
import sys
import asyncio
import discord


async def test_bot_connection(token):
    print("Testing Discord bot connection...")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Bot connected successfully!")
        print(f"Bot name: {client.user.name}")
        print(f"Bot ID: {client.user.id}")
        print(f"Connected to {len(client.guilds)} servers:")
        for guild in client.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")
        await client.close()

    @client.event
    async def on_error(event, *args, **kwargs):
        print(f"❌ Error: {event}")
        await client.close()

    try:
        await client.start(token)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_bot.py YOUR_BOT_TOKEN")
        sys.exit(1)

    token = sys.argv[1]
    asyncio.run(test_bot_connection(token))
