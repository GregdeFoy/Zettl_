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
[bold green]zettl v0.6.1[/bold green] - A Zettelkasten-style note-taking tool

[bold]NOTE MANAGEMENT[/bold]
  [bold yellow]todo[/bold yellow] / [bold yellow]t[/bold yellow]            List todos OR create new todo (auto-tagged 'todo')
    [blue]→[/blue] zettl todo                  # List active todos
    [blue]→[/blue] zettl t "Call dentist" @health-project

  [bold yellow]idea[/bold yellow] / [bold yellow]i[/bold yellow]            List ideas OR create new idea (auto-tagged 'idea')
    [blue]→[/blue] zettl idea                  # List active ideas
    [blue]→[/blue] zettl i "Add caching layer" @dev-project

  [bold yellow]note[/bold yellow] / [bold yellow]n[/bold yellow]            List notes OR create new note (auto-tagged 'note')
    [blue]→[/blue] zettl note                  # List active notes
    [blue]→[/blue] zettl n "Meeting notes" @work-project

  [bold yellow]project[/bold yellow] / [bold yellow]p[/bold yellow]         List/view/create projects (auto-tagged 'project')
    [blue]→[/blue] zettl project               # List all projects with stats
    [blue]→[/blue] zettl p learn-rust          # View project detail
    [blue]→[/blue] zettl project "New Project" --id my-proj

  [bold yellow]show[/bold yellow]                Display note content and related notes
    [blue]→[/blue] zettl show 22a4b
    [blue]→[/blue] zettl show 22a4b -r         # Show with related notes

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

  [bold yellow]graph[/bold yellow]               Export graph visualization data
    [blue]→[/blue] zettl graph 22a4b --output graph.json --depth 2

[bold]ORGANIZATION[/bold]
  [bold yellow]tags[/bold yellow]                List all tags, show/add note tags
    [blue]→[/blue] zettl tags                  # List all tags
    [blue]→[/blue] zettl tags 22a4b            # Show note's tags
    [blue]→[/blue] zettl tags 22a4b "concept"  # Add tag to note

  [bold yellow]untag[/bold yellow]               Remove tag from note
    [blue]→[/blue] zettl untag 22a4b "concept"

[bold]AI FEATURES[/bold]
  [bold yellow]llm[/bold yellow]                 AI-powered note analysis
    [blue]→[/blue] zettl llm 22a4b --action summarize
    [blue]→[/blue] zettl llm 22a4b --action tags | connect | expand | concepts | questions | critique

