import collections
import queue
import threading
import time
import wave
import io
import numpy as np
import sounddevice as sd
import webrtcvad

# ---------- Config ----------
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
VAD_MODE = 2  # Less aggressive mode (0=least aggressive, 3=most aggressive)
START_CONSECUTIVE = 3  # 90ms to start speech detection (3 * 30ms)
END_CONSECUTIVE = 10   # 900ms of silence before ending speech (30 * 30ms)
DEVICE = None
BLOCK_SIZE = 1024
# ----------------------------

BYTES_PER_SAMPLE = 2
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
FRAME_BYTES = FRAME_SIZE * BYTES_PER_SAMPLE


class VADStream:
    def __init__(self, on_speech_start=None, on_speech_end=None):
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

        self.q = queue.Queue()
        self.running = False

        self._speech = False
        self._start_counter = 0
        self._end_counter = 0

        self._segment = bytearray()   # holds PCM16 data for current utterance

    def audio_callback(self, indata, frames, time_info, status):
        if indata.ndim > 1:
            mono = np.mean(indata, axis=1)
        else:
            mono = indata
        pcm16 = (mono * 32767.0).astype(np.int16).tobytes()
        self.q.put(pcm16)

    def start(self):
        self.running = True
        self.proc_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.proc_thread.start()

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype='float32',
            channels=1,
            device=DEVICE,
            callback=self.audio_callback
        )
        self.stream.start()
        print("VAD stream started — listening...")

    def stop(self):
        self.running = False
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        while not self.q.empty():
            self.q.get_nowait()

    def _pcm_to_wav_bytes(self, pcm_bytes):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    def _process_frame(self, frame_bytes):
        is_speech = self.vad.is_speech(frame_bytes, SAMPLE_RATE)

        if is_speech:
            self._start_counter += 1
            self._end_counter = 0
        else:
            self._end_counter += 1
            self._start_counter = 0

        # speech start
        if (not self._speech) and (self._start_counter >= START_CONSECUTIVE):
            self._speech = True
            self._start_counter = 0
            self._segment.clear()
            if callable(self.on_speech_start):
                self.on_speech_start()

        # accumulate speech segment if active
        if self._speech:
            self._segment.extend(frame_bytes)

        # speech end
        if self._speech and (self._end_counter >= END_CONSECUTIVE):
            self._speech = False
            self._end_counter = 0
            wav_bytes = self._pcm_to_wav_bytes(self._segment)
            duration = len(self._segment) / (SAMPLE_RATE * BYTES_PER_SAMPLE)
            if callable(self.on_speech_end):
                self.on_speech_end(wav_bytes, duration)

    def _processing_loop(self):
        buffer = bytearray()
        while self.running:
            try:
                chunk = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            buffer.extend(chunk)
            while len(buffer) >= FRAME_BYTES:
                frame = bytes(buffer[:FRAME_BYTES])
                del buffer[:FRAME_BYTES]
                self._process_frame(frame)


# ---------------- Example usage ----------------

def example():
    def on_start():
        print("[EVENT] Speech START")

    def on_end(wav_bytes, duration):
        print(f"[EVENT] Speech END, duration={duration:.2f}s, wav_size={len(wav_bytes)} bytes")
        # Example: save each utterance to file
        fname = f"segment_{int(time.time())}.wav"
        with open(fname, "wb") as f:
            f.write(wav_bytes)
        print(f"Saved {fname}")

    vad = VADStream(on_speech_start=on_start, on_speech_end=on_end)
    vad.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        vad.stop()


if __name__ == "__main__":
    example()