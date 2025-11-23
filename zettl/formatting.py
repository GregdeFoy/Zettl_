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
            # CLI: use rich markup - bright green for high readability
            return f"[bold bright_green]{text}[/bold bright_green]"

    @classmethod
    def note_id(cls, note_id):
        """Format a note ID."""
        if cls._mode == 'web':
            # Web: use backticks for monospace + emphasis
            return f"`#{note_id}`"
        else:
            # Bold bright cyan for excellent readability on black backgrounds
            return f"[bold bright_cyan]#{note_id}[/bold bright_cyan]"

    @classmethod
    def timestamp(cls, date_str):
        """Format a timestamp."""
        if cls._mode == 'web':
            # Web: use italics for timestamps
            return f"*{date_str}*"
        else:
            # Dim gray for de-emphasized timestamps
            return f"[bright_black]{date_str}[/bright_black]"

    @classmethod
    def tag(cls, tag_text):
        """Format a tag."""
        if cls._mode == 'web':
            # Web: use backticks for tags
            return f"`#{tag_text}`"
        else:
            # Bright yellow with brackets for clear tag identification
            # Escape brackets to prevent rich from parsing them as markup
            return f"[bright_yellow]\\[{tag_text}][/bright_yellow]"

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
    def render_note(cls, note, tags=None, mode='full'):
        """Unified note rendering function.

        Args:
            note: Note dictionary with 'id' and 'content'
            tags: Optional list of tag strings
            mode: Display mode - 'full', 'preview', or 'compact'
                  - 'full': Show ID, tags, and full markdown content
                  - 'preview': Show ID, tags | first line of content
                  - 'compact': Show only ID
        """
        note_id = note['id']
        content = note['content']
        formatted_id = cls.note_id(note_id)

        if mode == 'compact':
            # Just show the ID
            console.print(formatted_id)

        elif mode == 'preview':
            # ID [tags] | first line
            line_parts = [formatted_id]
            if tags:
                formatted_tags = [cls.tag(t) for t in tags]
                line_parts.append(" ".join(formatted_tags))

            first_line = content.split('\n')[0]
            line_parts.append(f"| {first_line}")
            console.print("  ".join(line_parts))

        else:  # mode == 'full'
            # ID and tags on first line
            id_line = formatted_id
            if tags:
                formatted_tags = [cls.tag(t) for t in tags]
                id_line += "  " + " ".join(formatted_tags)

            console.print(id_line)
            console.print()  # Empty line after header

            # Render content as markdown
            if cls._mode == 'cli':
                md = Markdown(content)
                console.print(md)
            else:
                console.print(content)