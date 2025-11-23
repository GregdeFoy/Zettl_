# help.py
import re
from zettl import __version__

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
        # [bold]text[/bold green] -> **text**
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
[bold green]zettl v{__version__}[/bold green] - A Zettelkasten-style note-taking tool

[bold]NOTE MANAGEMENT[/bold]
  [bold yellow]todo[/bold yellow]                List todos OR create new todo
    [blue]→[/blue] zettl todo                  # List active todos
    [blue]→[/blue] zettl todo "Call dentist" -l health-project

  [bold yellow]idea[/bold yellow]                List ideas OR create new idea
    [blue]→[/blue] zettl idea                  # List active ideas
    [blue]→[/blue] zettl idea "Add caching" -l dev-project

  [bold yellow]note[/bold yellow]                List notes OR create new note
    [blue]→[/blue] zettl note                  # List active notes
    [blue]→[/blue] zettl note "Meeting notes" -l work-project

  [bold yellow]project[/bold yellow]             List/view/create projects
    [blue]→[/blue] zettl project               # List all projects with stats
    [blue]→[/blue] zettl project -l learn-rust # View project detail
    [blue]→[/blue] zettl project "New Project" --id my-proj

  [bold yellow]show[/bold yellow]                Display note content and related notes
    [blue]→[/blue] zettl show 22a4b -r

  [bold yellow]list[/bold yellow]                List recent notes
    [blue]→[/blue] zettl list --limit 10

  [bold yellow]search[/bold yellow]              Search by text, tag, or date
    [blue]→[/blue] zettl search "concept" -t work

  [bold yellow]edit[/bold yellow]                Edit note in default text editor
    [blue]→[/blue] zettl edit 22a4b

  [bold yellow]append[/bold yellow]              Add text to end of note
    [blue]→[/blue] zettl append 22a4b "Additional content"

  [bold yellow]prepend[/bold yellow]             Add text to beginning of note
    [blue]→[/blue] zettl prepend 22a4b "IMPORTANT: "

  [bold yellow]merge[/bold yellow]               Combine multiple notes into one
    [blue]→[/blue] zettl merge 22a4b 18c3d

  [bold yellow]delete[/bold yellow]              Delete note and associated data
    [blue]→[/blue] zettl delete 22a4b

[bold]CONNECTIONS[/bold]
  [bold yellow]link[/bold yellow]                Create or remove link between notes
    [blue]→[/blue] zettl link 22a4b 18c3d
    [blue]→[/blue] zettl link 22a4b 18c3d -r   # Remove link

  [bold yellow]graph[/bold yellow]               Export graph visualization data
    [blue]→[/blue] zettl graph 22a4b --depth 2

[bold]ORGANIZATION[/bold]
  [bold yellow]tags[/bold yellow]                List all tags or manage note tags
    [blue]→[/blue] zettl tags                  # List all tags
    [blue]→[/blue] zettl tags 22a4b            # Show note's tags
    [blue]→[/blue] zettl tags 22a4b "concept"  # Add tag
    [blue]→[/blue] zettl tags 22a4b "concept" -r  # Remove tag

[bold]AI FEATURES[/bold]
  [bold yellow]llm[/bold yellow]                 AI-powered note analysis
    [blue]→[/blue] zettl llm 22a4b --action summarize
    [blue]→[/blue] zettl llm 22a4b --action tags

[bold]SPECIALIZED[/bold]
  [bold yellow]rules[/bold yellow]               Display random rule from notes
    [blue]→[/blue] zettl rules

[bold]SYSTEM[/bold]
  [bold yellow]auth setup[/bold yellow]          Configure API key authentication
    [blue]→[/blue] zettl auth setup

  [bold yellow]auth status[/bold yellow]         Check authentication status
    [blue]→[/blue] zettl auth status

[bold]GETTING STARTED[/bold]
  1. Set up authentication:     [cyan]zettl auth setup[/cyan]
  2. Create a project:          [cyan]zettl project "My Project" --id my-project[/cyan]
  3. Add tasks to project:      [cyan]zettl todo "First task" -l my-project[/cyan]
  4. List your notes:           [cyan]zettl list[/cyan]

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
[bold green]auth[/bold green] - Authentication management

[bold]Subcommands:[/bold]
  [yellow]setup[/yellow]   Configure API key
  [yellow]status[/yellow]  Check authentication status

[bold]Examples:[/bold]
  [blue]zettl auth setup[/blue]
  [blue]zettl auth status[/blue]

[bold]Description:[/bold]
  Configure authentication before using zettl. Get your API key from the web interface.
""",

            "todo": f"""
[bold green]todo [CONTENT][/bold green] - List todos OR create new todo

[bold]Usage:[/bold]
  zettl todo                   # List active todos
  zettl todo "Task to do"      # Create new todo

