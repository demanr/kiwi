# In main, start a hotword listener. if it hears tango, call a function that prints "Heard tango"
from groq import Groq
from audio import HotwordListener
from clipboard import ClipboardMonitor
import time
import os
import instructor
from pydantic import BaseModel

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
groq_client = instructor.from_provider(
    "groq/gpt-oss-20b", api_key=os.getenv("GROQ_API_KEY")
)

monitor = ClipboardMonitor()
monitor.start(log=True)


class ClipboardContent(BaseModel):
    """Structured response containing only the content to be copied to clipboard."""

    content_for_clipboard: str


def on_hotword_detected(text, audio):
    prompt = f"Voice Command: {text}"
    prompt += "\n\n"
    prompt += "Clipboard Content:\n"
    prompt += f"{monitor.get_last()}"

    chat_completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",  # or another available Groq model
        response_model=ClipboardContent,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant responding to voice commands managing someone's clipboard.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    # response = chat_completion.choices[0].message.content
    print(f"Full Groq response: {chat_completion}")
    response = chat_completion.content_for_clipboard
    print(f"Groq response: {response}")
    # use instructor to remove fluff so response is only the text to copy to clipboard
    monitor.copy_text(response)
    print("Clipboard updated with Groq response.")

    # Here you can add more actions, e.g., interact with clipboard or other functionalities


if __name__ == "__main__":
    listener = HotwordListener("tango", on_hotword_detected)
    listener.start(background=True)

    # Keep the main thread alive to allow background listening
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping listener...")
        listener.stop()
