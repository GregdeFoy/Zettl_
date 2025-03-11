# zettl/interactive.py
import os
import sys
import re
import subprocess
from typing import List, Dict, Any, Optional, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style

# Import the database module to fetch notes
from zettl.notes import Notes

class NoteCompleter(Completer):
    """Custom completer for note IDs with content preview."""
    
    def __init__(self):
        self.notes_manager = Notes()
        self.note_cache = {}
        self.last_refresh = 0
        self.refresh_interval = 5  # Refresh note cache every 5 seconds
        
    def refresh_notes(self) -> None:
        """Refresh the note cache."""
        import time
        current_time = time.time()
        
        # Only refresh if enough time has passed since last refresh
        if current_time - self.last_refresh > self.refresh_interval:
            try:
                # Fetch a reasonable number of notes (adjust as needed)
                notes = self.notes_manager.list_notes(limit=50)
                
                # Update the cache
                self.note_cache = {
                    note['id']: self._get_preview(note['content']) 
                    for note in notes
                }
                
                self.last_refresh = current_time
            except Exception as e:
                # If there's an error fetching notes, don't crash the shell
                print(f"Warning: Error refreshing note cache: {str(e)}", file=sys.stderr)
    
    def _get_preview(self, content: str, max_len: int = 50) -> str:
        """Create a short preview of note content."""
        if not content:
            return ""
            
        # Clean up the content (remove extra whitespace, newlines, etc.)
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Truncate if needed
        if len(content) > max_len:
            return content[:max_len] + "..."
        return content
    
    def get_completions(self, document, complete_event):
        """Return completions for the current text."""
        self.refresh_notes()
        
        # Get the word being completed
        word_before_cursor = document.get_word_before_cursor()
        
        # Get entire text before cursor to check if we're in a note ID position
        text_before_cursor = document.text_before_cursor
        
        # Define commands that expect a note ID
        note_id_commands = [
            'show', 'link', 'tags', 'related', 'graph', 'llm'
        ]
        
        # Check if we're in a position where note ID completion makes sense
        should_complete = False
        
        # Parse the command to see if we're in a position where a note ID is expected
        words = text_before_cursor.strip().split()
        
        if len(words) >= 1:
            # Handle the case where command is directly used
            if len(words) == 1 and words[0] in note_id_commands:
                should_complete = True
            # Handle the case where a command is used and we're typing a note ID
            elif len(words) >= 2:
                if words[0] in note_id_commands:
                    should_complete = True
                # Handle "zettl command" or "z command" followed by note ID
                elif words[0] in ('z', 'zettl') and words[1] in note_id_commands:
                    should_complete = True
                # Special case for link command which takes two note IDs
                elif len(words) >= 3 and words[0] in ('z', 'zettl') and words[1] == 'link':
                    should_complete = True
        
        if not should_complete:
            return
        
        # Filter notes based on the current input
        matching_notes = {
            note_id: preview
            for note_id, preview in self.note_cache.items()
            if note_id.startswith(word_before_cursor)
        }
        
        # Return matching completions with previews
        for note_id, preview in matching_notes.items():
            display_text = f"{note_id}: {preview}"
            yield Completion(
                note_id,
                start_position=-len(word_before_cursor),
                display=display_text,
                style="fg:cyan"
            )

class PromptToolkitShell:
    def __init__(self):
        self.running = True
        self.quote_commands = {
            'new', 'add', 'search', 'link', 'tags'
        }
        self.note_completer = NoteCompleter()
        self.bindings = self.create_key_bindings()
        
        # Create a nested completer for commands
        command_completer = NestedCompleter.from_nested_dict({
            'new': None,
            'add': None,
            'list': None,
            'show': self.note_completer,
            'link': self.note_completer,
            'tags': self.note_completer,
            'search': None,
            'related': self.note_completer,
            'graph': self.note_completer,
            'llm': self.note_completer,
            'workflow': None,
            'exit': None,
            'quit': None,
            'z': {
                'show': self.note_completer,
                'link': self.note_completer,
                'tags': self.note_completer,
                'related': self.note_completer,
                'graph': self.note_completer,
                'llm': self.note_completer,
            },
            'zettl': {
                'show': self.note_completer,
                'link': self.note_completer,
                'tags': self.note_completer,
                'related': self.note_completer,
                'graph': self.note_completer,
                'llm': self.note_completer,
            }
        })
        
        # Create a session with our completers and key bindings
        self.session = PromptSession(
            key_bindings=self.bindings,
            auto_suggest=AutoSuggestFromHistory(),
            completer=command_completer,
            complete_in_thread=True,
            complete_while_typing=False,  # Only complete when Tab is pressed
        )
        
    def create_key_bindings(self):
        """Create custom key bindings for auto-quoting"""
        bindings = KeyBindings()
        
        # Auto-close quotes when " is pressed
        @bindings.add('"')
        def _(event):
            """Auto-close quotes when pressing double quote"""
            # Insert the opening quote
            event.app.current_buffer.insert_text('"')
            
            # Count quotes to see if we should auto-close
            text = event.app.current_buffer.document.text
            if text.count('"') % 2 == 1:
                # Insert the closing quote
                event.app.current_buffer.insert_text('"')
                # Move cursor back one position
                event.app.current_buffer.cursor_left()
                
        # Handle space key for auto-quoting after commands
        @bindings.add(' ')
        def _(event):
            """Auto-add quotes after specific commands"""
            # Insert the space first
            event.app.current_buffer.insert_text(' ')
            
            # Get the text up to the cursor
            text = event.app.current_buffer.document.text_before_cursor
            
            # Check if we just completed a command word
            words = text.strip().split()
            if len(words) == 1:
                cmd = words[0]
                # Handle zettl/z prefix
                if cmd in ('z', 'zettl'):
                    pass  # Wait for the command word
                elif cmd in self.quote_commands:
                    # Auto-add quotes and position cursor between them
                    event.app.current_buffer.insert_text('""')
                    event.app.current_buffer.cursor_left()
            elif len(words) == 2 and words[0] in ('z', 'zettl'):
                cmd = words[1]
                if cmd in self.quote_commands:
                    # Auto-add quotes and position cursor between them
                    event.app.current_buffer.insert_text('""')
                    event.app.current_buffer.cursor_left()
        
        return bindings
    
    def process_command(self, command):
        """Process the entered command"""
        if command.lower() in ('exit', 'quit'):
            self.running = False
            return
            
        # Skip empty commands
        if not command.strip():
            return
            
        # Execute the zettl command
        try:
            # Need to prefix with 'z' if not already specified
            if not command.startswith(('z ', 'zettl ')):
                command = f"z {command}"
                
            # Execute the command
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
                
            # Force refresh of note cache after commands that might modify notes
            if any(cmd in command for cmd in ['new', 'add']):
                self.note_completer.refresh_notes()
                
        except Exception as e:
            print(f"Error executing command: {str(e)}", file=sys.stderr)
    
    def run(self):
        """Run the interactive shell"""
        print("Zettl Interactive Shell (type 'exit' to quit)")
        print("Auto-quoting enabled for commands: " + ", ".join(self.quote_commands))
        print("Tab completion available for commands and note IDs")
        print("Features: Auto-close quotes, auto-insert quotes, and note ID completion")
        
        while self.running:
            try:
                command = self.session.prompt("zettl> ")
                self.process_command(command)
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                print("\nExiting...")
                break

def main():
    """Run the interactive shell"""
    shell = PromptToolkitShell()
    shell.run()

if __name__ == "__main__":
    main()