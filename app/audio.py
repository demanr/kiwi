import os
import tempfile
import threading
from dotenv import load_dotenv
from groq import Groq
from vad import VADStream

load_dotenv()

class HotwordListener:
    """Listens for a specified hotword using VAD and invokes a callback using Groq transcription."""
    def __init__(self, keyword, callback):
        self.keyword = keyword.lower()
        self.callback = callback
        # Initialize Groq client
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Initialize VAD stream
        self.vad_stream = None

    def _on_speech_end(self, wav_bytes, duration):
        """Called when VAD detects end of speech."""
        print(f"Speech detected, duration: {duration:.2f}s")
        
        # Only transcribe audio longer than 1 second
        if duration > 1.0:
            try:
                # Create a temporary file for Groq API
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(wav_bytes)
                    tmp_file.flush()
                    
                    with open(tmp_file.name, "rb") as file:
                        transcription = self.groq_client.audio.transcriptions.create(
                            file=(tmp_file.name, file.read()),
                            model="whisper-large-v3",
                        )
                        text = transcription.text
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
                print(f"Groq heard: {text}")
                if self.keyword in text.lower():
                    self.callback(text, wav_bytes)
            except Exception as e:
                print(f"Error during transcription/detection: {e}")
        else:
            print(f"Audio too short ({duration:.2f}s), skipping transcription")

    def start(self, background=False):
        """Begin listening loop. Use background=True to run in a daemon thread."""
        print("Listening for hotword...")
        
        def _on_speech_start():
            print("Speech started...")
        
        self.vad_stream = VADStream(
            on_speech_start=_on_speech_start,
            on_speech_end=self._on_speech_end
        )
        
        if background:
            threading.Thread(target=self._run, daemon=True).start()
        else:
            self._run()

    def _run(self):
        """Main listening loop."""
        self.vad_stream.start()
        try:
            # Keep the main thread alive while VAD runs
            import time
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the listening loop."""
        if self.vad_stream:
            self.vad_stream.stop()

# Example usage:
if __name__ == "__main__":
    def demo(text, audio):
        print(f"Detected hotword in: {text}")

    listener = HotwordListener("tango", demo)
    listener.start()

