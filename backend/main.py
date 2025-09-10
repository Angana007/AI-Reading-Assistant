import os
from dotenv import load_dotenv
import uuid
import textwrap
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from PyPDF2 import PdfReader
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread

# ------------------- Setup -------------------
app = FastAPI(title="AI Reading Assistant")

# Load .env file
load_dotenv()

# Ensure API key is read from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

client = OpenAI(api_key=api_key)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Enable CORS for React frontend
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Progress Tracking -------------------
# Store progress {job_id: percentage}
progress_dict = {}

def generate_audio(pdf_path, audio_path, voice, job_id):
    """Background function to generate TTS audio and update progress"""
    try:
        reader = PdfReader(pdf_path)
        text = "".join([p.extract_text() + "\n" for p in reader.pages if p.extract_text()])

        if not text.strip():
            progress_dict[job_id] = -1  # Error
            return

        chunks = textwrap.wrap(text, 4000)
        total_chunks = len(chunks)

        with open(audio_path, "wb") as f_out:
            for i, chunk in enumerate(chunks, start=1):
                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice=voice,
                    input=chunk,
                )
                f_out.write(response.read())
                # Update progress percentage
                progress_dict[job_id] = int((i / total_chunks) * 100)

        progress_dict[job_id] = 100  # Done
    except Exception as e:
        print(f"Error generating audio for job {job_id}: {e}")
        progress_dict[job_id] = -1  # Error

# ------------------- Endpoints -------------------

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...), voice: str = "ash"):
    """
    Upload a PDF and generate TTS audio asynchronously.
    Returns: job_id to track progress, audio_url for download/playback
    """
    # Save uploaded PDF
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # Generate unique audio filename
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")

    # Initialize progress
    progress_dict[audio_id] = 0

    # Start TTS generation in background
    thread = Thread(target=generate_audio, args=(pdf_path, audio_path, voice, audio_id))
    thread.start()

    return {"job_id": audio_id, "audio_url": f"/audio/{audio_id}"}


@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Return progress of TTS generation for a given job_id"""
    progress = progress_dict.get(job_id)
    if progress is None:
        return JSONResponse({"error": "Invalid job ID"}, status_code=404)
    return {"progress": progress}


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Retrieve generated audio by ID"""
    audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")
    if os.path.exists(audio_path):
        return FileResponse(audio_path, media_type="audio/mpeg")
    return {"error": "Audio not found"}