[bold]List Mode:[/bold]
  [yellow]-a, --all[/yellow]           Show all todos (active, done, canceled)
  [yellow]-dt, --donetoday[/yellow]    Show todos completed today
  [yellow]-c, --cancel[/yellow]        Show canceled todos only
  [yellow]-t, --tag TAG[/yellow]       Filter by additional tag
  [yellow]-l, --link NOTE_ID[/yellow]  Filter by linked note

[bold]Create Mode:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags
  [yellow]-l, --link NOTE_ID[/yellow]  Link to note
  [yellow]--id CUSTOM_ID[/yellow]      Use custom ID

[bold]Examples:[/bold]
  [blue]zettl todo[/blue]                   List active todos
  [blue]zettl todo -a[/blue]                Show all todos
  [blue]zettl todo -l my-project[/blue]     Filter by project
  [blue]zettl todo -dt[/blue]               Completed today
  [blue]zettl todo "Review PR"[/blue]       Create todo
  [blue]zettl todo "Call dentist" -l health-project[/blue]
""",

            "t": f"""
[bold green]t [CONTENT][/bold green] - Shortcut for 'todo' command

See 'zettl todo --help' for full documentation.
""",

            "idea": f"""
[bold green]idea [CONTENT][/bold green] - List ideas OR create new idea

[bold]Usage:[/bold]
  zettl idea                   # List active ideas
  zettl idea "New idea"        # Create new idea

[bold]List Mode:[/bold]
  [yellow]-a, --all[/yellow]           Show all ideas (active, done, canceled)
  [yellow]-c, --cancel[/yellow]        Show canceled ideas only
  [yellow]-t, --tag TAG[/yellow]       Filter by additional tag
  [yellow]-l, --link NOTE_ID[/yellow]  Filter by linked note

[bold]Create Mode:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags
  [yellow]-l, --link NOTE_ID[/yellow]  Link to note
  [yellow]--id CUSTOM_ID[/yellow]      Use custom ID

[bold]Examples:[/bold]
  [blue]zettl idea[/blue]                   List active ideas
  [blue]zettl idea -a[/blue]                Show all ideas
  [blue]zettl idea -l my-project[/blue]     Filter by project
  [blue]zettl idea "Add caching layer"[/blue]
  [blue]zettl idea "Redesign UI" -l frontend-project[/blue]
""",

            "i": f"""
[bold green]i [CONTENT][/bold green] - Shortcut for 'idea' command

See 'zettl idea --help' for full documentation.
""",

            "note": f"""
[bold green]note [CONTENT][/bold green] - List notes OR create new note

[bold]Usage:[/bold]
  zettl note                   # List active notes
  zettl note "New note"        # Create new note

[bold]List Mode:[/bold]
  [yellow]-a, --all[/yellow]           Show all notes (active, done, canceled)
  [yellow]-c, --cancel[/yellow]        Show canceled notes only
  [yellow]-t, --tag TAG[/yellow]       Filter by additional tag
  [yellow]-l, --link NOTE_ID[/yellow]  Filter by linked note

[bold]Create Mode:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags
  [yellow]-l, --link NOTE_ID[/yellow]  Link to note
  [yellow]--id CUSTOM_ID[/yellow]      Use custom ID

[bold]Examples:[/bold]
  [blue]zettl note[/blue]                   List active notes
  [blue]zettl note -a[/blue]                Show all notes
  [blue]zettl note -l my-project[/blue]     Filter by project
  [blue]zettl note "Meeting notes"[/blue]
  [blue]zettl note "Architecture decisions" -l dev-project[/blue]
""",

            "n": f"""
[bold green]n [CONTENT][/bold green] - Shortcut for 'note' command

See 'zettl note --help' for full documentation.
""",

            "project": f"""
[bold green]project [CONTENT][/bold green] - List/view/create projects

[bold]Usage:[/bold]
  zettl project                # List all projects with stats
  zettl project -l PROJECT_ID  # View project detail
  zettl project "New Project"  # Create project

[bold]List Mode:[/bold]
  Shows all projects with active todo/idea/note counts

[bold]Detail Mode (-l required):[/bold]
  [yellow]-l, --link PROJECT_ID[/yellow]  View project detail
  [yellow]-a, --all[/yellow]              Show all notes (active, done, canceled)
  [yellow]-f, --full[/yellow]             Show full content
  [yellow]-t, --tag TAG[/yellow]          Filter by additional tag

[bold]Create Mode:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags
  [yellow]--id CUSTOM_ID[/yellow]      Use custom ID (recommended)

[bold]Examples:[/bold]
  [blue]zettl project[/blue]                List all projects
  [blue]zettl project -l learn-rust[/blue]    View project detail
  [blue]zettl project -l learn-rust -f[/blue] View with full content
  [blue]zettl project "Learn Rust" --id learn-rust[/blue]
  [blue]zettl project "Website Redesign" --id web-redesign[/blue]
