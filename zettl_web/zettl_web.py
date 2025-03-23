# File: zettl_web.py

import os
import json
import logging
import shlex
from flask import Flask, request, jsonify, render_template, Response, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import re

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
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
auth = HTTPBasicAuth()

# Get username/password from environment variables
ZETTL_WEB_USER = os.getenv("ZETTL_WEB_USER")
ZETTL_WEB_PASS = os.getenv("ZETTL_WEB_PASS")

# Print debug info to console
print(f"Auth credentials from env: User='{ZETTL_WEB_USER}', Pass set: {'Yes' if ZETTL_WEB_PASS else 'No'}")

# Set up users dictionary for authentication
users = {}
if ZETTL_WEB_USER and ZETTL_WEB_PASS:
    users[ZETTL_WEB_USER] = generate_password_hash(ZETTL_WEB_PASS)
    print(f"Added user '{ZETTL_WEB_USER}' to authentication system")
else:
    # For development, add a default user if environment variables aren't set
    users["admin"] = generate_password_hash("admin")
    print("WARNING: Using default credentials (admin/admin) - not secure for production!")

print(f"Authentication users: {list(users.keys())}")

# Now import Zettl components - do this after environment is set up
try:
    from zettl.notes import Notes
    from zettl.database import Database
    from zettl.llm import LLMHelper
    from zettl.formatting import ZettlFormatter, Colors
    
    # Initialize core Zettl components
    notes_manager = Notes()
    llm_helper = LLMHelper()
    logger.debug("Successfully imported and initialized Zettl components")
