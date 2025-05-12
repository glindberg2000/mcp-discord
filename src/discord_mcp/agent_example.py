import os
import json
import time
from typing import List, Dict, Any
from mcp.client import MCPClient

LAST_SEEN_FILE = "last_seen_message_id.json"
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")  # Set this in your environment
MCP_SERVER = os.environ.get("MCP_SERVER", "http://localhost:8000")


def load_last_seen() -> str:
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_seen_id")
    return None


def save_last_seen(message_id: str):
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump({"last_seen_id": message_id}, f)


def agent_decision_logic(messages: List[Dict[str, Any]]):
    # Placeholder: Replace with your AI or rules logic
    print("\n--- AGENT DECISION LOGIC ---")
    for msg in messages:
        print(f"[{msg['timestamp']}] {msg['author']}: {msg['content']}")
    print("--- END ---\n")
    # Example: Just print the latest message
    if messages:
        print(f"Latest message: {messages[-1]['content']}")


def main():
    client = MCPClient(MCP_SERVER)
    last_seen_id = load_last_seen()
    print(f"Loaded last seen message ID: {last_seen_id}")

    while True:
        # 1. Fetch all unread messages as a batch
        args = {"channel_id": CHANNEL_ID}
        if last_seen_id:
            args["since_message_id"] = last_seen_id
        result = client.call_tool("get_unread_messages", args)
        # Parse messages from result
        messages = []
        if result and result[0]["type"] == "text":
            # Parse messages from the text output (assumes standard format)
            lines = result[0]["text"].split("\nID: ")
            for line in lines[1:]:
                parts = line.split("\n", 2)
                msg_id = parts[0].strip()
                rest = parts[1] if len(parts) > 1 else ""
                author, rest2 = rest.split(" (", 1) if " (" in rest else (rest, "")
                timestamp, content = (
                    rest2.split("): ", 1) if "): " in rest2 else (rest2, "")
                )
                messages.append(
                    {
                        "id": msg_id,
                        "author": author.strip(),
                        "timestamp": timestamp.strip().rstrip(")"),
                        "content": content.strip(),
                    }
                )
        # 2. Pass batch to agent logic
        if messages:
            agent_decision_logic(messages)
            # 3. Update last seen message ID
            last_seen_id = messages[-1]["id"]
            save_last_seen(last_seen_id)
            print(f"Updated last seen message ID: {last_seen_id}")
        # 4. Switch to real-time listening
        print("Waiting for new message (real-time)...")
        wait_args = {"channel_id": CHANNEL_ID}
        result = client.call_tool("wait_for_message", wait_args)
        # 5. On new message, repeat backlog fetch and processing
        # (loop continues)
        time.sleep(1)


if __name__ == "__main__":
    main()
