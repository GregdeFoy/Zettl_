# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgREST API configuration
POSTGREST_URL = os.getenv("POSTGREST_URL", "https://zettlnotes.app/api/v1")
AUTH_URL = os.getenv("AUTH_URL", "https://zettlnotes.app/api/auth")

# Claude API configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Application settings
APP_NAME = "zettl"
APP_VERSION = "0.1.0"