import os
import uuid
import boto3
from dotenv import load_dotenv
from faster_whisper import WhisperModel


load_dotenv()

# Load Whisper model (tiny/intended for CPU in Hugging Face Spaces)
whisper_model = WhisperModel("tiny", compute_type="int8")

def transcribe_audio(filepath: str) -> str:
    """
        Transcribes speech from the given audio file using Whisper.
        Returns the full transcription string.
    """
    try:
        segments, _ = whisper_model.transcribe(filepath)
        transcript = " ".join(segment.text for segment in segments)
        return transcript.strip()
    except Exception as e:
        return f"[Transcription Error: {e}]"

# ------------------- Text-to-Speech with AWS Polly -------------------
def synthesize_voice(text: str, gender: str = "male", output_folder="audio") -> str:
    """
        Synthesizes voice from text using AWS Polly and saves to the specified folder.
        Returns the full file path of the generated audio.
    """
    # Load AWS credentials from .env
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if not all([aws_access_key, aws_secret_key]):
        raise EnvironmentError("AWS credentials not set in environment.")

    # Select voice by gender
    voice_map = {
        "male": "Matthew",   # High-quality US male voice
        "female": "Joanna"   # High-quality US female voice
    }
    selected_voice = voice_map.get(gender.lower(), "Matthew")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(output_folder, filename)

    # Set up Polly client
    polly = boto3.client(
        "polly",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )

    try:
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=selected_voice,
            Engine="neural"
        )
        with open(file_path, "wb") as f:
            f.write(response["AudioStream"].read())
    except Exception as e:
        raise RuntimeError(f"Polly synthesis failed: {e}")

    return file_path
