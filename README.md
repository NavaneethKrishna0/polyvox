# Polyvox: AI PDF-to-Audio Converter

A full-stack, asynchronous web application that converts PDF documents into multi-language audio, complete with AI summarization, OCR for scanned files, and an interactive audio player.



## 🌟 Key Features

* **Secure User Authentication:** Full signup, login, and session management using JWT.
* **Asynchronous Processing:** Uses **Celery** and **Redis** for a non-blocking UI, handling long-running audio generation in the background.
* **AI Summarization:** Integrates **Hugging Face Transformers** to provide concise summaries of long documents.
* **OCR for Scanned PDFs:** Uses **Tesseract** to extract text from image-based PDFs, making all documents accessible.
* **Multi-Language Audio:** Generates audio in various languages (English, Spanish, Hindi, etc.) using `gTTS`.
* **Interactive Player:** A custom player that highlights text chunks in sync with the audio, using timestamps calculated with `pydub` silence detection.
* **Full Job Management:** Users can view a dashboard of their job history and delete jobs (which also cleans up stored files).

## 🛠️ Tech Stack & Architecture

This project uses a modern, decoupled architecture.



* **Frontend:** React (Next.js), TypeScript, Tailwind CSS
* **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
* **Database:** PostgreSQL (managed by Supabase)
* **Task Queue:** Celery, Redis
* **AI / Data Processing:** Hugging Face Transformers, Tesseract (OCR), PyMuPDF, pydub
* **Authentication:** JWT (passlib, python-jose)

## Running Locally

### Prerequisites

* Python 3.11
* Node.js & npm
* PostgreSQL (Supabase)
* Redis (via Docker: `docker-compose up -d`)
* Tesseract OCR Engine (System install)
* FFmpeg (System install, for `pydub`)

### 1. Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create and activate virtual environment (using Python 3.11)
python -m venv venv
source venv/bin/activate  # (or .\venv\Scripts\activate on Windows)

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add your DB_URL, SUPABASE_KEY, etc.
cp .env.example .env 
# (You should create a .env.example file)

# Start the API server
uvicorn main:app --reload --reload-exclude venv