# Modular Event-Driven `wait_for_message` Tool for MCP Discord

## Overview
This document outlines the design and rationale for adding a modular, event-driven `wait_for_message` tool to the custom `mcp-discord` fork. The goal is to enable efficient, real-time agent workflows (like bots waiting for tasks) without polling, and to make the logic reusable for other MCP integrations (e.g., Slack, custom chat servers).

---

## Motivation
- **Polling is inefficient** for real-time chat/agent workflows, wasting compute and API tokens.
- **WebSocket/event-driven** models allow agents to wait for messages efficiently, just like our custom chat server bot.
- **Modularization** enables code reuse for other chat platforms.

---

## Robust Agent Workflow for Unread Message Handling

### Key Principle
- **Discord message IDs are unique, strictly increasing, and chronologically ordered.**
- This allows agents to reliably track which messages have been seen and process any missed messages in order.

### Step-by-Step Workflow
1. **Track the Last Seen Message ID:**
   - Store the highest message ID the agent has processed (not just sent).
   - On startup, load this from a file, database, or (if stateless) set to the last message the agent sent.

2. **On Login:**
   - Call `get_unread_messages` with the last seen message ID.
   - Process all returned messages in order (oldest to newest).
   - After each message, update the last seen message ID.

3. **After Each Task:**
   - Before waiting for new messages, check for any new messages since the last seen ID.
   - Process and update the last seen ID as above.

4. **Switch to Real-Time Waiting:**
   - Once the backlog is empty, use `wait_for_message` to catch new, real-time messages as they arrive.

5. **Fallback for Stateless Agents:**
   - If the agent cannot persist state, fetch the last N messages and process any with a higher ID than the last message it sent.

### Why This Works
- **No missed messages:** All messages sent while the agent was offline are processed on login.
- **No double-processing:** Each message is only handled once, thanks to the unique, increasing ID.
- **Chronological order:** Tasks are processed in the order they were sent, just like a human would.

---

## Implementation Notes
- The `get_unread_messages` tool should always be called with the last seen message ID.
- The agent should update its last seen message ID after each processed message.
- This pattern is robust and can be adapted for any chat platform with unique, ordered message IDs.

---

## See also
- `event_waiter.py` for the modular event-driven message waiter implementation.
- `server.py` for MCP tool registration and usage examples.

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

---

## Current Status
- [x] Event-driven wait_for_message tool for efficient agent workflows
- [x] Robust unread message handling using message IDs (get_unread_messages)

## Next Steps for Humanlike Agent Robustness

- [ ] Mention/DM/Author Filtering for targeted agent triggers
- [ ] Duplicate/Replay Protection (track last seen message ID per channel)
- [ ] Backlog Processing Loop (process all unread, then wait for new)
- [ ] Graceful Error Handling & Logging for auditability
- [ ] Multi-Channel/DM Support (track unread per channel/DM)
- [ ] Agent Identity & Presence (set status: available/working)
- [ ] History Search/Recall (search message history for context)
- [ ] Configurable Filters & Triggers (runtime config for triggers)

---

## Robust Unread Message Logic
- On login, agent calls get_unread_messages with last seen message ID (if available)
- If no last seen ID, fetches latest N messages for first login
- Processes all unread messages in order, updating last seen ID after each
- Switches to wait_for_message for real-time event-driven workflow
- Ensures no missed or double-processed messages, even if agent was offline 

## Agent Backlog Processing Pattern (Humanlike Robustness)

### Rationale
Agents should not process unread messages one-by-one, as this can lead to acting on outdated or cancelled instructions. Instead, agents should fetch all unread messages as a batch and reason over the full context, just as a human would when catching up on a conversation.

### Workflow
- On startup/login, call `get_unread_messages` with the last seen message ID.
- Pass the entire batch of unread messages to the agent's decision logic.
- The agent should reason over the full backlog, taking into account reversals, clarifications, and cancellations.
- After processing, update and persist the last seen message ID.
- Switch to real-time listening with `wait_for_message`.
- On new message, repeat the backlog fetch and processing.

### Implementation Steps
1. Fetch all unread messages as a batch.
2. Pass the batch to agent logic for context-aware decision making.
3. Update and persist the last seen message ID.
4. Use `wait_for_message` for real-time operation.
5. On new message, repeat backlog fetch and processing.

This pattern is now the recommended approach for all Discord agent workflows in this repo. 