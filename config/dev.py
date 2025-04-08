import os

DEBUG = os.getenv("DEBUG", "False") == "True"
DATABASE_URL = os.getenv("DB_URL")