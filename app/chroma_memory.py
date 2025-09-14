"""
Enhanced memory system using ChromaDB for semantic search.
Replaces SQLite-based memory with vector embeddings for better relevance.
"""

import chromadb
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import uuid


@dataclass
class MemoryEntry:
    """Represents a memory entry."""
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    entry_type: Optional[str] = None  # 'voice_command', 'response', 'clipboard_content', 'context'
    content: Optional[str] = None
    metadata: Optional[Dict] = None


class ChromaMemorySystem:
    """ChromaDB-based memory system with semantic search capabilities."""

    def __init__(self, db_path: str = None):
        """Initialize the ChromaDB memory system."""
        if db_path is None:
            # Create database in the app directory
            app_dir = Path(__file__).parent
            db_path = str(app_dir / "chroma_memory")
        
        self.db_path = db_path
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="kiwi_memory",
            metadata={"description": "Kiwi assistant memory storage"}
        )

    def store_memory(self, entry_type: str, content: str, metadata: Dict = None) -> str:
        """
        Store a memory entry in ChromaDB.
        
        Args:
            entry_type: Type of entry ('voice_command', 'response', 'clipboard_content', 'context')
            content: The main content to store
            metadata: Additional metadata as a dictionary
            
        Returns:
            The ID of the stored entry
        """
        # Generate unique ID
        entry_id = str(uuid.uuid4())
        
        # Prepare metadata
        entry_metadata = metadata.copy() if metadata else {}
        entry_metadata.update({
            "entry_type": entry_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stored_explicitly": False
        })
        
        # Store in ChromaDB
        self.collection.add(
            documents=[content],
            metadatas=[entry_metadata],
            ids=[entry_id]
        )
        
        return entry_id

    def search_memory(self, query: str, entry_type: str = None, limit: int = 10) -> List[MemoryEntry]:
        """
        Search memory entries using semantic similarity.
        
        Args:
            query: Search query string
            entry_type: Optional filter by entry type
            limit: Maximum number of results to return
            
        Returns:
            List of MemoryEntry objects matching the search
        """
        # Build where clause for filtering
        where_clause = {}
        if entry_type:
            where_clause["entry_type"] = entry_type
        
        # Perform semantic search
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_clause if where_clause else None
        )
        
        # Convert results to MemoryEntry objects
        memory_entries = []
        
        if results['ids'] and results['ids'][0]:  # Check if results exist
            for i in range(len(results['ids'][0])):
                entry_id = results['ids'][0][i]
                document = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i] if 'distances' in results else None
                
                # Parse timestamp
                timestamp_str = metadata.get('timestamp')
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None
                
                # Create MemoryEntry
                entry = MemoryEntry(
                    id=entry_id,
                    timestamp=timestamp,
                    entry_type=metadata.get('entry_type'),
                    content=document,
                    metadata={**metadata, 'similarity_score': 1 - distance if distance else None}
                )
                memory_entries.append(entry)
        
        return memory_entries

    def get_recent_memories(self, entry_type: str = None, limit: int = 10) -> List[MemoryEntry]:
        """
        Get recent memory entries.
        
        Args:
            entry_type: Optional filter by entry type
            limit: Maximum number of results to return
            
        Returns:
            List of recent MemoryEntry objects
        """
        # Build where clause
        where_clause = {}
        if entry_type:
            where_clause["entry_type"] = entry_type
        
        # Get all entries (ChromaDB doesn't have direct "recent" query, so we get all and sort)
        results = self.collection.get(
            where=where_clause if where_clause else None,
            limit=limit * 3  # Get more than needed to sort properly
        )
        
        # Convert to MemoryEntry objects and sort by timestamp
        memory_entries = []
        
        if results['ids']:
            for i in range(len(results['ids'])):
                entry_id = results['ids'][i]
                document = results['documents'][i]
                metadata = results['metadatas'][i]
                
                # Parse timestamp
                timestamp_str = metadata.get('timestamp')
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.min
                
                entry = MemoryEntry(
                    id=entry_id,
                    timestamp=timestamp,
                    entry_type=metadata.get('entry_type'),
                    content=document,
                    metadata=metadata
                )
                memory_entries.append(entry)
        
        # Sort by timestamp (most recent first) and limit
        memory_entries.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
        return memory_entries[:limit]

    def get_relevant_context(self, current_input: str, max_entries: int = 5) -> str:
        """
        Get relevant context from memory based on the current input.
        
        Args:
            current_input: The current user input or voice command
            max_entries: Maximum number of context entries to include
            
        Returns:
            Formatted context string
        """
        # Search for relevant memories
        relevant_memories = self.search_memory(current_input, limit=max_entries)
        
        if not relevant_memories:
            return "No relevant previous context found."
        
        context_parts = ["Previous relevant interactions:"]
        
        for memory in relevant_memories:
            timestamp_str = memory.timestamp.strftime("%Y-%m-%d %H:%M") if memory.timestamp else "Unknown"
            similarity = memory.metadata.get('similarity_score', 0) if memory.metadata else 0
            
            # Only include if reasonably similar (threshold to avoid noise)
            if similarity is None or similarity > 0.3:
                content_preview = (memory.content[:200] + "..." 
                                 if len(memory.content) > 200 
                                 else memory.content)
                
                context_parts.append(
                    f"[{timestamp_str}] {memory.entry_type}: {content_preview}"
                )
        
        return "\n".join(context_parts) if len(context_parts) > 1 else "No highly relevant previous context found."

    def store_interaction(self, voice_command: str, response: str, clipboard_content: str = None, 
                         action_type: str = None):
        """
        Store a complete interaction (voice command + response + context).
        
        Args:
            voice_command: The user's voice command
            response: The assistant's response
            clipboard_content: Current clipboard content
            action_type: The type of action taken
        """
        interaction_metadata = {
            "action_type": action_type,
            "has_clipboard": clipboard_content is not None
        }
        
        # Store voice command
        self.store_memory("voice_command", voice_command, interaction_metadata)
        
        # Store response
        self.store_memory("response", response, interaction_metadata)
        
        # Store clipboard content if available
        if clipboard_content:
            self.store_memory("clipboard_content", clipboard_content, interaction_metadata)

    def store_explicit_memory(self, entry_type: str, content: str, metadata: Dict = None) -> str:
        """
        Store explicitly saved memory with special marking.
        
        Args:
            entry_type: Type of memory ('preference', 'important_info', 'reminder', 'note')
            content: Content to store
            metadata: Additional metadata
            
        Returns:
            Entry ID
        """
        # Mark as explicitly stored
        save_metadata = metadata.copy() if metadata else {}
        save_metadata["stored_explicitly"] = True
        
        return self.store_memory(entry_type, content, save_metadata)

    def cleanup_old_entries(self, days_to_keep: int = 30):
        """
        Clean up old memory entries to prevent database from growing too large.
        Note: ChromaDB doesn't have built-in cleanup, so we'll implement basic cleanup
        
        Args:
            days_to_keep: Number of days to keep entries for
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cutoff_iso = cutoff_date.isoformat()
        
        # Get all entries
        all_entries = self.collection.get()
        
        # Find entries to delete
        ids_to_delete = []
        for i, metadata in enumerate(all_entries['metadatas']):
            timestamp_str = metadata.get('timestamp')
            if timestamp_str:
                entry_timestamp = datetime.fromisoformat(timestamp_str)
                # Keep explicitly stored entries longer, delete automatic logs
                if (entry_timestamp < cutoff_date and 
                    not metadata.get('stored_explicitly', False)):
                    ids_to_delete.append(all_entries['ids'][i])
        
        # Delete old entries
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            print(f"Cleaned up {len(ids_to_delete)} old memory entries")

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the memory database."""
        # Get all entries
        all_entries = self.collection.get()
        total_entries = len(all_entries['ids']) if all_entries['ids'] else 0
        
        # Count by type
        stats = {"total_entries": total_entries}
        
        if all_entries['metadatas']:
            type_counts = {}
            explicit_count = 0
            
            for metadata in all_entries['metadatas']:
                entry_type = metadata.get('entry_type', 'unknown')
                type_counts[entry_type] = type_counts.get(entry_type, 0) + 1
                
                if metadata.get('stored_explicitly', False):
                    explicit_count += 1
            
            stats.update(type_counts)
            stats["explicit_memories"] = explicit_count
        
        return stats


