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
logging.basicConfig(level=logging.DEBUG)
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

def extract_options(args):
    """
    Extract --options and -flags from arguments
    Returns options dict, flags list, and remaining args
    """
    options = {}
    flags = []
    remaining_args = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        # Handle long options with values: --option value
        if arg.startswith('--'):
            option_name = arg[2:]
            if i + 1 < len(args) and not args[i+1].startswith('-'):
                options[option_name] = args[i+1]
                i += 2
            else:
                # Option without value (boolean flag)
                flags.append(option_name)
                i += 1
                
        # Handle short options: -f
        elif arg.startswith('-'):
            flag_name = arg[1:]
            flags.append(flag_name)
            i += 1
            
        # Regular arguments
        else:
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
    
    # Extract options, flags and non-option args
    options, flags, remaining_args = extract_options(args)
    
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
                    result += f"{note['content']}\n\n"
                else:
                    # Default mode - ID, timestamp, and preview
                    formatted_id = ZettlFormatter.note_id(note_id)
                    formatted_time = ZettlFormatter.timestamp(created_at)
                    content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                    result += f"{formatted_id} [{formatted_time}]: {content_preview}\n\n"  # Added extra newline

                    
        elif cmd == "new" or cmd == "add":
            # Handle content and tags
            content = remaining_args[0] if remaining_args else ""
            tags = options.get('tag', '').split(',') if 'tag' in options else []
            
            # Also check for -t option
            if 't' in options:
                tags.extend(options['t'].split(','))
                
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
            
        elif cmd == "show":
            # Display a note
            note_id = remaining_args[0] if remaining_args else ""
            
            try:
                note = notes_manager.get_note(note_id)
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
                    logger.error(f"Error getting tags: {e}")
            except Exception as e:
                result = ZettlFormatter.error(str(e))
                
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
                        result += f"{note['content']}\n\n"
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
                
                if action == "summarize":
                    summary = llm_helper.summarize_note(note_id)
                    result = f"{ZettlFormatter.header(f'AI Summary for Note #{note_id}')}\n\n{summary}"
                elif action == "tags":
                    tags = llm_helper.suggest_tags(note_id, count)
                    result = f"{ZettlFormatter.header(f'AI-Suggested Tags for Note #{note_id}')}\n\n"
                    for tag in tags:
                        result += f"{ZettlFormatter.tag(tag)}\n"
                else:
                    result = f"LLM action '{action}' not fully implemented in web version."
                
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
        
        elif cmd == "todos":
            # List all notes tagged with 'todo'
            done = 'done' in flags or 'd' in flags
            donetoday = 'donetoday' in flags or 'dt' in flags
            filter_tags = options.get('filter', '').split(',') if 'filter' in options else []
            
            # Get all notes tagged with 'todo'
            todo_notes = notes_manager.get_notes_by_tag('todo')
            
            if not todo_notes:
                result = ZettlFormatter.warning("No todos found.")
            else:
                result = f"{ZettlFormatter.header('Todos')}\n\n"
                
                # Apply simple filter based on 'done' tag
                for note in todo_notes:
                    note_id = note['id']
                    tags = notes_manager.get_tags(note_id)
                    tags_lower = [t.lower() for t in tags]
                    
                    # Check if this is a done todo
                    is_done = 'done' in tags_lower
                    
                    # Skip done todos if not explicitly included
                    if is_done and not done:
                        continue
                        
                        
                    # Display the todo
                    result += f"{ZettlFormatter.note_id(note_id)}: {note['content']}\n"
                    if tags:
                        result += f"  Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}\n"
                    result += "\n\n"  # Added extra newline
                
        elif cmd == "help" or cmd == "--help":
            # Show well-formatted help similar to CLI
            result = f"""
{Colors.GREEN}{Colors.BOLD}zettl v0.1.0{Colors.RESET} - A Zettelkasten-style note-taking tool

{Colors.BOLD}Core Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}new{Colors.RESET} - Create a new note with the given content
    {Colors.BLUE}→{Colors.RESET} zettl new "This is a new note about an interesting concept"

  {Colors.YELLOW}{Colors.BOLD}list{Colors.RESET} - List recent notes
    {Colors.BLUE}→{Colors.RESET} zettl list --limit 5

  {Colors.YELLOW}{Colors.BOLD}show{Colors.RESET} - Display note content
    {Colors.BLUE}→{Colors.RESET} zettl show 22a4b

  {Colors.YELLOW}{Colors.BOLD}search{Colors.RESET} - Search for notes containing text
    {Colors.BLUE}→{Colors.RESET} zettl search "concept"

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
    {Colors.BLUE}→{Colors.RESET} zettl todos --done

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