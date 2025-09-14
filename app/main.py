# In main, start a hotword listener. if it hears tango, call a function that prints "Heard tango"
from enum import Enum
from groq import Groq
from audio import HotwordListener
from clipboard import ClipboardMonitor
from typing import Optional
import time
import os
import instructor
from pydantic import BaseModel, Field
import subprocess
from pymacnotifier import MacNotifier

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
groq_client = instructor.from_provider(
    "groq/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY")
)

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


class AssistantResponse(BaseModel):
    """Assistant response indicating whether to act and the action details. Follow the user's instructions to do this."""

    thinking: str
    actionType: ActionType

    message: str = Field(
        ...,
        description="A short message to the user about what action was taken. Be extremely concise, since there is a 50 character limit.",
    )
    emoji: Optional[str] = Field(
        None,
        description="An optional emotion based on the message. The options are angry, annoyed, excited, happy, love, sad, surprised, thinking, winking. Always use an emoji that matches the tone of the message.",
    )
    content_for_clipboard: Optional[str] = None
    meme_top_text: Optional[str] = Field(None, description="Top text for the meme")
    meme_bottom_text: Optional[str] = Field(
        None, description="Bottom text for the meme"
    )


hotword = "tango"


def on_hotword_detected(text, audio):
    prompt = f"Voice Command: {text}"
    prompt += "\n\n"
    prompt += "Clipboard Content:\n"
    prompt += f"{monitor.get_last()}"

    chat_completion = groq_client.chat.completions.create(
        model="qwen/qwen3-32b",  # or another available Groq model
        response_model=AssistantResponse,
        messages=[
            {
                "role": "system",
                "content": f"You are {hotword}, an assistant responding to voice commands. You can copy text to clipboard or create memes from images in clipboard. Only respond with JSON in the specified format. Always follow the user's instructions carefully and try to respond to the best of your abilties.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    # response = chat_completion.choices[0].message.content
    print(f"Full Groq response: {chat_completion}")
    if chat_completion.actionType == ActionType.NO_ACTION:
        if chat_completion.message:
            notifier.simple_notify(
                message=chat_completion.message, emotion=chat_completion.emoji
            )
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
        notifier.simple_notify(
            message=chat_completion.message, emotion=chat_completion.emoji
        )
        return

    if chat_completion.actionType == ActionType.MAKE_MEME:
        # Handle meme creation
        print("Creating meme...")
        data_type, value = monitor.get_last()
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
        notifier.simple_notify(
            message=chat_completion.message, emotion=chat_completion.emoji
        )
        return

    if chat_completion.actionType == ActionType.SHORT_REPLY:
        if chat_completion.message:
            notifier.simple_notify(
                message=chat_completion.message, emotion=chat_completion.emoji
            )
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
