# formatting.py
import sys
from rich.console import Console
from rich.markdown import Markdown

# Initialize colorama for Windows support
if sys.platform == 'win32':
    try:
        import colorama
        colorama.init()
    except ImportError:
        # If colorama is not installed, colors won't work on Windows
        # but the program will still function
        pass

# Rich console for markdown rendering
console = Console()

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

class ZettlFormatter:
    """Utility class for formatting Zettl output in the terminal."""
    
    @staticmethod
    def header(text):
        """Format a header."""
        return f"{Colors.BOLD}{Colors.GREEN}{text}{Colors.RESET}"
    
    @staticmethod
    def note_id(note_id):
        """Format a note ID."""
        return f"{Colors.CYAN}#{note_id}{Colors.RESET}"
    
    @staticmethod
    def timestamp(date_str):
        """Format a timestamp."""
        return f"{Colors.BLUE}{date_str}{Colors.RESET}"
    
    @staticmethod
    def tag(tag_text):
        """Format a tag."""
        return f"{Colors.YELLOW}#{tag_text}{Colors.RESET}"
    
    @staticmethod
    def error(text):
        """Format an error message."""
        return f"{Colors.RED}Error: {text}{Colors.RESET}"
    
    @staticmethod
    def warning(text):
        """Format a warning message."""
        return f"{Colors.YELLOW}Warning: {text}{Colors.RESET}"
    
    @staticmethod
    def success(text):
        """Format a success message."""
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    @staticmethod
    def info(text):
        """Format an info message."""
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    @staticmethod
    def format_note_display(note, notes_manager, render_markdown=True):
        """Format a full note for display with optional markdown rendering."""
        note_id = note['id']
        created_at = notes_manager.format_timestamp(note['created_at'])

        formatted_id = ZettlFormatter.note_id(note_id)
        formatted_time = ZettlFormatter.timestamp(created_at)

        header_line = f"{formatted_id} [{formatted_time}]"
        separator = "-" * 40

        # Print header and separator
        print(header_line)
        print(separator)

        # Render markdown content if enabled
        if render_markdown:
            ZettlFormatter.render_markdown(note['content'])
        else:
            print(note['content'])

        # Return empty string since we're printing directly
        return ""

    @staticmethod
    def render_markdown(content):
        """Render markdown content using rich."""
        md = Markdown(content)
        console.print(md)