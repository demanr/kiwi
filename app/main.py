# In main, start a hotword listener. if it hears tango, call a function that prints "Heard tango"
from enum import Enum
from groq import Groq
from audio import HotwordListener
from clipboard import ClipboardMonitor
from chroma_memory import get_memory, search_memory_tool
from typing import Optional
import time
import os
import instructor
from pydantic import BaseModel, Field, field_validator
import subprocess
from pymacnotifier import MacNotifier

# Import Google GenAI for search capabilities
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("google-genai not available, search functionality will be disabled")

# Environment variable for model provider
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "groq").lower()

def create_client():
    """Create the appropriate client based on MODEL_PROVIDER environment variable."""
    if MODEL_PROVIDER == "gemini":
        try:
            if GENAI_AVAILABLE:
                # Create native GenAI client for search capabilities
                native_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                
                # Create instructor client for structured outputs
                instructor_client = instructor.from_provider(
                    "google/gemini-2.5-flash-lite",
                    api_key=os.getenv("GEMINI_API_KEY")
                )
                
                return {
                    "instructor": instructor_client,
                    "native": native_client,
                    "model": "gemini-2.5-flash-lite",
                    "provider": "gemini"
                }
            else:
                raise Exception("Google GenAI not available")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            print("Falling back to Groq...")
            # Fall back to Groq
    
    # Default to Groq
    client = instructor.from_provider(
        "groq/llama-3.3-70b-versatile", 
        api_key=os.getenv("GROQ_API_KEY")
    )
    return {
        "instructor": client,
        "native": None,
        "model": "llama-3.3-70b-versatile",
        "provider": "groq"
    }

# Initialize client based on provider
client_config = create_client()
print(f"Using {client_config['provider']} provider with model: {client_config['model']}")

monitor = ClipboardMonitor()
monitor.start(log=True)

# Initialize the Mac notifier with a default title
notifier = MacNotifier(default_title="Tango")


class CopyTextToClipboardResponse(BaseModel):
    """Structured response containing the content to be copied to clipboard."""

    content_for_clipboard: str


class ActionType(Enum):
    """Types of actions the assistant can take."""

    COPY_TEXT_TO_CLIPBOARD = "COPY_TEXT_TO_CLIPBOARD"
    SHORT_REPLY = "SHORT_REPLY"
    NO_ACTION = "NO_ACTION"
    MAKE_MEME = "MAKE_MEME"
    SEARCH_MEMORY = "SEARCH_MEMORY"
    SAVE_TO_MEMORY = "SAVE_TO_MEMORY"


class AssistantResponse(BaseModel):
    """Assistant response indicating whether to act and the action details. Follow the user's instructions to do this."""

    thinking: str
    actionType: ActionType

    message: str = Field(
        ...,
        description="A short message to the user about what action was taken. Be extremely concise, since there is a 50 character limit.",
    )
    content_for_clipboard: Optional[str] = None
    meme_top_text: Optional[str] = Field(None, description="Top text for the meme")
    meme_bottom_text: Optional[str]     = Field(
        None, description="Bottom text for the meme"
    )
    memory_search_query: Optional[str] = Field(
        None, description="Query to search memory when action is SEARCH_MEMORY"
    )
    memory_save_content: Optional[str] = Field(
        None, description="Content to save to memory when action is SAVE_TO_MEMORY"
    )
    memory_save_type: Optional[str] = Field(
        None, description="Type of memory entry to save (e.g., 'important_info', 'preference', 'note', 'reminder')"
    )
    
    @field_validator('actionType', mode='before')
    @classmethod
    def validate_action_type(cls, v):
        if isinstance(v, str):
            # Try to convert string to enum
            for action in ActionType:
                if action.value == v:
                    return action
            # If no match found, raise error with helpful message
            valid_values = [action.value for action in ActionType]
            raise ValueError(f"Invalid actionType: {v}. Must be one of: {valid_values}")
        return v


hotword = "tango"


