# In main, start a hotword listener. if it hears tango, call a function that prints "Heard tango"
from groq import Groq
from audio import HotwordListener
from clipboard import ClipboardMonitor
import time
import os

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

monitor = ClipboardMonitor()
monitor.start(log=True)

def on_hotword_detected(text, audio):
    prompt = f"Voice Command: {text}"
    prompt += "\n\n"
    prompt += "Clipboard Content:\n"
    prompt += f"{monitor.get_last()}"

    chat_completion = groq_client.chat.completions.create(
    model="openai/gpt-oss-20b",  # or another available Groq model
    messages=[
            {"role": "system", "content": "You are a helpful assistant responding to voice commands managing someone's clipboard."},
            {"role": "user", "content": prompt}
        ],
    )

    response = chat_completion.choices[0].message.content
    print(f"Groq response: {response}")
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