# Zettl Development Guide

## Setup & Commands
- **Install:** `pip install -e .` (installs package in development mode)
- **Run CLI:** `python -m zettl.cli` or just `zettl` after installation
- **Create venv:** `python -m venv venv && source venv/bin/activate`
- **Install dev dependencies:** `pip install pytest pylint mypy black`

## Code Style
- **Imports:** Standard library first, then third-party, then local
- **Formatting:** Use black with default settings
- **Type hints:** Add type hints to function parameters and return values
- **Naming:** 
  - snake_case for functions and variables
  - PascalCase for classes
  - UPPER_CASE for constants
- **Docstrings:** Use triple quotes for all functions and classes
- **Error handling:** Use try/except blocks with specific exceptions
- **Module structure:** Each file should have a single responsibility

## Database
- Supabase is used for data storage (check config.py for credentials)
- Use prepared statements for all database queries
- Ensure proper error handling for database operations