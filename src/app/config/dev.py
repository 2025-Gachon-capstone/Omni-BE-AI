import os

DEBUG = os.getenv("DEBUG", "False") == "True"

DB_HOST = os.getenv("DB_HOST")  
DB_PORT = os.getenv("DB_PORT")           
DB_USER = os.getenv("DB_USER")   
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_NAME = os.getenv("DB_NAME")   
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  