""",

            "p": f"""
[bold green]p [CONTENT][/bold green] - Shortcut for 'project' command

See 'zettl project --help' for full documentation.
""",

            "list": f"""
[bold green]list[/bold green] - List recent notes

[bold]Options:[/bold]
  [yellow]-l, --limit NUMBER[/yellow]  Number of notes (default: 10)
  [yellow]-f, --full[/yellow]          Show full content
  [yellow]-c, --compact[/yellow]       Show IDs only

[bold]Examples:[/bold]
  [blue]zettl list[/blue]
  [blue]zettl list --limit 20[/blue]
  [blue]zettl list --full[/blue]
""",

            "show": f"""
[bold green]show NOTE_ID[/bold green] - Display note content and related notes

[bold]Options:[/bold]
  [yellow]-r, --related[/yellow]       Show linked notes (bidirectional)
  [yellow]-f, --full[/yellow]          Show full content of related notes

[bold]Examples:[/bold]
  [blue]zettl show 22a4b[/blue]
  [blue]zettl show 22a4b -r[/blue]
  [blue]zettl show 22a4b -r -f[/blue]
""",

            "search": f"""
[bold green]search [QUERY][/bold green] - Search notes by text, tags, or date

[bold]Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]        Must have tag (AND with multiple)
  [yellow]+t, --exclude-tag TAG[/yellow] Must not have tag (OR with multiple)
  [yellow]-d, --date DATE[/yellow]      Created on date (YYYY-MM-DD)
  [yellow]-f, --full[/yellow]           Show full content

[bold]Examples:[/bold]
  [blue]zettl search "keyword"[/blue]
  [blue]zettl search -t work -t urgent[/blue]    Has work AND urgent
  [blue]zettl search -t project +t done[/blue]   Has project, not done
  [blue]zettl search -d 2025-04-07 -t work[/blue]
""",

            "link": f"""
[bold green]link SOURCE_ID TARGET_ID[/bold green] - Create or remove link between notes

[bold]Options:[/bold]
  [yellow]-c, --context TEXT[/yellow]   Add context
  [yellow]-r, --remove[/yellow]         Remove link

[bold]Examples:[/bold]
  [blue]zettl link 22a4b 18c3d[/blue]
  [blue]zettl link 22a4b 18c3d --context "Related"[/blue]
  [blue]zettl link 22a4b 18c3d -r[/blue]
""",

            "related": f"""
[bold green]related NOTE_ID[/bold green] - Show connected notes

[bold yellow]DEPRECATED:[/bold yellow] Use [cyan]show -r[/cyan] instead.

[bold]Examples:[/bold]
  [blue]zettl show 22a4b -r[/blue]          Show note and related notes
  [blue]zettl show 22a4b -r -f[/blue]       Show with full content
""",

            "graph": f"""
[bold green]graph [NOTE_ID][/bold green] - Export graph visualization data

[bold]Options:[/bold]
  [yellow]-o, --output FILE[/yellow]  Output file (default: zettl_graph.json)
  [yellow]-d, --depth NUMBER[/yellow]  Connection depth (default: 2)

[bold]Examples:[/bold]
  [blue]zettl graph[/blue]                    All notes
  [blue]zettl graph 22a4b[/blue]              Centered on note
  [blue]zettl graph 22a4b --depth 3[/blue]    3 links deep
""",

            "tags": f"""
[bold green]tags [NOTE_ID] ["TAGS"][/bold green] - List all tags or manage note tags

[bold]Usage:[/bold]
  zettl tags                  List all tags
  zettl tags NOTE_ID          Show note's tags
  zettl tags NOTE_ID "TAG"    Add tag
  zettl tags NOTE_ID "TAG" -r Remove tag

[bold]Options:[/bold]
  [yellow]-r, --remove[/yellow]   Remove tag instead of adding

[bold]Examples:[/bold]
  [blue]zettl tags[/blue]
  [blue]zettl tags 22a4b[/blue]
  [blue]zettl tags 22a4b concept[/blue]
  [blue]zettl tags 22a4b "todo urgent"[/blue]
  [blue]zettl tags 22a4b concept -r[/blue]
""",

"todos": f"""
[bold green]todos[/bold green] - List todos

[bold yellow]DEPRECATED:[/bold yellow] Use [cyan]todo[/cyan] instead.

[bold]Examples:[/bold]
  [blue]zettl todo[/blue]      List active todos
  [blue]zettl todo -a[/blue]   Show all todos
""",

            "delete": f"""
[bold green]delete NOTE_ID[/bold green] - Delete a note

[bold]Options:[/bold]
  [yellow]-f, --force[/yellow]      Skip confirmation
  [yellow]--keep-links[/yellow]     Keep links
  [yellow]--keep-tags[/yellow]      Keep tags

