# File: zettl_web.py

import os
import json
import logging
import shlex
import sys
import requests
from flask import Flask, request, jsonify, render_template, Response, session, redirect, url_for
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import re
import jwt
from datetime import datetime, timezone

# Add the parent directory to the Python path to find the zettl module
sys.path.insert(0, '/app')

from zettl.nutrition import NutritionTracker
from zettl.help import CommandHelp

# Load environment variables from parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
dotenv_path = os.path.join(parent_dir, '.env')
print(f"Looking for .env file at: {dotenv_path}")
print(f"File exists: {os.path.exists(dotenv_path)}")
load_dotenv(dotenv_path)

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Read secret key from file if available, otherwise use environment or generate random
secret_key_file = os.getenv('SECRET_KEY_FILE')
if secret_key_file and os.path.exists(secret_key_file):
    with open(secret_key_file, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Auth service configuration
AUTH_URL = os.getenv('AUTH_URL', 'http://auth-service:3001')
JWT_SECRET_FILE = os.getenv('JWT_SECRET_FILE')

# Read JWT secret for token validation
JWT_SECRET = None
if JWT_SECRET_FILE and os.path.exists(JWT_SECRET_FILE):
    with open(JWT_SECRET_FILE, 'r') as f:
        JWT_SECRET = f.read().strip()
else:
    JWT_SECRET = os.getenv('JWT_SECRET')

print(f"Auth service URL: {AUTH_URL}")
print(f"JWT secret configured: {'Yes' if JWT_SECRET else 'No'}")

# Import Zettl components
from zettl.notes import Notes
from zettl.database import Database
from zettl.llm import LLMHelper
from zettl.formatting import ZettlFormatter, Colors
from zettl.nutrition import NutritionTracker
from zettl.help import CommandHelp

logger.debug("Successfully imported Zettl components")

# JWT token validation decorator
def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Check for token in session first
        if 'access_token' in session:
            token = session['access_token']
        # Check Authorization header as fallback
        elif 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No token provided'}), 401
            else:
                return redirect(url_for('login_page'))

        try:
            # Validate token with auth service
            response = requests.post(f'{AUTH_URL}/api/auth/validate',
                                   json={'token': token},
                                   timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    request.current_user = data.get('user')
                    return f(*args, **kwargs)

            # Token invalid - clear session and redirect
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Invalid or expired token'}), 401
            else:
                return redirect(url_for('login_page'))

        except requests.RequestException as e:
            logger.error(f"Auth service connection error: {e}")
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication service unavailable'}), 503
            else:
                return render_template('login.html', error='Authentication service unavailable')

    return decorated_function

def get_notes_manager():
    """Get a Notes manager instance with the current user's JWT token."""
    # Get JWT token from session
    jwt_token = session.get('access_token')
    return Notes(jwt_token=jwt_token)

def get_llm_helper():
    """Get an LLM helper instance."""
    return LLMHelper()

# Command parsing utilities
def parse_command(command_str):
    """
    Parse a command string into components while preserving quotes
    """
    try:
        # Use shlex to handle quoted arguments properly
        parts = shlex.split(command_str)
        if not parts:
            return None, []
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
    except Exception as e:
        logger.error(f"Error parsing command: {e}")
        return command_str.split()[0], [] 


COMMAND_OPTIONS = {
    'new': {
            'short_opts': {
        't': {'name': 'tag', 'multiple': True},
        'l': {'name': 'link'}
    },
    'long_opts': {
        'tag': {'multiple': True},
        'link': {}
    }
    },
    'add': {
            'short_opts': {
        't': {'name': 'tag', 'multiple': True},
        'l': {'name': 'link'}
    },
    'long_opts': {
        'tag': {'multiple': True},
        'link': {}
    }
    },
    'list': {
        'short_opts': {
            'l': {'name': 'limit', 'type': int},
            'f': {'name': 'full', 'flag': True},
            'c': {'name': 'compact', 'flag': True}
        },
        'long_opts': {
            'limit': {'type': int},
            'full': {'flag': True},
            'compact': {'flag': True}
        }
    },
    'todos': {
        'short_opts': {
            'dt': {'name': 'donetoday', 'flag': True},
            'a': {'name': 'all', 'flag': True},
            'c': {'name': 'cancel', 'flag': True},
            't': {'name': 'tag', 'multiple': True},
            'e': {'name': 'eisenhower', 'flag': True}  # Add the new flag
        },
        'long_opts': {
            'donetoday': {'flag': True},
            'all': {'flag': True},
            'cancel': {'flag': True},
            'tag': {'multiple': True},
            'eisenhower': {'flag': True}  # Add the new flag
        }
    },
    'search': {
        'short_opts': {
            't': {'name': 'tag'},
            'f': {'name': 'full', 'flag': True}
        },
        'long_opts': {
            'tag': {},
            'exclude-tag': {},
            'full': {'flag': True}
        }
    },
    'llm': {
        'short_opts': {
            'a': {'name': 'action'},
            'c': {'name': 'count', 'type': int},
            's': {'name': 'show-source', 'flag': True},
            'd': {'name': 'debug', 'flag': True}
        },
        'long_opts': {
            'action': {},
            'count': {'type': int},
            'show-source': {'flag': True},
            'debug': {'flag': True}
        }
    },
    'rules': {
        'short_opts': {
            's': {'name': 'source', 'flag': True}
        },
        'long_opts': {
            'source': {'flag': True}
        }
    },
    'nutrition': {
        'short_opts': {
            'd': {'name': 'days', 'type': int},
            'p': {'name': 'past'}
        },
        'long_opts': {
            'days': {'type': int},
            'past': {}
        }
    },
    'nut': {
        'short_opts': {
            'd': {'name': 'days', 'type': int},
            'p': {'name': 'past'}
        },
        'long_opts': {
            'days': {'type': int},
            'past': {}
        }
    },
    'merge': {
        'short_opts': {
            'f': {'name': 'force', 'flag': True}
        },
        'long_opts': {
            'force': {'flag': True}
        }
    },
    'append': {
        'short_opts': {},
        'long_opts': {}
    },
    'prepend': {
        'short_opts': {},
        'long_opts': {}
    },

    # Add similar configs for other commands
}


def extract_options(args, cmd):
    """
    Extract options and flags from arguments based on command configuration
    Returns options dict, flags list, and remaining args
    """
    options = {}
    flags = []
    remaining_args = []
    
    # Get command configuration or empty dict if command not found
    cmd_config = COMMAND_OPTIONS.get(cmd, {'short_opts': {}, 'long_opts': {}})
    short_opts = cmd_config['short_opts']
    long_opts = cmd_config['long_opts']
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '-dt':
            flags.append('dt')
            options['donetoday'] = True
            i += 1
        # Handle long options (--option)
        elif arg.startswith('--'):
            opt_name = arg[2:]
            opt_config = long_opts.get(opt_name, {})
            
            # If it's a flag option
            if opt_config.get('flag', False):
                flags.append(opt_name)
                options[opt_name] = True
                i += 1
            # If it takes a value
            elif i + 1 < len(args) and not args[i+1].startswith('-'):
                value = args[i+1]
                
                # Convert type if specified
                if 'type' in opt_config:
                    try:
                        value = opt_config['type'](value)
                    except ValueError:
                        pass
                
                # Handle multiple values
                if opt_config.get('multiple', False):
                    if opt_name not in options:
                        options[opt_name] = []
                    options[opt_name].append(value)
                else:
                    options[opt_name] = value
                i += 2
            else:
                # Treat as flag if no value provided
                flags.append(opt_name)
                options[opt_name] = True
                i += 1
                
        # Handle short options (-o)
        elif arg.startswith('-') and len(arg) == 2:
            opt_char = arg[1]
            if opt_char in short_opts:
                opt_config = short_opts[opt_char]
                opt_name = opt_config.get('name', opt_char)
                
                # If it's a flag option
                if opt_config.get('flag', False):
                    flags.append(opt_char)
                    options[opt_name] = True
                    i += 1
                # If it takes a value
                elif i + 1 < len(args) and not args[i+1].startswith('-'):
                    value = args[i+1]
                    
                    # Convert type if specified
                    if 'type' in opt_config:
                        try:
                            value = opt_config['type'](value)
                        except ValueError:
                            pass
                    
                    # Handle multiple values
                    if opt_config.get('multiple', False):
                        if opt_name not in options:
                            options[opt_name] = []
                        options[opt_name].append(value)
                    else:
                        options[opt_name] = value
                    i += 2
                else:
                    # Treat as flag if no value provided
                    flags.append(opt_char)
                    options[opt_name] = True
                    i += 1
            else:
                # Unknown short option, treat as flag
                flags.append(opt_char)
                i += 1
                
        # Handle combined short options (-abc)
        elif arg.startswith('-') and len(arg) > 2:
            combined_flags = arg[1:]
            for flag in combined_flags:
                flags.append(flag)
                # Map to long option name if exists
                if flag in short_opts:
                    opt_name = short_opts[flag].get('name', flag)
                    options[opt_name] = True
                else:
                    # Even if not in short_opts config, keep the flag
                    options[flag] = True
            i += 1
        elif arg.startswith('+t'):
            if i + 1 < len(args) and not args[i+1].startswith('-'):
                options['exclude-tag'] = args[i+1]
                i += 2
            else:
                options['exclude-tag'] = True
                i += 1
        else:
            # Add this else clause to capture non-option arguments
            remaining_args.append(arg)
            i += 1
            
    return options, flags, remaining_args

# ANSI color code to HTML span conversion
def ansi_to_html(text):
    """
    Convert ANSI color codes to HTML spans and convert newlines to <br> tags
    for proper HTML rendering
    """
    # Map ANSI color codes to CSS classes
    ansi_map = {
        '\033[92m': '<span class="green">',    # GREEN
        '\033[94m': '<span class="blue">',     # BLUE
        '\033[93m': '<span class="yellow">',   # YELLOW
        '\033[91m': '<span class="red">',      # RED
        '\033[96m': '<span class="cyan">',     # CYAN
        '\033[1m': '<span class="bold">',      # BOLD
        '\033[0m': '</span>'                   # RESET
    }
    
    # Replace ANSI codes with HTML spans
    for ansi, html in ansi_map.items():
        text = text.replace(ansi, html)
    
    # Handle nested spans correctly by counting resets
    reset_count = text.count('</span>')
    open_count = sum(text.count(span) for span in ansi_map.values() if span != '</span>')
    
    # Add any missing closing spans
    if open_count > reset_count:
        text += '</span>' * (open_count - reset_count)
        
    # Convert newlines to HTML breaks
    # Double newlines (paragraph breaks) get extra spacing
    text = text.replace('\n\n', '<br><br style="margin-bottom: 10px">')
    text = text.replace('\n', '<br>')
    
    return text

def show_command_help(cmd):
    """Show detailed help for a specific command."""
    help_text = CommandHelp.get_command_help(cmd)
    return jsonify({'result': ansi_to_html(help_text)})


# Routes
@app.route('/login')
def login_page():
    # If user is already logged in, redirect to main page
    if 'access_token' in session:
        try:
            response = requests.post(f'{AUTH_URL}/api/auth/validate',
                                   json={'token': session['access_token']},
                                   timeout=5)
            if response.status_code == 200 and response.json().get('valid'):
                return redirect(url_for('index'))
        except:
            session.clear()

    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required', 'success': False}), 400

    try:
        # Authenticate with auth service
        response = requests.post(f'{AUTH_URL}/api/auth/login',
                               json={'username': username, 'password': password},
                               timeout=10)

        if response.status_code == 200:
            data = response.json()
            # Store tokens in session
            session['access_token'] = data['accessToken']
            session['refresh_token'] = data['refreshToken']
            session['user'] = data['user']

            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': data['user']
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'error': error_data.get('error', 'Login failed'),
                'success': False
            }), response.status_code

    except requests.RequestException as e:
        logger.error(f"Auth service connection error: {e}")
        return jsonify({
            'error': 'Authentication service unavailable',
            'success': False
        }), 503

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email and password required', 'success': False}), 400

    try:
        # Register with auth service
        response = requests.post(f'{AUTH_URL}/api/auth/register',
                               json={'username': username, 'email': email, 'password': password},
                               timeout=10)

        if response.status_code == 201:
            return jsonify({
                'success': True,
                'message': 'Registration successful'
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'error': error_data.get('error', 'Registration failed'),
                'success': False
            }), response.status_code

    except requests.RequestException as e:
        logger.error(f"Auth service connection error: {e}")
        return jsonify({
            'error': 'Authentication service unavailable',
            'success': False
        }), 503