def on_hotword_detected(text, audio):
    # Get memory system instance
    memory = get_memory()
    
    # Get current clipboard content
    clipboard_data = monitor.get_last()
    if clipboard_data is None:
        clipboard_data_type, clipboard_content = None, None
        clipboard_str = "Empty"
    else:
        clipboard_data_type, clipboard_content = clipboard_data
        clipboard_str = f"Type: {clipboard_data_type}, Content: {str(clipboard_content)[:200]}..." if clipboard_content else "Empty"
    
    # Get relevant context from memory
    relevant_context = memory.get_relevant_context(text, max_entries=3)
    
    # Get current date/time
    from datetime import datetime
    current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Build the prompt with memory context
    prompt = f"Current Date/Time: {current_datetime}"
    prompt += f"\n\nVoice Command: {text}"
    prompt += "\n\n"
    prompt += "Current Clipboard Content:\n"
    prompt += clipboard_str
    prompt += "\n\n"
    # prompt += "Relevant Previous Context:\n"
    # prompt += relevant_context

    # Use appropriate client based on provider and search needs
    if client_config["provider"] == "gemini" and client_config["native"]:
        # For Gemini, try to use search first, then fall back to structured response
        try:
            # Check if the query might benefit from web search
            search_keywords = ["current", "recent", "latest", "news", "today", "now", "update"]
            should_search = any(keyword in text.lower() for keyword in search_keywords)
            
            if should_search:
                # Use native client with search tool
                grounding_tool = types.Tool(google_search=types.GoogleSearch())
                config = types.GenerateContentConfig(tools=[grounding_tool])
                
                search_response = client_config["native"].models.generate_content(
                    model=client_config["model"],
                    contents=f"{prompt}\n\nUser Query: {text}",
                    config=config,
                )
                
                # If we got search results, use them in the structured response
                if hasattr(search_response.candidates[0], 'grounding_metadata') and search_response.candidates[0].grounding_metadata:
                    prompt += f"\n\nWeb Search Results: {search_response.text}"
        except Exception as e:
            print(f"Search failed, continuing with regular response: {e}")
    
    # Generate structured response
    try:
        chat_completion = client_config["instructor"].chat.completions.create(
            model=client_config["model"],
            response_model=AssistantResponse,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are {hotword}, a voice assistant that responds to commands. You have access to several actions:

CURRENT CONTEXT: Use the provided current date/time to understand temporal references like "today", "tomorrow", "next week", "yesterday", etc.

MEMORY ACTIONS:
- SAVE_TO_MEMORY: Use when users explicitly want to save information for later recall
  * Keywords: "remember that", "save this", "note that", "keep in mind", "don't forget"
  * Types to use:
    - "preference": User likes/dislikes ("remember I like oat milk lattes")  
    - "important_info": Critical personal info ("note that I'm allergic to shellfish")
    - "reminder": Time-sensitive items ("remember my assignment is due next week")
    - "note": General facts ("save that the WiFi password is xyz123")
  * Example: "Remember that I have a sustainability assignment due next week" → SAVE_TO_MEMORY with type "reminder"

- SEARCH_MEMORY: Use when users want to find past information
  * Keywords: "what did we", "find that", "recall when", "search for", "do you remember"
  * Example: "What did we talk about yesterday?" → SEARCH_MEMORY with query "yesterday conversations"
  * Example: "Find that email address I saved" → SEARCH_MEMORY with query "email address"

OTHER ACTIONS:
- COPY_TEXT_TO_CLIPBOARD: Copy specific text user requests. This is your primary action for most commands, as the user will be asking you to help with their clipboard content.
- MAKE_MEME: Create meme from clipboard image with top/bottom text
- SHORT_REPLY: Just notify user with a message. Their clipboard remains unchanged.

Use the current date/time to understand when things happened relative to now. Only respond with valid JSON matching the AssistantResponse schema.

Remember that you are primariy interacting via short messages and by assisting the user with their clipboard content. There might be some noisey text from the voice recognition, so focus on the core intent of the command.
""",
                },
                {"role": "user", "content": prompt},
            ],
        )
        
        print(f"Raw response type: {type(chat_completion)}")
        print(f"Raw response actionType: {chat_completion.actionType} (type: {type(chat_completion.actionType)})")
        
    except Exception as e:
        print(f"Error during response generation: {e}")
        print(f"Error type: {type(e)}")
        # Create a fallback response
        chat_completion = AssistantResponse(
            thinking="Error occurred during response generation",
            actionType=ActionType.SHORT_REPLY,
            message="Sorry, I encountered an error processing your request."
        )

    # Store the interaction in memory
    action_type_str = chat_completion.actionType.value if chat_completion.actionType else "UNKNOWN"
    memory.store_interaction(
        voice_command=text,
        response=chat_completion.message,
        clipboard_content=clipboard_str if clipboard_content else None,
        action_type=action_type_str
    )

    # response = chat_completion.choices[0].message.content
    print(f"Full Groq response: {chat_completion}")
    if chat_completion.actionType == ActionType.NO_ACTION:
        if chat_completion.message:
            notifier.simple_notify(message=chat_completion.message)
        print("No action needed.")
        return

    if (
        chat_completion.actionType == ActionType.COPY_TEXT_TO_CLIPBOARD
        and chat_completion.content_for_clipboard
    ):
        response = chat_completion.content_for_clipboard
        print(f"Groq response: {response}")
        # use instructor to remove fluff so response is only the text to copy to clipboard
        monitor.copy_text(response)
        print("Clipboard updated with Groq response.")
        notifier.simple_notify(message=chat_completion.message)
        return

    if chat_completion.actionType == ActionType.MAKE_MEME:
        # Handle meme creation
        print("Creating meme...")
        clipboard_data = monitor.get_last()
        if clipboard_data is None:
            print("No clipboard data found to create a meme.")
            return
        data_type, value = clipboard_data
        if data_type is None or value is None or data_type != "image":
            print("No image found in clipboard to create a meme.")
            return
        from meme import make_meme

        meme_image = make_meme(
            value,
            upper_text=chat_completion.meme_top_text or "",
            lower_text=chat_completion.meme_bottom_text or "",
        )
        monitor.copy_image(meme_image)
        print("Meme created and copied to clipboard.")
        notifier.simple_notify(message=chat_completion.message)
        return

    if chat_completion.actionType == ActionType.SHORT_REPLY:
        if chat_completion.message:
            notifier.simple_notify(message=chat_completion.message)
        return

    if chat_completion.actionType == ActionType.SEARCH_MEMORY:
        # Handle memory search - do a two-step process
        if chat_completion.memory_search_query:
            search_results = search_memory_tool(chat_completion.memory_search_query)
            print(f"Memory search results: {search_results}")
            
            # Now ask the LLM again with the search results to provide a proper answer
            follow_up_prompt = f"Current Date/Time: {current_datetime}"
            follow_up_prompt += f"\n\nOriginal Voice Command: {text}"
            follow_up_prompt += f"\n\nMemory Search Results:\n{search_results}"
            follow_up_prompt += f"\n\nPlease provide a helpful response based on the search results above. If the search results contain relevant information, use it to answer the user's question properly."
            
            follow_up_completion = client_config["instructor"].chat.completions.create(
                model=client_config["model"],
                response_model=AssistantResponse,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are {hotword}, providing information from memory search results.

TASK: Answer the user's original question using the search results provided.

ACTIONS AVAILABLE:
- COPY_TEXT_TO_CLIPBOARD: If user wants specific information copied (emails, passwords, addresses, etc.)
- SHORT_REPLY: For conversational responses about what you found
- NO_ACTION: If no specific action is needed

INSTRUCTIONS:
- If search results are empty/irrelevant: "I couldn't find any relevant information about [topic]"  
- If results contain useful info: Summarize what you found and offer to copy specific details if helpful
- Be conversational and helpful - don't just list raw search results
- Keep messages under 50 characters due to notification limits""",
                    },
                    {"role": "user", "content": follow_up_prompt},
                ],
            )
            
            print(f"Follow-up response: {follow_up_completion}")
            
            # Handle the follow-up response
            if follow_up_completion.actionType == ActionType.COPY_TEXT_TO_CLIPBOARD and follow_up_completion.content_for_clipboard:
                monitor.copy_text(follow_up_completion.content_for_clipboard)
                notifier.simple_notify(message=follow_up_completion.message)
            elif follow_up_completion.actionType == ActionType.SHORT_REPLY:
                notifier.simple_notify(message=follow_up_completion.message)
            
            # Store the memory search interaction
            memory.store_interaction(
                voice_command=text,
                response=follow_up_completion.message,
                clipboard_content=search_results,
                action_type="MEMORY_SEARCH_FOLLOWUP"
            )
        return

    if chat_completion.actionType == ActionType.SAVE_TO_MEMORY:
        # Handle saving important information to memory
        if chat_completion.memory_save_content:
            memory_type = chat_completion.memory_save_type or "user_note"
            metadata = {
                "original_command": text,
                "save_type": memory_type
            }
            # Use explicit memory storage method for ChromaDB
            entry_id = memory.store_explicit_memory(memory_type, chat_completion.memory_save_content, metadata)
            print(f"Saved to memory with ID: {entry_id}")
            notifier.simple_notify(message=chat_completion.message)
        return


if __name__ == "__main__":
    listener = HotwordListener(hotword, on_hotword_detected)
    listener.start(background=True)

    # Keep the main thread alive to allow background listening
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping listener...")
        listener.stop()
