# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Claude API configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Application settings
APP_NAME = "zettl"
APP_VERSION = "0.1.0"