[bold]SPECIALIZED FEATURES[/bold]
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
  2. Create a project:          [cyan]zettl project "My Project" --id my-project[/cyan]
  3. Add tasks to project:      [cyan]zettl todo "First task" @my-project[/cyan]
  4. Capture ideas:            [cyan]zettl idea "Great idea!" @my-project[/cyan]
  5. List your notes:          [cyan]zettl list[/cyan]
  6. View todos:               [cyan]zettl todo[/cyan]
  7. View project stats:       [cyan]zettl project[/cyan]
  8. Get AI suggestions:       [cyan]zettl llm NOTE_ID --action tags[/cyan]

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

            "todo": f"""
[bold green]todo [CONTENT][/bold green] - List todos OR create new todo (automatically tagged with 'todo')

[bold]DUAL MODE COMMAND:[/bold]
  • [bold]No content[/bold] = LIST MODE: Shows active todos (like old 'todos' command)
  • [bold]With content[/bold] = CREATE MODE: Creates a new todo

[bold]List Mode Options:[/bold]
  [yellow]-a, --all[/yellow]           Show all todos (active, done, and canceled)
  [yellow]-dt, --donetoday[/yellow]    Show todos completed today
  [yellow]-c, --cancel[/yellow]        Show canceled todos
  [yellow]-t, --tag TAG[/yellow]       Filter todos by additional tag (can specify multiple)
  [yellow]@PROJECT_ID[/yellow]         Filter todos by project (use @ notation)

[bold]Create Mode Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags to the todo
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note
  [yellow]--id CUSTOM_ID[/yellow]      Use a custom ID instead of auto-generated one
  [yellow]@PROJECT_ID[/yellow]         Link to a project (use @ notation in content)

[bold]Examples:[/bold]
  [cyan]# List Mode[/cyan]
  [blue]zettl todo[/blue]                   List active todos
  [blue]zettl todo -a[/blue]                Show all todos
  [blue]zettl todo @my-project[/blue]       List todos for a project
  [blue]zettl todo -t urgent[/blue]         List urgent todos
  [blue]zettl todo -dt[/blue]               Show todos completed today

  [cyan]# Create Mode[/cyan]
  [blue]zettl todo "Review pull request"[/blue]
  [blue]zettl todo "Call dentist" @health-project[/blue]
  [blue]zettl todo "Fix bug #123" @dev --id bug-123[/blue]
  [blue]zettl todo "Write tests" -t urgent[/blue]
""",

            "t": f"""
[bold green]t [CONTENT][/bold green] - Shortcut for 'todo' command

See 'zettl todo --help' for full documentation.
""",

            "idea": f"""
[bold green]idea [CONTENT][/bold green] - List ideas OR create new idea (automatically tagged with 'idea')

[bold]DUAL MODE COMMAND:[/bold]
  • [bold]No content[/bold] = LIST MODE: Shows active ideas
  • [bold]With content[/bold] = CREATE MODE: Creates a new idea

[bold]List Mode Options:[/bold]
  [yellow]-a, --all[/yellow]           Show all ideas (active, done, and canceled)
  [yellow]-c, --cancel[/yellow]        Show canceled ideas
  [yellow]-t, --tag TAG[/yellow]       Filter ideas by additional tag (can specify multiple)
  [yellow]@PROJECT_ID[/yellow]         Filter ideas by project (use @ notation)

[bold]Create Mode Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags to the idea
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note
  [yellow]--id CUSTOM_ID[/yellow]      Use a custom ID instead of auto-generated one
  [yellow]@PROJECT_ID[/yellow]         Link to a project (use @ notation in content)

[bold]Examples:[/bold]
  [cyan]# List Mode[/cyan]
  [blue]zettl idea[/blue]                   List active ideas
  [blue]zettl idea -a[/blue]                Show all ideas
  [blue]zettl idea @my-project[/blue]       List ideas for a project
  [blue]zettl idea -t backend[/blue]        List backend ideas

  [cyan]# Create Mode[/cyan]
  [blue]zettl idea "Add caching layer for better performance"[/blue]
  [blue]zettl idea "Redesign UI" @frontend-project[/blue]
  [blue]zettl idea "Try new algorithm" @research --id algo-001[/blue]
""",

            "i": f"""
[bold green]i [CONTENT][/bold green] - Shortcut for 'idea' command

See 'zettl idea --help' for full documentation.
""",

            "note": f"""
[bold green]note [CONTENT][/bold green] - List notes OR create new note (automatically tagged with 'note')

[bold]DUAL MODE COMMAND:[/bold]
  • [bold]No content[/bold] = LIST MODE: Shows active notes
  • [bold]With content[/bold] = CREATE MODE: Creates a new note

[bold]List Mode Options:[/bold]
  [yellow]-a, --all[/yellow]           Show all notes (active, done, and canceled)
  [yellow]-c, --cancel[/yellow]        Show canceled notes
  [yellow]-t, --tag TAG[/yellow]       Filter notes by additional tag (can specify multiple)
  [yellow]@PROJECT_ID[/yellow]         Filter notes by project (use @ notation)

[bold]Create Mode Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags to the note
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note
  [yellow]--id CUSTOM_ID[/yellow]      Use a custom ID instead of auto-generated one
  [yellow]@PROJECT_ID[/yellow]         Link to a project (use @ notation in content)

[bold]Examples:[/bold]
  [cyan]# List Mode[/cyan]
  [blue]zettl note[/blue]                   List active notes
  [blue]zettl note -a[/blue]                Show all notes
  [blue]zettl note @my-project[/blue]       List notes for a project
  [blue]zettl note -t meeting[/blue]        List meeting notes

  [cyan]# Create Mode[/cyan]
  [blue]zettl note "Meeting notes from standup"[/blue]
  [blue]zettl note "Architecture decisions" @dev-project[/blue]
  [blue]zettl note "Research findings" @research --id research-001[/blue]
""",

            "n": f"""
[bold green]n [CONTENT][/bold green] - Shortcut for 'note' command

See 'zettl note --help' for full documentation.
""",

            "project": f"""
[bold green]project [CONTENT][/bold green] - List/view/create projects (automatically tagged with 'project')

[bold]THREE MODE COMMAND:[/bold]
  • [bold]No content[/bold] = LIST MODE: Shows all projects with statistics
  • [bold]@project_id[/bold] = DETAIL MODE: Shows project with categorized linked notes
  • [bold]Content (no @)[/bold] = CREATE MODE: Creates a new project

[bold]List Mode:[/bold]
  [blue]zettl project[/blue]                Shows all projects with active todo/idea/note counts

[bold]Detail Mode (requires @):[/bold]
  [blue]zettl project @project_id[/blue]   View project detail with categorized notes

  [bold]Options:[/bold]
  [yellow]-a, --all[/yellow]           Show all linked notes (active, done, and canceled)
  [yellow]-f, --full[/yellow]          Show full content instead of previews
  [yellow]-t, --tag TAG[/yellow]       Filter linked notes by additional tag

[bold]Create Mode Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]       Add additional tags to the project
  [yellow]-l, --link NOTE_ID[/yellow]  Create a link to another note
  [yellow]--id CUSTOM_ID[/yellow]      Use a custom, memorable ID (recommended for projects)

[bold]Examples:[/bold]
  [cyan]# List Mode[/cyan]
  [blue]zettl project[/blue]                List all projects with stats

  [cyan]# Detail Mode (note the @ prefix)[/cyan]
  [blue]zettl project @learn-rust[/blue]    View project detail with categorized notes
  [blue]zettl project @learn-rust -f[/blue] View with full note content
  [blue]zettl project @learn-rust -t backend[/blue]  Filter to backend-tagged notes

  [cyan]# Create Mode[/cyan]
  [blue]zettl project "Learn Rust" --id learn-rust[/blue]
  [blue]zettl project "Q1 Planning" --id q1-2024[/blue]
  [blue]zettl project "Website Redesign" --id web-redesign -t urgent[/blue]
  [blue]zettl project np[/blue]             Creates project "np" with random ID

[bold]Note:[/bold] Projects serve as organizational containers. Use custom IDs to make
them easy to reference when creating tasks, ideas, and notes with @project-id.
The @ prefix is required for viewing project details, maintaining consistency
with the todo/idea/note filtering behavior.
""",

            "p": f"""
[bold green]p [CONTENT][/bold green] - Shortcut for 'project' command (detail/create only)

[bold]Note:[/bold] The 'p' shortcut works for detail view and create mode, but not list mode.
For listing all projects, use the full command: [cyan]zettl project[/cyan]

See 'zettl project --help' for full documentation.
""",

            "list": f"""
[bold green]list[/bold green] - List recent notes

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
[bold green]show NOTE_ID[/bold green] - Display note content and optionally related notes

[bold]Options:[/bold]
  [yellow]-r, --related[/yellow]       Also show all notes linked to this note (bidirectional)
  [yellow]-f, --full[/yellow]          Show full content of related notes (requires -r)

[bold]Examples:[/bold]
  [blue]zettl show 22a4b[/blue]          Show content of note with ID 22a4b
  [blue]zettl show 22a4b -r[/blue]       Show note and all related notes
  [blue]zettl show 22a4b -r -f[/blue]    Show note and related notes with full content

[bold]Note:[/bold] The -r flag shows bidirectional links (both incoming and outgoing).
This replaces the old 'related' command.
""",

            "search": f"""
[bold green]search [QUERY][/bold green] - Search for notes containing text, with tags, or by date

[bold]Options:[/bold]
  [yellow]-t, --tag TAG[/yellow]        Include notes with this tag (can specify multiple, must have ALL)
  [yellow]+t, --exclude-tag TAG[/yellow] Exclude notes with this tag (can specify multiple, excludes ANY)
  [yellow]-d, --date DATE[/yellow]      Search for notes created on a specific date (YYYY-MM-DD)
  [yellow]-f, --full[/yellow]           Show full content of matching notes

[bold]Tag Logic:[/bold]
  • Multiple [cyan]-t[/cyan] tags: Note must have ALL specified tags (AND logic)
  • Multiple [cyan]+t[/cyan] tags: Note must not have ANY specified tags (OR logic)
  • Combining both: Must match includes AND not match excludes

[bold]Examples:[/bold]
  [blue]zettl search "keyword"[/blue]                 Search notes containing "keyword"
  [blue]zettl search -t work -t urgent[/blue]         Notes with BOTH "work" AND "urgent" tags
  [blue]zettl search -t project +t done[/blue]        "project" tags but NOT "done"
  [blue]zettl search +t todo +t done[/blue]           Exclude notes with "todo" OR "done" tags
  [blue]zettl search -t work -t urgent +t done[/blue] "work" AND "urgent" but NOT "done"
  [blue]zettl search -d 2025-04-07 -t work[/blue]     Created on date AND has "work" tag
""",

            "link": f"""
[bold green]link SOURCE_ID TARGET_ID[/bold green] - Create link between notes

[bold]Usage:[/bold]
  zettl link SOURCE_ID TARGET_ID

[bold]Options:[/bold]
  [yellow]-c, --context TEXT[/yellow]   Add context to the link

[bold]Examples:[/bold]
  [blue]zettl link 22a4b 18c3d[/blue]
  [blue]zettl link 22a4b 18c3d --context "These concepts are related"[/blue]
""",

            "related": f"""
[bold green]related NOTE_ID[/bold green] - Show notes connected to this note

[bold yellow]DEPRECATED:[/bold yellow] This functionality has been merged into the 'show' command.
Use [cyan]show -r[/cyan] instead.

[bold]New Usage:[/bold]
  [cyan]zettl show NOTE_ID -r[/cyan]         Show note and all related notes
  [cyan]zettl show NOTE_ID -r -f[/cyan]      Show with full content of related notes

[bold]Examples:[/bold]
  [blue]zettl show 22a4b -r[/blue]          (replaces: zettl related 22a4b)
  [blue]zettl show 22a4b -r -f[/blue]       (replaces: zettl related 22a4b --full)

See 'zettl show --help' for more information.
""",

            "graph": f"""
[bold green]graph [NOTE_ID][/bold green] - Generate a graph visualization of notes

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
[bold green]tags [NOTE_ID] ["TAGS"][/bold green] - Show or add tags to a note

[bold]Usage:[/bold]
  zettl tags                          List all tags
  zettl tags NOTE_ID                  Show tags for a specific note
  zettl tags NOTE_ID "TAG"            Add a single tag to a note
  zettl tags NOTE_ID "TAG1 TAG2..."  Add multiple tags to a note (space-separated in quotes)

[bold]Examples:[/bold]
  [blue]zettl tags[/blue]                         List all tags with counts
  [blue]zettl tags 22a4b[/blue]                   Show tags for note 22a4b
  [blue]zettl tags 22a4b concept[/blue]           Add "concept" tag to note 22a4b
  [blue]zettl tags 22a4b "todo urgent"[/blue]     Add "todo" and "urgent" tags to note 22a4b
  [blue]zettl tags xyz12 "tag1 tag2 tag3"[/blue] Add multiple tags at once
""",

