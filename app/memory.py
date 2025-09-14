"""
Persistent memory system using SQLite with full-text search capabilities.
Stores and retrieves interactions, commands, and context for the Kiwi assistant.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryEntry:
    """Represents a memory entry in the database."""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    entry_type: Optional[str] = None  # 'voice_command', 'response', 'clipboard_content', 'context'
    content: Optional[str] = None
    metadata: Optional[Dict] = None


class MemorySystem:
    """SQLite-based memory system with full-text search capabilities."""

    def __init__(self, db_path: str = None):
        """Initialize the memory system with SQLite database."""
        if db_path is None:
            # Create database in the app directory
            app_dir = Path(__file__).parent
            db_path = app_dir / "kiwi_memory.db"
        
        self.db_path = str(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database with FTS (Full-Text Search) table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create the main memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create FTS virtual table for full-text search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    entry_id,
                    entry_type,
                    content,
                    metadata,
                    content='memory_entries',
                    content_rowid='id'
                )
            """)
            
            # Create triggers to keep FTS table in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_entries BEGIN
                    INSERT INTO memory_fts(entry_id, entry_type, content, metadata)
                    VALUES (new.id, new.entry_type, new.content, new.metadata);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory_entries BEGIN
                    DELETE FROM memory_fts WHERE entry_id = old.id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memory_entries BEGIN
                    DELETE FROM memory_fts WHERE entry_id = old.id;
                    INSERT INTO memory_fts(entry_id, entry_type, content, metadata)
                    VALUES (new.id, new.entry_type, new.content, new.metadata);
                END
            """)
            
            conn.commit()

    def store_memory(self, entry_type: str, content: str, metadata: Dict = None) -> int:
        """
        Store a memory entry in the database.
        
        Args:
            entry_type: Type of entry ('voice_command', 'response', 'clipboard_content', 'context')
            content: The main content to store
            metadata: Additional metadata as a dictionary
            
        Returns:
            The ID of the stored entry
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_entries (timestamp, entry_type, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (timestamp, entry_type, content, metadata_json))
            conn.commit()
            return cursor.lastrowid

    def search_memory(self, query: str, entry_type: str = None, limit: int = 10) -> List[MemoryEntry]:
        """
        Search memory entries using full-text search.
        
        Args:
            query: Search query string
            entry_type: Optional filter by entry type
            limit: Maximum number of results to return
            
        Returns:
            List of MemoryEntry objects matching the search
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sanitize the query for FTS5 - escape special characters and quotes
            sanitized_query = query.replace('"', '""').replace("'", "''")
            
            try:
                # Try FTS search first
                if entry_type:
                    # Use column filter for entry_type
                    cursor.execute("""
                        SELECT m.id, m.timestamp, m.entry_type, m.content, m.metadata
                        FROM memory_entries m
                        JOIN memory_fts f ON m.id = f.entry_id
                        WHERE memory_fts MATCH ? AND m.entry_type = ?
                        ORDER BY bm25(memory_fts) ASC
                        LIMIT ?
                    """, (f'"{sanitized_query}"', entry_type, limit))
                else:
                    cursor.execute("""
                        SELECT m.id, m.timestamp, m.entry_type, m.content, m.metadata
                        FROM memory_entries m
                        JOIN memory_fts f ON m.id = f.entry_id
                        WHERE memory_fts MATCH ?
                        ORDER BY bm25(memory_fts) ASC
                        LIMIT ?
                    """, (f'"{sanitized_query}"', limit))
                
            except sqlite3.OperationalError as e:
                # If FTS search fails, fall back to LIKE search
                print(f"FTS search failed ({e}), falling back to LIKE search")
                if entry_type:
                    cursor.execute("""
                        SELECT id, timestamp, entry_type, content, metadata
                        FROM memory_entries
                        WHERE (content LIKE ? OR entry_type LIKE ?) AND entry_type = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (f'%{query}%', f'%{query}%', entry_type, limit))
                else:
                    cursor.execute("""
                        SELECT id, timestamp, entry_type, content, metadata
                        FROM memory_entries
                        WHERE content LIKE ? OR entry_type LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (f'%{query}%', f'%{query}%', limit))
            
            results = []
            for row in cursor.fetchall():
                entry_id, timestamp, entry_type, content, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else None
                
                results.append(MemoryEntry(
                    id=entry_id,
                    timestamp=datetime.fromisoformat(timestamp),
                    entry_type=entry_type,
                    content=content,
                    metadata=metadata
                ))
            
            return results

    def get_recent_memories(self, entry_type: str = None, limit: int = 10) -> List[MemoryEntry]:
        """
        Get recent memory entries.
        
        Args:
            entry_type: Optional filter by entry type
            limit: Maximum number of results to return
            
        Returns:
            List of recent MemoryEntry objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if entry_type:
                cursor.execute("""
                    SELECT id, timestamp, entry_type, content, metadata
                    FROM memory_entries
                    WHERE entry_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (entry_type, limit))
            else:
                cursor.execute("""
                    SELECT id, timestamp, entry_type, content, metadata
                    FROM memory_entries
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                entry_id, timestamp, entry_type, content, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else None
                
                results.append(MemoryEntry(
                    id=entry_id,
                    timestamp=datetime.fromisoformat(timestamp),
                    entry_type=entry_type,
                    content=content,
                    metadata=metadata
                ))
            
            return results

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
            timestamp_str = memory.timestamp.strftime("%Y-%m-%d %H:%M")
            context_parts.append(
                f"[{timestamp_str}] {memory.entry_type}: {memory.content[:200]}..."
                if len(memory.content) > 200 else
                f"[{timestamp_str}] {memory.entry_type}: {memory.content}"
            )
        
        return "\n".join(context_parts)

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

    def cleanup_old_entries(self, days_to_keep: int = 30):
        """
        Clean up old memory entries to prevent database from growing too large.
        
        Args:
            days_to_keep: Number of days to keep entries for
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cutoff_iso = cutoff_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM memory_entries 
                WHERE timestamp < ?
            """, (cutoff_iso,))
            conn.commit()
            
            # The FTS triggers will automatically clean up the FTS table

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the memory database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            total_entries = cursor.fetchone()[0]
            
            # Entries by type
            cursor.execute("""
                SELECT entry_type, COUNT(*) 
                FROM memory_entries 
                GROUP BY entry_type
            """)
            
            stats = {"total_entries": total_entries}
            for entry_type, count in cursor.fetchall():
                stats[f"{entry_type}_count"] = count
            
            return stats


# Global memory instance
_memory_instance = None


def get_memory() -> MemorySystem:
    """Get the global memory system instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemorySystem()
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
        timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M")
        content_preview = result.content[:150] + "..." if len(result.content) > 150 else result.content
        formatted_results.append(
            f"{i}. [{timestamp}] {result.entry_type}: {content_preview}"
        )
    
    return "\n".join(formatted_results)


def store_memory_tool(entry_type: str, content: str, metadata: str = None) -> str:
    """
    Tool function to store a memory entry.
    """
    memory = get_memory()
    metadata_dict = json.loads(metadata) if metadata else None
    entry_id = memory.store_memory(entry_type, content, metadata_dict)
    return f"Stored memory entry with ID: {entry_id}"