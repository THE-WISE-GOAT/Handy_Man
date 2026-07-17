from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

# Core Application Imports
from src.core import model, schema
from src.database.database import engine, get_db

# Route Imports (Imported exactly ONCE)
from src.core.router import (
    auth, 
    login, 
    user, 
    worker, 
    chat_customer, 
    chat_worker,
    job_router,
    worker_onboarding,
    worker_table_router,
    chat_worker_ws
)

# 1. Define the startup logic using a SINGLE lifespan block
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs BEFORE the server starts accepting requests
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))  # Ensure pgvector is active
        conn.commit()
    
    # Create all tables safely now that extensions are active
    model.Base.metadata.create_all(bind=engine)
    yield

# 2. Initialize FastAPI exactly ONCE
app = FastAPI(lifespan=lifespan)

# 3. CORS Configuration
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 4. Include Routers sequentially (Exactly ONCE)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(login.router)
app.include_router(worker.router)
app.include_router(chat_customer.router)
app.include_router(chat_customer.match_router)
app.include_router(chat_worker.router)
app.include_router(job_router.router)
app.include_router(worker_onboarding.router)
app.include_router(worker_table_router.router)
app.include_router(chat_worker_ws.router)


# 5. Core Alias Root Routes
@app.post("/register", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
@app.post("/signup", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def register_alias(new_user: schema.UserCreate, db: Session = Depends(get_db)):
    return auth._create_user(new_user, db)

@app.post("/login", response_model=schema.Token)
@app.post("/login/", response_model=schema.Token, include_in_schema=False)
def login_alias(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return login.login(user_credentials, db)
