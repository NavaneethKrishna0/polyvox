# backend/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base

# This is the base class our models will inherit from
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # This creates a link so we can easily access all jobs for a user
    jobs = relationship("Job", back_populates="owner")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="PENDING")
    pdf_filename = Column(String)
    audio_filename = Column(String, nullable=True) # Can be null until ready
    result_text = Column(Text, nullable=True)
    timestamps_json = Column(Text, nullable=True)

    # This links each job to a specific user
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")