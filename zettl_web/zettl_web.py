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

from zettl.help import CommandHelp

# Load environment variables from parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
dotenv_path = os.path.join(parent_dir, '.env')
print(f"Looking for .env file at: {dotenv_path}")
print(f"File exists: {os.path.exists(dotenv_path)}")
load_dotenv(dotenv_path)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
from zettl.formatting import ZettlFormatter
from zettl.help import CommandHelp

# Set formatter and help to web mode for markdown output
ZettlFormatter.set_mode('web')
CommandHelp.set_mode('web')

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
    """Get an LLM helper instance with the current user's JWT token and Claude API key."""
    # Get JWT token from session
    jwt_token = session.get('access_token')

    # Fetch Claude API key from auth service (via Docker network)
    claude_api_key = None
    try:
        url = f'{AUTH_URL}/api/auth/settings/claude-key'
        logger.info(f"Fetching Claude API key from: {url}")
        response = requests.get(
            url,
            headers={'Authorization': f'Bearer {jwt_token}'},
            timeout=5
        )
        logger.info(f"Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            claude_api_key = data.get('claude_api_key')
            logger.info(f"Claude API key fetched: {'YES' if claude_api_key else 'NO'}")
        else:
            logger.warning(f"Failed to fetch Claude key: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Could not fetch Claude API key: {e}")

    # Create LLMHelper instance
    llm_helper = LLMHelper(jwt_token=jwt_token)

    # Override the api_key if we successfully fetched it
    if claude_api_key:
        llm_helper.api_key = claude_api_key
    else:
        logger.warning("No Claude API key available for LLMHelper")

    return llm_helper

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
            't': {'name': 'tag', 'multiple': True},
            'f': {'name': 'full', 'flag': True}
        },
        'long_opts': {
            'tag': {'multiple': True},
            'exclude-tag': {'multiple': True},
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
    'api-key': {
        'short_opts': {
            'g': {'name': 'generate', 'flag': True},
            'l': {'name': 'list', 'flag': True}
        },
        'long_opts': {
            'generate': {'flag': True},
            'list': {'flag': True}
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
    'edit': {
        'short_opts': {},
        'long_opts': {}
    },
    'task': {
        'short_opts': {
            't': {'name': 'tag', 'multiple': True},
            'l': {'name': 'link'}
        },
        'long_opts': {
            'tag': {'multiple': True},
            'link': {},
            'id': {}
        }
    },
    'idea': {
        'short_opts': {
            't': {'name': 'tag', 'multiple': True},
            'l': {'name': 'link'}
        },
        'long_opts': {
            'tag': {'multiple': True},
            'link': {},
            'id': {}
        }
    },
    'note': {
        'short_opts': {
            't': {'name': 'tag', 'multiple': True},
            'l': {'name': 'link'}
        },
        'long_opts': {
            'tag': {'multiple': True},
            'link': {},
            'id': {}
        }
    },
    'project': {
        'short_opts': {
            't': {'name': 'tag', 'multiple': True},
            'l': {'name': 'link'}
        },
        'long_opts': {
            'tag': {'multiple': True},
            'link': {},
            'id': {}
        }
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
                # Handle multiple exclude tags
                if 'exclude-tag' not in options:
                    options['exclude-tag'] = []
                options['exclude-tag'].append(args[i+1])
                i += 2
            else:
                # If +t without value, treat as flag
                if 'exclude-tag' not in options:
                    options['exclude-tag'] = []
                options['exclude-tag'].append(True)
                i += 1
        else:
            # Add this else clause to capture non-option arguments
            remaining_args.append(arg)
            i += 1
            
    return options, flags, remaining_args

# Simplified HTML processing for markdown content
def process_for_web(text):
    """
    Process text for web display - everything is treated as markdown unless it's already HTML.
    No ANSI codes, no special markers needed.
    """
    # If the text already contains HTML tags (like from Eisenhower matrix), don't wrap it in markdown-content
    # This allows raw HTML to pass through for complex layouts like tables
    if '<div' in text or '<table' in text or '<span' in text:
        return text

    # Otherwise, wrap in markdown-content div for markdown rendering
    return f'<div class="markdown-content">{text}</div>'

def format_note_content_for_web(note, notes_manager):
    """Format a note for web display with markdown support."""
    note_id = note['id']
    created_at = notes_manager.db.format_timestamp(note['created_at'])

    formatted_id = ZettlFormatter.note_id(note_id)
    formatted_time = ZettlFormatter.timestamp(created_at)

    header_line = f"{formatted_id} [{formatted_time}]"
    separator = "-" * 40

    # Return formatted parts - everything is markdown now
    return {
        'header': header_line,
        'separator': separator,
        'content': note['content'],
        'is_markdown': True
    }

def show_command_help(cmd):
    """Show detailed help for a specific command."""
    help_text = CommandHelp.get_command_help(cmd)
    return jsonify({'result': process_for_web(help_text)})


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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker healthcheck"""
    return jsonify({'status': 'healthy'}), 200

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

@app.route('/settings')
@jwt_required
def settings_page():
    """Display the settings page."""
    user = getattr(request, 'current_user', session.get('user', {}))
    username = user.get('username', 'Unknown')
    logger.debug(f"Rendering settings page for user: {username}")
    return render_template('settings.html', username=username)

@app.route('/api/settings/data', methods=['GET'])
@jwt_required
def get_settings_data():
    """Get current user settings and CLI tokens."""
    try:
        user_id = request.current_user.get('id')
        token = session.get('access_token')

        # Get user settings from auth service
        response = requests.get(
            f'{AUTH_URL}/api/auth/settings',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'data': response.json()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch settings'
            }), response.status_code

    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings/claude-key', methods=['POST'])
@jwt_required
def update_claude_key():
    """Update Claude API key for the current user."""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()

        # Basic validation
        if api_key and not api_key.startswith('sk-ant-'):
            return jsonify({
                'success': False,
                'error': 'Invalid API key format. Claude API keys start with "sk-ant-"'
            }), 400

        token = session.get('access_token')

        # Send to auth service
        response = requests.post(
            f'{AUTH_URL}/api/auth/settings/claude-key',
            headers={'Authorization': f'Bearer {token}'},
            json={'api_key': api_key},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Claude API key updated successfully'
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'success': False,
                'error': error_data.get('error', 'Failed to update API key')
            }), response.status_code

    except Exception as e:
        logger.error(f"Error updating Claude API key: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings/hidden-buttons', methods=['POST'])
@jwt_required
def update_hidden_buttons():
    """Update hidden buttons preference for the current user."""
    try:
        data = request.get_json()
        hidden_buttons = data.get('hidden_buttons', [])

        # Basic validation - ensure it's a list
        if not isinstance(hidden_buttons, list):
            return jsonify({
                'success': False,
                'error': 'hidden_buttons must be an array'
            }), 400

        token = session.get('access_token')

        # Send to auth service
        response = requests.post(
            f'{AUTH_URL}/api/auth/settings/hidden-buttons',
            headers={'Authorization': f'Bearer {token}'},
            json={'hidden_buttons': hidden_buttons},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Button preferences updated successfully'
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'success': False,
                'error': error_data.get('error', 'Failed to update button preferences')
            }), response.status_code

    except Exception as e:
        logger.error(f"Error updating hidden buttons: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cli-token/generate', methods=['POST'])
@jwt_required
def generate_cli_token():
    """Generate a new CLI access token."""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'CLI Token')

        token = session.get('access_token')

        # Generate token via auth service
        response = requests.post(
            f'{AUTH_URL}/api/auth/cli-token',
            headers={'Authorization': f'Bearer {token}'},
            json={'name': name},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                **response.json()
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'success': False,
                'error': error_data.get('error', 'Failed to generate token')
            }), response.status_code

    except Exception as e:
        logger.error(f"Error generating CLI token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cli-token/<int:token_id>', methods=['DELETE'])
@jwt_required
def revoke_cli_token(token_id):
    """Revoke a CLI access token."""
    try:
        token = session.get('access_token')

        # Revoke token via auth service
        response = requests.delete(
            f'{AUTH_URL}/api/auth/cli-token/{token_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Token revoked successfully'
            })
        else:
            error_data = response.json() if response.content else {}
            return jsonify({
                'success': False,
                'error': error_data.get('error', 'Failed to revoke token')
            }), response.status_code

    except Exception as e:
        logger.error(f"Error revoking CLI token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update-note', methods=['POST'])
@jwt_required
def update_note():
    """API endpoint to update note content from the edit modal."""
    data = request.json
    note_id = data.get('note_id')
    content = data.get('content')

    if not note_id or content is None:
        return jsonify({'error': 'Missing note_id or content'}), 400

    try:
        notes_manager = get_notes_manager()
        notes_manager.update_note(note_id, content)
        return jsonify({
            'success': True,
            'message': f'Updated note #{note_id}'
        })
    except Exception as e:
        logger.exception(f"Error updating note {note_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        return jsonify({'result': process_for_web(error_msg)})

    # Parse the command with better handling for options and quotes
    cmd, args = parse_command(command)

    # Map shortcut commands to their full versions
    command_map = {
        't': 'task',
        'i': 'idea',
        'n': 'note',
        'p': 'project'
    }

    # Apply command mapping for shortcuts
    if cmd in command_map:
        cmd = command_map[cmd]

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


        elif cmd in ["task", "idea", "note", "project"]:
            # Handle specialized note creation commands with @ linking support
            import re

            # Parse @ project links from content
            def parse_project_links(content):
                """Extract @project references from content and return cleaned content and project IDs."""
                pattern = r'@(\S+)'
                project_ids = re.findall(pattern, content)
                # Remove @ references from content
                cleaned_content = re.sub(pattern, '', content).strip()
                return cleaned_content, project_ids

            # Join remaining args into content string (support multiple words without quotes)
            content = ' '.join(remaining_args) if remaining_args else ""

            # Parse and remove @ references from content
            cleaned_content, project_links = parse_project_links(content)

            # Get custom ID if provided
            custom_id = options.get('id', '')

            # Get tags from options
            tags = []
            if 'tag' in options:
                if isinstance(options['tag'], list):
                    tags.extend(options['tag'])
                else:
                    tags.append(options['tag'])

            # Add automatic tags based on command type
            auto_tags = []
            if cmd == "task":
                auto_tags = ['task', 'todo']
            elif cmd == "idea":
                auto_tags = ['idea']
            elif cmd == "note":
                auto_tags = ['note']
            elif cmd == "project":
                auto_tags = ['project']

            # Create the note with custom ID if provided
            if custom_id:
                try:
                    from datetime import datetime
                    now = datetime.now().isoformat()
                    note_id = notes_manager.create_note_with_timestamp(cleaned_content, now, custom_id)
                    result = f"Created {cmd} #{note_id}\n"
                except Exception as e:
                    # If custom ID already exists, use regular creation
                    if "already exists" in str(e) or "duplicate" in str(e).lower():
                        note_id = notes_manager.create_note(cleaned_content)
                        result = f"Created {cmd} #{note_id} (custom ID '{custom_id}' already exists)\n"
                    else:
                        raise e
            else:
                note_id = notes_manager.create_note(cleaned_content)
                result = f"Created {cmd} #{note_id}\n"

            # Add automatic tags
            for tag in auto_tags:
                try:
                    notes_manager.add_tag(note_id, tag)
                    result += f"Added tag '{tag}' to note #{note_id}\n"
                except Exception as e:
                    result += f"{ZettlFormatter.warning(f'Could not add tag {tag}: {str(e)}')}\n"

            # Add user-provided tags
            for tag in tags:
                if tag and tag not in auto_tags:
                    try:
                        notes_manager.add_tag(note_id, tag)
                        result += f"Added tag '{tag}' to note #{note_id}\n"
                    except Exception as e:
                        result += f"{ZettlFormatter.warning(f'Could not add tag {tag}: {str(e)}')}\n"

            # Create links from @ references
            for project_id in project_links:
                try:
                    notes_manager.create_link(note_id, project_id)
                    result += f"Created link from #{note_id} to project #{project_id}\n"
                except Exception as e:
                    result += f"{ZettlFormatter.warning(f'Could not create link to project #{project_id}: {str(e)}')}\n"

            # Create link from -l option if provided
            link = options.get('link', options.get('l', ''))
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

                    # Format header
                    result = f"{ZettlFormatter.note_id(note_id)} [{ZettlFormatter.timestamp(created_at)}]\n"
                    result += "-" * 40 + "\n"
                    # Add content
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
            # Import re module for pattern matching in search highlighting
            import re

            # Parse options - handle both single values and lists
            tags = options.get('tag', [])
            exclude_tags = options.get('exclude-tag', [])

            # Ensure tags and exclude_tags are always lists
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            if not isinstance(exclude_tags, list):
                exclude_tags = [exclude_tags] if exclude_tags else []

            full = 'f' in flags or 'full' in flags
            query = remaining_args[0] if remaining_args else ""
            search_description = []

            # Step 1: Get initial result set based on primary criteria
            if query:
                # Search by content
                search_results = notes_manager.search_notes(query)
                if not search_results:
                    result = ZettlFormatter.warning(f"No notes found containing '{query}'")
                else:
                    search_description.append(f"containing '{query}'")
                    result = ""
            else:
                # No primary search criteria - start with all notes
                # If we have any tag filters, we need to search ALL notes
                if tags or exclude_tags:
                    search_results = notes_manager.list_notes(limit=10000)
                    result = ""
                else:
                    # No filters at all - just list recent notes
                    search_results = notes_manager.list_notes(limit=50)
                    result = f"{ZettlFormatter.header(f'Listing notes (showing {len(search_results)}):')}\n\n"

            # Step 2: Apply include tag filters (must have ALL specified tags)
            if tags and 'search_results' in locals():
                # Get note IDs for each required tag
                tag_note_sets = []
                for t in tags:
                    tag_notes = notes_manager.get_notes_by_tag(t)
                    tag_note_ids = {note['id'] for note in tag_notes}
                    tag_note_sets.append(tag_note_ids)

                # Find intersection - notes that have ALL required tags
                if tag_note_sets:
                    required_ids = set.intersection(*tag_note_sets) if tag_note_sets else set()

                    # Filter results to only include notes with ALL required tags
                    original_count = len(search_results)
                    search_results = [note for note in search_results if note['id'] in required_ids]

                    tags_str = "', '".join(tags)
                    search_description.append(f"with tags '{tags_str}'")

                    if not search_results and original_count > 0:
                        result = ZettlFormatter.warning(f"No notes found with all tags: '{tags_str}'")

            # Step 3: Apply exclude tag filters (must not have ANY excluded tags)
            if exclude_tags and 'search_results' in locals():
                # Get note IDs for each excluded tag
                excluded_ids = set()
                for et in exclude_tags:
                    excluded_notes = notes_manager.get_notes_by_tag(et)
                    excluded_ids.update(note['id'] for note in excluded_notes)

                # Filter out notes with ANY excluded tag
                original_count = len(search_results)
                search_results = [note for note in search_results if note['id'] not in excluded_ids]

                excluded_tags_str = "', '".join(exclude_tags)

                if original_count != len(search_results):
                    if not result:
                        result = ""
                    result += f"{ZettlFormatter.info(f'Excluded {original_count - len(search_results)} notes with tags: {excluded_tags_str}')}\n\n"

            # Build and display search header
            if 'search_results' in locals() and search_results:
                if search_description or tags or exclude_tags:
                    header_msg = f"Found {len(search_results)} notes"
                    if search_description:
                        header_msg += f" {' and '.join(search_description)}"
                    if not result:
                        result = ""
                    result = f"{ZettlFormatter.header(header_msg)}\n\n" + result
            
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
                            # Highlight the query in the preview with markdown bold
                            pattern = re.compile(re.escape(query), re.IGNORECASE)
                            content_preview = pattern.sub(r"**\g<0>**", content_preview)

                        result += f"{ZettlFormatter.note_id(note['id'])}: {content_preview}\n"
                    
        elif cmd == "tags":
            # Handle various ways the tags command is used
            # Usage: tags                       - List all tags
            #        tags note_id               - Show tags for note
            #        tags note_id "tag1"        - Add single tag
            #        tags note_id "tag1 tag2..." - Add multiple tags (space-separated in quotes or as separate args)
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

                # Handle both formats:
                # 1. Multiple separate arguments: tags note_id tag1 tag2 tag3
                # 2. Single quoted string: tags note_id "tag1 tag2 tag3"
                if len(remaining_args) > 2:
                    # Multiple separate arguments
                    tags_to_add = remaining_args[1:]
                elif len(remaining_args) == 2:
                    # Could be single tag or space-separated tags in quotes
                    tag_string = remaining_args[1]
                    tags_to_add = tag_string.split() if ' ' in tag_string else [tag_string]
                else:
                    tags_to_add = []

                # If tags were provided, add them
                if tags_to_add:
                    if len(tags_to_add) == 1:
                        # Single tag - use existing add_tag method
                        notes_manager.add_tag(note_id, tags_to_add[0])
                        result = f"Added tag '{tags_to_add[0]}' to note #{note_id}\n"
                    else:
                        # Multiple tags - use batch method
                        notes_manager.add_tags_batch(note_id, tags_to_add)
                        result = f"Added {len(tags_to_add)} tags to note #{note_id}: {', '.join(tags_to_add)}\n"
                else:
                    result = ""

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
                    return jsonify({'result': process_for_web(result)})
                    
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
                                result += f"**Note #{conn_id}**\n\n{conn['explanation']}\n\n"

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
                                result += f"{i}. **{concept['concept']}**\n\n   {concept['explanation']}\n\n"

                    elif action == "questions":
                        questions = llm_helper.generate_question_note(note_id, count)
                        result += f"{ZettlFormatter.header(f'Thought-Provoking Questions from Note #{note_id}')}\n\n"
                        if not questions:
                            result += ZettlFormatter.warning("No questions generated.")
                        else:
                            for i, question in enumerate(questions, 1):
                                result += f"{i}. **{question['question']}**\n\n   {question['explanation']}\n\n"

                    elif action == "critique":
                        critique = llm_helper.critique_note(note_id)
                        result += f"{ZettlFormatter.header(f'AI Critique of Note #{note_id}')}\n\n"

                        # Display strengths
                        if critique['strengths']:
                            result += "## Strengths\n\n"
                            for strength in critique['strengths']:
                                result += f"- {strength}\n"
                            result += "\n"

                        # Display weaknesses
                        if critique['weaknesses']:
                            result += "## Areas for Improvement\n\n"
                            for weakness in critique['weaknesses']:
                                result += f"- {weakness}\n"
                            result += "\n"

                        # Display suggestions
                        if critique['suggestions']:
                            result += "## Suggestions\n\n"
                            for suggestion in critique['suggestions']:
                                result += f"- {suggestion}\n"

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
                    return jsonify({'result': process_for_web(result)})
                
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

        elif cmd == "edit":
            # Edit command - return a special response for the web app to handle
            if not remaining_args:
                result = ZettlFormatter.error("Please provide a note ID")
            else:
                note_id = remaining_args[0]
                try:
                    note = notes_manager.get_note(note_id)
                    # Return a special marker for the frontend to detect and open modal
                    return jsonify({
                        'result': '',
                        'edit_modal': True,
                        'note_id': note_id,
                        'content': note['content']
                    })
                except Exception as e:
                    result = ZettlFormatter.error(f"Error loading note: {str(e)}")

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
            # Import re module for pattern matching
            import re

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
                                return jsonify({'result': process_for_web(result)})
                        
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
                            return jsonify({'result': process_for_web(result)})
                                    
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

                                        # Format note ID on its own line, then content (for proper markdown rendering)
                                        output += f"  {formatted_id}:\n"
                                        output += f"{note['content']}\n\n"
                                
                            if uncategorized_list:
                                output += "Uncategorized\n\n"
                                for note in uncategorized_list:
                                    formatted_id = ZettlFormatter.note_id(note['id'])

                                    # Format note ID on its own line, then content (for proper markdown rendering)
                                    output += f"  {formatted_id}:\n"
                                    output += f"{note['content']}\n\n"
                            
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
            # Handle API key operations with flag-based interface
            generate = 'generate' in options or 'g' in flags
            list_keys = 'list' in options or 'l' in flags

            if generate:
                # Generate new API key
                try:
                    token = session.get('access_token')
                    if not token:
                        result = ZettlFormatter.error("Not authenticated. Please login first.")
                    else:
                        # Get optional key name from remaining args
                        key_name = remaining_args[0] if remaining_args else "Web Interface Key"

                        response = requests.post(f'{AUTH_URL}/api/auth/api-key',
                                               headers={'Authorization': f'Bearer {token}'},
                                               json={'name': key_name})
                        if response.status_code == 200:
                            api_key = response.json()['apiKey']
                            result = "🎉 API Key Generated Successfully!\n\n"
                            result += f"🔑 Your new API key: {api_key}\n\n"
                            result += "⚠️  IMPORTANT: Copy this key now! You won't be able to see it again.\n\n"
                            result += "To use this key with the CLI:\n"
                            result += "  zettl auth setup\n"
                        else:
                            result = ZettlFormatter.error("Failed to generate API key")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error generating API key: {str(e)}")
            elif list_keys:
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
                                result = "No API keys found. Use 'api-key --generate' to create one."
                        else:
                            result = ZettlFormatter.error("Failed to list API keys")
                except Exception as e:
                    result = ZettlFormatter.error(f"Error listing API keys: {str(e)}")
            else:
                result = ZettlFormatter.error("Usage: api-key --list | api-key --generate [name]")

        else:
            result = f"Unknown command: {cmd}. Try 'help' for available commands."
            
        logger.debug(f"Command result: {result[:100]}...")

        # Process result for web display
        result = process_for_web(result)
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

        return jsonify({'result': process_for_web(error_msg)})


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
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ZettlFormatter.warning(f'Uncategorized Todos ({len(uncategorized)})')}:</div>"
        for note in uncategorized:
            output += format_note_html(note)

    if include_done and done_todos:
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ZettlFormatter.header(f'Completed Todos ({len(done_todos)})')}:</div>"
        for note in done_todos:
            output += format_note_html(note)

    if include_cancel and canceled_todos:
        output += f"<div style='margin: 20px 0 10px 0; padding-top: 20px; border-top: 1px solid #444;'>{ZettlFormatter.header(f'Canceled Todos ({len(canceled_todos)})')}:</div>"
        for note in canceled_todos:
            output += format_note_html(note)
    
    return output




# ============================================================================
# Chat API Endpoints
# ============================================================================

@app.route('/api/chat/conversations', methods=['GET'])
@jwt_required
def list_conversations():
    """List all conversations for the current user"""
    try:
        from zettl.chat.manager import ChatManager

        chat_manager = ChatManager(jwt_token=session['access_token'])
        conversations = chat_manager.list_conversations(limit=50)

        return jsonify({
            'success': True,
            'conversations': conversations
        })
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/conversations', methods=['POST'])
@jwt_required
def create_conversation():
    """Create a new chat conversation"""
    try:
        from zettl.chat.manager import ChatManager

        data = request.json
        title = data.get('title')
        context_note_ids = data.get('context_note_ids', [])

        logger.info(f"Creating conversation with title='{title}', context_note_ids={context_note_ids}")

        chat_manager = ChatManager(jwt_token=session['access_token'])
        conversation_id = chat_manager.create_conversation(
            title=title,
            context_note_ids=context_note_ids
        )

        logger.info(f"Successfully created conversation: {conversation_id}")

        return jsonify({
            'success': True,
            'conversation_id': conversation_id
        })
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/conversations/<conversation_id>/messages', methods=['GET'])
@jwt_required
def get_conversation_messages(conversation_id):
    """Get all messages in a conversation"""
    try:
        from zettl.chat.manager import ChatManager

        chat_manager = ChatManager(jwt_token=session['access_token'])
        messages = chat_manager.get_conversation_messages(conversation_id)

        return jsonify({
            'success': True,
            'messages': messages
        })
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/message', methods=['POST'])
@jwt_required
def send_chat_message():
    """Send a message and get AI response using MCP tools"""
    import sys
    print("=== CHAT MESSAGE REQUEST RECEIVED ===", file=sys.stderr, flush=True)
    logger.info("=== CHAT MESSAGE REQUEST RECEIVED ===")
    try:
        from zettl.chat.manager import ChatManager
        from anthropic import Anthropic

        data = request.json
        logger.info(f"Request data: conversation_id={data.get('conversation_id')}, message={data.get('message')[:50] if data.get('message') else None}...")
        conversation_id = data.get('conversation_id')
        user_message = data.get('message')
        context_note_ids = data.get('context_note_ids', [])

        if not conversation_id or not user_message:
            return jsonify({
                'success': False,
                'error': 'conversation_id and message are required'
            }), 400

        # Initialize chat manager
        chat_manager = ChatManager(jwt_token=session['access_token'])

        # Save user message
        chat_manager.add_message(
            conversation_id=conversation_id,
            role='user',
            content=user_message
        )

        # Get conversation history
        messages = chat_manager.get_conversation_messages(conversation_id)

        # Build context from visible notes
        notes_manager = get_notes_manager()
        context_str = ""
        if context_note_ids:
            context_parts = []
            for note_id in context_note_ids:
                try:
                    note = notes_manager.db.get_note(note_id)
                    context_parts.append(f"Note {note_id}:\n{note['content']}\n")
                except:
                    pass
            if context_parts:
                context_str = "Currently visible notes:\n\n" + "\n".join(context_parts)

        # Get MCP server URL
        mcp_url = os.getenv('MCP_URL', 'http://mcp-server:3002')

        # Get available tools from MCP server
        try:
            tools_response = requests.get(f'{mcp_url}/tools', timeout=5)
            tool_definitions = tools_response.json()['tools']
        except Exception as e:
            logger.error(f"Failed to get tools from MCP server: {e}")
            return jsonify({
                'success': False,
                'error': 'MCP server unavailable'
            }), 503

        # Get LLM helper (for Claude API key)
        llm_helper = get_llm_helper()
        if not llm_helper or not llm_helper.api_key:
            return jsonify({
                'success': False,
                'error': 'Claude API key not configured'
            }), 500

        # Initialize Anthropic client
        client = Anthropic(api_key=llm_helper.api_key)

        # Build message history for Claude
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

        # Build system prompt with context
        system_prompt = """You are a helpful assistant for Zettl, a Zettelkasten note-taking system.
You have access to tools that can READ notes (search, get, list) and WRITE notes (create, append, add tags, create links).

IMPORTANT TOOL USE WORKFLOW:
1. When the user asks about their notes, you MUST use the available tools to retrieve the actual data.
2. Do NOT say you will search - actually call the search_notes or other tools immediately.
3. After you receive tool results, you MUST provide a complete answer to the user's original question using the retrieved data.
4. NEVER just acknowledge receiving tool results - always synthesize the data into a helpful response that answers the user's question.
5. If the tool returns empty results, explain that no matching notes were found and suggest alternatives.

TOOL USAGE EXAMPLES:

Example 1 - Search and summarize:
User: "Show me my notes about Blackbird"
→ Use: search_notes(query="Blackbird")
→ Then: Summarize the findings in a formatted list

Example 2 - Create a note:
User: "Create a note: Meeting with team about Q1 goals"
→ Use: create_note(content="Meeting with team about Q1 goals", tags=["meeting", "todo"])
→ Then: Confirm creation with note ID

Example 3 - Get specific note with details:
User: "Show me the full content of note #abc123"
→ Use: get_note(note_id="abc123")
→ Then: Display full content with tags and links

Example 4 - Filter by tag:
User: "What are my todo items?"
→ Use: get_notes_by_tag(tag="todo")
→ Then: List all todos in a formatted way

Example 5 - Add context to existing note:
User: "Add to note #abc123: Completed the database migration"
→ Use: append_to_note(note_id="abc123", content="Completed the database migration")
→ Then: Confirm the update

Example 6 - Create connection:
User: "Link note #abc123 to note #def456 because they're related"
→ Use: create_link_between_notes(source_id="abc123", target_id="def456", context="related topics")
→ Then: Confirm link creation

Example 7 - Add tags for organization:
User: "Tag note #abc123 with project and urgent"
→ Use: add_tags_to_note(note_id="abc123", tags=["project", "urgent"])
→ Then: Confirm tags added

TOOL SELECTION TIPS:
- For broad queries → use search_notes or list_recent_notes
- For specific tags → use get_notes_by_tag
- For exact note lookup → use get_note
- For creating quick notes → use create_note
- For adding to existing → use append_to_note
- For organization → use add_tags_to_note or create_link_between_notes
- Don't use get_notes_by_tag multiple times for slight variations (blackbird, blackbirdrates, blackbirdlens) - use search_notes instead

FORMATTING GUIDELINES - Use markdown formatting following Zettl's conventions:
- Use **bold** for headers and important information
- Format note IDs as `#123` (backticks for monospace)
- Format tags as `#tagname` (backticks for monospace)
- Use *italics* for timestamps and dates
- Use horizontal rules (---) to separate sections
- Use code blocks with ``` for multi-line code or data
- Use bullet lists (- or *) for multiple items
- When showing note previews, limit to ~50 chars + "..."
- When displaying full notes, use this structure:
  `#<note_id>` [*timestamp*]
  ---
  <note content>
  Tags: `#tag1` `#tag2`

Example response format:
**Found 3 notes:**

`#42` [*2024-01-15*]
This is a sample note about...

`#87` [*2024-01-20*]
Another note discussing...

Keep responses concise and well-structured. Always use markdown for better readability."""

        if context_str:
            system_prompt += f"\n\n{context_str}"

        # Call Claude with tool use
        logger.info(f"Calling Claude with {len(tool_definitions)} tools")
        logger.info(f"System prompt: {system_prompt[:200]}...")
        logger.info(f"Message count: {len(claude_messages)}")

        # Tool use loop - continue until Claude provides a final text response
        tool_execution_details = []  # Track tool details for frontend display
        tool_results_data = []  # Track raw tool results data for main screen display
        tool_results = []  # Initialize to empty list for cases where no tools are used
        max_tool_rounds = 10  # Prevent infinite loops (increased for complex queries)

        for round_num in range(max_tool_rounds):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=claude_messages,
                tools=[{
                    'name': tool['name'],
                    'description': tool['description'],
                    'input_schema': tool['inputSchema']
                } for tool in tool_definitions]
            )

            logger.info(f"Claude response (round {round_num + 1}) stop_reason: {response.stop_reason}")
            logger.info(f"Claude response content blocks: {len(response.content)}")

            # If no more tool use, we're done
            if response.stop_reason != "tool_use":
                break

            # Handle tool use by calling MCP server
            tool_results = []
            logger.info("Processing tool use requests...")
            for content_block in response.content:
                logger.info(f"Content block type: {content_block.type}")
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    logger.info(f"Calling tool: {tool_name} with input: {tool_input}")

                    # Call MCP server to execute the tool using JWT token
                    try:
                        tool_response = requests.post(
                            f'{mcp_url}/tool/{tool_name}',
                            headers={'Authorization': f'Bearer {session["access_token"]}'},
                            json=tool_input,
                            timeout=10
                        )

                        logger.info(f"MCP server response status: {tool_response.status_code}")
                        logger.info(f"MCP server response body: {tool_response.text}")

                        if tool_response.status_code == 200:
                            result = tool_response.json()['result']
                            logger.info(f"Tool result: {result}")
                            tool_results.append({
                                'type': 'tool_result',
                                'tool_use_id': tool_use_id,
                                'content': json.dumps(result)
                            })
                            # Track tool execution for frontend
                            tool_execution_details.append({
                                'name': tool_name,
                                'input': tool_input,
                                'success': True
                            })
                            # Track raw tool result data for main screen display
                            tool_results_data.append({
                                'name': tool_name,
                                'input': tool_input,
                                'result': result,
                                'success': True
                            })
                        else:
                            logger.error(f"Tool call failed with status {tool_response.status_code}")
                            error_msg = f'HTTP {tool_response.status_code}: {tool_response.text}'
                            tool_results.append({
                                'type': 'tool_result',
                                'tool_use_id': tool_use_id,
                                'content': json.dumps({'error': error_msg})
                            })
                            # Track failed tool execution
                            tool_execution_details.append({
                                'name': tool_name,
                                'input': tool_input,
                                'success': False,
                                'error': f'HTTP {tool_response.status_code}'
                            })
                            # Track raw tool result data for main screen display
                            tool_results_data.append({
                                'name': tool_name,
                                'input': tool_input,
                                'result': {'error': error_msg},
                                'success': False
                            })
                    except Exception as e:
                        logger.error(f"Error calling MCP tool {tool_name}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        error_msg = str(e)
                        tool_results.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_use_id,
                            'content': json.dumps({'error': error_msg})
                        })
                        # Track failed tool execution
                        tool_execution_details.append({
                            'name': tool_name,
                            'input': tool_input,
                            'success': False,
                            'error': error_msg
                        })
                        # Track raw tool result data for main screen display
                        tool_results_data.append({
                            'name': tool_name,
                            'input': tool_input,
                            'result': {'error': error_msg},
                            'success': False
                        })

            # Add tool results to conversation and continue loop
            logger.info(f"Sending {len(tool_results)} tool results back to Claude")
            claude_messages.append({
                'role': 'assistant',
                'content': response.content
            })
            claude_messages.append({
                'role': 'user',
                'content': tool_results
            })

        # If we hit max rounds while still wanting to use tools, force a final response
        if response.stop_reason == "tool_use":
            logger.warning(f"Hit max tool rounds ({max_tool_rounds}) - requesting final response")
            claude_messages.append({
                'role': 'user',
                'content': 'Please provide your final answer based on all the data you\'ve gathered. Summarize the key findings in a clear, well-formatted response.'
            })
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=claude_messages
                # Note: No tools parameter - force text-only response
            )
            logger.info(f"Final forced response stop_reason: {response.stop_reason}")

        # Extract assistant's response
        assistant_message = ""
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                assistant_message += content_block.text

        logger.info(f"Assistant message length: {len(assistant_message)}")

        # Save assistant message
        chat_manager.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=assistant_message,
            tool_calls=tool_results if tool_results else None
        )

        return jsonify({
            'success': True,
            'message': assistant_message,
            'tool_calls': len(tool_results),
            'tool_details': tool_execution_details,
            'tool_results_data': tool_results_data
        })

    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("Starting Zettl Web Server...")
    # For development - set host to 0.0.0.0 to access from other devices on network
    app.run(debug=True, host='0.0.0.0', port=5001)