@app.route('/api/logout', methods=['POST'])
@jwt_required
def logout():
    try:
        # Call auth service logout if we have tokens
        if 'access_token' in session:
            requests.post(f'{AUTH_URL}/api/auth/logout',
                        headers={'Authorization': f'Bearer {session["access_token"]}'},
                        timeout=5)
    except:
        pass  # Ignore auth service errors during logout

    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/generate-api-key', methods=['POST'])
@jwt_required
def generate_api_key():
    data = request.get_json() or {}
    name = data.get('name', 'CLI Key')

    try:
        # Generate API key via auth service
        response = requests.post(f'{AUTH_URL}/api/auth/api-key',
                               headers={'Authorization': f'Bearer {session["access_token"]}'},
                               json={'name': name},
                               timeout=10)

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'api_key': response.json()['apiKey'],
                'name': response.json()['name']
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'error': error_data.get('error', 'Failed to generate API key'),
                'success': False
            }), response.status_code

    except requests.RequestException as e:
        logger.error(f"Auth service connection error: {e}")
        return jsonify({
            'error': 'Authentication service unavailable',
            'success': False
        }), 503

@app.route('/api/list-api-keys', methods=['GET'])
@jwt_required
def list_api_keys():
    try:
        # List API keys via auth service
        response = requests.get(f'{AUTH_URL}/api/auth/api-keys',
                              headers={'Authorization': f'Bearer {session["access_token"]}'},
                              timeout=10)

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'api_keys': response.json()
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'error': error_data.get('error', 'Failed to list API keys'),
                'success': False
            }), response.status_code

    except requests.RequestException as e:
        logger.error(f"Auth service connection error: {e}")
        return jsonify({
            'error': 'Authentication service unavailable',
            'success': False
        }), 503

@app.route('/')
@jwt_required
def index():
    user = getattr(request, 'current_user', session.get('user', {}))
    username = user.get('username', 'Unknown')
    logger.debug(f"Rendering index page for user: {username}")
    return render_template('index.html', username=username)

