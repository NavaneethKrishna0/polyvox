# backend/celery_worker.py
from celery import Celery
import os
import fitz # PyMuPDF
from deep_translator import GoogleTranslator
from gtts import gTTS
from database import SessionLocal
import crud
from transformers import pipeline
import json
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

# --- NEW: OCR Imports ---
import pytesseract
from PIL import Image # Pillow library for image handling
import io # To handle image bytes
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load summarization pipeline
print("Loading summarization model...")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
print("Summarization model loaded.")

# Define directories & Redis URL
UPLOADS_DIR = "uploads"
AUDIO_DIR = "audio_outputs"
REDIS_URL = "redis://localhost:6379/0"

# Create Celery app instance
celery = Celery(
    __name__,
    broker=REDIS_URL,
    backend=REDIS_URL
)

# --- (calculate_timestamps function remains the same) ---
def calculate_timestamps(audio_path, text, min_silence_len=500, silence_thresh=-40):
    # ... (Keep the existing timestamp calculation logic here) ...
    try:
        audio = AudioSegment.from_mp3(audio_path)
        audio_duration_ms = len(audio)
        nonsilent_ranges = detect_nonsilent(
            audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
        )
        if not nonsilent_ranges: # Handle only silence case
            words = text.split()
            word_count = len(words)
            if word_count == 0: return []
            time_per_word = audio_duration_ms / word_count
            timestamps = [{"word": word, "start": (i * time_per_word) / 1000.0, "end": ((i + 1) * time_per_word) / 1000.0} for i, word in enumerate(words)]
            return timestamps # Return simplified timestamps directly here

        speech_duration_ms = sum(end - start for start, end in nonsilent_ranges)
        total_chars = len(text)
        if total_chars == 0 or speech_duration_ms == 0: return []
        time_per_char = speech_duration_ms / total_chars
        timestamps = []
        current_char_index = 0
        start_offset_ms = nonsilent_ranges[0][0]
        words = text.split()
        for word in words:
            word_len = len(word) + 1
            estimated_start_speech_ms = current_char_index * time_per_char
            estimated_end_speech_ms = (current_char_index + word_len) * time_per_char
            absolute_start_ms = start_offset_ms
            absolute_end_ms = start_offset_ms
            temp_speech_time = 0
            for i, (start, end) in enumerate(nonsilent_ranges):
                 segment_duration = end - start
                 if estimated_start_speech_ms < temp_speech_time + segment_duration:
                      offset_in_segment = estimated_start_speech_ms - temp_speech_time
                      absolute_start_ms = start + offset_in_segment
                      if estimated_end_speech_ms <= temp_speech_time + segment_duration:
                          end_offset_in_segment = estimated_end_speech_ms - temp_speech_time
                          absolute_end_ms = start + end_offset_in_segment
                      else:
                          absolute_end_ms = end
                      break
                 temp_speech_time += segment_duration
                 if i + 1 < len(nonsilent_ranges):
                      silence_duration = nonsilent_ranges[i+1][0] - end
                      start_offset_ms += segment_duration + silence_duration # Update the overall offset

            timestamps.append({"word": word, "start": absolute_start_ms / 1000.0, "end": absolute_end_ms / 1000.0})
            current_char_index += word_len

        # Simple chunking logic
        chunked_timestamps = []
        chunk_size = 5
        current_chunk = []
        for i, ts in enumerate(timestamps):
            current_chunk.append(ts)
            if (i + 1) % chunk_size == 0 or i == len(timestamps) - 1:
                chunk_text = " ".join([c["word"] for c in current_chunk])
                chunk_start = current_chunk[0]["start"]
                chunk_end = current_chunk[-1]["end"]
                chunked_timestamps.append({"chunk": chunk_text, "start": chunk_start, "end": chunk_end})
                current_chunk = []
        return chunked_timestamps
    except Exception as e:
        print(f"Error calculating timestamps: {e}")
        return []


