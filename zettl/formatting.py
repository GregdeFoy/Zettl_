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

    @classmethod
    def truncate_content_by_lines(cls, content, max_lines=3):
        """Truncate content to max_lines, adding ellipsis if truncated."""
        lines = content.split('\n')
        if len(lines) > max_lines:
            truncated_lines = lines[:max_lines]
            # Add ellipsis to last line
            truncated_lines[-1] = truncated_lines[-1].rstrip() + '[...]'
            return '\n'.join(truncated_lines)
        return content

    @classmethod
    def format_note_preview(cls, note, tags=None, max_lines=3):
        """Format a note in preview mode with pipe separator.

        Args:
            note: Note dictionary with 'id' and 'content'
            tags: Optional list of tag strings
            max_lines: Maximum lines of content to show (default 3)
        """
        note_id = note['id']
        content = note['content']

        # Format ID and tags, then pipe, then first line of content
        formatted_id = cls.note_id(note_id)
        content_first_line = content.split('\n')[0]

        # Build the line: ID [tags] | content
        line_parts = [formatted_id]
        if tags:
            formatted_tags = [cls.tag(t) for t in tags]
            line_parts.append(" ".join(formatted_tags))
        line_parts.append(f"| {content_first_line}")

        return "  ".join(line_parts)

    @classmethod
    def format_note_full(cls, note, tags=None, notes_manager=None):
        """Format a note with full content and indented layout.

        Args:
            note: Note dictionary with 'id' and 'content'
            tags: Optional list of tag strings
            notes_manager: Optional notes manager for markdown rendering
        """
        note_id = note['id']
        content = note['content']

        # Format ID and tags on first line
        formatted_id = cls.note_id(note_id)
        id_line = formatted_id

        if tags:
            formatted_tags = [cls.tag(t) for t in tags]
            id_line += "  " + " ".join(formatted_tags)

        console.print(id_line)

        # Render markdown content with indentation
        # We'll indent by printing with proper spacing
        content_lines = content.split('\n')
        for line in content_lines:
            console.print(f"        {line}")

        return ""  # Already printed

    @classmethod
    def format_linked_notes(cls, linked_notes, full=False):
        """Format linked notes display.

        Args:
            linked_notes: List of linked note dictionaries
            full: If True, show full content preview; if False, show brief preview
        """
        if not linked_notes:
            return

        console.print(f"\n[bright_black]Links:[/bright_black]")

        for note in linked_notes:
            note_id = note['id']
            content = note['content']

            formatted_id = cls.note_id(note_id)

            if full:
                # Show first 2 lines of content
                preview = cls.truncate_content_by_lines(content, 2)
                console.print(f"  [bright_blue]→[/bright_blue] {formatted_id}")
                for line in preview.split('\n'):
                    console.print(f"            {line}")
                console.print()  # Empty line between linked notes
            else:
                # Show first line only, inline
                first_line = content.split('\n')[0]
                if len(first_line) > 60:
                    first_line = first_line[:60] + '[...]'
                console.print(f"  [bright_blue]→[/bright_blue] {formatted_id}  {first_line}")