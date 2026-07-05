from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core import model, schema
from src.database.database import engine, get_db
from src.core.router import (
    auth, 
    login, 
    user, 
    worker, 
    service_task, 
    chat_customer, 
    chat_worker,
    connection_manager
)

# 1. Define the startup logic using lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs BEFORE the server starts accepting requests
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    
    # Create all tables safely now that PostGIS is active
    model.Base.metadata.create_all(bind=engine)
    yield

# 2. Pass the lifespan to FastAPI (ONLY ONCE)
app = FastAPI(lifespan=lifespan)

# 3. CORS Configuration
origins = ["*"]  # allows all origins to access our API during development

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Global Inline Custom Alias Routes
@app.post("/register", status_code=201, response_model=schema.UserOut)
@app.post("/signup", status_code=201, response_model=schema.UserOut)
def register_alias(new_user: schema.UserCreate, db: Session = Depends(get_db)):
    return auth._create_user(new_user, db)

@app.post("/login", response_model=schema.Token)
@app.post("/login/", response_model=schema.Token, include_in_schema=False)
def login_alias(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return login.login(user_credentials, db)

# 5. Core Application Routers (Included once and clearly)

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(login.router)
app.include_router(worker.router)
app.include_router(chat_customer.router)
app.include_router(chat_worker.router)
app.include_router(connection_manager.router)
app.include_router(service_task.router)