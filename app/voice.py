import struct
import pvporcupine
import sounddevice as sd
import os
from dotenv import load_dotenv
import speech_recognition as sr
import time
import threading

# Create a Porcupine wake word detector
# porcupine = pvporcupine.create(keywords=["porcupine"])

# # Path to your custom wake word model (.ppn file)
# WAKEWORD_PATH = "my_custom_kiwi.ppn"
load_dotenv()
ACCESS_KEY = os.getenv("ACCESS_KEY")
# # # Initialize Porcupine with the custom wake word
tango = pvporcupine.create(
    access_key=ACCESS_KEY, keyword_paths=["./assets/Tango_en_mac_v3_0_0.ppn"]
)


class SpeechProcessor(threading.Thread):
    def __init__(self, recognizer, callback=None):
        super().__init__(daemon=True)
        self.recognizer = recognizer
        self.callback = callback
        self._stop_event = threading.Event()

    def run(self):
        try:
            # Give time for wake word stream to settle
            time.sleep(0.2)

            with sr.Microphone() as source:
                print("Listening for speech for 5 seconds...")
                # Shorter ambient noise adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                # Increased timeout and phrase limit
                audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=7)

                print("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")

                if self.callback:
                    self.callback(text)

        except sr.WaitTimeoutError:
            print("No speech detected within timeout period")
        except sr.UnknownValueError:
            print("Could not understand the speech")
        except sr.RequestError as e:
            print(f"Error with speech recognition service: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


class VoiceRecognitionManager:
    def __init__(self):
        self.tango = pvporcupine.create(
            access_key=ACCESS_KEY, keyword_paths=["Tango_en_mac_v3_0_0.ppn"]
        )
        self.waiting_to_tango = True
        self.running = False
        self.recognizer = sr.Recognizer()
        self.speech_thread = None
        self._setup_recognizer()

    def _setup_recognizer(self):
        # More sensitive settings
        self.recognizer.energy_threshold = 200
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def on_speech_recognized(self, text):
        """Override this method to handle recognized speech"""
        pass

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)

        if not self.waiting_to_tango:
            return

        pcm = struct.unpack_from("h" * self.tango.frame_length, indata)
        result = self.tango.process(pcm)

        if result >= 0:
            print("Wake word 'tango' detected!")
            self.waiting_to_tango = False

            # Start speech processing in separate thread
            self.speech_thread = SpeechProcessor(
                self.recognizer, self.on_speech_recognized
            )
            self.speech_thread.start()

            # Re-enable wake word detection after speech processing
            threading.Timer(8.0, self._reset_tango_listening).start()

    def _reset_tango_listening(self):
        """Reset to listening for wake word"""
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=1.0)

        self.waiting_to_tango = True
        print("Resuming listening for 'tango'...")

    def start(self):
        self.running = True

        with sd.RawInputStream(
            samplerate=self.tango.sample_rate,
            blocksize=self.tango.frame_length,
            dtype="int16",
            channels=1,
            callback=self.audio_callback,
        ):
            print("Listening for 'tango'... Press Ctrl+C to stop.")
            try:
                while self.running:
                    sd.sleep(1000)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        self.running = False
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=1.0)
        self.tango.delete()
        print("Voice recognition stopped.")


if __name__ == "__main__":
    voice_manager = VoiceRecognitionManager()
    voice_manager.start()
