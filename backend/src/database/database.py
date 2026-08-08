# this will handle the database connection, creates tables, and establishes sessions for the application
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.configuration.config import (
    settings,
)  # imports the settings from our config.py file, which allows environment variables indirectly

SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"  # URL to connect to the PostgreSQL database

# --- UPDATED: Added pool_pre_ping and pool_recycle to handle closed Docker/DB sockets ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Tests the DB connection before issuing queries; drops dead connections seamlessly
    pool_recycle=3600,   # Recycles pool connections every hour to prevent OS socket timeouts
)  # creates an engine to connect to the database

# --- FIX: Activate pgvector extension inside the database on startup ---
with engine.connect() as connection:
    # Postgres extensions require a commit to persist across connections
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
# ----------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# creates a session factory that will be used to create sessions for interacting with the database
# autocommit = False means that changes are not automatically committed to the database, that way we can have more control over when changes are saved
# autoflush = False means that changes are not automatically sent to the database, just wait until we explicitly commit them
# bind=engine means that the sessions created by this factory will be bound to the engine we created, so they will use that engine to connect to the database
# SUSHANT SINGH RAUT
Base = (
    declarative_base()
)  # creates a base class for our database models, acts as glue between our Python classes and the database tables, allows us to define our models as Python classes and have them automatically mapped to database tables.


def get_db():
    db = SessionLocal()  # creates a new session
    try:
        yield db  # this allows us to use this get_db function as a dependency, so we can get access to the database session in our API endpoints
    finally:
        db.close()  # ensuring that db session is closed