[bold]Examples:[/bold]
  [blue]zettl delete 22a4b[/blue]
  [blue]zettl delete 22a4b --force[/blue]
  [blue]zettl delete 22a4b --keep-tags[/blue]
""",

            "untag": f"""
[bold green]untag[/bold green] - Remove tag from note

[bold yellow]DEPRECATED:[/bold yellow] Use [cyan]tags -r[/cyan] instead.

[bold]Example:[/bold]
  [blue]zettl tags 22a4b concept -r[/blue]
""",

            "unlink": f"""
[bold green]unlink[/bold green] - Remove link between notes

[bold yellow]DEPRECATED:[/bold yellow] Use [cyan]link -r[/cyan] instead.

[bold]Example:[/bold]
  [blue]zettl link 22a4b 18c3d -r[/blue]
""",

            "append": f"""
[bold green]append NOTE_ID TEXT[/bold green] - Add text to end of note

[bold]Examples:[/bold]
  [blue]zettl append 22a4b "Additional thoughts"[/blue]
  [blue]zettl append 22a4b "Follow-up: new findings"[/blue]
""",

            "prepend": f"""
[bold green]prepend NOTE_ID TEXT[/bold green] - Add text to beginning of note

[bold]Examples:[/bold]
  [blue]zettl prepend 22a4b "UPDATE: "[/blue]
  [blue]zettl prepend 22a4b "IMPORTANT: Revised"[/blue]
""",

            "edit": f"""
[bold green]edit NOTE_ID[/bold green] - Edit note in default text editor

[bold]Description:[/bold]
  Opens note in $EDITOR (defaults to nano on Linux/Mac, notepad on Windows).

[bold]Examples:[/bold]
  [blue]zettl edit 22a4b[/blue]
  [blue]export EDITOR=vim && zettl edit 22a4b[/blue]
""",

            "merge": f"""
[bold green]merge NOTE_ID1 NOTE_ID2 [...][/bold green] - Combine multiple notes into one

[bold]Description:[/bold]
  Combines content, tags, and links. Deletes old notes after merge.

[bold]Options:[/bold]
  [yellow]-f, --force[/yellow]  Skip confirmation

[bold]Examples:[/bold]
  [blue]zettl merge 22a4b 18c3d[/blue]
  [blue]zettl merge 22a4b 18c3d 45f6g[/blue]
  [blue]zettl merge 22a4b 18c3d --force[/blue]
""",

            "llm": f"""
[bold green]llm NOTE_ID[/bold green] - AI-powered note analysis

[bold]Actions:[/bold]
  [yellow]summarize[/yellow]   Generate summary (default)
  [yellow]connect[/yellow]     Find connections to other notes
  [yellow]tags[/yellow]        Suggest tags
  [yellow]expand[/yellow]      Create expanded version
  [yellow]concepts[/yellow]    Extract key concepts
  [yellow]questions[/yellow]   Generate questions
  [yellow]critique[/yellow]    Provide feedback

[bold]Options:[/bold]
  [yellow]-a, --action ACTION[/yellow]  Action to perform
  [yellow]-c, --count NUMBER[/yellow]   Number of results (default: 3)
  [yellow]-s, --show-source[/yellow]    Show source note
  [yellow]-d, --debug[/yellow]          Show debug info

[bold]Examples:[/bold]
  [blue]zettl llm 22a4b[/blue]
  [blue]zettl llm 22a4b -a tags[/blue]
  [blue]zettl llm 22a4b -a connect -c 5[/blue]
  [blue]zettl llm 22a4b -a expand[/blue]
""",

            "api-key": f"""
[bold green]api-key[/bold green] - Manage API keys

[bold]Usage:[/bold]
  api-key                    List existing keys
  api-key generate           Generate new key
  api-key generate "Name"    Generate with custom name

[bold]Examples:[/bold]
  [blue]api-key generate "Development Key"[/blue]
  [blue]api-key[/blue]

[bold]Note:[/bold] Keys are only shown once. Configure with: zettl auth setup
""",

            "rules": f"""
[bold green]rules[/bold green] - Display random rule from notes

[bold]Options:[/bold]
  [yellow]-s, --source[/yellow]  Show source note ID

[bold]Examples:[/bold]
  [blue]zettl rules[/blue]
  [blue]zettl rules --source[/blue]
""",

            "help": f"""
[bold green]help[/bold green] - Show help information

[bold]Usage:[/bold]
  zettl help              General help
  zettl COMMAND --help    Command-specific help

[bold]Examples:[/bold]
  [blue]zettl help[/blue]
  [blue]zettl todo --help[/blue]
"""
        }
        
        help_text = help_templates.get(command, f"No detailed help available for '{command}'. Try 'help' for a list of all commands.")

        if cls._mode == 'web':
            return cls._convert_to_markdown(help_text)
        return help_text