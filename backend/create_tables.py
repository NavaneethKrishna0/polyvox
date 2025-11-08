# backend/create_tables.py
from database import create_db_tables

print("Connecting to the database and creating tables...")
create_db_tables()
print("Tables created successfully!")