@celery.task
def process_pdf_task(pdf_path: str, original_filename: str, target_lang: str, job_id: int, summarize: bool):
    """
    Background task using gTTS, summarization, and OCR.
    """
    db = SessionLocal()
    timestamps_json = None
    extracted_text = "" # Initialize extracted_text

    try:
        # --- MODIFIED: Step 1: Attempt Text Extraction, then OCR if needed ---
        print(f"Job {job_id}: Opening PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        
        # Try extracting embedded text first
        embedded_text = "".join(page.get_text("text") for page in doc) # Use "text" for plain text
        
        # Check if extracted text is substantial (adjust threshold as needed)
        if len(embedded_text.strip()) > 100: # Arbitrary threshold, maybe 100 characters?
             print(f"Job {job_id}: Found substantial embedded text.")
             extracted_text = embedded_text
        else:
             print(f"Job {job_id}: No substantial embedded text found. Attempting OCR...")
             ocr_text_parts = []
             # Iterate through pages, render as images, and OCR
             for page_num in range(len(doc)):
                 page = doc.load_page(page_num)
                 # Render page to an image (pixmap) - higher DPI for better OCR
                 pix = page.get_pixmap(dpi=300)
                 img_bytes = pix.tobytes("png") # Get image bytes
                 img = Image.open(io.BytesIO(img_bytes)) # Open image with Pillow

                 # Perform OCR on the image
                 try:
                      page_text = pytesseract.image_to_string(img)
                      ocr_text_parts.append(page_text)
                      print(f"Job {job_id}: OCR processed page {page_num + 1}/{len(doc)}")
                 except pytesseract.TesseractNotFoundError:
                      raise RuntimeError("Tesseract is not installed or not in PATH.")
                 except Exception as ocr_err:
                      print(f"Job {job_id}: OCR failed on page {page_num + 1}: {ocr_err}")
                      # Continue to next page or handle error appropriately

             extracted_text = "\n".join(ocr_text_parts)
             if not extracted_text.strip():
                 raise ValueError("OCR failed to extract any text from the PDF images.")
             print(f"Job {job_id}: OCR completed.")

        doc.close() # Close the PDF document

        # Now use 'extracted_text' for the rest of the process
        if not extracted_text.strip():
            raise ValueError("No text could be extracted from the PDF.")

        text_to_process = extracted_text
        text_for_db = extracted_text[:1000]

        # Step 2: AI Summarization (if requested)
        if summarize:
            print(f"Job {job_id}: Summarizing text...")
            summary_input = text_to_process[:10000] # Use extracted text
            summary_result = summarizer(summary_input, max_length=250, min_length=50, do_sample=False)
            text_to_process = summary_result[0]['summary_text']
            text_for_db = text_to_process
            print(f"Job {job_id}: Summarization complete.")

        # Step 3: Translation
        print(f"Job {job_id}: Translating text...")
        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text_to_process)
        if not translated_text: raise ValueError("Translation failed.")
        if target_lang != 'en' or summarize: text_for_db = translated_text[:1000]

        # Step 4: Generate Audio with gTTS
        print(f"Job {job_id}: Generating audio with gTTS...")
        tts = gTTS(translated_text, lang=target_lang)
        audio_filename = f"{os.path.splitext(original_filename)[0]}_{target_lang}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        tts.save(audio_path)
        print(f"Job {job_id}: Audio saved to {audio_path}")

        # Step 5: Calculate Timestamps
        print(f"Job {job_id}: Calculating timestamps...")
        timestamp_data = calculate_timestamps(audio_path, translated_text)
        timestamps_json = json.dumps(timestamp_data)
        print(f"Job {job_id}: Timestamps calculated.")

        # Step 6: Update database
        crud.update_job_status(
            db, job_id=job_id, status="SUCCESS", audio_filename=audio_filename,
            result_text=text_for_db, timestamps_json=timestamps_json
        )
        return {"status": "SUCCESS", "audio_filename": audio_filename}

    except Exception as e:
        # ... (Error handling remains the same) ...
        print(f"Job {job_id}: FAILED with error: {e}")
        import traceback
        print(traceback.format_exc())
        crud.update_job_status(db, job_id=job_id, status="FAILURE", result_text=f"Error: {str(e)}")
        return {"status": "FAILURE", "error": str(e)}
    finally:
        db.close()