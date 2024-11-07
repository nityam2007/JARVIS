import json
import os
from datetime import datetime
import time

class MemoryManager:
    """
    Manages conversation history, user preferences, and persistent storage
    """
    def __init__(self, config):
        """
        Initialize the MemoryManager with given configuration
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.conversation_history = []
        self.max_history = config.get("memory_settings", {}).get("max_history_length", 10)
        self.history_file = config.get("memory_settings", {}).get("history_file", "conversation_history.json")
        self.load_history()

    def add_to_history(self, role, content):
        """
        Add a new message to conversation history
        
        Args:
            role (str): Role of the speaker ("user" or "assistant")
            content (str): Content of the message
        """
        timestamp = datetime.now().isoformat()
        entry = {
            "role": role,
            "content": content,
            "timestamp": timestamp
        }
        
        self.conversation_history.append(entry)
        
        # Maintain history length limit
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Save history periodically
        self.save_history()

    def get_recent_history(self, limit=None):
        """
        Get recent conversation history
        
        Args:
            limit (int, optional): Number of recent messages to return
            
        Returns:
            list: Recent conversation history
        """
        if limit is None:
            return self.conversation_history
        return self.conversation_history[-limit:]

    def save_history(self):
        """Save conversation history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation history: {e}")

    def load_history(self):
        """Load conversation history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            self.conversation_history = []

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.save_history()

    def get_messages_for_ai(self, limit=5):
        """
        Get formatted message history for AI model
        
        Args:
            limit (int): Number of recent messages to include
            
        Returns:
            list: Formatted message history
        """
        recent_history = self.get_recent_history(limit)
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in recent_history]

    def search_history(self, query):
        """
        Search conversation history
        
        Args:
            query (str): Search query
            
        Returns:
            list: Matching conversation entries
        """
        query = query.lower()
        return [entry for entry in self.conversation_history 
                if query in entry["content"].lower()]

    def get_statistics(self):
        """
        Get conversation statistics
        
        Returns:
            dict: Statistics about the conversation history
        """
        if not self.conversation_history:
            return {}
            
        user_messages = [msg for msg in self.conversation_history 
                        if msg["role"] == "user"]
        assistant_messages = [msg for msg in self.conversation_history 
                            if msg["role"] == "assistant"]
                            
        first_timestamp = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
        last_timestamp = datetime.fromisoformat(self.conversation_history[-1]["timestamp"])
        
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "conversation_duration": str(last_timestamp - first_timestamp),
            "first_message": first_timestamp.isoformat(),
            "last_message": last_timestamp.isoformat()
        }

    def export_history(self, format="json"):
        """
        Export conversation history in specified format
        
        Args:
            format (str): Export format ("json" or "txt")
            
        Returns:
            str: Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = f"conversation_export_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2)
                
        elif format == "txt":
            filename = f"conversation_export_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for msg in self.conversation_history:
                    f.write(f"{msg['role'].upper()}: {msg['content']}\n")
                    f.write(f"Time: {msg['timestamp']}\n")
                    f.write("-" * 80 + "\n")
        
        return filename