except ImportError as e:
    logger.error(f"Error importing Zettl modules: {e}")
    # Provide dummy implementations for testing if needed
    class DummyNotes:
        def list_notes(self, limit=10):
            return [{"id": "12345", "content": "This is a test note", "created_at": "2025-03-13T12:00:00Z"}]
        def format_timestamp(self, date_str):
            return "2025-03-13 12:00"
        def create_note(self, content):
            return "12345"
        def get_note(self, note_id):
            return {"id": note_id, "content": "This is a test note", "created_at": "2025-03-13T12:00:00Z"}
        def get_tags(self, note_id):
            return ["test", "dummy"]
        def add_tag(self, note_id, tag):
            pass
        def search_notes(self, query):
            return [{"id": "12345", "content": "This is a test note containing " + query, "created_at": "2025-03-13T12:00:00Z"}]
        def create_link(self, source_id, target_id, context=""):
            pass
        def get_related_notes(self, note_id):
            return [{"id": "67890", "content": "This is a related test note", "created_at": "2025-03-13T12:00:00Z"}]
        def delete_note(self, note_id, cascade=True):
            pass
        def delete_tag(self, note_id, tag):
            pass
        def delete_link(self, source_id, target_id):
            pass
        def get_notes_by_tag(self, tag):
            return [{"id": "12345", "content": "This is a todo note", "created_at": "2025-03-13T12:00:00Z"}]
        def get_all_tags_with_counts(self):
            return [{"tag": "test", "count": 1}, {"tag": "todo", "count": 2}]
    
    class DummyLLM:
        def summarize_note(self, note_id):
            return "This is a test summary."
        def suggest_tags(self, note_id, count=3):
            return ["test", "dummy", "example"]
    
    class DummyColors:
        GREEN = "\033[92m"
        BLUE = "\033[94m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        CYAN = "\033[96m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
    
    class DummyFormatter:
        @staticmethod
        def header(text):
            return f"\033[1m\033[92m{text}\033[0m"
        
        @staticmethod
        def note_id(note_id):
            return f"\033[96m#{note_id}\033[0m"
        
        @staticmethod
        def timestamp(date_str):
            return f"\033[94m{date_str}\033[0m"
        
        @staticmethod
        def tag(tag_text):
            return f"\033[93m#{tag_text}\033[0m"
        
        @staticmethod
        def error(text):
            return f"\033[91mError: {text}\033[0m"
        
        @staticmethod
        def warning(text):
            return f"\033[93mWarning: {text}\033[0m"
        
        @staticmethod
        def success(text):
            return f"\033[92m{text}\033[0m"
    
    notes_manager = DummyNotes()
    llm_helper = DummyLLM()
    Colors = DummyColors()
    ZettlFormatter = DummyFormatter()
    logger.debug("Using dummy implementations for testing")

@auth.verify_password
def verify_password(username, password):
    print(f"Verifying password for user: {username}")
    if username in users and check_password_hash(users.get(username), password):
        print(f"Authentication successful for user: {username}")
        return username
    print(f"Authentication failed for user: {username}")
    return None

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
            'c': {'name': 'cancel', 'flag': True},  # Added cancel option
            't': {'name': 'tag', 'multiple': True}
        },
        'long_opts': {
            'donetoday': {'flag': True},
            'all': {'flag': True},
            'cancel': {'flag': True},  # Added cancel option
            'tag': {'multiple': True}
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
    help_text = ""
    
    if cmd == "search":
        help_text = f"""
{Colors.GREEN}{Colors.BOLD}search [QUERY]{Colors.RESET} - Search for notes containing text

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}        Search for notes with this tag
  {Colors.YELLOW}+t, --exclude-tag TAG{Colors.RESET} Exclude notes with this tag
  {Colors.YELLOW}-f, --full{Colors.RESET}           Show full content of matching notes

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}search "keyword"{Colors.RESET}       Search notes containing "keyword"
  {Colors.BLUE}search -t concept{Colors.RESET}      Show notes tagged with "concept"
  {Colors.BLUE}search -t work +t done{Colors.RESET} Show notes tagged "work" but not "done"
"""
    elif cmd == "todos":
        help_text = f"""
{Colors.GREEN}{Colors.BOLD}todos{Colors.RESET} - List all notes tagged with 'todo'

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-a, --all{Colors.RESET}            Show all todos (active and completed)
  {Colors.YELLOW}-dt, --donetoday{Colors.RESET}     Show todos completed today
  {Colors.YELLOW}-c, --cancel{Colors.RESET}         Show canceled todos
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}        Filter todos by additional tag

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}todos{Colors.RESET}                  Show active todos
  {Colors.BLUE}todos -a{Colors.RESET}               Show all todos (active and completed)
  {Colors.BLUE}todos -dt{Colors.RESET}              Show todos completed today
  {Colors.BLUE}todos -c{Colors.RESET}               Show canceled todos
  {Colors.BLUE}todos -t work{Colors.RESET}          Show todos tagged with "work"
"""
    elif cmd == "llm":
        """Show detailed help specifically for the LLM command."""
        help_text = f"""
    {Colors.GREEN}{Colors.BOLD}llm NOTE_ID{Colors.RESET} - Use Claude AI to analyze and enhance notes

    {Colors.BOLD}Actions:{Colors.RESET}
    {Colors.YELLOW}summarize{Colors.RESET}   Generate a concise summary of the note
    {Colors.YELLOW}connect{Colors.RESET}     Find potential connections to other notes
    {Colors.YELLOW}tags{Colors.RESET}        Suggest relevant tags for the note
    {Colors.YELLOW}expand{Colors.RESET}      Create an expanded version of the note
    {Colors.YELLOW}concepts{Colors.RESET}    Extract key concepts from the note
    {Colors.YELLOW}questions{Colors.RESET}   Generate thought-provoking questions
    {Colors.YELLOW}critique{Colors.RESET}    Provide constructive feedback on the note

    {Colors.BOLD}Options:{Colors.RESET}
    {Colors.YELLOW}-a, --action ACTION{Colors.RESET}  LLM action to perform (see above)
    {Colors.YELLOW}-c, --count NUMBER{Colors.RESET}   Number of results to return (default: 3)
    {Colors.YELLOW}-s, --show-source{Colors.RESET}    Show the source note before analysis
    {Colors.YELLOW}-d, --debug{Colors.RESET}          Show debug information for troubleshooting

    {Colors.BOLD}Examples:{Colors.RESET}
    {Colors.BLUE}llm 22a4b{Colors.RESET}                 Summarize note 22a4b (default action)
    {Colors.BLUE}llm 22a4b -a tags{Colors.RESET}         Suggest tags for note 22a4b
    {Colors.BLUE}llm 22a4b -a connect -c 5{Colors.RESET} Find 5 related notes to note 22a4b
    """
    elif cmd == "rules":
        help_text = f"""
        {Colors.YELLOW}{Colors.BOLD}rules{Colors.RESET} - Display a random rule from notes tagged with 'rules'
    {Colors.BLUE}→{Colors.RESET} zettl rules
    {Colors.BLUE}→{Colors.RESET} zettl rules --source  # Show the source note ID
    """
    elif cmd == "help":
        # For "help --help", just show general help
        return execute_command("help", [], {}, [])
    else:
        help_text = f"No detailed help available for '{cmd}'. Try 'help' for a list of all commands."
        
    return jsonify({'result': ansi_to_html(help_text)})


# Routes
@app.route('/')
@auth.login_required
def index():
    logger.debug(f"Rendering index page for user: {auth.current_user()}")
    return render_template('index.html', username=auth.current_user())

@app.route('/api/command', methods=['POST'])
@auth.login_required
def execute_command():
    command = request.json.get('command', '').strip()
    logger.debug(f"Executing command: {command}")
    
    if not command:
        return jsonify({'result': 'No command provided'})
        
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
                created_at = notes_manager.format_timestamp(note['created_at'])
                
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
            # Debugging for the show command
            logger.debug(f"Executing show command with args: {remaining_args}")
            
            if not remaining_args:
                result = ZettlFormatter.error("Please provide a note ID")
            else:
                note_id = remaining_args[0]
                logger.debug(f"Attempting to retrieve note with ID: {note_id}")
                
                try:
                    # Try to directly access the database to check if the note exists
                    db_client = notes_manager.db.client
                    logger.debug(f"Database client initialized: {db_client is not None}")
                    
                    # Check if the note exists directly with a database query
                    query_result = db_client.table('notes').select('*').eq('id', note_id).execute()
                    logger.debug(f"Direct DB query result: {query_result}")
                    
                    if not query_result.data:
                        logger.debug(f"Note {note_id} not found in direct DB query")
                        result = ZettlFormatter.error(f"Note {note_id} not found")
                        return jsonify({'result': ansi_to_html(result)})
                        
                    # If we get here, the note exists in the database
                    logger.debug(f"Note {note_id} found in database, attempting to load")
                    
                    # Now try to load it using the notes_manager
                    note = notes_manager.get_note(note_id)
                    logger.debug(f"Note loaded successfully: {note is not None}")
                    
                    created_at = notes_manager.format_timestamp(note['created_at'])
                    
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
                    
                    # Provide a more helpful error message based on the exception
                    if "connection" in str(e).lower():
                        result = ZettlFormatter.error(f"Database connection error: {str(e)}")
                    elif "not found" in str(e).lower():
                        result = ZettlFormatter.error(f"Note {note_id} not found")
                    elif "authentication" in str(e).lower():
                        result = ZettlFormatter.error(f"Authentication error: {str(e)}")
                    else:
                        # Detailed error message with exception type
                        error_type = type(e).__name__
                        result = ZettlFormatter.error(f"Error ({error_type}): {str(e)}")
                        
                    # Log the full stack trace for server debugging
                    import traceback
                    logger.error(f"Full stack trace for show command error:\n{traceback.format_exc()}")

                
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
                    created_at = notes_manager.format_timestamp(source_note['created_at'])
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
                            note_created_at = notes_manager.format_timestamp(note['created_at'])
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
            # List all notes tagged with 'todo' grouped by category
            donetoday = 'donetoday' in flags or 'dt' in flags
            all_todos = 'all' in flags or 'a' in flags
            cancel = 'cancel' in flags or 'c' in flags  # Add the cancel flag
            done = all_todos
            filter_tags = []
            if all_todos:
                done = True
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
                # Get notes with 'done' tag added today (for donetoday option)
                done_today_ids = set()
                if donetoday:
                    from datetime import datetime, timezone
                    import logging
                    
                    # Get today's date in UTC for consistent comparison
                    today = datetime.now(timezone.utc).date()
                    logger.debug(f"Today's date (UTC): {today}")
                    
                    try:
                        tags_result = notes_manager.db.client.table('tags').select('note_id, created_at').eq('tag', 'done').execute()
                        
                        if tags_result.data:
                            logger.debug(f"Found {len(tags_result.data)} 'done' tags")
                            for tag_data in tags_result.data:
                                note_id = tag_data.get('note_id')
                                created_at = tag_data.get('created_at', '')
                                
                                if note_id and created_at:
                                    try:
                                        # Better handling of date format
                                        logger.debug(f"Processing date: {created_at} for note_id: {note_id}")
                                        
                                        # Handle different ISO formats
                                        if 'Z' in created_at:
                                            created_at = created_at.replace('Z', '+00:00')
                                        elif 'T' in created_at and not ('+' in created_at or '-' in created_at[10:]):
                                            # No timezone info - assume UTC
                                            created_at = created_at + '+00:00'
                                            
                                        # Parse with timezone awareness
                                        parsed_datetime = datetime.fromisoformat(created_at)
                                        # Convert to UTC for comparison
                                        utc_datetime = parsed_datetime.astimezone(timezone.utc)
                                        tag_date = utc_datetime.date()
                                        
                                        logger.debug(f"Parsed date: {tag_date}")
                                        
                                        # Check if tag was created today
                                        if tag_date == today:
                                            logger.debug(f"Match found for note_id: {note_id}")
                                            done_today_ids.add(note_id)
                                    except Exception as e:
                                        logger.debug(f"Error parsing date '{created_at}': {str(e)}")
                            
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
            # Show well-formatted help similar to CLI
            result = f"""
{Colors.GREEN}{Colors.BOLD}zettl v0.1.0{Colors.RESET} - A Zettelkasten-style note-taking tool

{Colors.BOLD}Core Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}new{Colors.RESET} - Create a new note with the given content
    {Colors.BLUE}→{Colors.RESET} zettl new "This is a new note about an interesting concept"
    {Colors.BLUE}→{Colors.RESET} zettl new "Note with tag and link" --tag concept --link 22a4b

  {Colors.YELLOW}{Colors.BOLD}list{Colors.RESET} - List recent notes
    {Colors.BLUE}→{Colors.RESET} zettl list --limit 5
    {Colors.BLUE}→{Colors.RESET} zettl list --full  # Shows full content with tags

  {Colors.YELLOW}{Colors.BOLD}show{Colors.RESET} - Display note content
    {Colors.BLUE}→{Colors.RESET} zettl show 22a4b

  {Colors.YELLOW}{Colors.BOLD}search{Colors.RESET} - Search for notes containing text
    {Colors.BLUE}→{Colors.RESET} zettl search "concept"
    {Colors.BLUE}→{Colors.RESET} zettl search -t concept --full  # Show full content with tags
    {Colors.BLUE}→{Colors.RESET} zettl search "concept" +t done  # Exclude notes with 'done' tag

{Colors.BOLD}Connection Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}link{Colors.RESET} - Create link between notes
    {Colors.BLUE}→{Colors.RESET} zettl link 22a4b 18c3d

  {Colors.YELLOW}{Colors.BOLD}related{Colors.RESET} - Show notes connected to this note
    {Colors.BLUE}→{Colors.RESET} zettl related 22a4b

  {Colors.YELLOW}{Colors.BOLD}graph{Colors.RESET} - Generate a graph visualization of notes
    {Colors.BLUE}→{Colors.RESET} zettl graph 22a4b --output graph.json --depth 2

{Colors.BOLD}Organizational Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}tags{Colors.RESET} - Show or add tags to a note
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b "concept"

    {Colors.YELLOW}{Colors.BOLD}todos{Colors.RESET} - List notes tagged with 'todo'
    {Colors.BLUE}→{Colors.RESET} zettl todos
    {Colors.BLUE}→{Colors.RESET} zettl todos --all  # Show all todos (active and completed)
    {Colors.BLUE}→{Colors.RESET} zettl todos --donetoday  # Show todos completed today
    {Colors.BLUE}→{Colors.RESET} zettl todos --tag work  # Filter todos by tag

{Colors.BOLD}Management Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}delete{Colors.RESET} - Delete a note and its associated data
    {Colors.BLUE}→{Colors.RESET} zettl delete 22a4b
    {Colors.BLUE}→{Colors.RESET} zettl delete 22a4b --keep-tags

  {Colors.YELLOW}{Colors.BOLD}untag{Colors.RESET} - Remove a tag from a note
    {Colors.BLUE}→{Colors.RESET} zettl untag 22a4b "concept"

  {Colors.YELLOW}{Colors.BOLD}unlink{Colors.RESET} - Remove a link between two notes
    {Colors.BLUE}→{Colors.RESET} zettl unlink 22a4b 18c3d

{Colors.BOLD}AI-Powered Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}llm{Colors.RESET} - Use Claude AI to analyze and enhance notes
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action summarize
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action tags
"""
        else:
            result = f"Unknown command: {cmd}. Try 'help' for available commands."
            
        logger.debug(f"Command result: {result[:100]}...")
        
        # Convert ANSI color codes to HTML
        result = ansi_to_html(result)
        return jsonify({'result': result})
        
    except Exception as e:
        logger.exception(f"Error executing command: {e}")
        return jsonify({'result': ansi_to_html(ZettlFormatter.error(str(e)))})

if __name__ == '__main__':
    logger.info("Starting Zettl Web Server...")
    # For development - set host to 0.0.0.0 to access from other devices on network
    app.run(debug=True, host='0.0.0.0', port=5001)