"todos": f"""
[bold green]todos[/bold green] - List all notes tagged with 'todo'

[bold yellow]DEPRECATED:[/bold yellow] This command has been unified with the 'todo' command.
Use [cyan]todo[/cyan] (with no content) instead.

[bold]New Usage:[/bold]
  [cyan]zettl todo[/cyan]                    List active todos
  [cyan]zettl todo -a[/cyan]                 Show all todos (active, done, canceled)
  [cyan]zettl todo -dt[/cyan]                Show todos completed today
  [cyan]zettl todo -t work[/cyan]            Filter todos by tag
  [cyan]zettl todo @project[/cyan]           Filter todos by project

[bold]Examples:[/bold]
  [blue]zettl todo[/blue]                   (replaces: zettl todos)
  [blue]zettl todo -a[/blue]                (replaces: zettl todos -a)
  [blue]zettl todo -dt[/blue]               (replaces: zettl todos -dt)
  [blue]zettl todo -t work[/blue]           (replaces: zettl todos -t work)

[bold]Note:[/bold] The 'todo' command now has dual modes:
  • No content = List todos (old 'todos' command)
  • With content = Create todo (old 'task' command)

See 'zettl todo --help' for full documentation.
""",

            "delete": f"""
[bold green]delete NOTE_ID[/bold green] - Delete a note and its associated data

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
[bold green]untag NOTE_ID TAG[/bold green] - Remove a tag from a note

[bold]Usage:[/bold]
  zettl untag NOTE_ID TAG

[bold]Examples:[/bold]
  [blue]zettl untag 22a4b "concept"[/blue]  Remove "concept" tag from note 22a4b
""",

            "unlink": f"""
[bold green]unlink SOURCE_ID TARGET_ID[/bold green] - Remove a link between two notes

[bold]Usage:[/bold]
  zettl unlink SOURCE_ID TARGET_ID

[bold]Examples:[/bold]
  [blue]zettl unlink 22a4b 18c3d[/blue]  Remove link from note 22a4b to 18c3d
""",

            "append": f"""
[bold green]append NOTE_ID TEXT[/bold green] - Append text to the end of a note

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
[bold green]prepend NOTE_ID TEXT[/bold green] - Prepend text to the beginning of a note

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
[bold green]edit NOTE_ID[/bold green] - Edit a note in your default text editor

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
[bold green]merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...][/bold green] - Merge multiple notes into a single note

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
[bold green]llm NOTE_ID[/bold green] - Use Claude AI to analyze and enhance notes

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
[bold green]api-key[/bold green] - Manage API keys for CLI access

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
[bold green]rules[/bold green] - Display a random rule from notes tagged with 'rules'

[bold]Usage:[/bold]
  zettl rules

[bold]Options:[/bold]
  [yellow]-s, --source[/yellow]  Show the source note ID

[bold]Examples:[/bold]
  [blue]zettl rules[/blue]
  [blue]zettl rules --source[/blue]  # Show the source note ID
""",

            "help": f"""
[bold green]help[/bold green] - Show help information

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