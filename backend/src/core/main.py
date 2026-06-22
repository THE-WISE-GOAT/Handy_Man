from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.core import model, schema
from src.core.router import auth, chat, login, service_task, user, worker
from src.database.database import engine, get_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from src.database.database import engine
from src.core import model
from src.core.router import user, login, auth, worker, service_task, chat

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
    # This runs when the server shuts down (leave empty)
    pass

# 2. Pass the lifespan to FastAPI
app = FastAPI(lifespan=lifespan)


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
    # This runs when the server shuts down (leave empty)
    pass


# 2. Pass the lifespan to FastAPI
app = FastAPI(lifespan=lifespan)

origins = [
    "*"
]  # allows all origins to access our API, lets keep this access for development, but in production we should specify the allowed origins for security reasons
# eg: origins = ["http://localhost:3000"] if our frontend is running on localhost:3000

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allows the specified origins to access our API
    allow_credentials=True,  # allows cookies, HTTP authentication, or SSL client certificates to be included in requests from the frontend
    allow_methods=[
        "*"
    ],  # allows all HTTP methods (GET, POST, PUT, DELETE, etc.) to be used in requests from the frontend
    allow_headers=[
        "*"
    ],  # allows all headers to be included in requests from the frontend
)

app.include_router(
    user.router
)  # includes the user router, which contains all the API endpoints related to user's CRUD operations
app.include_router(
    auth.router
)  # includes the auth router, which contains the API endpoint for user registration and role assignment
app.include_router(
    worker.router
)  # includes the worker router, which contains the API endpoint for worker role application


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

app.include_router(user.router) # includes the user router, which contains all the API endpoints related to user's CRUD operations
app.include_router(auth.router) # includes the auth router, which contains the API endpoint for user registration and role assignment
app.include_router(login.router) # includes the login router, which contains the API endpoint for user login and token generation
app.include_router(worker.router) # includes the worker router, which contains the API endpoint for worker role application
app.include_router(chat.router) # includes the chat router, which contains the API endpoints for the customer support chat functionality

