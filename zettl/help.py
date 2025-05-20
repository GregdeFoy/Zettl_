# help.py
from zettl.formatting import Colors

class CommandHelp:
    """Centralized help system for Zettl commands."""
    
    @staticmethod
    def get_main_help():
        """Return the main help text."""
        return f"""
{Colors.GREEN}{Colors.BOLD}zettl v0.1.0{Colors.RESET} - A Zettelkasten-style note-taking tool

{Colors.BOLD}Core Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}new{Colors.RESET} - Create a new note with the given content
    {Colors.BLUE}→{Colors.RESET} zettl new "This is a new note about an interesting concept"
    {Colors.BLUE}→{Colors.RESET} zettl new "Note with tag and link" --tag concept --link 22a4b

  {Colors.YELLOW}{Colors.BOLD}list{Colors.RESET} - List recent notes
    {Colors.BLUE}→{Colors.RESET} zettl list --limit 5
    {Colors.BLUE}→{Colors.RESET} zettl list --full  # Shows full content with tags

  {Colors.YELLOW}{Colors.BOLD}show{Colors.RESET} - Display note content
    {Colors.BLUE}→{Colors.RESET} zettl show 22a4b

  {Colors.YELLOW}{Colors.BOLD}search{Colors.RESET} - Search for notes by text, tag, or date
    {Colors.BLUE}→{Colors.RESET} zettl search "concept"
    {Colors.BLUE}→{Colors.RESET} zettl search -t concept --full  # Show full content with tags
    {Colors.BLUE}→{Colors.RESET} zettl search -d 2025-04-07      # Find notes from a specific date
    {Colors.BLUE}→{Colors.RESET} zettl search "concept" +t done  # Exclude notes with 'done' tag

{Colors.BOLD}Connection Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}link{Colors.RESET} - Create link between notes
    {Colors.BLUE}→{Colors.RESET} zettl link 22a4b 18c3d

  {Colors.YELLOW}{Colors.BOLD}related{Colors.RESET} - Show notes connected to this note
    {Colors.BLUE}→{Colors.RESET} zettl related 22a4b

  {Colors.YELLOW}{Colors.BOLD}graph{Colors.RESET} - Generate a graph visualization of notes
    {Colors.BLUE}→{Colors.RESET} zettl graph 22a4b --output graph.json --depth 2

{Colors.BOLD}Organizational Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}tags{Colors.RESET} - Show or add tags to a note
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b
    {Colors.BLUE}→{Colors.RESET} zettl tags 22a4b "concept"

    {Colors.YELLOW}{Colors.BOLD}todos{Colors.RESET} - List notes tagged with 'todo'
    {Colors.BLUE}→{Colors.RESET} zettl todos
    {Colors.BLUE}→{Colors.RESET} zettl todos --all  # Show all todos (active and completed)
    {Colors.BLUE}→{Colors.RESET} zettl todos --donetoday  # Show todos completed today
    {Colors.BLUE}→{Colors.RESET} zettl todos --tag work  # Filter todos by tag

{Colors.BOLD}Management Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}delete{Colors.RESET} - Delete a note and its associated data
    {Colors.BLUE}→{Colors.RESET} zettl delete 22a4b
    {Colors.BLUE}→{Colors.RESET} zettl delete 22a4b --keep-tags

  {Colors.YELLOW}{Colors.BOLD}untag{Colors.RESET} - Remove a tag from a note
    {Colors.BLUE}→{Colors.RESET} zettl untag 22a4b "concept"

  {Colors.YELLOW}{Colors.BOLD}unlink{Colors.RESET} - Remove a link between two notes
    {Colors.BLUE}→{Colors.RESET} zettl unlink 22a4b 18c3d

{Colors.BOLD}AI-Powered Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}llm{Colors.RESET} - Use Claude AI to analyze and enhance notes
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action summarize
    {Colors.BLUE}→{Colors.RESET} zettl llm 22a4b --action tags

{Colors.BOLD}Nutrition Tracking:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}nutrition{Colors.RESET} (alias: {Colors.YELLOW}nut{Colors.RESET}) - Track and analyze nutrition data
    {Colors.BLUE}→{Colors.RESET} zettl nut "Breakfast cal: 500 prot: 25"
    {Colors.BLUE}→{Colors.RESET} zettl nutrition --today
    {Colors.BLUE}→{Colors.RESET} zettl nutrition --history --days 14

{Colors.BOLD}Other Commands:{Colors.RESET}
  {Colors.YELLOW}{Colors.BOLD}rules{Colors.RESET} - Display a random rule from notes tagged with 'rules'
    {Colors.BLUE}→{Colors.RESET} zettl rules
    {Colors.BLUE}→{Colors.RESET} zettl rules --source  # Show source note ID

  {Colors.YELLOW}{Colors.BOLD}workflow{Colors.RESET} - Show example Zettl workflow
    {Colors.BLUE}→{Colors.RESET} zettl workflow
"""

    @staticmethod
    def get_command_help(command):
        """Return detailed help for a specific command."""
        help_templates = {
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

            "workflow": f"""
{Colors.GREEN}{Colors.BOLD}workflow{Colors.RESET} - Show an example workflow of using zettl

{Colors.BOLD}Usage:{Colors.RESET}
  zettl workflow

{Colors.BOLD}Description:{Colors.RESET}
  Displays a detailed step-by-step guide on how to effectively use Zettl
  for note-taking, connecting ideas, and building a knowledge network.
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