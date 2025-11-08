# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from sqlalchemy.orm import Session
from pydantic import ValidationError

# Import our modules
import crud, models, auth
from schemas import Job as JobSchema # Import schema with alias
from database import SessionLocal, engine
import schemas # Keep original import for other schema uses if needed
from celery_worker import process_pdf_task, celery

# This creates the tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polyvox API")

# OAuth2 Scheme definition
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- DEFINE DIRECTORIES ---
UPLOADS_DIR = "uploads"
AUDIO_DIR = "audio_outputs"
# Create directories if they don't exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
# --- END DEFINE DIRECTORIES ---


# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get the current user from a token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = auth.get_current_user_email(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# User Registration Endpoint
@app.post("/users/", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# Restore response_model and use detailed conversion check
@app.get("/jobs/me", response_model=list[JobSchema])
def read_user_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    print(f"--- Fetching jobs for user_id: {current_user.id} ---")
    db_jobs: list[models.Job] = crud.get_user_jobs(db, user_id=current_user.id)
    print(f"--- Found {len(db_jobs)} jobs in the database. ---")

    # --- DETAILED CONVERSION LOOP ---
    successful_jobs = []
    failed_job_ids = []
    for job in db_jobs:
        try:
            # Try to convert this specific job
            pydantic_job = JobSchema.from_orm(job)
            successful_jobs.append(pydantic_job)
        except ValidationError as e:
            # If conversion fails for THIS job, log it
            print(f"!!! Pydantic Validation Error for Job ID {job.id}: {e} !!!")
            print(f"--- Raw Data for failed Job ID {job.id}:")
            # Print raw attributes of the SQLAlchemy object
            print(f"    id: {job.id}")
            print(f"    status: {repr(job.status)}")
            print(f"    pdf_filename: {repr(job.pdf_filename)}")
            print(f"    audio_filename: {repr(job.audio_filename)}")
            print(f"    result_text (type): {type(job.result_text)}")
            print(f"    timestamps_json (type): {type(job.timestamps_json)}")
            # Avoid printing potentially huge text fields directly unless needed
            failed_job_ids.append(job.id)
        except Exception as e:
            # Catch other potential errors during conversion
            print(f"!!! UNEXPECTED Error converting Job ID {job.id}: {e} !!!")
            failed_job_ids.append(job.id)

    if failed_job_ids:
        print(f"--- WARNING: Failed to convert Job IDs: {failed_job_ids} ---")
        # Decide how to handle partial failure:
        # Option 1: Return only successful jobs (might hide errors from user)
        # return successful_jobs
        # Option 2: Raise an error if any job fails conversion
        raise HTTPException(status_code=500, detail=f"Error processing data for Job IDs: {failed_job_ids}")

    print(f"--- Successfully converted {len(successful_jobs)} jobs to schema. ---")
    return successful_jobs

# PDF Processing Endpoint
@app.post("/process-pdf/")
async def create_processing_job(
    uploaded_file: UploadFile = File(...),
    target_lang: str = Form("es"),
    summarize: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    safe_filename = "".join(c if c.isalnum() or c in ['.', '-'] else '_' for c in uploaded_file.filename)
    pdf_path = os.path.join(UPLOADS_DIR, safe_filename)
    count = 1
    base, ext = os.path.splitext(pdf_path)
    while os.path.exists(pdf_path):
         pdf_path = f"{base}_{count}{ext}"
         count += 1
         safe_filename = os.path.basename(pdf_path)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    job_record = crud.create_user_job(
        db=db, user_id=current_user.id, pdf_filename=safe_filename
    )
    task_id = str(job_record.id)
    task = process_pdf_task.apply_async(
        args=[pdf_path, safe_filename, target_lang, job_record.id, summarize], task_id=task_id
    )
    return JSONResponse({"job_id": job_record.id})


# Job Status Endpoint (Using Database Job ID)
@app.get("/status/db/{job_id}", response_model=JobSchema) # Use alias here too if preferred
def get_db_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # Protect this endpoint
):
    db_job = crud.get_job_by_id(db, job_id=job_id)
    if db_job is None: raise HTTPException(status_code=404, detail="Job not found")
    # Verify ownership
    if db_job.user_id != current_user.id: raise HTTPException(status_code=403, detail="Not authorized")
    return db_job


# Get Single Job Details Endpoint
@app.get("/jobs/{job_id}", response_model=JobSchema) # Use alias here too
def read_job_details(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_job = crud.get_job_by_id(db, job_id=job_id)
    if db_job is None: raise HTTPException(status_code=404, detail="Job not found")
    if db_job.user_id != current_user.id: raise HTTPException(status_code=403, detail="Not authorized")
    # print(f"API: Fetched job {job_id}, result_text from DB: '{db_job.result_text[:50] if db_job.result_text else None}...'") # Optional debug print
    return db_job

# --- CORRECTED Get All User Jobs Endpoint ---
@app.get("/jobs/me", response_model=list[JobSchema]) # <-- RESTORED response_model
def read_user_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    print(f"--- Fetching jobs for user_id: {current_user.id} ---")
    db_jobs = crud.get_user_jobs(db, user_id=current_user.id) # Fetches raw SQLAlchemy objects
    print(f"--- Found {len(db_jobs)} jobs in the database. ---")

    try:
        # --- USE EXPLICIT CONVERSION ---
        jobs_response = [JobSchema.from_orm(job) for job in db_jobs] # Convert each to Pydantic schema
        print(f"--- Successfully converted {len(jobs_response)} jobs to schema. ---")
        # Optional debug print for first item
        # if jobs_response:
        #     print(f"--- Data being returned (first item): {jobs_response[0].dict()} ---")
        return jobs_response # <-- RETURN the converted list of Pydantic objects
        # --- END EXPLICIT CONVERSION ---

    except Exception as e:
        print(f"!!! Error during Pydantic conversion or return: {e}")
        # Log problematic data if conversion fails
        problematic_data = []
        for job in db_jobs:
            try: JobSchema.from_orm(job)
            except Exception as inner_e: problematic_data.append(f"Job ID {job.id} failed validation: {inner_e}")
        print(f"!!! Problematic Data: {problematic_data}")
        raise HTTPException(status_code=500, detail=f"Error processing job data: {e}")

# Audio File Download Endpoint
@app.get("/audio/{filename}")
def get_audio_file(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if ".." in filename or filename.startswith("/"): raise HTTPException(status_code=400, detail="Invalid filename")
    if os.path.exists(file_path):
        media_type = "audio/mpeg" if filename.lower().endswith(".mp3") else "audio/wav"
        return FileResponse(file_path, media_type=media_type, filename=filename)
    return JSONResponse(status_code=404, content={"error": "File not found"})

# Delete Job Endpoint
@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    deleted = crud.delete_job_by_id(db, job_id=job_id, user_id=current_user.id)
    if not deleted: raise HTTPException(status_code=status.HTTP_404, detail="Job not found or not authorized")
    return None