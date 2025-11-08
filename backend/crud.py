# backend/crud.py
from sqlalchemy.orm import Session
import models, schemas
from passlib.context import CryptContext
import os

# Switch to a more compatible hashing algorithm
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    """Fetches a user from the database by their email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Creates a new user in the database with a hashed password."""
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_user_job(db: Session, user_id: int, pdf_filename: str):
    """Creates a new job record for a user."""
    db_job = models.Job(user_id=user_id, pdf_filename=pdf_filename)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def update_job_status(db: Session, job_id: int, status: str, audio_filename: str = None, result_text: str = None, timestamps_json: str = None): # <-- Add timestamps_json parameter
    """Updates status, audio, text, and timestamps of a job."""
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if db_job:
        print(f"CRUD: Updating job {job_id}. Received status: {status}, audio: {audio_filename}, text: '{result_text[:20] if result_text else None}...', timestamps: '{timestamps_json[:20] if timestamps_json else None}...'")
        db_job.status = status
        if audio_filename:
            db_job.audio_filename = audio_filename
        if result_text:
            db_job.result_text = result_text
        if timestamps_json: # <-- Add this block
            db_job.timestamps_json = timestamps_json
        try:
            db.commit()
            print(f"CRUD: Job {job_id} committed with status {status}.")
        except Exception as e:
            print(f"CRUD: Error committing job {job_id}: {e}")
            db.rollback()
    return db_job

def get_user_jobs(db: Session, user_id: int):
    """Fetches all jobs for a specific user."""
    return db.query(models.Job).filter(models.Job.user_id == user_id).all()
def get_job_by_id(db: Session, job_id: int):
    """Fetches a single job by its ID."""
    return db.query(models.Job).filter(models.Job.id == job_id).first()
def delete_job_by_id(db: Session, job_id: int, user_id: int):
    """Deletes a job if it belongs to the specified user."""
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    # Check if job exists AND belongs to the user trying to delete it
    if db_job and db_job.user_id == user_id:
        # Optional: Delete the associated audio file before deleting the record
        if db_job.audio_filename:
            audio_path = os.path.join("audio_outputs", db_job.audio_filename)
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"CRUD: Deleted audio file {audio_path}")
                except OSError as e:
                    print(f"CRUD: Error deleting audio file {audio_path}: {e}")
            else:
                 print(f"CRUD: Audio file not found, skipping delete: {audio_path}")

        db.delete(db_job)
        db.commit()
        print(f"CRUD: Deleted job {job_id} for user {user_id}")
        return True # Indicate successful deletion
    print(f"CRUD: Job {job_id} not found or user {user_id} not authorized to delete.")
    return False