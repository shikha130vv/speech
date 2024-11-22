import io
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment, silence
import simpleaudio as sa
import threading
import asyncio

import os

from openai import AzureOpenAI
import wave

from speech_demo_set_default_prompts import set_default_prompts_loan
from speech_demo_set_default_prompts import set_default_prompts_ecom 
from speech_demo_gen_avatars import gen_dalle_img
from speech_demo_get_conv_summary import get_summary

from speech_demo_human_response import human_speaking

import io
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment, silence
import simpleaudio as sa
import threading
import asyncio


from dotenv import load_dotenv
load_dotenv(override=True)

open_ai_endpoint = os.getenv("OPEN_AI_ENDPOINT")
open_ai_key = os.getenv("OPEN_AI_KEY")
open_ai_deployment_name = os.getenv("OPEN_AI_DEPLOYMENT_NAME")

speech_ep = os.getenv('SPEECH_EP')
speech_key = os.getenv('SPEECH_KEY')
speech_region = os.getenv('SPEECH_REGION')

api_version = "2024-02-15-preview"


def create_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=open_ai_key,  # key
        azure_endpoint=open_ai_endpoint,  # gpt4
        api_version=api_version,  # ver
    )

client = create_openai_client()


class PushAudioStreamWriter(speechsdk.audio.PushAudioOutputStreamCallback):
    def __init__(self):
        super().__init__()
        self.audio_buffer = io.BytesIO()
        self.lock = threading.Lock()

    def write(self, audio_buffer: memoryview) -> int:
        with self.lock:
            self.audio_buffer.write(audio_buffer.tobytes())
        return len(audio_buffer)

    def close(self):
        pass  # No action needed on close for buffering approach

    def get_audio_segment(self):
        with self.lock:
            self.audio_buffer.seek(0)
            audio_segment = AudioSegment.from_raw(self.audio_buffer, sample_width=2, frame_rate=16000, channels=1)
            self.audio_buffer = io.BytesIO()  # Reset buffer for the next chunk
        return audio_segment

    def remove_silence(self, audio_segment, silence_thresh=-40, min_silence_len=500, keep_silence=150):
        non_silent_ranges = silence.detect_nonsilent(audio_segment, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
        non_silent_audio = [audio_segment[start:end] for start, end in non_silent_ranges]
        combined_audio = AudioSegment.empty()
        for segment in non_silent_audio:
            combined_audio += segment + AudioSegment.silent(duration=keep_silence)
        return combined_audio

    def play_audio(self, audio_segment):
        play_obj = sa.play_buffer(audio_segment.raw_data, audio_segment.channels, audio_segment.sample_width, audio_segment.frame_rate)
        play_obj.wait_done()  # Ensure the audio finishes playing
        
        


final_segment = AudioSegment.empty()
async def text_to_speech_streaming(text, synthesizer, queue):
    loop = asyncio.get_event_loop()
    result_future = synthesizer.speak_text_async(text)
    result = await loop.run_in_executor(None, result_future.get)

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized for text [{text}]")
        audio_segment = stream_writer.get_audio_segment()
        audio_segment = stream_writer.remove_silence(audio_segment)  # Remove silence
        await queue.put(audio_segment)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")


stream_writer = PushAudioStreamWriter()
async def get_openai_resp_text_audio(agent_msgs, customer_msgs, language, blnAgent):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    if language == "English":
        speech_config.speech_synthesis_voice_name = 'en-US-JennyNeural'
    else:
        speech_config.speech_synthesis_voice_name = 'hi-IN-SwaraNeural'
    
    push_stream = speechsdk.audio.PushAudioOutputStream(stream_writer)
    audio_config = speechsdk.audio.AudioOutputConfig(stream=push_stream)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    global final_segment
    if blnAgent:
        message_text = agent_msgs
    else:
        message_text = customer_msgs
    #print(f"printing.....{message_text}")
    completion = client.chat.completions.create(
        model=open_ai_deployment_name,
        messages=message_text,
        temperature=0,
        max_tokens=200,
        top_p=0.95,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        stream=True
    )

    queue = asyncio.Queue()
    tasks = []
    text_buffer = ""
    
    
    async def process_queue():
        global final_segment
        combined_audio_segment = AudioSegment.empty()
        while True:
            audio_segment = await queue.get()
            if audio_segment is None:
                break
            combined_audio_segment += audio_segment
            final_segment += audio_segment
        stream_writer.play_audio(combined_audio_segment)

    processing_task = asyncio.create_task(process_queue())

    all_text = ""
    for event in completion:
        if human_speaking:
            break;
        if len(event.choices) > 0:
            for choice in event.choices:
                if choice.delta.content and len(choice.delta.content) > 0:
                    text_chunk = choice.delta.content
                    print(f"Received text chunk: {text_chunk}")
                    text_buffer += text_chunk
                    all_text += text_chunk
                    if any(p in text_chunk for p in ",;.!?"):  # Check for sentence-ending punctuation
                        task = text_to_speech_streaming(text_buffer.strip(), synthesizer, queue)
                        tasks.append(asyncio.create_task(task))
                        text_buffer = ""  # Reset buffer

     
    if not human_speaking and text_buffer.strip():  # Ensure any remaining text is processed
        task = text_to_speech_streaming(text_buffer.strip(), synthesizer, queue)
        tasks.append(asyncio.create_task(task))

    await asyncio.gather(*tasks)
    await queue.put(None)  # Signal the end of the queue
    await processing_task
    
    if blnAgent:
        agent_msgs.append({"role": "assistant", "content": all_text})
        customer_msgs.append({"role": "user", "content": all_text})
        
    else:
        customer_msgs.append({"role": "assistant", "content": all_text})
        agent_msgs.append({"role": "user", "content": all_text})


