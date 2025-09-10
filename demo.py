from PyPDF2 import PdfReader
from openai import OpenAI
import os
import time
import platform
import textwrap
from pydub import AudioSegment
from dotenv import load_dotenv
load_dotenv()  # This will read .env file
api_key = os.getenv("OPENAI_API_KEY")
# ---------- Configuration ----------
PDF_FILE = "1754186355.pdf"
OUTPUT_AUDIO = "output.mp3"
CHUNK_SIZE = 3000
MODEL = "gpt-4o-mini-tts"
# ----------------------------------

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("Please set your OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

voices = ["ash", "alloy", "verse", "sage"]

print("\nAvailable voices:")
for i, v in enumerate(voices, 1):
    print(f"{i}. {v}")
print("Default: 1 (ash, clear & precise)")
choice = input("Choose a voice number (press Enter to choose Ash): ").strip()

try:
    idx = int(choice) - 1
    if idx not in range(len(voices)):
        raise ValueError
    VOICE = voices[idx]
except:
    VOICE = "ash"

print(f"\nUsing voice: {VOICE}\n")

if not os.path.exists(PDF_FILE):
    raise FileNotFoundError(f"{PDF_FILE} not found in the current directory.")

reader = PdfReader(PDF_FILE)
text = "".join(page.extract_text() + "\n" for page in reader.pages if page.extract_text())

if not text.strip():
    raise ValueError("No text could be extracted from the PDF.")

chunks = textwrap.wrap(text, CHUNK_SIZE)
print(f"Generating audio in {len(chunks)} chunks...")

temp_files = []
for i, chunk in enumerate(chunks, 1):
    temp = f"chunk_{i}.mp3"
    with open(temp, "wb") as f:
        response = client.audio.speech.create(model=MODEL, voice=VOICE, input=chunk)
        f.write(response.content)
    temp_files.append(temp)
    print(f"Chunk {i}/{len(chunks)} done.")

print("Merging audio chunks...")
final = AudioSegment.empty()
for file in temp_files:
    final += AudioSegment.from_mp3(file)
final.export(OUTPUT_AUDIO, format="mp3")

for f in temp_files:
    os.remove(f)

print(f"Audio generation complete: {OUTPUT_AUDIO}")

def play_audio(path):
    os_name = platform.system()
    try:
        if os_name == "Windows":
            os.startfile(path)
        elif os_name == "Darwin":
            os.system(f"afplay \"{path}\"")
        else:
            if os.system("command -v mpg123 > /dev/null") == 0:
                os.system(f"mpg123 \"{path}\"")
            else:
                os.system(f"xdg-open \"{path}\"")
    except Exception as e:
        print("Could not auto-play audio. Please open manually.")
        print(e)

time.sleep(1)
play_audio(OUTPUT_AUDIO)
