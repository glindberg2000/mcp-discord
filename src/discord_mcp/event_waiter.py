"""
event_waiter.py

A modular, event-driven message waiter for Discord MCP tools.
Supports flexible filtering (channel, DM, mention, sender, content) and can be adapted for other chat platforms.

---

Robust Unread Message Handling:
- Always track the last seen message ID (Discord message IDs are unique and strictly increasing).
- On login, call get_unread_messages(channel_id, since_message_id=last_seen_id) to fetch all missed messages.
- Process all unread messages in order, updating last_seen_id after each.
- After backlog is empty, use wait_for_message for real-time events.
- This ensures no missed or double-processed messages, even if the agent was offline.

See DESIGN_PLAN.md for full workflow details.
"""

import asyncio
import re
from typing import Optional, Callable, Any


def _message_matches_filters(
    message, *, channel, dm_only, mention_only, sender, content_regex, client
):
    # Channel filter
    if channel is not None and message.channel.id != channel:
        return False
    # DM only
    if dm_only and message.guild is not None:
        return False
    # Mention only
    if mention_only and client.user not in message.mentions:
        return False
    # Sender filter
    if sender is not None and message.author.id != sender:
        return False
    # Content regex
    if content_regex is not None and not re.search(content_regex, message.content):
        return False
    return True


async def wait_for_message(
    client,
    channel: Optional[int] = None,
    dm_only: bool = False,
    mention_only: bool = False,
    sender: Optional[int] = None,
    content_regex: Optional[str] = None,
    timeout: Optional[float] = None,
    on_event: Optional[Callable[[Any], None]] = None,
) -> dict:
    """
    Wait for a Discord message matching the given filters. Returns the message dict or raises asyncio.TimeoutError.
    """
    future = asyncio.get_event_loop().create_future()

    # Define the async listener as a coroutine
    async def listener(message):
        if _message_matches_filters(
            message,
            channel=channel,
            dm_only=dm_only,
            mention_only=mention_only,
            sender=sender,
            content_regex=content_regex,
            client=client,
        ):
            if not future.done():
                future.set_result(
                    {
                        "id": str(message.id),
                        "author": str(message.author),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "channel_id": str(message.channel.id),
                    }
                )
            if on_event:
                on_event(message)

    # Register the listener
    client.add_listener(listener, "on_message")

    try:
        result = await asyncio.wait_for(future, timeout=timeout)
    finally:
        # Always remove the listener after completion or timeout
        client.remove_listener(listener, "on_message")
    return result
