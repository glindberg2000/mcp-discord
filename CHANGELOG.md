# Changelog for glindberg2000/mcp-discord

## [Unreleased]
- fix: get_unread_messages now fetches latest messages if no since_message_id is provided; robust unread and first-login agent workflow
- [x] Event-driven wait_for_message tool for efficient agent workflows
- [x] Robust unread message handling using message IDs (get_unread_messages)
- [ ] Mention/DM/Author Filtering for targeted agent triggers
- [ ] Duplicate/Replay Protection (track last seen message ID per channel)
- [ ] Backlog Processing Loop (process all unread, then wait for new)
- [ ] Graceful Error Handling & Logging for auditability
- [ ] Multi-Channel/DM Support (track unread per channel/DM)
- [ ] Agent Identity & Presence (set status: available/working)
- [ ] History Search/Recall (search message history for context)
- [ ] Configurable Filters & Triggers (runtime config for triggers)

## [fix-fstring-syntax] - 2025-05-11
- fix: remove nested f-string in reactions join (Python compatibility)
- fix: Discord MCP server and config updates

## [Initial Release]
- Upstream MCP Discord server import

## [docs: Add documentation for agent backlog processing pattern (batch unread, humanlike context handling)]
- docs: Add documentation for agent backlog processing pattern (batch unread, humanlike context handling)

## [feat(upcoming): Will implement agent logic to fetch all unread messages as a batch, pass to agent logic, update last seen message ID, and switch to real-time listening]
- feat(upcoming): Will implement agent logic to fetch all unread messages as a batch, pass to agent logic, update last seen message ID, and switch to real-time listening 