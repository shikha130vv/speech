import pyaudio
import numpy as np

class Player:
    def __init__(self):
        self.sample_rate = None
        self.audio_stream = None

    def init(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.audio_context = pyaudio.PyAudio()
        self.audio_stream = self.audio_context.open(format=pyaudio.paInt16,
                                                    channels=1,
                                                    rate=self.sample_rate,
                                                    output=True)

    def play(self, buffer: np.ndarray):
        if self.audio_stream:
            audio_data = buffer.tobytes()
            self.audio_stream.write(audio_data)

    def clear(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.audio_context:
            self.audio_context.terminate()
