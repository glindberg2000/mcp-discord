# Modular Event-Driven `wait_for_message` Tool for MCP Discord

## Overview
This document outlines the design and rationale for adding a modular, event-driven `wait_for_message` tool to the custom `mcp-discord` fork. The goal is to enable efficient, real-time agent workflows (like bots waiting for tasks) without polling, and to make the logic reusable for other MCP integrations (e.g., Slack, custom chat servers).

---

## Motivation
- **Polling is inefficient** for real-time chat/agent workflows, wasting compute and API tokens.
- **WebSocket/event-driven** models allow agents to wait for messages efficiently, just like our custom chat server bot.
- **Modularization** enables code reuse across Discord, Slack, and custom chat MCP tools, and makes future maintenance and PRs easier.

---

## Features & Requirements
- **Event-driven**: Waits for a message using Discord's Gateway (WebSocket API), not polling.
- **Flexible Filtering**:
  - By channel (ID or name)
  - By DM (direct message only)
  - By mention (only when the bot/user is mentioned)
  - By sender (user ID or username)
  - By content (regex or substring match)
- **Timeout**: Optional timeout parameter to avoid waiting forever.
- **Returns**: The first message matching the filter, with full metadata (sender, channel, timestamp, content).
- **Non-blocking**: Designed to be used as an async MCP tool, so it doesn't block the main event loop.

---

## Modularization Plan
- **New module**: `event_waiter.py` (or similar) in `mcp-discord/src/discord_mcp/`
- **Interface**: Expose a function/class that can be called from the MCP tool handler, e.g.:
  ```python
  await wait_for_message(
      client,  # Discord client instance
      channel=None,
      dm_only=False,
      mention_only=False,
      sender=None,
      content_regex=None,
      timeout=None
  )
  ```
- **Reusability**: The module should be generic enough to be adapted for Slack, custom chat, or other MCP tools with minimal changes.
- **Documentation**: All public functions/classes should be documented for future contributors and PRs.

---

## Implementation Steps
1. **Create the module** with the event-driven wait logic and filtering.
2. **Integrate** with the MCP Discord tool as a new tool/command (`wait_for_message`).
3. **Test** with real Discord events and various filter options.
4. **Document** usage and add examples.
5. **Update the changelog** and prepare for PR.

---

## Changelog Reference
See [CHANGELOG.md](CHANGELOG.md) for a summary of all patches and enhancements.

---

## Future Work
- Adapt the module for Slack and custom chat MCP tools.
- Add more advanced filtering (e.g., reactions, attachments).
- Contribute the enhancement upstream via PR. 