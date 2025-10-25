# formatting.py
import sys
from rich.console import Console
from rich.markdown import Markdown

# Rich console for CLI markdown rendering
console = Console()

class ZettlFormatter:
    """Context-aware formatter for both CLI (rich markup) and Web (HTML)."""

    # Mode: 'cli' for terminal, 'web' for HTML
    _mode = 'cli'

    @classmethod
    def set_mode(cls, mode):
        """Set formatter mode: 'cli' or 'web'"""
        cls._mode = mode

    @classmethod
    def header(cls, text):
        """Format a header."""
        if cls._mode == 'web':
            # Web: use markdown bold
            return f"**{text}**"
        else:
            # CLI: use rich markup
            return f"[bold green]{text}[/bold green]"

    @classmethod
    def note_id(cls, note_id):
        """Format a note ID."""
        if cls._mode == 'web':
            # Web: use backticks for monospace + emphasis
            return f"`#{note_id}`"
        else:
            return f"[cyan]#{note_id}[/cyan]"

    @classmethod
    def timestamp(cls, date_str):
        """Format a timestamp."""
        if cls._mode == 'web':
            # Web: use italics for timestamps
            return f"*{date_str}*"
        else:
            return f"[blue]{date_str}[/blue]"

    @classmethod
    def tag(cls, tag_text):
        """Format a tag."""
        if cls._mode == 'web':
            # Web: use backticks for tags
            return f"`#{tag_text}`"
        else:
            return f"[yellow]#{tag_text}[/yellow]"

    @classmethod
    def error(cls, text):
        """Format an error message."""
        if cls._mode == 'web':
            # Web: use bold for errors
            return f"**Error:** {text}"
        else:
            return f"[bold red]Error:[/bold red] {text}"

    @classmethod
    def warning(cls, text):
        """Format a warning message."""
        if cls._mode == 'web':
            # Web: use bold for warnings
            return f"**Warning:** {text}"
        else:
            return f"[bold yellow]Warning:[/bold yellow] {text}"

    @classmethod
    def success(cls, text):
        """Format a success message."""
        if cls._mode == 'web':
            # Web: plain text, markdown doesn't have success styling
            return text
        else:
            return f"[green]{text}[/green]"

    @classmethod
    def info(cls, text):
        """Format an info message."""
        if cls._mode == 'web':
            # Web: plain text
            return text
        else:
            return f"[cyan]{text}[/cyan]"

    @classmethod
    def format_note_display(cls, note, notes_manager, render_markdown=True):
        """Format a full note for display."""
        note_id = note['id']
        created_at = notes_manager.format_timestamp(note['created_at'])

        formatted_id = cls.note_id(note_id)
        formatted_time = cls.timestamp(created_at)

        header_line = f"{formatted_id} [{formatted_time}]"
        separator = "-" * 40

        # Print header and separator
        console.print(header_line)
        console.print(separator)

        # Render markdown content if enabled
        if render_markdown:
            cls.render_markdown(note['content'])
        else:
            console.print(note['content'])

        # Return empty string since we're printing directly
        return ""

    @classmethod
    def render_markdown(cls, content):
        """Render markdown content using rich (CLI only)."""
        md = Markdown(content)
        console.print(md)