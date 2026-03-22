import os
import tempfile

from openai import OpenAI

from .video_extractor import download_audio


def transcribe_video(url: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = download_audio(url, tmpdir)

        with open(audio_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

    return result.text