# Global memory instance
_memory_instance = None


def get_memory() -> ChromaMemorySystem:
    """Get the global ChromaDB memory system instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ChromaMemorySystem()
    return _memory_instance


# Tool functions for the assistant
def search_memory_tool(query: str, entry_type: str = None, limit: int = 5) -> str:
    """
    Tool function to search memory and return formatted results.
    This can be called by the assistant as a tool.
    """
    memory = get_memory()
    results = memory.search_memory(query, entry_type, limit)
    
    if not results:
        return f"No memories found matching '{query}'"
    
    formatted_results = [f"Found {len(results)} relevant memories:"]
    
    for i, result in enumerate(results, 1):
        timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M") if result.timestamp else "Unknown"
        content_preview = result.content[:150] + "..." if len(result.content) > 150 else result.content
        
        # Show similarity score if available
        similarity_info = ""
        if result.metadata and result.metadata.get('similarity_score'):
            similarity = result.metadata['similarity_score']
            similarity_info = f" (relevance: {similarity:.2f})"
        
        formatted_results.append(
            f"{i}. [{timestamp}] {result.entry_type}: {content_preview}{similarity_info}"
        )
    
    return "\n".join(formatted_results)


def store_memory_tool(entry_type: str, content: str, metadata: str = None) -> str:
    """
    Tool function to store a memory entry.
    """
    memory = get_memory()
    metadata_dict = json.loads(metadata) if metadata else None
    entry_id = memory.store_explicit_memory(entry_type, content, metadata_dict)
    return f"Stored memory entry with ID: {entry_id}"