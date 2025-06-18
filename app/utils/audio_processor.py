import os
import uuid
import boto3
from dotenv import load_dotenv
import openai  # ✅ use this, not OpenAI()


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio(filepath: str) -> str:
    try:
        with open(filepath, "rb") as audio_file:
            transcript_response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript_response.strip()
    except Exception as e:
        return f"[Transcription Error: {e}]"


def synthesize_voice(text: str, gender: str = "male", output_folder="audio") -> str:
    # Load AWS credentials from .env
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Select voice by gender
    voice_map = {
        "male": "Matthew",   # High-quality US male voice
        "female": "Joanna"   # High-quality US female voice
    }
    selected_voice = voice_map.get(gender.lower(), "Matthew")

    # Set up Polly client
    polly = boto3.client(
        "polly",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )

    # Generate output path
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(output_folder, filename)

    # Request speech synthesis
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=selected_voice,
        Engine="neural"  # for high-quality voice
    )

    # Save audio stream to file
    with open(file_path, "wb") as f:
        f.write(response["AudioStream"].read())

    return file_path
