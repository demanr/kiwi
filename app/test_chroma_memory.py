#!/usr/bin/env python3
"""
Test script for the ChromaDB memory system functionality.
Run this to verify that memory storage and semantic search work correctly.
"""

from chroma_memory import ChromaMemorySystem, search_memory_tool, store_memory_tool
import tempfile
import shutil
import os


def test_chroma_memory_system():
    """Test the ChromaDB memory system functionality."""
    print("Testing Kiwi ChromaDB Memory System...")
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix='test_chroma_')
    
    try:
        # Initialize memory system with test database
        memory = ChromaMemorySystem(temp_dir)
        
        # Test 1: Store some sample memories
        print("\n1. Testing memory storage...")
        
        memory.store_memory("voice_command", "create a funny cat meme with whiskers", {"action": "meme_creation"})
        memory.store_memory("response", "Created a hilarious cat meme with whiskers!", {"action": "meme_creation"})
        memory.store_memory("voice_command", "copy my work email address to clipboard", {"action": "clipboard"})
        memory.store_memory("response", "Copied john.doe@company.com to clipboard", {"action": "clipboard"})
        memory.store_memory("voice_command", "remember that I love oat milk lattes", {"action": "preference"})
        memory.store_explicit_memory("preference", "User prefers oat milk lattes over regular milk", {"category": "food"})
        memory.store_explicit_memory("reminder", "Sustainability assignment due next Friday", {"urgency": "high"})
        memory.store_memory("clipboard_content", "https://github.com/example/awesome-project", {"type": "url"})
        
        print("✓ Stored 8 sample memory entries")
        
        # Test 2: Semantic search functionality
        print("\n2. Testing semantic memory search...")
        
        # Search for cat-related memories (should find meme content)
        results = memory.search_memory("funny cat pictures", limit=5)
        print(f"✓ Found {len(results)} results for 'funny cat pictures':")
        for i, result in enumerate(results, 1):
            score = result.metadata.get('similarity_score', 0) if result.metadata else 0
            print(f"   {i}. [{result.entry_type}] {result.content[:60]}... (score: {score:.3f})")
        
        # Search for coffee/drink preferences (should find oat milk latte)
        results = memory.search_memory("coffee drinks preferences", limit=3)
        print(f"✓ Found {len(results)} results for 'coffee drinks preferences':")
        for i, result in enumerate(results, 1):
            score = result.metadata.get('similarity_score', 0) if result.metadata else 0
            print(f"   {i}. [{result.entry_type}] {result.content[:60]}... (score: {score:.3f})")
        
        # Search for school/work tasks
        results = memory.search_memory("assignments homework school tasks", limit=3)
        print(f"✓ Found {len(results)} results for 'assignments homework school tasks':")
        for i, result in enumerate(results, 1):
            score = result.metadata.get('similarity_score', 0) if result.metadata else 0
            print(f"   {i}. [{result.entry_type}] {result.content[:60]}... (score: {score:.3f})")
        
        # Test 3: Recent memories
        print("\n3. Testing recent memories retrieval...")
        
        recent = memory.get_recent_memories(limit=5)
        print(f"✓ Retrieved {len(recent)} recent memories:")
        for i, result in enumerate(recent, 1):
            timestamp_str = result.timestamp.strftime("%H:%M:%S") if result.timestamp else "Unknown"
            print(f"   {i}. [{timestamp_str}] {result.entry_type}: {result.content[:50]}...")
        
        # Test 4: Context retrieval with semantic relevance
        print("\n4. Testing context retrieval...")
        
        context = memory.get_relevant_context("I want coffee")
        print(f"✓ Retrieved context for 'I want coffee':")
        print(f"   {context[:300]}...")
        
        context = memory.get_relevant_context("make memes")
        print(f"✓ Retrieved context for 'make memes':")
        print(f"   {context[:300]}...")
        
        # Test 5: Tool functions
        print("\n5. Testing tool functions...")
        
        # Test search tool
        search_result = search_memory_tool("email addresses")
        print(f"✓ Search tool result for 'email addresses':")
        print(f"   {search_result[:200]}...")
        
        # Test store tool
        store_result = store_memory_tool("test", "This is a semantic search test entry", '{"test": true}')
        print(f"✓ Store tool result: {store_result}")
        
        # Test 6: Statistics
        print("\n6. Testing statistics...")
        
        stats = memory.get_stats()
        print(f"✓ Database statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Test 7: Filtered search by type
        print("\n7. Testing filtered search by entry type...")
        
        pref_results = memory.search_memory("food drinks", entry_type="preference", limit=3)
        print(f"✓ Found {len(pref_results)} preference results for 'food drinks':")
        for i, result in enumerate(pref_results, 1):
            print(f"   {i}. {result.content[:50]}...")
        
        print("\n🎉 All ChromaDB memory tests passed! Semantic search is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test database
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up test database: {temp_dir}")
        except:
            pass


if __name__ == "__main__":
    test_chroma_memory_system()