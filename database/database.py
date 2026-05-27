# this will handle the database connection, creates tables, and establishes sessions for the application
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:password@localhost:5432/handyman" # URL to connect to the PostgreSQL database

engine = create_engine(SQLALCHEMY_DATABASE_URL) # creates a engine to connect to the database

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
# creates a session factory that will be used to create sessions for interacting with the database
# autocommit = False means that changes are not automatically committed to the database, that way we can have more control over when changes are saved
# autoflush = False means that changes are not automatically sent to the database, just wait until we explicitly commit them
# bind=engine means that the sessions created by this factory will be bound to the engine we created, so they will use that engine to connect to the database

Base = declarative_base() # creates a base class for our database models, acts as glue between our Python classes and the database tables, allows us to define our models as Python classes and have them automatically mapped to database tables.

def get_db():
    db = SessionLocal() # creates a new session
    try:
        yield db # this allows us to use this get_db function as a dependency, so we can get access to the database session in our API endpoints
    finally:
        db.close() # ensuring that db session is closed
        
        