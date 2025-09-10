import os
import uuid
import textwrap
import logging
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from PyPDF2 import PdfReader
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware

# ---------------- Setup logger ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
)

# ---------------- Setup FastAPI ----------------
app = FastAPI(title="AI Reading Assistant")

# Load environment variables with your preferred method before running
from dotenv import load_dotenv
load_dotenv()

# Read OpenAI API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

client = OpenAI(api_key=api_key)

# Directories
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Enable CORS for frontend (adjust origin as needed)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for all origins (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Progress Tracking ----------------
progress_dict = {}  # job_id: progress percentage


def generate_audio(pdf_path: str, audio_path: str, voice: str, job_id: str):
    """Background task to generate TTS audio from PDF text with detailed debugging."""
    try:
        logging.info(f"Job {job_id}: Starting audio generation with voice '{voice}'")

        # Extract text from PDF pages
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            else:
                logging.warning(f"Job {job_id}: No text extracted from page {i}")

        if not text.strip():
            logging.error(f"Job {job_id}: No extractable text found in PDF")
            progress_dict[job_id] = -1
            return

        logging.debug(f"Job {job_id}: Extracted text length {len(text)} characters")

        # Chunk text for TTS API requests (approx 4000 chars each)
        chunks = textwrap.wrap(text, 4000)
        total_chunks = len(chunks)
        logging.info(f"Job {job_id}: Splitting text into {total_chunks} chunks")

        # Generate audio file by writing streamed chunks to output file
        with open(audio_path, "wb") as f_out:
            for i, chunk in enumerate(chunks, start=1):
                logging.debug(f"Job {job_id}: Sending chunk {i}/{total_chunks} to TTS API")
                response = client.audio.speech.create(
                    model="tts-1",  # Verify your actual model name here
                    voice=voice,
                    input=chunk,
                )
                audio_data = response.read()
                f_out.write(audio_data)

                current_progress = int((i / total_chunks) * 100)
                progress_dict[job_id] = current_progress
                logging.debug(f"Job {job_id}: Chunk {i} processed, progress {current_progress}%")

        progress_dict[job_id] = 100
        logging.info(f"Job {job_id}: Audio generation completed successfully")

    except Exception as e:
        logging.error(f"Job {job_id}: Error during audio generation: {e}")
        progress_dict[job_id] = -1


# ---------------- Endpoint definitions ----------------

@app.post("/upload/")
async def upload_pdf(
    file: UploadFile = File(...),
    voice: str = "ash",
    background_tasks: BackgroundTasks = None,
):
    """
    Accept PDF upload, initiate background TTS audio generation.
    Return job_id for polling progress and audio_url retrieval.
    """
    # Save uploaded PDF file
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    logging.info(f"Received PDF {file.filename} saved to {pdf_path}")

    # Generate unique audio file path
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")

    # Initialize job progress
    progress_dict[audio_id] = 0

    # Add background task for audio generation
    background_tasks.add_task(generate_audio, pdf_path, audio_path, voice, audio_id)

    return {"job_id": audio_id, "audio_url": f"/audio/{audio_id}"}


@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Provide progress percentage or error status for a job ID."""
    progress = progress_dict.get(job_id)
    if progress is None:
        logging.warning(f"Invalid progress query for job_id: {job_id}")
        return JSONResponse({"error": "Invalid job ID"}, status_code=404)
    return {"progress": progress}


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve generated audio file by audio ID."""
    audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")
    if os.path.exists(audio_path):
        logging.info(f"Serving audio file for job {audio_id}")
        return FileResponse(audio_path, media_type="audio/mpeg")
    logging.warning(f"Audio file not found for job {audio_id}")
    return JSONResponse({"error": "Audio not found"}, status_code=404)


@app.get("/")
async def root():
    """Basic root endpoint to verify service is running."""
    return {"message": "AI Reading Assistant backend running"}

