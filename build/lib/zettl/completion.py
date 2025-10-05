# completion.py
import readline
import sys
import re
import os

class ZettlCompleter:
    def __init__(self):
        # Commands that should trigger auto-quoting
        self.quote_commands = {
            'new', 'add', 'search'
        }
        # Current command being typed
        self.current_command = None
        # Flag to track if we just inserted quotes
        self.just_inserted_quotes = False
        
    def complete(self, text, state):
        """Completion function for readline"""
        # Not implementing actual completion suggestions here,
        # just returning None to indicate no completions
        return None
        
    def input_hook(self):
        """Hook function that gets called after each keystroke"""
        # Get the current line
        line = readline.get_line_buffer()
        
        # Check if we just inserted quotes and need to move cursor back
        if self.just_inserted_quotes:
            # Move cursor one character to the left (inside the quotes)
            readline.redisplay()
            self.just_inserted_quotes = False
            return
            
        # Detect the command part (first or second word)
        match = re.match(r'^(\w+)(?:\s+(\w+))?', line)
        if match:
            command_parts = [p for p in match.groups() if p]
            
            # Handle 'z' or 'zettl' followed by a command
            if len(command_parts) == 2 and command_parts[0] in ('z', 'zettl'):
                command = command_parts[1]
                # Check if the command should trigger auto-quoting
                if command in self.quote_commands:
                    self.current_command = command
                    
            # Handle just the command name (for testing)
            elif len(command_parts) == 1 and command_parts[0] in self.quote_commands:
                self.current_command = command_parts[0]
            else:
                self.current_command = None
                
        # Check if we just entered a double quote
        if line.endswith('"') and not line.endswith('\\"'):
            # Count quotes to determine if we should add a closing quote
            if line.count('"') % 2 == 1:  # Odd number of quotes, we need to add a closing one
                # Insert a closing quote
                readline.insert_text('"')
                # Set flag to move cursor back one character
                self.just_inserted_quotes = True
                
        # Check if we just completed a command that should have auto-quotes
        if self.current_command and line.endswith(' ') and not '"' in line:
            last_char_index = len(line) - 1
            if last_char_index >= 0 and line[last_char_index] == ' ':
                # Add quotes automatically after the command
                readline.insert_text('""')
                # Set flag to move cursor back one character
                self.just_inserted_quotes = True

def setup_completion():
    """Set up readline with our custom completer and hook"""
    completer = ZettlCompleter()
    
    # Set up readline
    readline.set_completer(completer.complete)
    
    # Set completion display function
    readline.set_completion_display_matches_hook(None)
    
    # Set pre-input hook
    if hasattr(readline, 'set_pre_input_hook'):
        readline.set_pre_input_hook(completer.input_hook)
        
    # Tab completion style
    readline.parse_and_bind('tab: complete')
    
    return completer

def custom_input(prompt=""):
    """Custom input function with auto-quoting"""
    completer = setup_completion()
    try:
        return input(prompt)
    finally:
        # Clean up
        if hasattr(readline, 'set_pre_input_hook'):
            readline.set_pre_input_hook(None)
            
# Example of integration with CLI
def main():
    print("Zettl CLI with auto-quoting (press Ctrl+C to exit)")
    print("Try typing: new, add, or search followed by a space")
    print("Or try typing a double quote")
    
    while True:
        try:
            command = custom_input("zettl> ")
            print(f"You entered: {command}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()