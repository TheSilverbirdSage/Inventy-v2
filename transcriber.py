import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class Transcriber:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1/"
        )

    def transcribe(self, file_path):
        """Transcribes an audio file to text using Groq's Whisper implementation."""
        with open(file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )
        return transcript.text
