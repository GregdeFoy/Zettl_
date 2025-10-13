# help.py
from zettl.formatting import Colors

class CommandHelp:
    """Centralized help system for Zettl commands."""

    @staticmethod
    def get_main_help():
        """Return the main help text."""
        return f"""
{Colors.GREEN}{Colors.BOLD}zettl v0.1.0{Colors.RESET} - A Zettelkasten-style note-taking tool

{Colors.BOLD}NOTE MANAGEMENT{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}new{Colors.RESET} / {Colors.YELLOW}{Colors.BOLD}add{Colors.RESET}          Create a new note
    {Colors.BLUE}→{Colors.RESET} zettl new "Your note content" --tag concept --link 22a4b

  {Colors.YELLOW}{Colors.BOLD}show{Colors.RESET}                Display full note content
    {Colors.BLUE}→{Colors.RESET} zettl show 22a4b

  {Colors.YELLOW}{Colors.BOLD}list{Colors.RESET}                List recent notes
    {Colors.BLUE}→{Colors.RESET} zettl list --limit 10 --full

  {Colors.YELLOW}{Colors.BOLD}search{Colors.RESET}              Search by text, tag, or date
    {Colors.BLUE}→{Colors.RESET} zettl search "concept" -t work +t done --full

  {Colors.YELLOW}{Colors.BOLD}edit{Colors.RESET}                Edit note in default text editor
    {Colors.BLUE}→{Colors.RESET} zettl edit 22a4b

  {Colors.YELLOW}{Colors.BOLD}append{Colors.RESET}              Add text to end of note
    {Colors.BLUE}→{Colors.RESET} zettl append 22a4b "Additional content"

  {Colors.YELLOW}{Colors.BOLD}prepend{Colors.RESET}             Add text to beginning of note
    {Colors.BLUE}→{Colors.RESET} zettl prepend 22a4b "IMPORTANT: "

  {Colors.YELLOW}{Colors.BOLD}merge{Colors.RESET}               Combine multiple notes into one
    {Colors.BLUE}→{Colors.RESET} zettl merge 22a4b 18c3d --force

  {Colors.YELLOW}{Colors.BOLD}delete{Colors.RESET}              Delete note and associated data
    {Colors.BLUE}→{Colors.RESET} zettl delete 22a4b --keep-tags

{Colors.BOLD}CONNECTIONS{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}link{Colors.RESET}                Create link between notes
    {Colors.BLUE}→{Colors.RESET} zettl link 22a4b 18c3d --context "Related concepts"

  {Colors.YELLOW}{Colors.BOLD}unlink{Colors.RESET}              Remove link between notes
    {Colors.BLUE}→{Colors.RESET} zettl unlink 22a4b 18c3d

  {Colors.YELLOW}{Colors.BOLD}related{Colors.RESET}             Show connected notes
    {Colors.BLUE}→{Colors.RESET} zettl related 22a4b --full

  {Colors.YELLOW}{Colors.BOLD}graph{Colors.RESET}               Export graph visualization data
    {Colors.BLUE}→{Colors.RESET} zettl graph 22a4b --output graph.json --depth 2

{Colors.BOLD}ORGANIZATION{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}tags{Colors.RESET}                List all tags, show/add note tags
    {Colors.BLUE}→{Colors.RESET} zettl tags                  # List all tags
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b            # Show note's tags
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b "concept"  # Add tag to note

  {Colors.YELLOW}{Colors.BOLD}untag{Colors.RESET}               Remove tag from note
    {Colors.BLUE}→{Colors.RESET} zettl untag 22a4b "concept"

  {Colors.YELLOW}{Colors.BOLD}todos{Colors.RESET}               Manage tasks (notes tagged 'todo')
    {Colors.BLUE}→{Colors.RESET} zettl todos --all --tag work --eisenhower

{Colors.BOLD}AI FEATURES{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}llm{Colors.RESET}                 AI-powered note analysis
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action summarize
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action tags | connect | expand | concepts | questions | critique

{Colors.BOLD}SPECIALIZED FEATURES{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}nutrition{Colors.RESET} / {Colors.YELLOW}{Colors.BOLD}nut{Colors.RESET}   Track calories and protein
    {Colors.BLUE}→{Colors.RESET} zettl nut "Breakfast cal: 500 prot: 25"
    {Colors.BLUE}→{Colors.RESET} zettl nutrition --today --history --days 14

  {Colors.YELLOW}{Colors.BOLD}rules{Colors.RESET}               Display random rule from notes
    {Colors.BLUE}→{Colors.RESET} zettl rules --source

{Colors.BOLD}SYSTEM{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}auth setup{Colors.RESET}          Configure API key authentication
    {Colors.BLUE}→{Colors.RESET} zettl auth setup

  {Colors.YELLOW}{Colors.BOLD}auth status{Colors.RESET}         Check authentication status
    {Colors.BLUE}→{Colors.RESET} zettl auth status

  {Colors.YELLOW}{Colors.BOLD}help{Colors.RESET}                Show this help or command help
    {Colors.BLUE}→{Colors.RESET} zettl help
    {Colors.BLUE}→{Colors.RESET} zettl COMMAND --help

{Colors.BOLD}GETTING STARTED{Colors.RESET}
  1. Set up authentication:     {Colors.CYAN}zettl auth setup{Colors.RESET}
  2. Create your first note:    {Colors.CYAN}zettl new "My first note" --tag idea{Colors.RESET}
  3. List your notes:           {Colors.CYAN}zettl list{Colors.RESET}
  4. Create connections:        {Colors.CYAN}zettl link NOTE_ID1 NOTE_ID2{Colors.RESET}
  5. Get AI suggestions:        {Colors.CYAN}zettl llm NOTE_ID --action tags{Colors.RESET}

For detailed help on any command: {Colors.CYAN}zettl COMMAND --help{Colors.RESET}
"""

    @staticmethod
    def get_command_help(command):
        """Return detailed help for a specific command."""
        help_templates = {
            "auth": f"""
{Colors.GREEN}{Colors.BOLD}auth{Colors.RESET} - Authentication management

{Colors.BOLD}Subcommands:{Colors.RESET}
  {Colors.YELLOW}setup{Colors.RESET}   Configure API key authentication for CLI access
  {Colors.YELLOW}status{Colors.RESET}  Check current authentication status

{Colors.BOLD}Usage:{Colors.RESET}
  zettl auth setup    # Set up authentication
  zettl auth status   # Check authentication status

{Colors.BOLD}Description:{Colors.RESET}
  The auth command manages your API key authentication. You need to set up
  authentication before using most zettl commands. Get your API key from
  the Zettl web interface.
""",

            "new": f"""
{Colors.GREEN}{Colors.BOLD}new [CONTENT]{Colors.RESET} - Create a new note with the given content

{Colors.BOLD}Usage:{Colors.RESET}
  zettl new "Your note content here"

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}       Add one or more tags to the note (can be used multiple times)
  {Colors.YELLOW}-l, --link NOTE_ID{Colors.RESET}  Create a link to another note

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl new "This is a new note"{Colors.RESET}
  {Colors.BLUE}zettl new "Note with tag" -t important{Colors.RESET}
  {Colors.BLUE}zettl new "Note with multiple tags" -t concept -t research{Colors.RESET}
  {Colors.BLUE}zettl new "Linked note" --link 22a4b{Colors.RESET}
""",

            "add": f"""
{Colors.GREEN}{Colors.BOLD}add [CONTENT]{Colors.RESET} - Create a new note with the given content (alias for 'new')

{Colors.BOLD}Usage:{Colors.RESET}
  zettl add "Your note content here"

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}       Add one or more tags to the note (can be used multiple times)
  {Colors.YELLOW}-l, --link NOTE_ID{Colors.RESET}  Create a link to another note

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl add "This is a new note"{Colors.RESET}
  {Colors.BLUE}zettl add "Note with tag" -t important{Colors.RESET}
  {Colors.BLUE}zettl add "Note with multiple tags" -t concept -t research{Colors.RESET}
  {Colors.BLUE}zettl add "Linked note" --link 22a4b{Colors.RESET}
""",

            "list": f"""
{Colors.GREEN}{Colors.BOLD}list{Colors.RESET} - List recent notes

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-l, --limit NUMBER{Colors.RESET}  Number of notes to display (default: 10)
  {Colors.YELLOW}-f, --full{Colors.RESET}          Show full content of notes
  {Colors.YELLOW}-c, --compact{Colors.RESET}       Show very compact list (IDs only)

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl list{Colors.RESET}                  Show 10 most recent notes
  {Colors.BLUE}zettl list --limit 5{Colors.RESET}        Show 5 most recent notes
  {Colors.BLUE}zettl list --full{Colors.RESET}           Show full content of recent notes
  {Colors.BLUE}zettl list -c{Colors.RESET}               Show compact list of note IDs
""",

            "show": f"""
{Colors.GREEN}{Colors.BOLD}show NOTE_ID{Colors.RESET} - Display note content

{Colors.BOLD}Usage:{Colors.RESET}
  zettl show NOTE_ID

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl show 22a4b{Colors.RESET}       Show content of note with ID 22a4b
""",

            "search": f"""
{Colors.GREEN}{Colors.BOLD}search [QUERY]{Colors.RESET} - Search for notes containing text, with tag, or by date

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}        Search for notes with this tag
  {Colors.YELLOW}+t, --exclude-tag TAG{Colors.RESET} Exclude notes with this tag
  {Colors.YELLOW}-d, --date DATE{Colors.RESET}      Search for notes created on a specific date (YYYY-MM-DD)
  {Colors.YELLOW}-f, --full{Colors.RESET}           Show full content of matching notes

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl search "keyword"{Colors.RESET}       Search notes containing "keyword"
  {Colors.BLUE}zettl search -t concept{Colors.RESET}      Show notes tagged with "concept"
  {Colors.BLUE}zettl search -d 2025-04-07{Colors.RESET}   Show notes created on April 7, 2025
  {Colors.BLUE}zettl search -t work +t done{Colors.RESET} Show notes tagged "work" but not "done"
  {Colors.BLUE}zettl search "keyword" --full{Colors.RESET} Show full content of matching notes
""",

            "link": f"""
{Colors.GREEN}{Colors.BOLD}link SOURCE_ID TARGET_ID{Colors.RESET} - Create link between notes

{Colors.BOLD}Usage:{Colors.RESET}
  zettl link SOURCE_ID TARGET_ID

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-c, --context TEXT{Colors.RESET}   Add context to the link

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl link 22a4b 18c3d{Colors.RESET}
  {Colors.BLUE}zettl link 22a4b 18c3d --context "These concepts are related"{Colors.RESET}
""",

            "related": f"""
{Colors.GREEN}{Colors.BOLD}related NOTE_ID{Colors.RESET} - Show notes connected to this note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl related NOTE_ID

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-f, --full{Colors.RESET}          Show full content of related notes

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl related 22a4b{Colors.RESET}
  {Colors.BLUE}zettl related 22a4b --full{Colors.RESET}
""",

            "graph": f"""
{Colors.GREEN}{Colors.BOLD}graph [NOTE_ID]{Colors.RESET} - Generate a graph visualization of notes

{Colors.BOLD}Usage:{Colors.RESET}
  zettl graph [NOTE_ID]

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-o, --output FILENAME{Colors.RESET}  Output file for graph data (default: zettl_graph.json)
  {Colors.YELLOW}-d, --depth NUMBER{Colors.RESET}     Depth of connections to include (default: 2)

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl graph{Colors.RESET}                         Graph all notes
  {Colors.BLUE}zettl graph 22a4b{Colors.RESET}                  Graph centered on note 22a4b
  {Colors.BLUE}zettl graph 22a4b --output my_graph.json{Colors.RESET}
  {Colors.BLUE}zettl graph 22a4b --depth 3{Colors.RESET}        Include notes up to 3 links away
""",

            "tags": f"""
{Colors.GREEN}{Colors.BOLD}tags [NOTE_ID] [TAG]{Colors.RESET} - Show or add tags to a note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl tags                  List all tags
  zettl tags NOTE_ID          Show tags for a specific note
  zettl tags NOTE_ID TAG      Add a tag to a note

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl tags{Colors.RESET}                 List all tags with counts
  {Colors.BLUE}zettl tags 22a4b{Colors.RESET}           Show tags for note 22a4b
  {Colors.BLUE}zettl tags 22a4b "concept"{Colors.RESET} Add "concept" tag to note 22a4b
""",

"todos": f"""
{Colors.GREEN}{Colors.BOLD}todos{Colors.RESET} - List all notes tagged with 'todo'

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-a, --all{Colors.RESET}            Show all todos (active and completed)
  {Colors.YELLOW}-dt, --donetoday{Colors.RESET}     Show todos completed today
  {Colors.YELLOW}-c, --cancel{Colors.RESET}         Show canceled todos
  {Colors.YELLOW}-t, --tag TAG{Colors.RESET}        Filter todos by additional tag
  {Colors.YELLOW}-e, --eisenhower{Colors.RESET}     Display todos in Eisenhower matrix format

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl todos{Colors.RESET}                  Show active todos
  {Colors.BLUE}zettl todos -a{Colors.RESET}               Show all todos (active and completed)
  {Colors.BLUE}zettl todos -dt{Colors.RESET}              Show todos completed today
  {Colors.BLUE}zettl todos -e{Colors.RESET}               Show todos in Eisenhower matrix
  {Colors.BLUE}zettl todos -t work{Colors.RESET}          Show todos tagged with "work"
  {Colors.BLUE}zettl todos -t work -t urgent{Colors.RESET} Show todos with multiple tags
""",

            "delete": f"""
{Colors.GREEN}{Colors.BOLD}delete NOTE_ID{Colors.RESET} - Delete a note and its associated data

{Colors.BOLD}Usage:{Colors.RESET}
  zettl delete NOTE_ID

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-f, --force{Colors.RESET}         Skip confirmation prompt
  {Colors.YELLOW}--keep-links{Colors.RESET}        Keep links to and from this note
  {Colors.YELLOW}--keep-tags{Colors.RESET}         Keep tags associated with this note

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl delete 22a4b{Colors.RESET}
  {Colors.BLUE}zettl delete 22a4b --force{Colors.RESET}     Delete without confirmation
  {Colors.BLUE}zettl delete 22a4b --keep-tags{Colors.RESET} Delete note but keep its tags
""",

            "untag": f"""
{Colors.GREEN}{Colors.BOLD}untag NOTE_ID TAG{Colors.RESET} - Remove a tag from a note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl untag NOTE_ID TAG

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl untag 22a4b "concept"{Colors.RESET}  Remove "concept" tag from note 22a4b
""",

            "unlink": f"""
{Colors.GREEN}{Colors.BOLD}unlink SOURCE_ID TARGET_ID{Colors.RESET} - Remove a link between two notes

{Colors.BOLD}Usage:{Colors.RESET}
  zettl unlink SOURCE_ID TARGET_ID

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl unlink 22a4b 18c3d{Colors.RESET}  Remove link from note 22a4b to 18c3d
""",

            "append": f"""
{Colors.GREEN}{Colors.BOLD}append NOTE_ID TEXT{Colors.RESET} - Append text to the end of a note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl append NOTE_ID "Text to append"

{Colors.BOLD}Description:{Colors.RESET}
  Adds the provided text to the end of an existing note.
  A newline is automatically added between the existing content and new text.

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl append 22a4b "Additional thoughts on this topic"{Colors.RESET}
  {Colors.BLUE}zettl append 22a4b "Follow-up: new research findings"{Colors.RESET}

{Colors.BOLD}Use cases:{Colors.RESET}
  • Adding new information to existing notes
  • Appending updates or follow-ups
  • Building notes incrementally over time
""",

            "prepend": f"""
{Colors.GREEN}{Colors.BOLD}prepend NOTE_ID TEXT{Colors.RESET} - Prepend text to the beginning of a note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl prepend NOTE_ID "Text to prepend"

{Colors.BOLD}Description:{Colors.RESET}
  Adds the provided text to the beginning of an existing note.
  A newline is automatically added between the new text and existing content.

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl prepend 22a4b "UPDATE: "{Colors.RESET}
  {Colors.BLUE}zettl prepend 22a4b "IMPORTANT: This has been revised"{Colors.RESET}

{Colors.BOLD}Use cases:{Colors.RESET}
  • Adding status updates at the top of notes
  • Inserting important context before original content
  • Marking notes with time-sensitive information
""",

            "edit": f"""
{Colors.GREEN}{Colors.BOLD}edit NOTE_ID{Colors.RESET} - Edit a note in your default text editor

{Colors.BOLD}Usage:{Colors.RESET}
  zettl edit NOTE_ID

{Colors.BOLD}Description:{Colors.RESET}
  Opens the note in your system's default text editor for full editing.

  {Colors.BOLD}Platform-specific behavior:{Colors.RESET}
  • {Colors.CYAN}Linux/Mac:{Colors.RESET} Uses $EDITOR or $VISUAL environment variable (defaults to nano)
  • {Colors.CYAN}Windows:{Colors.RESET} Uses notepad or $EDITOR environment variable

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl edit 22a4b{Colors.RESET}                  # Edit note 22a4b
  {Colors.BLUE}export EDITOR=vim && zettl edit 22a4b{Colors.RESET}  # Use vim (Linux/Mac)
  {Colors.BLUE}set EDITOR=code && zettl edit 22a4b{Colors.RESET}    # Use VS Code (Windows)

{Colors.BOLD}Tips:{Colors.RESET}
  • Set your preferred editor: export EDITOR=vim (or nano, emacs, etc.)
  • Changes are saved when you exit the editor
  • If no changes are made, the note remains unchanged
""",

            "merge": f"""
{Colors.GREEN}{Colors.BOLD}merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...]{Colors.RESET} - Merge multiple notes into a single note

{Colors.BOLD}Usage:{Colors.RESET}
  zettl merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...]

{Colors.BOLD}What it does:{Colors.RESET}
  • Combines content from all notes (ordered by creation date)
  • Collects all unique tags from all notes
  • Preserves external links (updates them to point to new note)
  • Deletes the old notes after successful merge

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-f, --force{Colors.RESET}  Skip confirmation prompt

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl merge 22a4b 18c3d{Colors.RESET}            Merge two notes
  {Colors.BLUE}zettl merge 22a4b 18c3d 45f6g{Colors.RESET}       Merge three notes
  {Colors.BLUE}zettl merge 22a4b 18c3d --force{Colors.RESET}     Merge without confirmation

{Colors.BOLD}Note:{Colors.RESET}
  This is useful for consolidating related notes or combining duplicates.
  All tags and external links are preserved in the new merged note.
""",

            "llm": f"""
{Colors.GREEN}{Colors.BOLD}llm NOTE_ID{Colors.RESET} - Use Claude AI to analyze and enhance notes

{Colors.BOLD}Actions:{Colors.RESET}
  {Colors.YELLOW}summarize{Colors.RESET}   Generate a concise summary of the note
  {Colors.YELLOW}connect{Colors.RESET}     Find potential connections to other notes
  {Colors.YELLOW}tags{Colors.RESET}        Suggest relevant tags for the note
  {Colors.YELLOW}expand{Colors.RESET}      Create an expanded version of the note
  {Colors.YELLOW}concepts{Colors.RESET}    Extract key concepts from the note
  {Colors.YELLOW}questions{Colors.RESET}   Generate thought-provoking questions
  {Colors.YELLOW}critique{Colors.RESET}    Provide constructive feedback on the note

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-a, --action ACTION{Colors.RESET}  LLM action to perform (see above)
  {Colors.YELLOW}-c, --count NUMBER{Colors.RESET}   Number of results to return (default: 3)
  {Colors.YELLOW}-s, --show-source{Colors.RESET}    Show the source note before analysis
  {Colors.YELLOW}-d, --debug{Colors.RESET}          Show debug information for troubleshooting

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl llm 22a4b{Colors.RESET}                 Summarize note 22a4b (default action)
  {Colors.BLUE}zettl llm 22a4b -a tags{Colors.RESET}         Suggest tags for note 22a4b
  {Colors.BLUE}zettl llm 22a4b -a connect -c 5{Colors.RESET} Find 5 related notes to note 22a4b
  {Colors.BLUE}zettl llm 22a4b -a expand{Colors.RESET}       Create an expanded version of the note
  {Colors.BLUE}zettl llm 22a4b -a concepts{Colors.RESET}     Extract key concepts from the note
  {Colors.BLUE}zettl llm 22a4b -a questions{Colors.RESET}    Generate questions based on the note
  {Colors.BLUE}zettl llm 22a4b -a critique{Colors.RESET}     Get constructive feedback on the note
""",

            "api-key": f"""
{Colors.GREEN}{Colors.BOLD}api-key{Colors.RESET} - Manage API keys for CLI access

{Colors.BOLD}Usage:{Colors.RESET}
  api-key                    # List your existing API keys
  api-key generate           # Generate new API key with default name
  api-key generate "My Key"  # Generate new API key with custom name

{Colors.BOLD}Description:{Colors.RESET}
  API keys allow you to authenticate with the Zettl CLI from the command line.
  Each key can have a custom name to help you identify its purpose.

{Colors.BOLD}Examples:{Colors.RESET}
  api-key generate "Development Key"  # Create key for development
  api-key                           # View all your keys

{Colors.BOLD}Notes:{Colors.RESET}
  - API keys are only shown once when generated
  - Copy and save them immediately
  - Configure with CLI: zettl auth setup
""",

            "rules": f"""
{Colors.GREEN}{Colors.BOLD}rules{Colors.RESET} - Display a random rule from notes tagged with 'rules'

{Colors.BOLD}Usage:{Colors.RESET}
  zettl rules

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-s, --source{Colors.RESET}  Show the source note ID

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl rules{Colors.RESET}
  {Colors.BLUE}zettl rules --source{Colors.RESET}  # Show the source note ID
""",

            "nutrition": f"""
{Colors.GREEN}{Colors.BOLD}nutrition{Colors.RESET} - Track and analyze nutrition data (calories and protein)

{Colors.BOLD}Usage:{Colors.RESET}
  zettl nutrition "Food description cal: XXX prot: YYY"  # Add new entry
  zettl nutrition --today                                # Show today's summary
  zettl nutrition --history                              # Show nutrition history

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --today{Colors.RESET}       Show today's nutrition summary
  {Colors.YELLOW}-i, --history{Colors.RESET}     Show nutrition history
  {Colors.YELLOW}-d, --days NUMBER{Colors.RESET} Number of days to show in history (default: 7)
  {Colors.YELLOW}-p, --past DATE{Colors.RESET}   Add an entry for a past date (YYYY-MM-DD format)

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl nutrition "Breakfast cal: 500 prot: 25"{Colors.RESET}
  {Colors.BLUE}zettl nutrition "Dinner cal: 800 prot: 40" --past 2025-04-05{Colors.RESET}
  {Colors.BLUE}zettl nutrition --today{Colors.RESET}
  {Colors.BLUE}zettl nutrition --history --days 14{Colors.RESET}
  
{Colors.BOLD}Shorthand:{Colors.RESET}
  You can use the alias 'nut' instead of 'nutrition'
  {Colors.BLUE}zettl nut "Lunch cal: 700 prot: 35"{Colors.RESET}
""",

            "nut": f"""
{Colors.GREEN}{Colors.BOLD}nut{Colors.RESET} - Track and analyze nutrition data (alias for 'nutrition')

{Colors.BOLD}Usage:{Colors.RESET}
  zettl nut "Food description cal: XXX prot: YYY"  # Add new entry
  zettl nut --today                                # Show today's summary
  zettl nut --history                              # Show nutrition history

{Colors.BOLD}Options:{Colors.RESET}
  {Colors.YELLOW}-t, --today{Colors.RESET}       Show today's nutrition summary
  {Colors.YELLOW}-i, --history{Colors.RESET}     Show nutrition history
  {Colors.YELLOW}-d, --days NUMBER{Colors.RESET} Number of days to show in history (default: 7)
  {Colors.YELLOW}-p, --past DATE{Colors.RESET}   Add an entry for a past date (YYYY-MM-DD format)

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl nut "Breakfast cal: 500 prot: 25"{Colors.RESET}
  {Colors.BLUE}zettl nut "Dinner cal: 800 prot: 40" --past 2025-04-05{Colors.RESET}
  {Colors.BLUE}zettl nut --today{Colors.RESET}
  {Colors.BLUE}zettl nut --history --days 14{Colors.RESET}
""",

            "help": f"""
{Colors.GREEN}{Colors.BOLD}help{Colors.RESET} - Show help information

{Colors.BOLD}Usage:{Colors.RESET}
  zettl help              Show general help
  zettl COMMAND --help    Show help for a specific command

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.BLUE}zettl help{Colors.RESET}
  {Colors.BLUE}zettl search --help{Colors.RESET}
"""
        }
        
        return help_templates.get(command, f"No detailed help available for '{command}'. Try 'help' for a list of all commands.")