@app.route('/api/command', methods=['POST'])
@jwt_required
def execute_command():
    command = request.json.get('command', '').strip()
    logger.debug(f"Executing command: {command}")

    if not command:
        return jsonify({'result': 'No command provided'})

    try:
        # Get Notes manager with JWT token for this request
        notes_manager = get_notes_manager()
        llm_helper = get_llm_helper()
    except Exception as e:
        logger.error(f"Failed to initialize Zettl components: {e}")
        error_msg = ZettlFormatter.error("Unable to connect to the database. Please check your authentication and try again.")
        return jsonify({'result': ansi_to_html(error_msg)})

    # Parse the command with better handling for options and quotes
    cmd, args = parse_command(command)

    # Check for command-specific help
    if '--help' in args or '-h' in args:
        return show_command_help(cmd)



    # Extract options, flags and non-option args
    options, flags, remaining_args = extract_options(args, cmd)
    
    try:
        result = ""
        
        # Map commands to Zettl functions
        if cmd == "list":
            # Handle options
            limit = int(options.get('limit', 10))
            full = 'f' in flags or 'full' in flags
            compact = 'c' in flags or 'compact' in flags
            
            notes = notes_manager.list_notes(limit)
            if not notes:
                result = "No notes found."
            else:
                result = f"{ZettlFormatter.header(f'Recent Notes (showing {len(notes)} of {len(notes)})')}\n\n"
                

            for note in notes:
                note_id = note['id']
                created_at = notes_manager.db.format_timestamp(note['created_at'])
                
                if compact:
                    # Very compact mode - just IDs
                    result += f"{ZettlFormatter.note_id(note_id)}\n"
                elif full:
                    # Full content mode
                    result += f"{ZettlFormatter.note_id(note_id)} [{ZettlFormatter.timestamp(created_at)}]\n"
                    result += "-" * 40 + "\n"
                    result += f"{note['content']}\n"
                    
                    # Add tags display
                    try:
                        tags = notes_manager.get_tags(note_id)
                        if tags:
                            result += f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}\n"
                    except Exception:
                        pass
                    
                    result += "\n"  # Extra line between notes
                else:
                    # Default mode - ID, timestamp, and preview
                    formatted_id = ZettlFormatter.note_id(note_id)
                    formatted_time = ZettlFormatter.timestamp(created_at)
                    content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                    result += f"{formatted_id} [{formatted_time}]: {content_preview}\n\n"  # Added extra newline

                    
        elif cmd == "new" or cmd == "add":
            # Handle content and tags
            content = remaining_args[0] if remaining_args else ""
            
            # Get tags from the 'tag' option which could be from -t or --tag
            tags = []
            if 'tag' in options:
                if isinstance(options['tag'], list):
                    # Multiple tag option usage
                    tags.extend(options['tag'])
                else:
                    # Single tag option
                    tags.append(options['tag'])
            
            # Create the note
            note_id = notes_manager.create_note(content)
            result = f"Created note #{note_id}\n"
            
            
            # Add tags if provided
            for tag in tags:
                if tag:
                    try:
                        notes_manager.add_tag(note_id, tag)
                        result += f"Added tag '{tag}' to note #{note_id}\n"
                    except Exception as e:
                        result += f"{ZettlFormatter.warning(f'Could not add tag {tag}: {str(e)}')}\n"


            link = options.get('link', options.get('l', ''))
            # Create link if provided
            if link:
                try:
                    notes_manager.create_link(note_id, link)
                    result += f"Created link from #{note_id} to #{link}\n"
                except Exception as e:
                    result += f"{ZettlFormatter.warning(f'Could not create link to note #{link}: {str(e)}')}\n"

                    
        elif cmd == "show":
            if not remaining_args:
                result = ZettlFormatter.error("Please provide a note ID")
            else:
                note_id = remaining_args[0]

                try:
                    # Get the note using the standard method
                    note = notes_manager.get_note(note_id)
                    created_at = notes_manager.db.format_timestamp(note['created_at'])

                    result = f"{ZettlFormatter.note_id(note_id)} [{ZettlFormatter.timestamp(created_at)}]\n"
                    result += "-" * 40 + "\n"
                    result += f"{note['content']}\n\n"

                    # Show tags if any
                    try:
                        tags = notes_manager.get_tags(note_id)
                        if tags:
                            result += f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}"
                    except Exception as e:
                        logger.exception(f"Error getting tags for note {note_id}: {e}")

                except Exception as e:
                    logger.exception(f"Error in show command for note {note_id}: {e}")

                    # Provide a helpful error message based on the exception
                    if "not found" in str(e).lower():
                        result = ZettlFormatter.error(f"Note {note_id} not found")
                    elif "connection" in str(e).lower() or "request failed" in str(e).lower():
                        result = ZettlFormatter.error(f"Database connection error: {str(e)}")
                    elif "authentication" in str(e).lower() or "401" in str(e):
                        result = ZettlFormatter.error(f"Authentication error: {str(e)}")
                    else:
                        result = ZettlFormatter.error(f"Error retrieving note: {str(e)}")

                
        elif cmd == "search":
            # Parse options
            tag = options.get('tag', options.get('t', ''))
            exclude_tag = options.get('exclude-tag', options.get('+t', ''))
            full = 'f' in flags or 'full' in flags
            query = remaining_args[0] if remaining_args else ""
            
            if tag:
                # Search by tag inclusion
                notes = notes_manager.get_notes_by_tag(tag)
                if not notes:
                    result = ZettlFormatter.warning(f"No notes found with tag '{tag}'")
                else:
                    result = f"{ZettlFormatter.header(f'Found {len(notes)} notes with tag {tag}:')}\n\n"
                    search_results = notes
            elif query:
                # Search by content
                notes = notes_manager.search_notes(query)
                if not notes:
                    result = ZettlFormatter.warning(f"No notes found containing '{query}'")
                else:
                    result = f"{ZettlFormatter.header(f'Found {len(notes)} notes containing {query}:')}\n\n"
                    search_results = notes
            else:
                # No search criteria specified, use a larger set
                search_results = notes_manager.list_notes(limit=50)
                result = f"{ZettlFormatter.header(f'Listing notes (showing {len(search_results)}):')}\n\n"
            
            # Filter out excluded tags if specified
            if exclude_tag and 'search_results' in locals():
                # Get IDs of notes with the excluded tag
                excluded_notes = notes_manager.get_notes_by_tag(exclude_tag)
                excluded_ids = {note['id'] for note in excluded_notes}
                
                # Filter out notes with the excluded tag
                original_count = len(search_results)
                search_results = [note for note in search_results if note['id'] not in excluded_ids]
                
                # Inform user about filtering
                if original_count != len(search_results):
                    result += f"{ZettlFormatter.warning(f'Excluded {original_count - len(search_results)} notes with tag {exclude_tag}')}\n\n"
            
            # Display the results if we have any
            if 'search_results' in locals() and search_results:
                for note in search_results:
                    if full:
                        # Full content mode
                        result += f"{ZettlFormatter.note_id(note['id'])}\n"
                        result += "-" * 40 + "\n"
                        result += f"{note['content']}\n"
                        
                        # Add tags display
                        try:
                            tags = notes_manager.get_tags(note['id'])
                            if tags:
                                result += f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}\n"
                        except Exception:
                            pass
                        
                        result += "\n"  # Extra line between notes
                    else:
                        # Preview mode
                        content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                        if query:
                            # Highlight the query in the preview
                            pattern = re.compile(re.escape(query), re.IGNORECASE)
                            content_preview = pattern.sub(f"{Colors.YELLOW}\\g<0>{Colors.RESET}", content_preview)
                        
                        result += f"{ZettlFormatter.note_id(note['id'])}: {content_preview}\n"
                    
        elif cmd == "tags":
            # Handle various ways the tags command is used
            if not remaining_args:
                # List all tags
                tags_with_counts = notes_manager.get_all_tags_with_counts()
                if tags_with_counts:
                    result = f"{ZettlFormatter.header(f'All Tags (showing {len(tags_with_counts)})')}\n\n"
                    for tag_info in tags_with_counts:
                        formatted_tag = ZettlFormatter.tag(tag_info['tag'])
                        result += f"{formatted_tag} ({tag_info['count']} notes)\n"
                else:
                    result = ZettlFormatter.warning("No tags found.")
            else:
                note_id = remaining_args[0]
                tag = remaining_args[1] if len(remaining_args) > 1 else ""
                
                # If a tag was provided, add it
                if tag:
                    notes_manager.add_tag(note_id, tag)
                    result = f"Added tag '{tag}' to note #{note_id}\n"
                
                # Show all tags for the note
                tags = notes_manager.get_tags(note_id)
                if tags:
                    result += f"Tags for note #{note_id}: {', '.join([ZettlFormatter.tag(t) for t in tags])}"
                else:
                    result += f"No tags for note #{note_id}"
                
        elif cmd == "link":
            # Create a link between notes
            if len(remaining_args) >= 2:
                source_id = remaining_args[0]
                target_id = remaining_args[1]
                context = options.get('context', options.get('c', ''))
                
                notes_manager.create_link(source_id, target_id, context)
                result = f"Created link from #{source_id} to #{target_id}"
            else:
                result = ZettlFormatter.error("Please provide source and target note IDs")
                
        elif cmd == "related":
            # Show related notes
            note_id = remaining_args[0] if remaining_args else ""
            full = 'f' in flags or 'full' in flags
            
            if not note_id:
                result = ZettlFormatter.error("Please provide a note ID")
            else:
                # First, show the source note
                try:
                    source_note = notes_manager.get_note(note_id)
                    result = f"{ZettlFormatter.header('Source Note')}\n"
                    created_at = notes_manager.db.format_timestamp(source_note['created_at'])
                    result += f"{ZettlFormatter.note_id(note_id)} [{ZettlFormatter.timestamp(created_at)}]\n"
                    result += "-" * 40 + "\n"
                    result += f"{source_note['content']}\n\n"
                except Exception as e:
                    result = f"{ZettlFormatter.warning(f'Could not display source note: {str(e)}')}\n"
                
                # Now show related notes
                related_notes = notes_manager.get_related_notes(note_id)
                if not related_notes:
                    result += ZettlFormatter.warning(f"No notes connected to note #{note_id}")
                else:
                    result += f"{ZettlFormatter.header(f'Connected Notes ({len(related_notes)} total)')}\n\n"
                    
                    for note in related_notes:
                        if full:
                            # Full content mode
                            note_created_at = notes_manager.db.format_timestamp(note['created_at'])
                            result += f"{ZettlFormatter.note_id(note['id'])} [{ZettlFormatter.timestamp(note_created_at)}]\n"
                            result += "-" * 40 + "\n"
                            result += f"{note['content']}\n\n"
                        else:
                            # Preview mode
                            content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                            result += f"{ZettlFormatter.note_id(note['id'])}: {content_preview}\n"
                
        elif cmd == "graph":
            # Generate graph - not fully implemented in web version
            note_id = remaining_args[0] if remaining_args else None
            output = options.get('output', options.get('o', 'zettl_graph.json'))
            result = f"Graph feature not fully implemented in web version.\n"
            result += f"On CLI, this would generate a graph visualization of notes and save to {output}"
            
        elif cmd == "llm":
            # LLM commands
            if not remaining_args:
                result = ZettlFormatter.error("Please provide a note ID")
            else:
                note_id = remaining_args[0]
                action = options.get('action', options.get('a', 'summarize'))
                count = int(options.get('count', options.get('c', '3')))
                debug = 'd' in flags or 'debug' in flags
                
                # Debug mode - show environment and configuration info
                if debug:
                    debug_info = f"{ZettlFormatter.header('LLM Debug Info')}\n\n"
                    debug_info += f"Note ID: {note_id}\n"
                    debug_info += f"Action: {action}\n"
                    debug_info += f"Count: {count}\n"
                    debug_info += f"LLM Helper Type: {type(llm_helper).__name__}\n"
                    debug_info += f"Claude API Key Set: {bool(llm_helper.api_key)}\n"
                    debug_info += f"Model: {getattr(llm_helper, 'model', 'unknown')}\n"
                    
                    try:
                        # Verify note exists
                        note = notes_manager.get_note(note_id)
                        debug_info += f"Note exists: Yes\n"
                        debug_info += f"Note content length: {len(note['content'])}\n"
                    except Exception as e:
                        debug_info += f"Note exists: No (Error: {str(e)})\n"
                        
                    try:
                        # Test anthropic import
                        import anthropic
                        debug_info += f"Anthropic package: Installed (version: {getattr(anthropic, '__version__', 'unknown')})\n"
                    except ImportError:
                        debug_info += "Anthropic package: Not installed\n"
                        
                    result = debug_info
                    return jsonify({'result': ansi_to_html(result)})
                    
                try:
                    # Check if the note exists first
                    note = notes_manager.get_note(note_id)
                    
                    # Add a processing message to warn the user this might take time
                    processing_message = f"Processing LLM {action} request for note #{note_id}. This may take a moment..."
                    result = f"{ZettlFormatter.warning(processing_message)}\n\n"
                    
                    if action == "summarize":
                        summary = llm_helper.summarize_note(note_id)
                        result += f"{ZettlFormatter.header(f'AI Summary for Note #{note_id}')}\n\n{summary}"
                        
                    elif action == "tags":
                        tags = llm_helper.suggest_tags(note_id, count)
                        result += f"{ZettlFormatter.header(f'AI-Suggested Tags for Note #{note_id}')}\n\n"
                        for tag in tags:
                            result += f"{ZettlFormatter.tag(tag)}\n"
                            
                    elif action == "connect":
                        connections = llm_helper.generate_connections(note_id, count)
                        result += f"{ZettlFormatter.header(f'AI-Suggested Connections for Note #{note_id}')}\n\n"
                        if not connections:
                            result += ZettlFormatter.warning("No potential connections found.")
                        else:
                            for conn in connections:
                                conn_id = conn['note_id']
                                formatted_id = ZettlFormatter.note_id(conn_id)
                                result += f"{formatted_id}\n"
                                result += f"  {conn['explanation']}\n\n"
                                
                    elif action == "expand":
                        expanded_content = llm_helper.expand_note(note_id)
                        result += f"{ZettlFormatter.header(f'AI-Expanded Version of Note #{note_id}')}\n\n{expanded_content}"
                        
                    elif action == "concepts":
                        concepts = llm_helper.extract_key_concepts(note_id, count)
                        result += f"{ZettlFormatter.header(f'Key Concepts from Note #{note_id}')}\n\n"
                        if not concepts:
                            result += ZettlFormatter.warning("No key concepts identified.")
                        else:
                            for i, concept in enumerate(concepts, 1):
                                result += f"{i}. {Colors.BOLD}{concept['concept']}{Colors.RESET}\n"
                                result += f"   {concept['explanation']}\n\n"
                                
                    elif action == "questions":
                        questions = llm_helper.generate_question_note(note_id, count)
                        result += f"{ZettlFormatter.header(f'Thought-Provoking Questions from Note #{note_id}')}\n\n"
                        if not questions:
                            result += ZettlFormatter.warning("No questions generated.")
                        else:
                            for i, question in enumerate(questions, 1):
                                result += f"{i}. {Colors.BOLD}{question['question']}{Colors.RESET}\n"
                                result += f"   {question['explanation']}\n\n"
                                
                    elif action == "critique":
                        critique = llm_helper.critique_note(note_id)
                        result += f"{ZettlFormatter.header(f'AI Critique of Note #{note_id}')}\n\n"
                        
                        # Display strengths
                        if critique['strengths']:
                            result += f"{Colors.BOLD}{Colors.GREEN}Strengths:{Colors.RESET}\n"
                            for strength in critique['strengths']:
                                result += f"  • {strength}\n"
                        
                        # Display weaknesses
                        if critique['weaknesses']:
                            result += f"\n{Colors.BOLD}{Colors.YELLOW}Areas for Improvement:{Colors.RESET}\n"
                            for weakness in critique['weaknesses']:
                                result += f"  • {weakness}\n"
                        
                        # Display suggestions
                        if critique['suggestions']:
                            result += f"\n{Colors.BOLD}{Colors.CYAN}Suggestions:{Colors.RESET}\n"
                            for suggestion in critique['suggestions']:
                                result += f"  • {suggestion}\n"
                                
                        # If no structured feedback was generated
                        if not (critique['strengths'] or critique['weaknesses'] or critique['suggestions']):
                            result += ZettlFormatter.warning("Could not generate structured feedback for this note.")
                    else:
                        result = ZettlFormatter.warning(f"Unknown LLM action: '{action}'. Available actions: summarize, connect, tags, expand, concepts, questions, critique")
                        
                except Exception as e:
                    # Enhanced error handling with specific messages
                    error_msg = str(e)
                    logger.exception(f"Error in LLM command: {error_msg}")
                    
                    if "authentication" in error_msg.lower() or "auth" in error_msg.lower() or "api key" in error_msg.lower():
                        result = ZettlFormatter.error(f"Authentication error: {error_msg}. Check your Claude API key in the .env file.")
                        
                    elif "note" in error_msg.lower() and "not found" in error_msg.lower():
                        result = ZettlFormatter.error(f"Note #{note_id} not found.")
                        
                    elif "import" in error_msg.lower() and "anthropic" in error_msg.lower():
                        result = ZettlFormatter.error("The anthropic package is not installed. Install it with: pip install anthropic")
                        
                    elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                        result = ZettlFormatter.error(f"Connection error: {error_msg}. Check your network connection.")
                        
                    else:
                        result = ZettlFormatter.error(f"Error processing LLM command: {error_msg}")
                
        elif cmd == "delete":
            # Delete a note
            if not remaining_args:
                result = ZettlFormatter.error("Please provide a note ID to delete")
            else:
                note_id = remaining_args[0]
                keep_links = 'keep-links' in flags
                keep_tags = 'keep-tags' in flags
                
                # Determine cascade setting based on flags
                cascade = not (keep_links and keep_tags)
                
                # Get the note to show what will be deleted
                try:
                    note = notes_manager.get_note(note_id)
                    content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                    result = f"Deleting note #{note_id}: {content_preview}\n"
                except Exception as e:
                    result = f"{ZettlFormatter.warning(f'Note not found: {str(e)}')}\n"
                    return jsonify({'result': ansi_to_html(result)})
                
                # Delete the note
                notes_manager.delete_note(note_id, cascade=cascade)
                result += ZettlFormatter.success(f"Deleted note #{note_id}")
                
        elif cmd == "untag":
            # Remove a tag from a note
            if len(remaining_args) < 2:
                result = ZettlFormatter.error("Please provide note ID and tag")
            else:
                note_id = remaining_args[0]
                tag = remaining_args[1]
                
                notes_manager.delete_tag(note_id, tag)
                result = ZettlFormatter.success(f"Removed tag '{tag}' from note #{note_id}")
        
        elif cmd == "unlink":
            # Remove a link between notes
            if len(remaining_args) < 2:
                result = ZettlFormatter.error("Please provide source and target note IDs")
            else:
                source_id = remaining_args[0]
                target_id = remaining_args[1]

                notes_manager.delete_link(source_id, target_id)
                result = ZettlFormatter.success(f"Removed link from note #{source_id} to note #{target_id}")

        elif cmd == "append":
            # Append text to the end of a note
            if len(remaining_args) < 2:
                result = ZettlFormatter.error("Please provide note ID and text to append")
            else:
                note_id = remaining_args[0]
                text = remaining_args[1]

                try:
                    notes_manager.append_to_note(note_id, text)
                    result = ZettlFormatter.success(f"Appended text to note #{note_id}")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error appending to note: {str(e)}")

        elif cmd == "prepend":
            # Prepend text to the beginning of a note
            if len(remaining_args) < 2:
                result = ZettlFormatter.error("Please provide note ID and text to prepend")
            else:
                note_id = remaining_args[0]
                text = remaining_args[1]

                try:
                    notes_manager.prepend_to_note(note_id, text)
                    result = ZettlFormatter.success(f"Prepended text to note #{note_id}")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error prepending to note: {str(e)}")

        elif cmd == "merge":
            # Merge multiple notes into one
            if len(remaining_args) < 2:
                result = ZettlFormatter.error("Must provide at least 2 notes to merge")
            else:
                note_ids = remaining_args
                force = 'f' in flags or 'force' in flags

                # Show preview of notes to be merged
                result = f"{ZettlFormatter.header(f'Notes to merge ({len(note_ids)} total):')}\n\n"

                all_tags = set()
                valid_notes = True

                for note_id in note_ids:
                    try:
                        note = notes_manager.get_note(note_id)
                        content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                        formatted_id = ZettlFormatter.note_id(note_id)
                        result += f"{formatted_id}\n"
                        result += f"  {content_preview}\n"

                        # Show tags
                        try:
                            tags = notes_manager.get_tags(note_id)
                            if tags:
                                all_tags.update(tags)
                                result += f"  Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}\n"
                        except Exception:
                            pass

                        result += "\n"
                    except Exception as e:
                        result = ZettlFormatter.error(f"Error fetching note {note_id}: {str(e)}")
                        valid_notes = False
                        break

                if valid_notes:
                    # Show what will be preserved
                    if all_tags:
                        result += f"{ZettlFormatter.header('Tags that will be added to merged note:')}\n"
                        result += f"{', '.join([ZettlFormatter.tag(t) for t in sorted(all_tags)])}\n\n"

                    # In web version, we can't do interactive confirmation easily
                    # So we'll proceed if force is set, otherwise show warning
                    if not force:
                        result += f"{ZettlFormatter.warning('⚠️  This will delete the original notes!')}\n"
                        result += f"{ZettlFormatter.warning('Use --force to proceed with merge')}\n"
                    else:
                        # Perform the merge
                        try:
                            merged_note_id = notes_manager.merge_notes(list(note_ids))
                            result = ZettlFormatter.success(f"Successfully merged {len(note_ids)} notes into #{merged_note_id}")
                            result += f"\n\nView merged note with: show {merged_note_id}"
                        except Exception as e:
                            result = ZettlFormatter.error(f"Error merging notes: {str(e)}")

        elif cmd == "rules":
            # Parse the source flag
            source = 'source' in flags or 's' in flags
            
            # Get all notes tagged with 'rules'
            rules_notes = notes_manager.get_notes_by_tag('rules')
            
            if not rules_notes:
                result = ZettlFormatter.warning("No notes found with tag 'rules'")
            else:
                # Extract rules from all notes
                all_rules = []
                
                for note in rules_notes:
                    note_id = note['id']
                    content = note['content']
                    
                    # Try to parse numbered rules (like "1. Rule text")
                    lines = content.split('\n')
                    rule_starts = []
                    
                    # Find line numbers where rules start
                    for i, line in enumerate(lines):
                        if re.match(r'^\s*\d+[\.\)]\s+', line):
                            rule_starts.append(i)
                    
                    if rule_starts:
                        # This note contains numbered rules
                        for i, start_idx in enumerate(rule_starts):
                            # Determine where this rule ends (next rule start or end of note)
                            end_idx = rule_starts[i+1] if i+1 < len(rule_starts) else len(lines)
                            
                            # Extract the rule text
                            rule_lines = lines[start_idx:end_idx]
                            full_text = '\n'.join(rule_lines).strip()
                            
                            rule = {
                                'note_id': note_id,
                                'full_text': full_text
                            }
                            all_rules.append(rule)
                    else:
                        # This note doesn't have numbered items, treat it as a single rule
                        rule = {
                            'note_id': note_id,
                            'full_text': content.strip()
                        }
                        all_rules.append(rule)
                        
                if not all_rules:
                    result = ZettlFormatter.warning("Couldn't extract any rules from the notes")
                else:
                    # Import random if not already imported
                    import random
                    
                    # Select a random rule
                    random_rule = random.choice(all_rules)
                    
                    # Display the rule
                    result = f"{ZettlFormatter.header('Random Rule')}\n\n"
                    
                    if source:
                        # Show the source note ID
                        result += f"Source: {ZettlFormatter.note_id(random_rule['note_id'])}\n\n"
                    
                    # Always show the full rule
                    result += random_rule['full_text']

        elif cmd == "todos":
            # Check for Eisenhower matrix flag
            eisenhower = 'e' in flags or 'eisenhower' in flags
            
            # Handle existing options
            donetoday = 'donetoday' in options or 'dt' in flags
            all_todos = 'all' in options or 'a' in flags
            cancel = 'cancel' in options or 'c' in options
            filter_tags = []
            done = all_todos
            if 'tag' in options:
                if isinstance(options['tag'], list):  # Multiple tags
                    filter_tags.extend(options['tag'])
                else:  # Single tag
                    filter_tags.append(options['tag'])
            
            # Get all notes tagged with 'todo'
            todo_notes = notes_manager.get_notes_by_tag('todo')
            
            if not todo_notes:
                result = ZettlFormatter.warning("No todos found.")
            else:
                if eisenhower:
                    # Display Eisenhower matrix
                    result = format_eisenhower_matrix(todo_notes, all_todos, donetoday, cancel, filter_tags)
                else:
                        # Get notes with 'done' tag added today (for donetoday option)
                        done_today_ids = set()
                        if donetoday:
                            from datetime import datetime, timezone
                            import logging
                            
                            # Get today's date in UTC for consistent comparison
                            today = datetime.now(timezone.utc).date()
                            logger.debug(f"Today's date (UTC): {today}")
                            
                            try:
                                # Get tags created today using the proper PostgREST method
                                done_tags_today = notes_manager.db.get_tags_created_today('done')

                                logger.debug(f"Found {len(done_tags_today)} 'done' tags created today")
                                for tag_data in done_tags_today:
                                    note_id = tag_data.get('note_id')
                                    if note_id:
                                        done_today_ids.add(note_id)
                                        logger.debug(f"Added note_id {note_id} to done today list")

                                logger.debug(f"Total todos done today: {len(done_today_ids)}")
                            except Exception as e:
                                error_msg = f"Could not determine todos completed today: {str(e)}"
                                logger.error(error_msg)
                                result += f"{ZettlFormatter.warning(error_msg)}\n\n"
                        
                        # Apply filters if specified
                        if filter_tags:
                            filtered_notes = []
                            
                            for note in todo_notes:
                                note_id = note['id']
                                tags = [t.lower() for t in notes_manager.get_tags(note_id)]
                                
                                # Check if all filters are in the note's tags
                                if all(f.lower() in tags for f in filter_tags):
                                    filtered_notes.append(note)
                                    
                            todo_notes = filtered_notes
                            
                            if not todo_notes:
                                filter_str = "', '".join(filter_tags)
                                result = ZettlFormatter.warning(f"No todos found with all tags: '{filter_str}'.")
                                return jsonify({'result': ansi_to_html(result)})
                        
                        # Group notes by their tags (categories)
                        active_todos_by_category = {}
                        done_todos_by_category = {}
                        donetoday_todos_by_category = {}
                        canceled_todos_by_category = {}  # New dict for canceled todos
                        uncategorized_active = []
                        uncategorized_done = []
                        uncategorized_donetoday = []
                        uncategorized_canceled = []  # New list for uncategorized canceled todos
                        
                        # Track unique note IDs to count them at the end
                        unique_active_ids = set()
                        unique_done_ids = set()
                        unique_donetoday_ids = set()
                        unique_canceled_ids = set()  # New set for canceled todos
                        
                        for note in todo_notes:
                            note_id = note['id']
                            # Get all tags for this note
                            tags = notes_manager.get_tags(note_id)
                            tags_lower = [t.lower() for t in tags]
                            
                            # Check if this is a done todo
                            is_done = 'done' in tags_lower
                            
                            # Check if this is a canceled todo
                            is_canceled = 'cancel' in tags_lower
                            
                            # Check if this is done today
                            is_done_today = note_id in done_today_ids
                            
                            # Skip done todos if not explicitly included, unless they're done today and we want those
                            if is_done and not done and not (is_done_today and donetoday):
                                continue
                                
                            # Skip canceled todos if not explicitly requested
                            if is_canceled and not cancel:
                                continue
                                
                            # Track unique IDs
                            if is_canceled:
                                unique_canceled_ids.add(note_id)
                            elif is_done_today and donetoday:
                                unique_donetoday_ids.add(note_id)
                            elif is_done:
                                unique_done_ids.add(note_id)
                            else:
                                unique_active_ids.add(note_id)
                            
                            # Find category tags (everything except 'todo', 'done', 'cancel', and the filter tags)
                            excluded_tags = ['todo', 'done', 'cancel']  # Added 'cancel' to exclusion list
                            if filter_tags:
                                excluded_tags.extend([f.lower() for f in filter_tags])
                                
                            categories = [tag for tag in tags if tag.lower() not in excluded_tags]
                            
                            # Assign note to appropriate category group
                            if not categories:
                                # This todo has no category tags
                                if is_canceled:
                                    uncategorized_canceled.append(note)
                                elif is_done_today and donetoday:
                                    uncategorized_donetoday.append(note)
                                elif is_done:
                                    uncategorized_done.append(note)
                                else:
                                    uncategorized_active.append(note)
                            else:
                                # Create a combined category key from all tags
                                if categories:
                                    combined_category = " - ".join(sorted(categories))
                                    
                                    if is_canceled:
                                        if combined_category not in canceled_todos_by_category:
                                            canceled_todos_by_category[combined_category] = []
                                        if note not in canceled_todos_by_category[combined_category]:
                                            canceled_todos_by_category[combined_category].append(note)
                                    elif is_done_today and donetoday:
                                        if combined_category not in donetoday_todos_by_category:
                                            donetoday_todos_by_category[combined_category] = []
                                        if note not in donetoday_todos_by_category[combined_category]:
                                            donetoday_todos_by_category[combined_category].append(note)
                                    elif is_done:
                                        if combined_category not in done_todos_by_category:
                                            done_todos_by_category[combined_category] = []
                                        if note not in done_todos_by_category[combined_category]:
                                            done_todos_by_category[combined_category].append(note)
                                    else:
                                        if combined_category not in active_todos_by_category:
                                            active_todos_by_category[combined_category] = []
                                        if note not in active_todos_by_category[combined_category]:
                                            active_todos_by_category[combined_category].append(note)
                                                
                        # Build the header message
                        header_parts = ["Todos"]
                        if filter_tags:
                            filter_str = "', '".join(filter_tags)
                            header_parts.append(f"tagged with '{filter_str}'")
                        
                        # Prepare the result
                        result = ""
                        
                        # Display todos by category
                        if (not active_todos_by_category and not uncategorized_active and 
                            (not done or (not done_todos_by_category and not uncategorized_done)) and
                            (not donetoday or (not donetoday_todos_by_category and not uncategorized_donetoday)) and
                            (not cancel or (not canceled_todos_by_category and not uncategorized_canceled))):
                            result = ZettlFormatter.warning("No todos match your criteria.")
                            return jsonify({'result': ansi_to_html(result)})
                                    
                        def display_todos_group(category_dict, uncategorized_list, header_text):
                            output = ""
                            if header_text:
                                output += f"{header_text}\n\n"
                            
                            if category_dict:
                                for category, notes in sorted(category_dict.items()):
                                    # Check if this is a combined category with multiple tags
                                    if " - " in category:
                                        # For combined categories, format each tag separately
                                        tags = category.split(" - ")
                                        formatted_tags = []
                                        for tag in tags:
                                            formatted_tags.append(ZettlFormatter.tag(tag))
                                        category_display = " - ".join(formatted_tags)
                                        output += f"{category_display} ({len(notes)})\n\n"
                                    else:
                                        # For single categories, use the original format
                                        output += f"{ZettlFormatter.tag(category)} ({len(notes)})\n\n"
                                    
                                    for note in notes:
                                        formatted_id = ZettlFormatter.note_id(note['id'])
                                        
                                        # Format with indentation
                                        content_lines = note['content'].split('\n')
                                        output += f"  {formatted_id}: {content_lines[0]}\n"
                                        if len(content_lines) > 1:
                                            for line in content_lines[1:]:
                                                output += f"      {line}\n"
                                        output += "\n"  # Add an empty line between notes
                                
                            if uncategorized_list:
                                output += "Uncategorized\n\n"
                                for note in uncategorized_list:
                                    formatted_id = ZettlFormatter.note_id(note['id'])
                                    
                                    # Format with indentation
                                    content_lines = note['content'].split('\n')
                                    output += f"  {formatted_id}: {content_lines[0]}\n"
                                    if len(content_lines) > 1:
                                        for line in content_lines[1:]:
                                            output += f"      {line}\n"
                                    output += "\n"  # Add an empty line between notes
                            
                            return output
                    
                        # Display active todos first
                        if active_todos_by_category or uncategorized_active:
                            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
                            result += display_todos_group(active_todos_by_category, uncategorized_active, active_header)
                        
                        # Display done today todos if requested
                        if donetoday:
                            if donetoday_todos_by_category or uncategorized_donetoday:
                                donetoday_header = ZettlFormatter.header(f"Completed Today {' '.join(header_parts)} ({len(unique_donetoday_ids)} total)")
                                result += "\n" + display_todos_group(donetoday_todos_by_category, uncategorized_donetoday, donetoday_header)
                            else:
                                result += "\n" + ZettlFormatter.warning("No todos were completed today.")
                        
                        # Display all done todos if requested
                        if done and (done_todos_by_category or uncategorized_done):
                            # Exclude today's completed todos if they're shown in their own section
                            if donetoday:
                                # Filter out notes that are done today from the regular done section
                                for category in list(done_todos_by_category.keys()):
                                    done_todos_by_category[category] = [
                                        note for note in done_todos_by_category[category] 
                                        if note['id'] not in done_today_ids
                                    ]
                                    # Remove empty categories
                                    if not done_todos_by_category[category]:
                                        del done_todos_by_category[category]
                                
                                # Filter uncategorized done notes too
                                uncategorized_done = [
                                    note for note in uncategorized_done 
                                    if note['id'] not in done_today_ids
                                ]
                            
                            # Only show this section if there are notes to display after filtering
                            if done_todos_by_category or uncategorized_done:
                                done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids - unique_donetoday_ids)} total)")
                                result += "\n" + display_todos_group(done_todos_by_category, uncategorized_done, done_header)

                            # Display canceled todos if requested
                            if cancel and (canceled_todos_by_category or uncategorized_canceled):
                                canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
                                result += "\n" + display_todos_group(canceled_todos_by_category, uncategorized_canceled, canceled_header)

                        
        elif cmd == "help" or cmd == "--help":
            result = CommandHelp.get_main_help()

        elif cmd == "api-key" or cmd == "apikey":
            # Handle API key operations
            if not remaining_args:
                # List existing API keys
                try:
                    token = session.get('access_token')
                    if not token:
                        result = ZettlFormatter.error("Not authenticated. Please login first.")
                    else:
                        response = requests.get(f'{AUTH_URL}/api/auth/api-keys',
                                              headers={'Authorization': f'Bearer {token}'})
                        if response.status_code == 200:
                            api_keys = response.json()
                            if api_keys:
                                result = "🔑 Your API Keys:\n\n"
                                for key in api_keys:
                                    created = key.get('created_at', 'Unknown')
                                    name = key.get('name', 'Unnamed')
                                    last_used = key.get('last_used', 'Never')
                                    result += f"• {name}\n"
                                    result += f"  Created: {created}\n"
                                    result += f"  Last used: {last_used}\n\n"
                            else:
                                result = "No API keys found. Use 'api-key generate' to create one."
                        else:
                            result = ZettlFormatter.error("Failed to list API keys")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error listing API keys: {str(e)}")
            elif remaining_args[0] == "generate" or remaining_args[0] == "create":
                # Generate new API key
                try:
                    token = session.get('access_token')
                    if not token:
                        result = ZettlFormatter.error("Not authenticated. Please login first.")
                    else:
                        key_name = remaining_args[1] if len(remaining_args) > 1 else "Web Interface Key"
                        response = requests.post(f'{AUTH_URL}/api/auth/api-key',
                                               headers={'Authorization': f'Bearer {token}'},
                                               json={'name': key_name})
                        if response.status_code == 200:
                            api_key = response.json()['apiKey']
                            result = "🎉 API Key Generated Successfully!\n\n"
                            result += f"🔑 Your new API key: {api_key}\n\n"
                            result += "⚠️  IMPORTANT: Copy this key now! You won't be able to see it again.\n\n"
                            result += "To use this key with the CLI:\n"
                            result += f"  export ZETTL_API_KEY={api_key}\n"
                            result += "  # OR\n"
                            result += "  zettl auth setup\n"
                        else:
                            result = ZettlFormatter.error("Failed to generate API key")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error generating API key: {str(e)}")
            else:
                result = ZettlFormatter.error("Usage: api-key [list|generate [name]]")

        elif cmd == "nutrition" or cmd == "nut":
            # Handle nutrition commands with the new structure
            tracker = NutritionTracker()
            
            # Check for flags/options
            today = 't' in flags or 'today' in flags
            history = 'i' in flags or 'history' in flags
            days = int(options.get('days', options.get('d', 7)))  # Default to 7 days
            past = options.get('past', options.get('p', None))  # Date for past entries
            
            # Determine what action to take based on provided options
            if today:
                # Show today's summary
                try:
                    result = tracker.format_today_summary()
                except Exception as e:
                    result = ZettlFormatter.error(str(e))
            elif history:
                # Show history
                try:
                    result = tracker.format_history(days=days)
                except Exception as e:
                    result = ZettlFormatter.error(str(e))
            elif remaining_args:
                # Add new entry (default behavior when content is provided)
                content = remaining_args[0]
                try:
                    data = tracker.parse_nutrition_data(content)
                    if not data:
                        result = ZettlFormatter.error("Invalid nutrition data format. Use 'cal: XXX prot: YYY'")
                    else:
                        # Get current calories/protein values
                        calories = data.get('calories', 0)
                        protein = data.get('protein', 0)
                        
                        # Create the note with optional past date
                        note_id = tracker.add_entry(content, past_date=past)
                        
                        # Determine what day to show in the message
                        date_label = f"for {past}" if past else ""
                        result = f"Added nutrition entry #{note_id} {date_label}\n\n"
                        
                        # Show today's totals if no past date was specified
                        if not past:
                            try:
                                today_entries = tracker.get_today_entries()
                                
                                total_calories = sum(entry['nutrition_data'].get('calories', 0) for entry in today_entries)
                                total_protein = sum(entry['nutrition_data'].get('protein', 0) for entry in today_entries)
                                
                                result += f"Today's totals so far:\n"
                                result += f"Calories: {total_calories:.1f}\n"
                                result += f"Protein: {total_protein:.1f}g"
                            except Exception as e:
                                result += f"\nEntry added with:\n"
                                result += f"Calories: {calories:.1f}\n"
                                result += f"Protein: {protein:.1f}g"
                        else:
                            # Just show the entry's values for past entries
                            result += f"\nEntry added with:\n"
                            result += f"Calories: {calories:.1f}\n"
                            result += f"Protein: {protein:.1f}g"
                except Exception as e:
                    result = ZettlFormatter.error(str(e))
            else:
                # If no options specified, show today's summary as default behavior
                try:
                    result = tracker.format_today_summary()
                except Exception as e:
                    result = ZettlFormatter.error(str(e))         

        else:
            result = f"Unknown command: {cmd}. Try 'help' for available commands."
            
        logger.debug(f"Command result: {result[:100]}...")
        
        # Convert ANSI color codes to HTML
        result = ansi_to_html(result)
        return jsonify({'result': result})
        
    except Exception as e:
        logger.exception(f"Error executing command: {e}")

        # Provide more specific error messages based on the type of error
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            error_msg = ZettlFormatter.error("Authentication failed. Please log out and log back in.")
        elif "connection" in error_str or "timeout" in error_str:
            error_msg = ZettlFormatter.error("Database connection error. Please try again.")
        elif "404" in error_str or "not found" in error_str:
            error_msg = ZettlFormatter.error("Requested resource not found.")
        else:
            error_msg = ZettlFormatter.error(f"Command execution failed: {str(e)}")

        return jsonify({'result': ansi_to_html(error_msg)})


