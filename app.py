"""
AI Reading Assistant: Chapter Extraction and Conversion API

This FastAPI service receives a PDF file upload, extracts the text of a sample chapter
(for demo: pages 1-3), and converts the extracted text to an audio MP3 using Google's
gTTS (Google Text-to-Speech) API. Returns metadata and the audio file name for playback.

Dependencies:
- FastAPI for API server
- PyPDF2 for PDF text extraction
- gTTS for text-to-speech conversion

Run locally with:
    uvicorn app:app --reload --host 0.0.0.0 --port 8000

Test with:
    curl -X POST "http://localhost:8000/upload_book/" -F "file=@sample.pdf"
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader     # Extract text from PDFs
from gtts import gTTS            # Convert text to speech
import os
import shutil

app = FastAPI(title="AI Reading Assistant: Runtime File Upload")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload_book/")
async def upload_book(file: UploadFile = File(...)):
    """
    Receive a PDF file at runtime, save it temporarily,
    extract first 3 pages text, convert to speech,
    and return the audio filename.

    Args:
        file (UploadFile): PDF file uploaded by user.

    Returns:
        JSON with success message and audio file path.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save uploaded file temporarily
    temp_pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text from first 3 pages
    try:
        reader = PdfReader(temp_pdf_path)
        chapter_text = ""
        total_pages = len(reader.pages)
        for i in range(min(1, total_pages)):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                chapter_text += text + "\n"
        if not chapter_text.strip():
            raise Exception("No extractable text found in PDF pages.")
    except Exception as e:
        os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {str(e)}")

    # Convert text to speech (gTTS) and save audio file
    audio_filename = f"{os.path.splitext(file.filename)[0]}_chapter1.mp3"
    audio_filepath = os.path.join(UPLOAD_DIR, audio_filename)
    try:
        tts = gTTS(chapter_text, lang="en")
        tts.save(audio_filepath)
    except Exception as e:
        os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"TTS conversion error: {str(e)}")

    # Clean up PDF file after processing
    os.remove(temp_pdf_path)

    return JSONResponse(
        content={
            "message": "Chapter extracted and audio generated successfully.",
            "audio_file": audio_filename,
        }
    )

@app.get("/")
async def root():
    return {"message": "AI Reading Assistant backend is running"}
