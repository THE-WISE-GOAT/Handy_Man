from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # allows frontend to make requests to our backend
from src.core.router import user 

app = FastAPI() # creates a new FastAPI application instance

origins = ["*"] # allows all origins to access our API, lets keep this access for development, but in production we should specify the allowed origins for security reasons
 # eg: origins = ["http://localhost:3000"] if our frontend is running on localhost:3000
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # allows the specified origins to access our API
    allow_credentials=True, # allows cookies, HTTP authentication, or SSL client certificates to be included in requests from the frontend
    allow_methods=["*"], # allows all HTTP methods (GET, POST, PUT, DELETE, etc.) to be used in requests from the frontend
    allow_headers=["*"], # allows all headers to be included in requests from the frontend
)

app.include_router(user.router) # includes the user router, which contains all the API endpoints related to user's CRUD operations