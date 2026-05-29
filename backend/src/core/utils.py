# Utility functions for the application
# this file have functions that are used for hashing passwords, verifying passwords, etc. These functions are used in the API endpoints to handle user authentication and password management.

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") # this creates a CryptContext object that will be used to hash and verify passwords
# we are using bcrypt as the hashing algorithm 
# we are setting deprecated to auto, which means that if we ever want to change the hashing algorithm in the future, we can do so without breaking existing passwords, as the old passwords will still be valid and can be verified using the old algorithm.

def hash_password(password:str)-> str:
    return pwd_context.hash(password) # this function takes a plain text password and returns a hashed version of the password using the CryptContext object we created

def verify_password(plain_password:str, hashed_password:str)-> bool:
    return pwd_context.verify(plain_password, hashed_password) # this function takes a plain text password and a hashed password and returns a boolean indicating whether they match