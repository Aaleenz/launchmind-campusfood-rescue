import json
import uuid
from datetime import datetime
from collections import defaultdict

class MessageBus:
    def __init__(self):
        self.messages = []  # List of all messages
        self.queues = defaultdict(list)  # Per-agent queues
    
    def send(self, from_agent: str, to_agent: str, message_type: str, payload: dict, parent_message_id: str = None):
        """Send a message to an agent"""
        message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "parent_message_id": parent_message_id
        }
        self.messages.append(message)
        self.queues[to_agent].append(message)
        
        # Print for debugging (optional)
        print(f"\n📨 {from_agent.upper()} -> {to_agent.upper()}: {message_type}")
        # print(f"   Payload preview: {str(payload)[:100]}...")
        
        return message["message_id"]
    
    def send_dict(self, message: dict):
        """Send a message dict (for compatibility)"""
        self.messages.append(message)
        self.queues[message["to_agent"]].append(message)
        print(f"\n📨 {message['from_agent'].upper()} -> {message['to_agent'].upper()}: {message['message_type']}")
        return message["message_id"]
    
    def receive(self, agent_name: str):
        """Get next message for an agent (FIFO)"""
        if self.queues[agent_name]:
            return self.queues[agent_name].pop(0)
        return None
    
    def get_messages_for(self, agent_name: str):
        """Get all pending messages for an agent (returns list, doesn't remove)"""
        # Return a copy to avoid modification issues
        return self.queues[agent_name].copy()
    
    def get_all_messages(self):
        """Get all messages (for debugging)"""
        return self.messages.copy()
    
    def clear(self):
        """Clear all messages"""
        self.messages = []
        self.queues = defaultdict(list)

# Global instance
message_bus = MessageBus()