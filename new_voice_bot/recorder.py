import pyaudio
import numpy as np
import base64

class Recorder:
    def __init__(self, on_data_available):
        self.on_data_available = on_data_available
        self.audio_context = None
        self.stream = None

    def start(self):
        try:
            self.audio_context = pyaudio.PyAudio()
            self.stream = self.audio_context.open(format=pyaudio.paInt16,
                                                  channels=1,
                                                  rate=24000,
                                                  input=True,
                                                  frames_per_buffer=4096,
                                                  stream_callback=self._process_audio)
            self.stream.start_stream()
        except Exception as error:
            self.stop()

    def _process_audio(self, in_data, frame_count, time_info, status_flags):
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        buffer = np.array(audio_data, dtype=np.int16)
        base64data = base64.b64encode(buffer).decode('utf-8')
        self.on_data_available(base64data)
        return (None, pyaudio.paContinue)

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio_context:
            self.audio_context.terminate()
