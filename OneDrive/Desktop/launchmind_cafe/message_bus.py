import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

class MessageBus:
    def __init__(self):
        self.messages: Dict[str, List[dict]] = {
            'ceo': [],
            'product': [],
            'engineer': [],
            'marketing': [],
            'qa': []
        }
        self.message_history: List[dict] = []
    
    def send(self, from_agent: str, to_agent: str, message_type: str, payload: dict, parent_message_id: Optional[str] = None) -> str:
        message_id = str(uuid.uuid4())
        message = {
            "message_id": message_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,  # 'task', 'result', 'revision_request', 'confirmation'
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "parent_message_id": parent_message_id
        }
        self.messages[to_agent].append(message)
        self.message_history.append(message)
        print(f"\n📨 {from_agent.upper()} -> {to_agent.upper()}: {message_type}")
        print(f"   Payload preview: {str(payload)[:100]}...")
        return message_id
    
    def receive(self, agent_name: str) -> Optional[dict]:
        if self.messages[agent_name]:
            return self.messages[agent_name].pop(0)
        return None
    
    def get_all_messages_for_agent(self, agent_name: str) -> List[dict]:
        return self.messages[agent_name]
    
    def get_conversation_history(self) -> List[dict]:
        return self.message_history

# Global instance
message_bus = MessageBus()