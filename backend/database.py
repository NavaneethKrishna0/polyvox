# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from models import Base # Import the Base from our models file

# Load environment variables from the .env file
load_dotenv()

# Get the database URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL not set in the .env file")

# The engine is the main entry point to the database
engine = create_engine(DATABASE_URL)
print("Connecting to:", DATABASE_URL)
# A session is used to have a conversation with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_tables():
    # This function will create all the tables defined in models.py
    Base.metadata.create_all(bind=engine)