def format_eisenhower_matrix(todo_notes, include_done=False, include_donetoday=False, include_cancel=False, filter_tags=None):
    """Format todos in an Eisenhower matrix for web display."""
    # Create four quadrants for Eisenhower categorization
    urgent_important = []      # do - Quadrant 1
    not_urgent_important = []  # pl - Quadrant 2
    urgent_not_important = []  # dl - Quadrant 3
    not_urgent_not_important = []  # dr - Quadrant 4
    uncategorized = []
    done_todos = []            # Completed todos
    canceled_todos = []        # Canceled todos
    
    # Track unique note IDs for counting
    unique_ids = set()
    
    # Get notes with 'done' tag added today
    done_today_ids = set()
    if include_donetoday:
        from datetime import datetime, timedelta, timezone
        today = datetime.now(timezone.utc).date()
        
        try:
            # Get tags created today using the proper PostgREST method
            done_tags_today = notes_manager.db.get_tags_created_today('done')

            for tag_data in done_tags_today:
                note_id = tag_data.get('note_id')
                if note_id:
                    done_today_ids.add(note_id)
        except Exception as e:
            logger.error(f"Could not determine todos completed today: {str(e)}")
    
    # Filter by tag if specified
    if filter_tags:
        filtered_notes = []
        for note in todo_notes:
            note_id = note['id']
            note_tags = [t.lower() for t in notes_manager.get_tags(note_id)]
            
            # Check if all filter tags are present
            if all(f.lower() in note_tags for f in filter_tags):
                filtered_notes.append(note)
        todo_notes = filtered_notes
    
    for note in todo_notes:
        note_id = note['id']
        # Get all tags for this note
        note_tags = notes_manager.get_tags(note_id)
        tags_lower = [t.lower() for t in note_tags]
        
        # Check status flags
        is_done = 'done' in tags_lower
        is_canceled = 'cancel' in tags_lower
        is_done_today = note_id in done_today_ids
        
        # Skip based on flags
        if is_canceled and not include_cancel:
            continue
            
        if is_done and not include_done and not (is_done_today and include_donetoday):
            continue
        
        # Add to appropriate category
        if is_canceled:
            canceled_todos.append(note)
        elif is_done:
            done_todos.append(note)
        elif 'do' in tags_lower:
            urgent_important.append(note)
        elif 'pl' in tags_lower:
            not_urgent_important.append(note)
        elif 'dl' in tags_lower:
            urgent_not_important.append(note)
        elif 'dr' in tags_lower:
            not_urgent_not_important.append(note)
        else:
            uncategorized.append(note)
        
        # Track all displayed todos
        unique_ids.add(note_id)
    
    # Start building HTML output
    output = f"<div style='margin-bottom: 20px;'>{ZettlFormatter.header('Eisenhower Matrix')}</div>"
    output += f"<div style='margin-bottom: 20px;'>Total todos: {len(unique_ids)}</div>"
    
    # Helper to format a single note for HTML
    def format_note_html(note):
        formatted_id = ZettlFormatter.note_id(note['id'])
        formatted_id = ansi_to_html(formatted_id)  # Convert ANSI colors to HTML
        content_lines = note['content'].split('\n')
        return f"<div style='margin: 5px 0'>{formatted_id}: {content_lines[0]}</div>"
    
    # Store the counts
    do_count = len(urgent_important)
    plan_count = len(not_urgent_important)
    delegate_count = len(urgent_not_important)
    drop_count = len(not_urgent_not_important)
    
    # Create HTML matrix table with explicit count values
    output += f"""
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr>
          <th style="width: 15%;"></th>
          <th style="width: 42.5%; color: #ffff00; text-align: center; padding: 10px; border: 1px solid #444;">URGENT</th>
          <th style="width: 42.5%; color: #ffff00; text-align: center; padding: 10px; border: 1px solid #444;">NOT URGENT</th>
        </tr>
        <tr>
          <th style="text-align: center; padding: 10px; border: 1px solid #444; font-weight: bold;">IMPORTANT</th>
          <td style="border: 1px solid #444; padding: 10px; vertical-align: top; background-color: rgba(0, 255, 0, 0.05);">
            <div style="color: #90ee90; font-weight: bold; margin-bottom: 10px;">DO ({do_count})</div>
    """
    
    # Add Q1 todos (Do - Urgent & Important)
    for note in urgent_important:
        output += format_note_html(note)
    
    output += f"""
          </td>
          <td style="border: 1px solid #444; padding: 10px; vertical-align: top; background-color: rgba(0, 0, 255, 0.05);">
            <div style="color: #add8e6; font-weight: bold; margin-bottom: 10px;">PLAN ({plan_count})</div>
    """
    
    # Add Q2 todos (Plan - Not Urgent & Important)
    for note in not_urgent_important:
        output += format_note_html(note)
    
    output += f"""
          </td>
        </tr>
        <tr>
          <th style="text-align: center; padding: 10px; border: 1px solid #444; font-weight: bold;">NOT<br>IMPORTANT</th>
          <td style="border: 1px solid #444; padding: 10px; vertical-align: top; background-color: rgba(255, 255, 0, 0.05);">
            <div style="color: #ffff00; font-weight: bold; margin-bottom: 10px;">DELEGATE ({delegate_count})</div>
    """
    
    # Add Q3 todos (Delegate - Urgent & Not Important)
    for note in urgent_not_important:
        output += format_note_html(note)
    
    output += f"""
          </td>
          <td style="border: 1px solid #444; padding: 10px; vertical-align: top; background-color: rgba(255, 0, 0, 0.05);">
            <div style="color: #ff6347; font-weight: bold; margin-bottom: 10px;">DROP ({drop_count})</div>
    """
    
    # Add Q4 todos (Drop - Not Urgent & Not Important)
    for note in not_urgent_not_important:
        output += format_note_html(note)
    
    output += """
          </td>
        </tr>
      </table>
    </div>
    """
    
    # Display additional categories if requested
    if uncategorized:
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ansi_to_html(ZettlFormatter.warning(f'Uncategorized Todos ({len(uncategorized)})'))}:</div>"
        for note in uncategorized:
            output += format_note_html(note)
    
    if include_done and done_todos:
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ansi_to_html(ZettlFormatter.header(f'Completed Todos ({len(done_todos)})'))}:</div>"
        for note in done_todos:
            output += format_note_html(note)
    
    if include_cancel and canceled_todos:
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ansi_to_html(ZettlFormatter.header(f'Canceled Todos ({len(canceled_todos)})'))}:</div>"
        for note in canceled_todos:
            output += format_note_html(note)
    
    return output




if __name__ == '__main__':
    logger.info("Starting Zettl Web Server...")
    # For development - set host to 0.0.0.0 to access from other devices on network
    app.run(debug=True, host='0.0.0.0', port=5001)