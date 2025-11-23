# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for server-side configuration only)
load_dotenv()

# PostgREST API configuration
POSTGREST_URL = os.getenv("POSTGREST_URL", "https://zettlnotes.app/api/v1")
AUTH_URL = os.getenv("AUTH_URL", "https://zettlnotes.app/api/auth")

# Application settings
APP_NAME = "zettl"

# Import version from package
from zettl import __version__
APP_VERSION = __version__