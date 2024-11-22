import os
import time
import sounddevice as sd
import numpy as np
import azure.cognitiveservices.speech as speechsdk
import wave

monitoring = True
human_speaking = False
human_text = ""
text = []
last_speech_time = time.time()

from dotenv import load_dotenv
load_dotenv(override=True)
speech_ep = os.getenv('SPEECH_EP')
speech_key = os.getenv('SPEECH_KEY')
speech_region = os.getenv('SPEECH_REGION')

def get_human_resp_text_audio(lang, wav_file, update_callback=None):
    global text, monitoring, last_speech_time
    if update_callback:
        print("callback found")
    else:
        print("no callback")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    monitoring = True
    last_speech_time = time.time()
    # Setup the audio stream
    stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=stream)

    # Instantiate the speech recognizer with push stream input
    speech_recognizer = speechsdk.SpeechRecognizer(language=lang, speech_config=speech_config, audio_config=audio_config)

    def handle_recognizing(evt):
        global human_speaking, last_speech_time
        human_speaking = True
        last_speech_time = time.time()  # Reset the timer
        print(human_speaking, evt.result.text)
        try:
            if update_callback:
                update_callback(evt.result.text)
                print("Calling updating callback with ", evt.result.text)
        except Exception as e:
            print(e)

    def handle_recognized(evt):
        global human_speaking, text, last_speech_time, monitoring
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text.append(evt.result.text)
            
            try:
                if update_callback:
                    update_callback(' '.join(text))
                    print("Calling update callback with ", evt.result.text)
            except Exception as e:
                print(e)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print('NOMATCH: Speech could not be recognized.')
        
        # Stop monitoring after recognition
        human_speaking = False
        monitoring = False
        print(f"Recognized: {human_speaking} {evt.result.text}")

    def handle_canceled(evt):
        print('CANCELED: {}'.format(evt))
        if evt.reason == speechsdk.CancellationReason.Error:
            print('CANCELED: Error details - {}'.format(evt.error_details))
        speech_recognizer.stop_continuous_recognition()
        monitoring = False

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognizing.connect(handle_recognizing)
    speech_recognizer.recognized.connect(handle_recognized)
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED: {}'.format(evt)))
    speech_recognizer.canceled.connect(handle_canceled)

    # Function to detect if the user starts speaking
    def detect_speech(indata, frames, time1, status):
        global human_speaking, last_speech_time
        volume_norm = np.linalg.norm(indata) * 10
        print(volume_norm)
        if volume_norm > 10000:  # Threshold for detecting speech
            print("Speech detected, starting transcription...")
            sd.stop()
            human_speaking = True
            last_speech_time = time.time()  # Reset the timer
            start_transcription()

    # Function to start the transcription process
    def start_transcription():
        global monitoring, last_speech_time
        last_speech_time = time.time()  # Reset the timer
        # Start continuous speech recognition
        speech_recognizer.start_continuous_recognition()

        
        wf = wave.open(wav_file, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # Callback function to push audio data to the stream
        def audio_callback(indata, frames, time1, status):
            if status:
                print(status)
            stream.write(indata.tobytes())
            wf.writeframes(indata.tobytes())
            
        # Start recording from the microphone
        try:
            with sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=audio_callback):
                print("Recording... Press Ctrl+C to stop.")
                while monitoring:
                    if time.time() - last_speech_time > 3:
                        print("No speech detected for 3 seconds, stopping transcription.")
                        monitoring = False
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("Recording stopped.")
        finally:
            # Stop recognition and clean up
            stream.close()
            speech_recognizer.stop_continuous_recognition()

    # Monitor the microphone input to detect speech
    try:
        with sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=detect_speech):
            print("Monitoring microphone... Start speaking to begin transcription.")
            while monitoring:
                if time.time() - last_speech_time > 5 and not human_speaking:
                    print("No speech detected for 5 seconds, stopping monitoring.")
                    monitoring = False
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("Monitoring stopped.")

    return ' '.join(text)

# Example usage
# recognized_text = trans_with_streaming("en-US")
# print("Final recognized text:", recognized_text)