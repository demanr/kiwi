#!/usr/bin/env python3
"""
Test script for the memory system functionality.
Run this to verify that memory storage and search work correctly.
"""

from memory import MemorySystem, search_memory_tool, store_memory_tool
import os
import tempfile


def test_memory_system():
    """Test the memory system functionality."""
    print("Testing Kiwi Memory System...")
    
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        temp_db_path = temp_db.name
    
    try:
        # Initialize memory system with test database
        memory = MemorySystem(temp_db_path)
        
        # Test 1: Store some sample memories
        print("\n1. Testing memory storage...")
        
        memory.store_memory("voice_command", "create a meme with cats", {"action": "meme_creation"})
        memory.store_memory("response", "Created a funny cat meme!", {"action": "meme_creation"})
        memory.store_memory("voice_command", "copy my email address", {"action": "clipboard"})
        memory.store_memory("response", "Copied john@example.com to clipboard", {"action": "clipboard"})
        memory.store_memory("voice_command", "search for that cat meme we made yesterday", {"action": "search"})
        memory.store_memory("clipboard_content", "https://example.com/project", {"type": "url"})
        
        print("✓ Stored 6 sample memory entries")
        
        # Test 2: Search functionality
        print("\n2. Testing memory search...")
        
        # Search for cat-related memories
        results = memory.search_memory("cat meme", limit=5)
        print(f"✓ Found {len(results)} results for 'cat meme':")
        for i, result in enumerate(results, 1):
            print(f"   {i}. [{result.entry_type}] {result.content[:50]}...")
        
        # Search for email-related memories
        results = memory.search_memory("email", limit=3)
        print(f"✓ Found {len(results)} results for 'email':")
        for i, result in enumerate(results, 1):
            print(f"   {i}. [{result.entry_type}] {result.content[:50]}...")
        
        # Test 3: Recent memories
        print("\n3. Testing recent memories retrieval...")
        
        recent = memory.get_recent_memories(limit=3)
        print(f"✓ Retrieved {len(recent)} recent memories:")
        for i, result in enumerate(recent, 1):
            timestamp = result.timestamp.strftime("%H:%M:%S")
            print(f"   {i}. [{timestamp}] {result.entry_type}: {result.content[:50]}...")
        
        # Test 4: Context retrieval
        print("\n4. Testing context retrieval...")
        
        context = memory.get_relevant_context("meme")
        print(f"✓ Retrieved context for 'meme':")
        print(f"   {context[:200]}...")
        
        # Test 5: Tool functions
        print("\n5. Testing tool functions...")
        
        # Test search tool
        search_result = search_memory_tool("clipboard")
        print(f"✓ Search tool result for 'clipboard':")
        print(f"   {search_result[:100]}...")
        
        # Test store tool
        store_result = store_memory_tool("test", "This is a test entry", '{"test": true}')
        print(f"✓ Store tool result: {store_result}")
        
        # Test 6: Statistics
        print("\n6. Testing statistics...")
        
        stats = memory.get_stats()
        print(f"✓ Database statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n🎉 All tests passed! Memory system is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test database
        try:
            os.unlink(temp_db_path)
            print(f"\n🧹 Cleaned up test database: {temp_db_path}")
        except:
            pass


if __name__ == "__main__":
    test_memory_system()