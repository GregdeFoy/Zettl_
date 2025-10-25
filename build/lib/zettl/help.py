# help.py
import re

class CommandHelp:
    """Centralized help system for Zettl commands."""

    # Mode: 'cli' for terminal rich markup, 'web' for markdown
    _mode = 'cli'

    @classmethod
    def set_mode(cls, mode):
        """Set help mode: 'cli' or 'web'"""
        cls._mode = mode

    @classmethod
    def _convert_to_markdown(cls, text):
        """Convert rich markup to markdown."""
        # [bold green]text[/bold green] -> **text**
        # [bold]text[/bold] -> **text**
        # [blue]text[/blue] -> *text* (use italic for colored text)
        # [cyan]text[/cyan] -> `text` (use code for cyan)
        # [bold yellow]text[/bold yellow] -> **text**

        # Replace bold with color markers -> just bold
        text = re.sub(r'\[bold [^\]]+\]([^\[]+)\[/bold [^\]]+\]', r'**\1**', text)
        # Replace plain bold
        text = re.sub(r'\[bold\]([^\[]+)\[/bold\]', r'**\1**', text)
        # Replace colored text with italics
        text = re.sub(r'\[blue\]([^\[]+)\[/blue\]', r'*\1*', text)
        # Replace cyan with inline code
        text = re.sub(r'\[cyan\]([^\[]+)\[/cyan\]', r'`\1`', text)
        # Replace yellow (keep plain for markdown)
        text = re.sub(r'\[yellow\]([^\[]+)\[/yellow\]', r'\1', text)
        text = re.sub(r'\[bold yellow\]([^\[]+)\[/bold yellow\]', r'**\1**', text)

        return text

    @classmethod
    def get_main_help(cls):
        """Return the main help text."""
        help_text = f"""
[bold green]zettl v0.1.0[/bold] - A Zettelkasten-style note-taking tool

[bold]NOTE MANAGEMENT[/bold]
  [bold yellow]new[/bold yellow] / [bold yellow]add[/bold yellow]          Create a new note
    [blue]→[/blue] zettl new "Your note content" --tag concept --link 22a4b

  [bold yellow]show[/bold yellow]                Display full note content
    [blue]→[/blue] zettl show 22a4b

  [bold yellow]list[/bold yellow]                List recent notes
    [blue]→[/blue] zettl list --limit 10 --full

  [bold yellow]search[/bold yellow]              Search by text, tag, or date
    [blue]→[/blue] zettl search "concept" -t work +t done --full

  [bold yellow]edit[/bold yellow]                Edit note in default text editor
    [blue]→[/blue] zettl edit 22a4b

  [bold yellow]append[/bold yellow]              Add text to end of note
    [blue]→[/blue] zettl append 22a4b "Additional content"

  [bold yellow]prepend[/bold yellow]             Add text to beginning of note
    [blue]→[/blue] zettl prepend 22a4b "IMPORTANT: "

  [bold yellow]merge[/bold yellow]               Combine multiple notes into one
    [blue]→[/blue] zettl merge 22a4b 18c3d --force

  [bold yellow]delete[/bold yellow]              Delete note and associated data
    [blue]→[/blue] zettl delete 22a4b --keep-tags

[bold]CONNECTIONS[/bold]
  [bold yellow]link[/bold yellow]                Create link between notes
    [blue]→[/blue] zettl link 22a4b 18c3d --context "Related concepts"

  [bold yellow]unlink[/bold yellow]              Remove link between notes
    [blue]→[/blue] zettl unlink 22a4b 18c3d

  [bold yellow]related[/bold yellow]             Show connected notes
    [blue]→[/blue] zettl related 22a4b --full

  [bold yellow]graph[/bold yellow]               Export graph visualization data
    [blue]→[/blue] zettl graph 22a4b --output graph.json --depth 2

[bold]ORGANIZATION[/bold]
  [bold yellow]tags[/bold yellow]                List all tags, show/add note tags
    [blue]→[/blue] zettl tags                  # List all tags
    [blue]→[/blue] zettl tags 22a4b            # Show note's tags
    [blue]→[/blue] zettl tags 22a4b "concept"  # Add tag to note

  [bold yellow]untag[/bold yellow]               Remove tag from note
    [blue]→[/blue] zettl untag 22a4b "concept"

  [bold yellow]todos[/bold yellow]               Manage tasks (notes tagged 'todo')
    [blue]→[/blue] zettl todos --all --tag work --eisenhower

[bold]AI FEATURES[/bold]
  [bold yellow]llm[/bold yellow]                 AI-powered note analysis
    [blue]→[/blue] zettl llm 22a4b --action summarize
    [blue]→[/blue] zettl llm 22a4b --action tags | connect | expand | concepts | questions | critique

[bold]SPECIALIZED FEATURES[/bold]
  [bold yellow]nutrition[/bold yellow] / [bold yellow]nut[/bold yellow]   Track calories and protein
    [blue]→[/blue] zettl nut "Breakfast cal: 500 prot: 25"
    [blue]→[/blue] zettl nutrition --today --history --days 14

  [bold yellow]rules[/bold yellow]               Display random rule from notes
    [blue]→[/blue] zettl rules --source

[bold]SYSTEM[/bold]
  [bold yellow]auth setup[/bold yellow]          Configure API key authentication
    [blue]→[/blue] zettl auth setup

  [bold yellow]auth status[/bold yellow]         Check authentication status
    [blue]→[/blue] zettl auth status

  [bold yellow]help[/bold yellow]                Show this help or command help
    [blue]→[/blue] zettl help
    [blue]→[/blue] zettl COMMAND --help

[bold]GETTING STARTED[/bold]
  1. Set up authentication:     [cyan]zettl auth setup[/cyan]
  2. Create your first note:    [cyan]zettl new "My first note" --tag idea[/cyan]
  3. List your notes:           [cyan]zettl list[/cyan]
  4. Create connections:        [cyan]zettl link NOTE_ID1 NOTE_ID2[/cyan]
  5. Get AI suggestions:        [cyan]zettl llm NOTE_ID --action tags[/cyan]

For detailed help on any command: [cyan]zettl COMMAND --help[/cyan]
"""

        if cls._mode == 'web':
            return cls._convert_to_markdown(help_text)
        return help_text

    @classmethod
    def get_command_help(cls, command):
        """Return detailed help for a specific command."""
        help_templates = {
            "auth": f"""
[bold green]auth[/bold] - Authentication management

[bold]Subcommands:[/bold]
  [yellow]setup[/yellow]   Configure API key authentication for CLI access
  [yellow]status[/yellow]  Check current authentication status

[bold]Usage:[/bold]
  zettl auth setup    # Set up authentication
  zettl auth status   # Check authentication status

[bold]Description:[/bold]
  The auth command manages your API key authentication. You need to set up
  authentication before using most zettl commands. Get your API key from
  the Zettl web interface.
""",

            "new": f"""
[bold green]new [CONTENT][/bold] - Create a new note with the given content

[bold]Usage:[/bold]
  zettl new "Your note content here"

[bold]Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add one or more tags to the note (can be used multiple times)
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note

[bold]Examples:[/bold]
  [blue]zettl new "This is a new note"[/blue]
  [blue]zettl new "Note with tag" -t important[/blue]
  [blue]zettl new "Note with multiple tags" -t concept -t research[/blue]
  [blue]zettl new "Linked note" --link 22a4b[/blue]
""",

            "add": f"""
[bold green]add [CONTENT][/bold] - Create a new note with the given content (alias for 'new')

[bold]Usage:[/bold]
  zettl add "Your note content here"

[bold]Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add one or more tags to the note (can be used multiple times)
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note

[bold]Examples:[/bold]
  [blue]zettl add "This is a new note"[/blue]
  [blue]zettl add "Note with tag" -t important[/blue]
  [blue]zettl add "Note with multiple tags" -t concept -t research[/blue]
  [blue]zettl add "Linked note" --link 22a4b[/blue]
""",

            "list": f"""
[bold green]list[/bold] - List recent notes

[bold]Options:[/bold]
  [yellow]-l, --limit NUMBER[/yellow]  Number of notes to display (default: 10)
  [yellow]-f, --full[/yellow]          Show full content of notes
  [yellow]-c, --compact[/yellow]       Show very compact list (IDs only)

[bold]Examples:[/bold]
  [blue]zettl list[/blue]                  Show 10 most recent notes
  [blue]zettl list --limit 5[/blue]        Show 5 most recent notes
  [blue]zettl list --full[/blue]           Show full content of recent notes
  [blue]zettl list -c[/blue]               Show compact list of note IDs
""",

            "show": f"""
[bold green]show NOTE_ID[/bold] - Display note content

[bold]Usage:[/bold]
  zettl show NOTE_ID

[bold]Examples:[/bold]
  [blue]zettl show 22a4b[/blue]       Show content of note with ID 22a4b
""",

            "search": f"""
[bold green]search [QUERY][/bold] - Search for notes containing text, with tag, or by date

[bold]Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]        Search for notes with this tag
  [yellow]+t, --exclude-tag TAG[/yellow] Exclude notes with this tag
  [yellow]-d, --date DATE[/yellow]      Search for notes created on a specific date (YYYY-MM-DD)
  [yellow]-f, --full[/yellow]           Show full content of matching notes

[bold]Examples:[/bold]
  [blue]zettl search "keyword"[/blue]       Search notes containing "keyword"
  [blue]zettl search -t concept[/blue]      Show notes tagged with "concept"
  [blue]zettl search -d 2025-04-07[/blue]   Show notes created on April 7, 2025
  [blue]zettl search -t work +t done[/blue] Show notes tagged "work" but not "done"
  [blue]zettl search "keyword" --full[/blue] Show full content of matching notes
""",

            "link": f"""
[bold green]link SOURCE_ID TARGET_ID[/bold] - Create link between notes

[bold]Usage:[/bold]
  zettl link SOURCE_ID TARGET_ID

[bold]Options:[/bold]
  [yellow]-c, --context TEXT[/yellow]   Add context to the link

[bold]Examples:[/bold]
  [blue]zettl link 22a4b 18c3d[/blue]
  [blue]zettl link 22a4b 18c3d --context "These concepts are related"[/blue]
""",

            "related": f"""
[bold green]related NOTE_ID[/bold] - Show notes connected to this note

[bold]Usage:[/bold]
  zettl related NOTE_ID

[bold]Options:[/bold]
  [yellow]-f, --full[/yellow]          Show full content of related notes

[bold]Examples:[/bold]
  [blue]zettl related 22a4b[/blue]
  [blue]zettl related 22a4b --full[/blue]
""",

            "graph": f"""
[bold green]graph [NOTE_ID][/bold] - Generate a graph visualization of notes

[bold]Usage:[/bold]
  zettl graph [NOTE_ID]

[bold]Options:[/bold]
  [yellow]-o, --output FILENAME[/yellow]  Output file for graph data (default: zettl_graph.json)
  [yellow]-d, --depth NUMBER[/yellow]     Depth of connections to include (default: 2)

[bold]Examples:[/bold]
  [blue]zettl graph[/blue]                         Graph all notes
  [blue]zettl graph 22a4b[/blue]                  Graph centered on note 22a4b
  [blue]zettl graph 22a4b --output my_graph.json[/blue]
  [blue]zettl graph 22a4b --depth 3[/blue]        Include notes up to 3 links away
""",

            "tags": f"""
[bold green]tags [NOTE_ID] [TAG][/bold] - Show or add tags to a note

[bold]Usage:[/bold]
  zettl tags                  List all tags
  zettl tags NOTE_ID          Show tags for a specific note
  zettl tags NOTE_ID TAG      Add a tag to a note

[bold]Examples:[/bold]
  [blue]zettl tags[/blue]                 List all tags with counts
  [blue]zettl tags 22a4b[/blue]           Show tags for note 22a4b
  [blue]zettl tags 22a4b "concept"[/blue] Add "concept" tag to note 22a4b
""",

"todos": f"""
[bold green]todos[/bold] - List all notes tagged with 'todo'

[bold]Options:[/bold]
  [yellow]-a, --all[/yellow]            Show all todos (active and completed)
  [yellow]-dt, --donetoday[/yellow]     Show todos completed today
  [yellow]-c, --cancel[/yellow]         Show canceled todos
  [yellow]-t, --tag TAG[/yellow]        Filter todos by additional tag
  [yellow]-e, --eisenhower[/yellow]     Display todos in Eisenhower matrix format

[bold]Examples:[/bold]
  [blue]zettl todos[/blue]                  Show active todos
  [blue]zettl todos -a[/blue]               Show all todos (active and completed)
  [blue]zettl todos -dt[/blue]              Show todos completed today
  [blue]zettl todos -e[/blue]               Show todos in Eisenhower matrix
  [blue]zettl todos -t work[/blue]          Show todos tagged with "work"
  [blue]zettl todos -t work -t urgent[/blue] Show todos with multiple tags
""",

            "delete": f"""
[bold green]delete NOTE_ID[/bold] - Delete a note and its associated data

[bold]Usage:[/bold]
  zettl delete NOTE_ID

[bold]Options:[/bold]
  [yellow]-f, --force[/yellow]         Skip confirmation prompt
  [yellow]--keep-links[/yellow]        Keep links to and from this note
  [yellow]--keep-tags[/yellow]         Keep tags associated with this note

[bold]Examples:[/bold]
  [blue]zettl delete 22a4b[/blue]
  [blue]zettl delete 22a4b --force[/blue]     Delete without confirmation
  [blue]zettl delete 22a4b --keep-tags[/blue] Delete note but keep its tags
""",

            "untag": f"""
[bold green]untag NOTE_ID TAG[/bold] - Remove a tag from a note

[bold]Usage:[/bold]
  zettl untag NOTE_ID TAG

[bold]Examples:[/bold]
  [blue]zettl untag 22a4b "concept"[/blue]  Remove "concept" tag from note 22a4b
""",

            "unlink": f"""
[bold green]unlink SOURCE_ID TARGET_ID[/bold] - Remove a link between two notes

[bold]Usage:[/bold]
  zettl unlink SOURCE_ID TARGET_ID

[bold]Examples:[/bold]
  [blue]zettl unlink 22a4b 18c3d[/blue]  Remove link from note 22a4b to 18c3d
""",

            "append": f"""
[bold green]append NOTE_ID TEXT[/bold] - Append text to the end of a note

[bold]Usage:[/bold]
  zettl append NOTE_ID "Text to append"

[bold]Description:[/bold]
  Adds the provided text to the end of an existing note.
  A newline is automatically added between the existing content and new text.

[bold]Examples:[/bold]
  [blue]zettl append 22a4b "Additional thoughts on this topic"[/blue]
  [blue]zettl append 22a4b "Follow-up: new research findings"[/blue]

[bold]Use cases:[/bold]
  • Adding new information to existing notes
  • Appending updates or follow-ups
  • Building notes incrementally over time
""",

            "prepend": f"""
[bold green]prepend NOTE_ID TEXT[/bold] - Prepend text to the beginning of a note

[bold]Usage:[/bold]
  zettl prepend NOTE_ID "Text to prepend"

[bold]Description:[/bold]
  Adds the provided text to the beginning of an existing note.
  A newline is automatically added between the new text and existing content.

[bold]Examples:[/bold]
  [blue]zettl prepend 22a4b "UPDATE: "[/blue]
  [blue]zettl prepend 22a4b "IMPORTANT: This has been revised"[/blue]

[bold]Use cases:[/bold]
  • Adding status updates at the top of notes
  • Inserting important context before original content
  • Marking notes with time-sensitive information
""",

            "edit": f"""
[bold green]edit NOTE_ID[/bold] - Edit a note in your default text editor

[bold]Usage:[/bold]
  zettl edit NOTE_ID

[bold]Description:[/bold]
  Opens the note in your system's default text editor for full editing.

  [bold]Platform-specific behavior:[/bold]
  • [cyan]Linux/Mac:[/cyan] Uses $EDITOR or $VISUAL environment variable (defaults to nano)
  • [cyan]Windows:[/cyan] Uses notepad or $EDITOR environment variable

[bold]Examples:[/bold]
  [blue]zettl edit 22a4b[/blue]                  # Edit note 22a4b
  [blue]export EDITOR=vim && zettl edit 22a4b[/blue]  # Use vim (Linux/Mac)
  [blue]set EDITOR=code && zettl edit 22a4b[/blue]    # Use VS Code (Windows)

[bold]Tips:[/bold]
  • Set your preferred editor: export EDITOR=vim (or nano, emacs, etc.)
  • Changes are saved when you exit the editor
  • If no changes are made, the note remains unchanged
""",

            "merge": f"""
[bold green]merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...][/bold] - Merge multiple notes into a single note

[bold]Usage:[/bold]
  zettl merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...]

[bold]What it does:[/bold]
  • Combines content from all notes (ordered by creation date)
  • Collects all unique tags from all notes
  • Preserves external links (updates them to point to new note)
  • Deletes the old notes after successful merge

[bold]Options:[/bold]
  [yellow]-f, --force[/yellow]  Skip confirmation prompt

[bold]Examples:[/bold]
  [blue]zettl merge 22a4b 18c3d[/blue]            Merge two notes
  [blue]zettl merge 22a4b 18c3d 45f6g[/blue]       Merge three notes
  [blue]zettl merge 22a4b 18c3d --force[/blue]     Merge without confirmation

[bold]Note:[/bold]
  This is useful for consolidating related notes or combining duplicates.
  All tags and external links are preserved in the new merged note.
""",

            "llm": f"""
[bold green]llm NOTE_ID[/bold] - Use Claude AI to analyze and enhance notes

[bold]Actions:[/bold]
  [yellow]summarize[/yellow]   Generate a concise summary of the note
  [yellow]connect[/yellow]     Find potential connections to other notes
  [yellow]tags[/yellow]        Suggest relevant tags for the note
  [yellow]expand[/yellow]      Create an expanded version of the note
  [yellow]concepts[/yellow]    Extract key concepts from the note
  [yellow]questions[/yellow]   Generate thought-provoking questions
  [yellow]critique[/yellow]    Provide constructive feedback on the note

[bold]Options:[/bold]
  [yellow]-a, --action ACTION[/yellow]  LLM action to perform (see above)
  [yellow]-c, --count NUMBER[/yellow]   Number of results to return (default: 3)
  [yellow]-s, --show-source[/yellow]    Show the source note before analysis
  [yellow]-d, --debug[/yellow]          Show debug information for troubleshooting

[bold]Examples:[/bold]
  [blue]zettl llm 22a4b[/blue]                 Summarize note 22a4b (default action)
  [blue]zettl llm 22a4b -a tags[/blue]         Suggest tags for note 22a4b
  [blue]zettl llm 22a4b -a connect -c 5[/blue] Find 5 related notes to note 22a4b
  [blue]zettl llm 22a4b -a expand[/blue]       Create an expanded version of the note
  [blue]zettl llm 22a4b -a concepts[/blue]     Extract key concepts from the note
  [blue]zettl llm 22a4b -a questions[/blue]    Generate questions based on the note
  [blue]zettl llm 22a4b -a critique[/blue]     Get constructive feedback on the note
""",

            "api-key": f"""
[bold green]api-key[/bold] - Manage API keys for CLI access

[bold]Usage:[/bold]
  api-key                    # List your existing API keys
  api-key generate           # Generate new API key with default name
  api-key generate "My Key"  # Generate new API key with custom name

[bold]Description:[/bold]
  API keys allow you to authenticate with the Zettl CLI from the command line.
  Each key can have a custom name to help you identify its purpose.

[bold]Examples:[/bold]
  api-key generate "Development Key"  # Create key for development
  api-key                           # View all your keys

[bold]Notes:[/bold]
  - API keys are only shown once when generated
  - Copy and save them immediately
  - Configure with CLI: zettl auth setup
""",

            "rules": f"""
[bold green]rules[/bold] - Display a random rule from notes tagged with 'rules'

[bold]Usage:[/bold]
  zettl rules

[bold]Options:[/bold]
  [yellow]-s, --source[/yellow]  Show the source note ID

[bold]Examples:[/bold]
  [blue]zettl rules[/blue]
  [blue]zettl rules --source[/blue]  # Show the source note ID
""",

            "nutrition": f"""
[bold green]nutrition[/bold] - Track and analyze nutrition data (calories and protein)

[bold]Usage:[/bold]
  zettl nutrition "Food description cal: XXX prot: YYY"  # Add new entry
  zettl nutrition --today                                # Show today's summary
  zettl nutrition --history                              # Show nutrition history

[bold]Options:[/bold]
  [yellow]-t, --today[/yellow]       Show today's nutrition summary
  [yellow]-i, --history[/yellow]     Show nutrition history
  [yellow]-d, --days NUMBER[/yellow] Number of days to show in history (default: 7)
  [yellow]-p, --past DATE[/yellow]   Add an entry for a past date (YYYY-MM-DD format)

[bold]Examples:[/bold]
  [blue]zettl nutrition "Breakfast cal: 500 prot: 25"[/blue]
  [blue]zettl nutrition "Dinner cal: 800 prot: 40" --past 2025-04-05[/blue]
  [blue]zettl nutrition --today[/blue]
  [blue]zettl nutrition --history --days 14[/blue]
  
[bold]Shorthand:[/bold]
  You can use the alias 'nut' instead of 'nutrition'
  [blue]zettl nut "Lunch cal: 700 prot: 35"[/blue]
""",

            "nut": f"""
[bold green]nut[/bold] - Track and analyze nutrition data (alias for 'nutrition')

[bold]Usage:[/bold]
  zettl nut "Food description cal: XXX prot: YYY"  # Add new entry
  zettl nut --today                                # Show today's summary
  zettl nut --history                              # Show nutrition history

[bold]Options:[/bold]
  [yellow]-t, --today[/yellow]       Show today's nutrition summary
  [yellow]-i, --history[/yellow]     Show nutrition history
  [yellow]-d, --days NUMBER[/yellow] Number of days to show in history (default: 7)
  [yellow]-p, --past DATE[/yellow]   Add an entry for a past date (YYYY-MM-DD format)

[bold]Examples:[/bold]
  [blue]zettl nut "Breakfast cal: 500 prot: 25"[/blue]
  [blue]zettl nut "Dinner cal: 800 prot: 40" --past 2025-04-05[/blue]
  [blue]zettl nut --today[/blue]
  [blue]zettl nut --history --days 14[/blue]
""",

            "help": f"""
[bold green]help[/bold] - Show help information

[bold]Usage:[/bold]
  zettl help              Show general help
  zettl COMMAND --help    Show help for a specific command

[bold]Examples:[/bold]
  [blue]zettl help[/blue]
  [blue]zettl search --help[/blue]
"""
        }
        
        help_text = help_templates.get(command, f"No detailed help available for '{command}'. Try 'help' for a list of all commands.")

        if cls._mode == 'web':
            return cls._convert_to_markdown(help_text)
        return help_text