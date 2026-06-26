from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

audio_path = "/Users/rohankrishnan/Coding/clipping_bot/chunks/chunk_000.mp3"
output_path = "/Users/rohankrishnan/Coding/clipping_bot/transcript.json"

with open(audio_path, "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        timestamp_granularities=["segment"]
    )

data = transcript.model_dump()

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Saved transcript to {output_path}")