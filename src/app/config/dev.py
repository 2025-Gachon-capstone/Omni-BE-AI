import os

DEBUG = os.getenv("DEBUG", "False") == "True"

# MYSQL
DB_HOST = os.getenv("DB_HOST")  
DB_PORT = os.getenv("DB_PORT")           
DB_USER = os.getenv("DB_USER")   
# NEO4J
NEO4J_HOST = os.getenv("NEO4J_HOST")
NEO4J_PORT = os.getenv("NEO4J_PORT")
NEO4J_USER = os.getenv("NEO4J_USER")
# DB 공통
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_NAME = os.getenv("DB_NAME")   
# GOOGLE
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
GOOGLE_PROJECT = os.getenv("GOOGLE_PROJECT") 

CARD_SERVER_ADDRESS = os.getenv("CARD_SERVER_ADDRESS")

SWAGGER_SPECS_ROUTE = os.getenv("SWAGGER_SPECS_ROUTE")
SWAGGER_SPECS_JSON_ROUTE = os.getenv("SWAGGER_SPECS_JSON_ROUTE")
SWAGGER_STATIC_PATH = os.getenv("SWAGGER_STATIC_PATH")