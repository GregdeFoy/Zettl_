# cli.py
import click
import os
from datetime import datetime
import time
from typing import Optional
from zettl.notes import Notes
from zettl.graph import NoteGraph
from zettl.llm import LLMHelper
from zettl.config import APP_NAME, APP_VERSION
from zettl.formatting import ZettlFormatter,Colors
import re
import random
from zettl.nutrition import NutritionTracker
from zettl.help import CommandHelp
from zettl.auth import auth as zettl_auth

# Get authenticated components
def get_notes_manager():
    """Get an authenticated Notes manager."""
    api_key = zettl_auth.require_auth()
    return Notes(api_key=api_key)

def get_graph_manager():
    """Get a graph manager (doesn't need auth currently)."""
    return NoteGraph()

def get_llm_helper():
    """Get an LLM helper (doesn't need auth currently)."""
    return LLMHelper()

# Define the function that both commands will use
def create_new_note(content, tag, link=None):
    """Create a new note with the given content and optional tags."""
    try:
        notes_manager = get_notes_manager()
        note_id = notes_manager.create_note(content)
        click.echo(f"Created note #{note_id}")

        # Add tags if provided
        if tag:
            for t in tag:
                try:
                    notes_manager.add_tag(note_id, t)
                    click.echo(f"Added tag '{t}' to note #{note_id}")
                except Exception as e:
                    click.echo(f"Warning: Could not add tag '{t}': {str(e)}", err=True)

        # Create link if provided
        if link:
            try:
                notes_manager.create_link(note_id, link)
                click.echo(f"Created link from #{note_id} to #{link}")
            except Exception as e:
                click.echo(f"Warning: Could not create link to note #{link}: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Error creating note: {str(e)}", err=True)


@click.group()
@click.version_option(version=APP_VERSION)
def cli():
    """A Zettelkasten-style note-taking CLI tool."""
    pass

@cli.group()
def auth():
    """Authentication commands."""
    pass

@auth.command()
def setup():
    """Set up API key authentication."""
    click.echo("Setting up Zettl CLI authentication...")
    click.echo("")
    click.echo("1. Go to your Zettl web interface")
    click.echo("2. Log in to your account")
    click.echo("3. Generate an API key for CLI access")
    click.echo("")

    api_key = click.prompt("Enter your API key", hide_input=True)

    if not api_key.startswith('zettl_'):
        click.echo("Warning: API key should start with 'zettl_'", err=True)

    # Test the API key
    click.echo("Testing API key...")
    if zettl_auth.test_api_key(api_key):
        if zettl_auth.set_api_key(api_key):
            click.echo(ZettlFormatter.success("✓ API key saved successfully!"))
            click.echo("You can now use the Zettl CLI.")
        else:
            click.echo(ZettlFormatter.error("✗ Failed to save API key"))
    else:
        click.echo(ZettlFormatter.error("✗ Invalid API key. Please check and try again."))

@auth.command()
def status():
    """Check authentication status."""
    api_key = zettl_auth.get_api_key()
    if api_key:
        if zettl_auth.test_api_key(api_key):
            click.echo(ZettlFormatter.success("✓ Authenticated"))
        else:
            click.echo(ZettlFormatter.error("✗ API key is invalid or expired"))
    else:
        click.echo(ZettlFormatter.warning("⚠ Not authenticated. Run 'zettl auth setup'"))

@cli.command()
def commands():
    """Show all available commands with examples."""
    click.echo(CommandHelp.get_main_help())

@cli.command()
@click.argument('content')
@click.option('--tag', '-t', multiple=True, help='Tag(s) to add to the new note')
@click.option('--link', '-l', help='Note ID to link this note to')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def new(content, tag, link, help):
    """Create a new note with the given content and optional tags."""
    if help:
        click.echo(CommandHelp.get_command_help("new"))
        return
    
    create_new_note(content, tag, link)

@cli.command()
@click.argument('content')
@click.option('--tag', '-t', multiple=True, help='Tag(s) to add to the new note')
@click.option('--link', '-l', help='Note ID to link this note to')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def add(content, tag, link, help):
    """Create a new note with the given content and optional tags. Alias for 'new'."""
    if help:
        click.echo(CommandHelp.get_command_help("add"))
        return
    
    create_new_note(content, tag, link)

# Update the list command
@cli.command()
@click.option('--limit', '-l', default=10, help='Number of notes to display')
@click.option('--full', '-f', is_flag=True, help='Show full content of notes')
@click.option('--compact', '-c', is_flag=True, help='Show very compact list (IDs only)')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def list(limit, full, compact, help):
    """List recent notes with formatting options."""
    if help:
        click.echo(CommandHelp.get_command_help("list"))
        return

    try:
        notes = get_notes_manager().list_notes(limit)
        if not notes:
            click.echo("No notes found.")
            return
            
        click.echo(ZettlFormatter.header(f"Recent Notes (showing {len(notes)} of {len(notes)})"))
        
        for note in notes:
            note_id = note['id']
            created_at = get_notes_manager().format_timestamp(note['created_at'])
            
            if compact:
                # Very compact mode - just IDs
                click.echo(ZettlFormatter.note_id(note_id))
            elif full:
                # Full content mode
                click.echo(ZettlFormatter.format_note_display(note, get_notes_manager()))
                
                # Add tags if there are any
                try:
                    tags = get_notes_manager().get_tags(note_id)
                    if tags:
                        click.echo(f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
                except Exception:
                    pass
                
                click.echo()  # Extra line between notes
            else:
                # Default mode - ID, timestamp, and preview
                formatted_id = ZettlFormatter.note_id(note_id)
                formatted_time = ZettlFormatter.timestamp(created_at)
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                click.echo(f"{formatted_id} [{formatted_time}]: {content_preview}")
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('note_id')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def show(note_id, help):

    if help:
        click.echo(CommandHelp.get_command_help("list"))
        return

    """Display note content."""
    try:
        note = get_notes_manager().get_note(note_id)
        click.echo(ZettlFormatter.format_note_display(note, get_notes_manager()))
        
        # Show tags if any
        try:
            tags = get_notes_manager().get_tags(note_id)
            if tags:
                click.echo(f"Tags: {', '.join(tags)}")
        except Exception:
            pass
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('source_id')
@click.argument('target_id')
@click.option('--context', '-c', default="", help='Optional context for the link')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def link(source_id, target_id, context, help):
    if help:
        click.echo(CommandHelp.get_command_help("link"))
        return

    """Create link between notes."""
    try:
        get_notes_manager().create_link(source_id, target_id, context)
        click.echo(f"Created link from #{source_id} to #{target_id}")
    except Exception as e:
        click.echo(f"Error creating link: {str(e)}", err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.argument('tag', required=False)
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def tags(note_id, tag, help):

    if help:
        click.echo(CommandHelp.get_command_help("tags"))
        return
    """Show or add tags to a note. If no note_id is provided, list all tags."""
    try:
        # If no note_id is provided, list all tags
        if not note_id:
            tags_with_counts = get_notes_manager().get_all_tags_with_counts()
            if tags_with_counts:
                click.echo(ZettlFormatter.header(f"All Tags (showing {len(tags_with_counts)})"))
                for tag_info in tags_with_counts:
                    formatted_tag = ZettlFormatter.tag(tag_info['tag'])
                    click.echo(f"{formatted_tag} ({tag_info['count']} notes)")
            else:
                click.echo(ZettlFormatter.warning("No tags found."))
            return
            
        # If a tag was provided, add it
        if tag:
            get_notes_manager().add_tag(note_id, tag)
            click.echo(f"Added tag '{tag}' to note #{note_id}")
            
        # Show all tags for the note
        tags = get_notes_manager().get_tags(note_id)
        if tags:
            click.echo(f"Tags for note #{note_id}: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
        else:
            click.echo(f"No tags for note #{note_id}")
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('query', required=False)
@click.option('--tag', '-t', help='Search for notes with this tag')
@click.option('--exclude-tag', '+t', help='Exclude notes with this tag')
@click.option('--date', '-d', help='Search for notes created on a specific date (YYYY-MM-DD format)')
@click.option('--full', '-f', is_flag=True, help='Show full content of matching notes')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def search(query, tag, exclude_tag, date, full, help):

    if help:
        click.echo(CommandHelp.get_command_help("search"))
        return
    """Search for notes containing text, with specific tag, or by date."""
    try:
        results = []
        
        if tag:
            # Search by tag inclusion
            notes = get_notes_manager().get_notes_by_tag(tag)
            if not notes:
                click.echo(ZettlFormatter.warning(f"No notes found with tag '{tag}'"))
                return
                
            click.echo(ZettlFormatter.header(f"Found {len(notes)} notes with tag '{tag}':"))
            results = notes
        elif date:
            # Search by date
            try:
                notes = get_notes_manager().search_notes_by_date(date)
                if not notes:
                    click.echo(ZettlFormatter.warning(f"No notes found for date '{date}'"))
                    return
                    
                click.echo(ZettlFormatter.header(f"Found {len(notes)} notes created on '{date}':"))
                results = notes
            except ValueError as e:
                click.echo(ZettlFormatter.error(str(e)))
                return
        elif query:
            # Search by content
            notes = get_notes_manager().search_notes(query)
            if not notes:
                click.echo(ZettlFormatter.warning(f"No notes found containing '{query}'"))
                return
                
            click.echo(ZettlFormatter.header(f"Found {len(notes)} notes containing '{query}':"))
            results = notes
        else:
            # No search criteria specified, use a larger set
            results = get_notes_manager().list_notes(limit=50)
            click.echo(ZettlFormatter.header(f"Listing notes (showing {len(results)}):"))
        
        # Filter out excluded tags if specified
        if exclude_tag:
            # Get IDs of notes with the excluded tag
            excluded_notes = get_notes_manager().get_notes_by_tag(exclude_tag)
            excluded_ids = {note['id'] for note in excluded_notes}
            
            # Filter out notes with the excluded tag
            original_count = len(results)
            results = [note for note in results if note['id'] not in excluded_ids]
            
            # Inform user about filtering
            if original_count != len(results):
                click.echo(ZettlFormatter.warning(f"Excluded {original_count - len(results)} notes with tag '{exclude_tag}'"))
        
        # Display the final results
        if not results:
            click.echo(ZettlFormatter.warning("No notes match your criteria after filtering."))
            return
            
        for note in results:
            if full:
                # Full content mode
                click.echo(ZettlFormatter.format_note_display(note, get_notes_manager()))
                
                # Add tags if there are any
                try:
                    tags = get_notes_manager().get_tags(note['id'])
                    if tags:
                        click.echo(f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
                except Exception:
                    pass
                
                click.echo()  # Extra line between notes
            else:
                # Preview mode
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                if query:
                    # Highlight the query in the preview
                    pattern = re.compile(re.escape(query), re.IGNORECASE)
                    content_preview = pattern.sub(f"{Colors.YELLOW}\\g<0>{Colors.RESET}", content_preview)
                
                formatted_id = ZettlFormatter.note_id(note['id'])
                click.echo(f"{formatted_id}: {content_preview}")
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('note_id')
@click.option('--full', '-f', is_flag=True, help='Show full content of related notes')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def related(note_id, full, help):
    if help:
        click.echo(CommandHelp.get_command_help("related"))
        return
    """Show notes connected to this note with improved formatting."""
    try:
        # First, show the source note
        try:
            source_note = get_notes_manager().get_note(note_id)
            click.echo(ZettlFormatter.header(f"Source Note"))
            click.echo(ZettlFormatter.format_note_display(source_note, get_notes_manager()))
            click.echo("\n")  # Extra space after source note
        except Exception as e:
            click.echo(ZettlFormatter.warning(f"Could not display source note: {str(e)}"))
        
        # Now show related notes
        related_notes = get_notes_manager().get_related_notes(note_id)
        if not related_notes:
            click.echo(ZettlFormatter.warning(f"No notes connected to note #{note_id}"))
            return
            
        click.echo(ZettlFormatter.header(f"Connected Notes ({len(related_notes)} total)"))
        
        for note in related_notes:
            if full:
                # Full content mode
                click.echo(ZettlFormatter.format_note_display(note, get_notes_manager()))
                click.echo()  # Extra line between notes
            else:
                # Preview mode
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                formatted_id = ZettlFormatter.note_id(note['id'])
                click.echo(f"{formatted_id}: {content_preview}")
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.option('--output', '-o', default='zettl_graph.json', help='Output file for graph data')
@click.option('--depth', '-d', default=2, help='How many levels of connections to include')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def graph(note_id, output, depth, help):

    if help:
        click.echo(CommandHelp.get_command_help("graph"))
        return

    """Generate a graph visualization of notes and their connections."""
    try:
        file_path = get_graph_manager().export_graph(output, note_id, depth)
        click.echo(f"Graph data exported to {file_path}")
        click.echo("You can visualize this data using a graph visualization tool.")
    except Exception as e:
        click.echo(f"Error generating graph: {str(e)}", err=True)

@cli.command()
@click.argument('note_id')
@click.option('--action', '-a', 
              type=click.Choice(['summarize', 'connect', 'tags', 'expand', 'concepts', 'questions', 'critique']), 
              default='summarize', 
              help='LLM action to perform')
@click.option('--count', '-c', default=3, help='Number of results to return for tags/connections/concepts/questions')
@click.option('--show-source', '-s', is_flag=True, help='Show the source note before analysis')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def llm(note_id, action, count, show_source, help):

    if help:
        click.echo(CommandHelp.get_command_help("llm"))
        return
    """Use Claude AI to analyze and enhance notes."""
    try:
        # Show the source note if requested
        if show_source:
            try:
                source_note = get_notes_manager().get_note(note_id)
                click.echo(ZettlFormatter.header("Source Note"))
                click.echo(ZettlFormatter.format_note_display(source_note, get_notes_manager()))
                click.echo("\n")  # Extra space after source note
            except Exception as e:
                click.echo(ZettlFormatter.warning(f"Could not display source note: {str(e)}"))
        
        if action == 'summarize':
            click.echo(ZettlFormatter.header(f"AI Summary for Note #{note_id}"))
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating summary') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                summary = get_llm_helper().summarize_note(note_id)
            
            click.echo(f"\n{Colors.YELLOW}{summary}{Colors.RESET}")
            
        elif action == 'connect':
            click.echo(ZettlFormatter.header(f"AI-Suggested Connections for Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Finding connections') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                connections = get_llm_helper().generate_connections(note_id, count)
            
            if not connections:
                click.echo(ZettlFormatter.warning("No potential connections found."))
                return
                
            for conn in connections:
                conn_id = conn['note_id']
                formatted_id = ZettlFormatter.note_id(conn_id)
                click.echo(f"\n{formatted_id}")
                click.echo(f"  {Colors.YELLOW}{conn['explanation']}{Colors.RESET}")
                
                # Try to show a preview of the connected note
                try:
                    conn_note = get_notes_manager().get_note(conn_id)
                    content_preview = conn_note['content'][:100] + "..." if len(conn_note['content']) > 100 else conn_note['content']
                    click.echo(f"  {Colors.CYAN}Preview:{Colors.RESET} {content_preview}")
                    
                    # Add option to link notes
                    if click.confirm(f"\nCreate link from #{note_id} to #{conn_id}?"):
                        get_notes_manager().create_link(note_id, conn_id, conn['explanation'])
                        click.echo(ZettlFormatter.success(f"Created link from #{note_id} to #{conn_id}"))
                except Exception:
                    pass
            
        elif action == 'tags':
            click.echo(ZettlFormatter.header(f"AI-Suggested Tags for Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating tags') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                tags = get_llm_helper().suggest_tags(note_id, count)
            
            if not tags:
                click.echo(ZettlFormatter.warning("No tags suggested."))
                return
                
            click.echo("\nSuggested tags:")
            for tag in tags:
                formatted_tag = ZettlFormatter.tag(tag)
                click.echo(f"{formatted_tag}")
                
            # Ask if user wants to add these tags
            if click.confirm("\nWould you like to add these tags to the note?"):
                for tag in tags:
                    try:
                        get_notes_manager().add_tag(note_id, tag)
                        click.echo(ZettlFormatter.success(f"Added tag '{tag}' to note #{note_id}"))
                    except Exception as e:
                        click.echo(ZettlFormatter.error(f"Error adding tag '{tag}': {str(e)}"), err=True)

        elif action == 'expand':
            click.echo(ZettlFormatter.header(f"AI-Expanded Version of Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Expanding note') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                expanded_content = get_llm_helper().expand_note(note_id)
            
            click.echo(f"\n{Colors.YELLOW}{expanded_content}{Colors.RESET}")
            
            # Ask if user wants to create a new note with the expanded content
            if click.confirm("\nCreate a new note with this expanded content?"):
                try:
                    # Create new note with expanded content
                    new_note_id = get_notes_manager().create_note(expanded_content)
                    click.echo(ZettlFormatter.success(f"Created expanded note #{new_note_id}"))
                    
                    # Create link from original to expanded note
                    get_notes_manager().create_link(note_id, new_note_id, "Expanded version")
                    click.echo(ZettlFormatter.success(f"Linked original #{note_id} to expanded #{new_note_id}"))
                    
                    # Copy tags from original note to new note
                    try:
                        original_tags = get_notes_manager().get_tags(note_id)
                        for tag in original_tags:
                            get_notes_manager().add_tag(new_note_id, tag)
                        if original_tags:
                            click.echo(ZettlFormatter.success(f"Copied {len(original_tags)} tags to new note"))
                    except Exception:
                        pass
                except Exception as e:
                    click.echo(ZettlFormatter.error(f"Error creating expanded note: {str(e)}"), err=True)
        
        elif action == 'concepts':
            click.echo(ZettlFormatter.header(f"Key Concepts from Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Extracting concepts') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                concepts = get_llm_helper().extract_key_concepts(note_id, count)
            
            if not concepts:
                click.echo(ZettlFormatter.warning("No key concepts identified."))
                return
                
            for i, concept in enumerate(concepts, 1):
                click.echo(f"\n{Colors.BOLD}{Colors.CYAN}{i}. {concept['concept']}{Colors.RESET}")
                click.echo(f"   {Colors.YELLOW}{concept['explanation']}{Colors.RESET}")
                
                # Ask if user wants to create a new note for this concept
                if click.confirm(f"\nCreate a new note for the concept '{concept['concept']}'?"):
                    try:
                        # Prepare content for the new note
                        concept_content = f"{concept['concept']}\n\n{concept['explanation']}"
                        
                        # Create new note
                        new_note_id = get_notes_manager().create_note(concept_content)
                        click.echo(ZettlFormatter.success(f"Created concept note #{new_note_id}"))
                        
                        # Create link from original to concept note
                        get_notes_manager().create_link(note_id, new_note_id, f"Concept: {concept['concept']}")
                        click.echo(ZettlFormatter.success(f"Linked original #{note_id} to concept #{new_note_id}"))
                    except Exception as e:
                        click.echo(ZettlFormatter.error(f"Error creating concept note: {str(e)}"), err=True)
        
        elif action == 'questions':
            click.echo(ZettlFormatter.header(f"Thought-Provoking Questions from Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating questions') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                questions = get_llm_helper().generate_question_note(note_id, count)
            
            if not questions:
                click.echo(ZettlFormatter.warning("No questions generated."))
                return
                
            for i, question in enumerate(questions, 1):
                click.echo(f"\n{Colors.BOLD}{Colors.CYAN}{i}. {question['question']}{Colors.RESET}")
                click.echo(f"   {Colors.YELLOW}{question['explanation']}{Colors.RESET}")
                
                # Ask if user wants to create a new note for this question
                if click.confirm(f"\nCreate a new note for this question?"):
                    try:
                        # Prepare content for the new note
                        question_content = f"{question['question']}\n\n{question['explanation']}"
                        
                        # Create new note
                        new_note_id = get_notes_manager().create_note(question_content)
                        click.echo(ZettlFormatter.success(f"Created question note #{new_note_id}"))
                        
                        # Create link from original to question note
                        get_notes_manager().create_link(note_id, new_note_id, "Question derived from this note")
                        click.echo(ZettlFormatter.success(f"Linked original #{note_id} to question #{new_note_id}"))
                    except Exception as e:
                        click.echo(ZettlFormatter.error(f"Error creating question note: {str(e)}"), err=True)
        
        elif action == 'critique':
            click.echo(ZettlFormatter.header(f"AI Critique of Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Analyzing note') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                critique = get_llm_helper().critique_note(note_id)
            
            # Display strengths
            if critique['strengths']:
                click.echo(f"\n{Colors.BOLD}{Colors.GREEN}Strengths:{Colors.RESET}")
                for strength in critique['strengths']:
                    click.echo(f"  • {strength}")
            
            # Display weaknesses
            if critique['weaknesses']:
                click.echo(f"\n{Colors.BOLD}{Colors.YELLOW}Areas for Improvement:{Colors.RESET}")
                for weakness in critique['weaknesses']:
                    click.echo(f"  • {weakness}")
            
            # Display suggestions
            if critique['suggestions']:
                click.echo(f"\n{Colors.BOLD}{Colors.CYAN}Suggestions:{Colors.RESET}")
                for suggestion in critique['suggestions']:
                    click.echo(f"  • {suggestion}")
            
            # If no structured feedback was generated
            if not (critique['strengths'] or critique['weaknesses'] or critique['suggestions']):
                click.echo(ZettlFormatter.warning("Could not generate structured feedback for this note."))
                
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

@cli.command()
@click.argument('note_id')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.option('--keep-links', is_flag=True, help='Keep links to and from this note')
@click.option('--keep-tags', is_flag=True, help='Keep tags associated with this note')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def delete(note_id, force, keep_links, keep_tags,help):

    if help:
        click.echo(CommandHelp.get_command_help("delete"))
        return

    """Delete a note and its associated data."""
    try:
        # First get the note to show what will be deleted
        try:
            note = get_notes_manager().get_note(note_id)
            
            # Get related data counts for information
            try:
                tags = get_notes_manager().get_tags(note_id)
                related_notes = get_notes_manager().get_related_notes(note_id)
                tag_count = len(tags)
                link_count = len(related_notes)
            except Exception:
                tag_count = 0
                link_count = 0
                
            # Show preview of what will be deleted
            click.echo(ZettlFormatter.header(f"Note to delete: #{note_id}"))
            content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
            click.echo(f"Content: {content_preview}")
            click.echo(f"Associated tags: {tag_count}")
            click.echo(f"Connected notes: {link_count}")
            
        except Exception as e:
            if not force:
                click.echo(ZettlFormatter.warning(f"Could not retrieve note: {str(e)}"))
                if not click.confirm("Continue with deletion anyway?"):
                    click.echo("Deletion cancelled.")
                    return
        
        # Confirm deletion if not forced
        if not force and not click.confirm(f"Delete note #{note_id}?"):
            click.echo("Deletion cancelled.")
            return
        
        # Determine cascade setting based on flags
        cascade = not (keep_links and keep_tags)
        
        # Delete with custom handling if specific items should be kept
        if cascade and (keep_links or keep_tags):
            # Custom deletion flow
            if not keep_tags:
                get_notes_manager().delete_note_tags(note_id)
                click.echo(f"Deleted tags for note #{note_id}")
            
            if not keep_links:
                get_notes_manager().delete_note_links(note_id)
                click.echo(f"Deleted links for note #{note_id}")
            
            # Now delete the note itself (with cascade=False since we handled dependencies)
            get_notes_manager().delete_note(note_id, cascade=False)
        else:
            # Standard cascade deletion
            get_notes_manager().delete_note(note_id, cascade=cascade)
        
        click.echo(ZettlFormatter.success(f"Deleted note #{note_id}"))
        
    except Exception as e:
        click.echo(ZettlFormatter.error(f"Error deleting note: {str(e)}"), err=True)

@cli.command()
@click.argument('note_id')
@click.argument('tag')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def untag(note_id, tag,help):

    if help:
        click.echo(CommandHelp.get_command_help("untag"))
        return
    """Remove a tag from a note."""
    try:
        get_notes_manager().delete_tag(note_id, tag)
        click.echo(ZettlFormatter.success(f"Removed tag '{tag}' from note #{note_id}"))
    except Exception as e:
        click.echo(ZettlFormatter.error(f"Error removing tag: {str(e)}"), err=True)

@cli.command()
@click.argument('source_id')
@click.argument('target_id')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def unlink(source_id, target_id,help):

    if help:
        click.echo(CommandHelp.get_command_help("unlink"))
        return

    """Remove a link between two notes."""
    try:
        get_notes_manager().delete_link(source_id, target_id)
        click.echo(ZettlFormatter.success(f"Removed link from note #{source_id} to note #{target_id}"))
    except Exception as e:
        click.echo(ZettlFormatter.error(f"Error removing link: {str(e)}"), err=True)

@cli.command()
@click.argument('note_ids', nargs=-1, required=False)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def merge(note_ids, force, help):
    """Merge multiple notes into a single note.

    This command combines the content of multiple notes, preserves all tags
    and external links, and deletes the original notes.

    Usage: zettl merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...]
    """
    if help:
        click.echo(CommandHelp.get_command_help("merge"))
        return

    try:
        # Validate we have at least 2 notes
        if not note_ids or len(note_ids) < 2:
            click.echo(ZettlFormatter.error("Must provide at least 2 notes to merge"))
            return

        # Show preview of notes to be merged
        click.echo(ZettlFormatter.header(f"Notes to merge ({len(note_ids)} total):"))
        notes_manager = get_notes_manager()

        all_tags = set()
        for note_id in note_ids:
            try:
                note = notes_manager.get_note(note_id)
                content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                formatted_id = ZettlFormatter.note_id(note_id)
                click.echo(f"\n{formatted_id}")
                click.echo(f"  {content_preview}")

                # Show tags
                try:
                    tags = notes_manager.get_tags(note_id)
                    if tags:
                        all_tags.update(tags)
                        click.echo(f"  Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
                except Exception:
                    pass

            except Exception as e:
                click.echo(ZettlFormatter.error(f"Error fetching note {note_id}: {str(e)}"), err=True)
                return

        # Show what will be preserved
        if all_tags:
            click.echo(f"\n{ZettlFormatter.header('Tags that will be added to merged note:')}")
            click.echo(f"{', '.join([ZettlFormatter.tag(t) for t in sorted(all_tags)])}")

        # Confirm merge if not forced
        if not force:
            click.echo("")
            if not click.confirm("Proceed with merge? This will delete the original notes."):
                click.echo("Merge cancelled.")
                return

        # Perform the merge
        # Note: we pass note_ids directly (it's a tuple, which works fine)
        # Can't use list() here because there's a Click command named 'list'
        merged_note_id = notes_manager.merge_notes(note_ids)

        click.echo(ZettlFormatter.success(f"\nSuccessfully merged {len(note_ids)} notes into #{merged_note_id}"))
        click.echo(f"\nView merged note with: zettl show {merged_note_id}")

    except Exception as e:
        click.echo(ZettlFormatter.error(f"Error merging notes: {str(e)}"), err=True)

@cli.command()
@click.option('--donetoday', '-dt', is_flag=True, help='List todos that were completed today')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all todos (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled todos')
@click.option('--tag', '-t', multiple=True, help='Filter todos by one or more additional tags')
@click.option('--eisenhower', '-e', is_flag=True, help='Display todos in Eisenhower matrix format')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def todos(donetoday, show_all, cancel, tag, eisenhower, help):
    """List all notes tagged with 'todo' grouped by category."""
    if help:
        click.echo(CommandHelp.get_command_help("todos"))
        return

    try:
        # Get the notes manager once and reuse it
        notes_manager = get_notes_manager()

        # Get all notes tagged with 'todo' along with ALL their tags efficiently
        todo_notes = notes_manager.get_notes_with_all_tags_by_tag('todo')

        if not todo_notes:
            click.echo(ZettlFormatter.warning("No todos found."))
            return

        # Filter for todos completed today if requested
        if donetoday:
            done_today_data = notes_manager.get_tags_created_today('done')
            if not done_today_data:
                click.echo(ZettlFormatter.warning("No todos completed today."))
                return

            # Extract note IDs from the done today data
            done_today_ids = {item['note_id'] for item in done_today_data}

            # Filter todo_notes to only include those completed today
            todo_notes = [note for note in todo_notes if note['id'] in done_today_ids]

            if not todo_notes:
                click.echo(ZettlFormatter.warning("No todos completed today."))
                return

        # Special handling for Eisenhower matrix display
        if eisenhower:
            display_eisenhower_matrix(todo_notes, show_all, donetoday, cancel)
            return

        # Apply filters if specified - now using pre-loaded tags
        if tag:
            filters = [f.lower() for f in tag]
            filtered_notes = []

            for note in todo_notes:
                note_tags_lower = [t.lower() for t in note.get('all_tags', [])]

                # Check if all filters are in the note's tags
                if all(f in note_tags_lower for f in filters):
                    filtered_notes.append(note)

            todo_notes = filtered_notes

            if not todo_notes:
                filter_str = "', '".join(tag)
                click.echo(ZettlFormatter.warning(f"No todos found with all tags: '{filter_str}'."))
                return

        # Group notes by their tags (categories) - using pre-loaded tags
        active_todos_by_category = {}
        done_todos_by_category = {}
        canceled_todos_by_category = {}
        uncategorized_active = []
        uncategorized_done = []
        uncategorized_canceled = []

        # Track unique note IDs to count them at the end
        unique_active_ids = set()
        unique_done_ids = set()
        unique_canceled_ids = set()

        for note in todo_notes:
            note_id = note['id']
            note_tags = note.get('all_tags', [])
            tags_lower = [t.lower() for t in note_tags]

            # Check if this is a done todo
            is_done = 'done' in tags_lower

            # Check if this is a canceled todo
            is_canceled = 'cancel' in tags_lower

            # Skip done todos if not explicitly included
            if is_done and not show_all and not donetoday:
                continue

            # Skip canceled todos if not explicitly requested
            if is_canceled and not cancel:
                continue

            # Track unique IDs
            if is_canceled:
                unique_canceled_ids.add(note_id)
            elif is_done:
                unique_done_ids.add(note_id)
            else:
                unique_active_ids.add(note_id)

            # Find category tags (everything except 'todo', 'done', 'cancel', and the filter tags)
            excluded_tags = ['todo', 'done', 'cancel']
            if tag:
                excluded_tags.extend([f.lower() for f in tag])

            categories = [t for t in note_tags if t.lower() not in excluded_tags]

            if not categories:
                # This todo has no category tags
                if is_canceled:
                    uncategorized_canceled.append(note)
                elif is_done:
                    uncategorized_done.append(note)
                else:
                    uncategorized_active.append(note)
            else:
                # Create a combined category key from all tags
                combined_category = " - ".join(sorted(categories))

                if is_canceled:
                    if combined_category not in canceled_todos_by_category:
                        canceled_todos_by_category[combined_category] = []
                    canceled_todos_by_category[combined_category].append(note)
                elif is_done:
                    if combined_category not in done_todos_by_category:
                        done_todos_by_category[combined_category] = []
                    done_todos_by_category[combined_category].append(note)
                else:
                    if combined_category not in active_todos_by_category:
                        active_todos_by_category[combined_category] = []
                    active_todos_by_category[combined_category].append(note)

        # Build the header message
        header_parts = ["Todos"]
        if tag:
            filter_str = "', '".join(tag)
            header_parts.append(f"tagged with '{filter_str}'")

        # Display todos by category
        if (not active_todos_by_category and not uncategorized_active and
            (not show_all and not donetoday or (not done_todos_by_category and not uncategorized_done)) and
            (not cancel or (not canceled_todos_by_category and not uncategorized_canceled))):
            click.echo(ZettlFormatter.warning("No todos match your criteria."))
            return

        # Helper function to display a group of todos
        def display_todos_group(category_dict, uncategorized_list, header_text):
            if header_text:
                click.echo(header_text)

            if category_dict:
                for category, notes in sorted(category_dict.items()):
                    # Check if this is a combined category with multiple tags
                    if " - " in category:
                        # For combined categories, format each tag separately
                        tags = category.split(" - ")
                        formatted_tags = []
                        for tag_name in tags:
                            formatted_tags.append(ZettlFormatter.tag(tag_name))
                        category_display = " - ".join(formatted_tags)
                        click.echo(f"\n{category_display} ({len(notes)})")
                    else:
                        # For single categories, use the original format
                        click.echo(f"\n{ZettlFormatter.tag(category)} ({len(notes)})")

                    for note in notes:
                        formatted_id = ZettlFormatter.note_id(note['id'])

                        # Format with indentation
                        content_lines = note['content'].split('\n')
                        click.echo(f"  {formatted_id}: {content_lines[0]}")
                        if len(content_lines) > 1:
                            for line in content_lines[1:]:
                                click.echo(f"      {line}")
                        click.echo("")  # Add an empty line between notes

            if uncategorized_list:
                click.echo("\nUncategorized")
                for note in uncategorized_list:
                    formatted_id = ZettlFormatter.note_id(note['id'])

                    # Format with indentation
                    content_lines = note['content'].split('\n')
                    click.echo(f"  {formatted_id}: {content_lines[0]}")
                    if len(content_lines) > 1:
                        for line in content_lines[1:]:
                            click.echo(f"      {line}")
                    click.echo("")  # Add an empty line between notes

        # Display active todos first
        if active_todos_by_category or uncategorized_active:
            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
            display_todos_group(active_todos_by_category, uncategorized_active, active_header)

        # Display all done todos if requested
        if (show_all or donetoday) and (done_todos_by_category or uncategorized_done):
            done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids)} total)")
            click.echo(f"\n{done_header}")
            display_todos_group(done_todos_by_category, uncategorized_done, "")

        # Display canceled todos if requested
        if cancel and (canceled_todos_by_category or uncategorized_canceled):
            canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
            click.echo(f"\n{canceled_header}")
            display_todos_group(canceled_todos_by_category, uncategorized_canceled, "")

    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)

def display_eisenhower_matrix(todo_notes, include_done=False, include_donetoday=False, include_cancel=False):
    """Display todos in an Eisenhower matrix format."""
    # Create four quadrants for Eisenhower categorization
    urgent_important = []      # do - Quadrant 1
    not_urgent_important = []  # pl - Quadrant 2
    urgent_not_important = []  # dl - Quadrant 3
    not_urgent_not_important = []  # dr - Quadrant 4
    uncategorized = []
    done_todos = []            # Completed todos
    canceled_todos = []        # Canceled todos

    # Track unique note IDs for counting
    unique_ids = set()

    for note in todo_notes:
        note_id = note['id']
        # Use the pre-loaded tags from the view
        note_tags = note.get('all_tags', [])
        tags_lower = [t.lower() for t in note_tags]
        
        # Check status flags
        is_done = 'done' in tags_lower
        is_canceled = 'cancel' in tags_lower

        # Skip based on flags
        if is_canceled and not include_cancel:
            continue

        if is_done and not include_done:
            continue
        
        # Add to appropriate category
        if is_canceled:
            canceled_todos.append(note)
        elif is_done:
            done_todos.append(note)
        elif 'do' in tags_lower:
            urgent_important.append(note)
        elif 'pl' in tags_lower:
            not_urgent_important.append(note)
        elif 'dl' in tags_lower:
            urgent_not_important.append(note)
        elif 'dr' in tags_lower:
            not_urgent_not_important.append(note)
        else:
            uncategorized.append(note)
        
        # Track all displayed todos
        unique_ids.add(note_id)
    
    # Display matrix header
    click.echo(ZettlFormatter.header("Eisenhower Matrix"))
    click.echo(f"Total todos: {len(unique_ids)}")
    click.echo()
    
    # Helper to format a single note
    def format_note(note):
        formatted_id = ZettlFormatter.note_id(note['id'])
        content_lines = note['content'].split('\n')
        return f"  {formatted_id}: {content_lines[0]}"
    
    # Matrix dimension and layout constants
    MATRIX_WIDTH = 120
    COL_WIDTH = MATRIX_WIDTH // 2 - 2  # Allow for the divider
    separator = "-" * MATRIX_WIDTH
    
    # Display top header
    click.echo(f"{' ' * 20}URGENT{' ' * (COL_WIDTH - 26)}|{' ' * 10}NOT URGENT")
    click.echo(separator)
    
    # Display Q1 and Q2 headers (DO and PLAN)
    q1_header = f"{Colors.BOLD}IMPORTANT{Colors.RESET}"
    q1_label = f"{Colors.GREEN}DO{Colors.RESET} ({len(urgent_important)})"
    q2_label = f"{Colors.BLUE}PLAN{Colors.RESET} ({len(not_urgent_important)})"
    
    click.echo(f"{q1_header.ljust(15)} | {q1_label.ljust(COL_WIDTH - 3)}| {q2_label}")
    click.echo(separator)
    
    # Display Q1 and Q2 content
    q1_height = len(urgent_important)
    q2_height = len(not_urgent_important)
    max_top_height = max(q1_height, q2_height)
    
    for i in range(max_top_height):
        left = format_note(urgent_important[i]) if i < q1_height else ""
        right = format_note(not_urgent_important[i]) if i < q2_height else ""
        
        # Ensure columns align properly
        if len(left) > COL_WIDTH:
            left = left[:COL_WIDTH-3] + "..."
            
        click.echo(f"{left.ljust(COL_WIDTH)} | {right}")
    
    click.echo(separator)
    
    # Display Q3 and Q4 headers (DELEGATE and DROP)
    q3_header = f"{Colors.BOLD}NOT IMPORTANT{Colors.RESET}"
    q3_label = f"{Colors.YELLOW}DELEGATE{Colors.RESET} ({len(urgent_not_important)})"
    q4_label = f"{Colors.RED}DROP{Colors.RESET} ({len(not_urgent_not_important)})"
    
    click.echo(f"{q3_header.ljust(15)} | {q3_label.ljust(COL_WIDTH - 3)}| {q4_label}")
    click.echo(separator)
    
    # Display Q3 and Q4 content
    q3_height = len(urgent_not_important)
    q4_height = len(not_urgent_not_important)
    max_bottom_height = max(q3_height, q4_height)
    
    for i in range(max_bottom_height):
        left = format_note(urgent_not_important[i]) if i < q3_height else ""
        right = format_note(not_urgent_not_important[i]) if i < q4_height else ""
        
        # Ensure columns align properly
        if len(left) > COL_WIDTH:
            left = left[:COL_WIDTH-3] + "..."
            
        click.echo(f"{left.ljust(COL_WIDTH)} | {right}")
    
    # Display additional categories if requested
    if uncategorized:
        click.echo("\n" + separator)
        click.echo(ZettlFormatter.warning(f"Uncategorized Todos ({len(uncategorized)})"))
        for note in uncategorized:
            click.echo(format_note(note))
    
    if include_done and done_todos:
        click.echo("\n" + separator)
        click.echo(ZettlFormatter.header(f"Completed Todos ({len(done_todos)})"))
        for note in done_todos:
            click.echo(format_note(note))
    
    if include_cancel and canceled_todos:
        click.echo("\n" + separator)
        click.echo(ZettlFormatter.header(f"Canceled Todos ({len(canceled_todos)})"))
        for note in canceled_todos:
            click.echo(format_note(note))


@cli.command()
@click.option('--source', '-s', is_flag=True, help='Show the source note ID')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def rules(source,help):

    if help:
        click.echo(CommandHelp.get_command_help("rules"))
        return

    """Display a random rule from notes tagged with 'rules'."""
    try:
        # Get all notes tagged with 'rules'
        rules_notes = get_notes_manager().get_notes_by_tag('rules')
        
        if not rules_notes:
            click.echo(ZettlFormatter.warning("No notes found with tag 'rules'"))
            return
            
        # Extract rules from all notes
        all_rules = []
        
        for note in rules_notes:
            note_id = note['id']
            content = note['content']
            
            # Try to parse numbered rules (like "1. Rule text")
            lines = content.split('\n')
            rule_starts = []
            
            # Find line numbers where rules start
            for i, line in enumerate(lines):
                if re.match(r'^\s*\d+[\.\)]\s+', line):
                    rule_starts.append(i)
            
            if rule_starts:
                # This note contains numbered rules
                for i, start_idx in enumerate(rule_starts):
                    # Determine where this rule ends (next rule start or end of note)
                    end_idx = rule_starts[i+1] if i+1 < len(rule_starts) else len(lines)
                    
                    # Extract the rule text
                    rule_lines = lines[start_idx:end_idx]
                    full_text = '\n'.join(rule_lines).strip()
                    
                    rule = {
                        'note_id': note_id,
                        'full_text': full_text
                    }
                    all_rules.append(rule)
            else:
                # This note doesn't have numbered items, treat it as a single rule
                rule = {
                    'note_id': note_id,
                    'full_text': content.strip()
                }
                all_rules.append(rule)
                
        if not all_rules:
            click.echo(ZettlFormatter.warning("Couldn't extract any rules from the notes"))
            return
            
        # Select a random rule
        random_rule = random.choice(all_rules)
        
        # Display the rule
        click.echo(ZettlFormatter.header("Random Rule"))
        
        if source:
            # Show the source note ID
            click.echo(f"Source: {ZettlFormatter.note_id(random_rule['note_id'])}\n")
        
        # Always show the full rule
        click.echo(random_rule['full_text'])
            
    except Exception as e:
        click.echo(ZettlFormatter.error(str(e)), err=True)


@cli.command()
def workflow():
    """Show an example workflow of using zettl."""
    # Colors for better readability
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    click.echo(f"\n{BOLD}{GREEN}Example Zettl Workflow{RESET}\n")
    click.echo("This guide demonstrates a typical Zettl workflow.\n")
    
    steps = [
        {
            "title": "Create a new note",
            "command": "zettl new \"The Feynman Technique is a mental model to convey information using concise thoughts and simple language.\"",
            "explanation": "This creates a new note and returns a unique ID (let's call it 22a4b)."
        },
        {
            "title": "Create another related note",
            "command": "zettl new \"Spaced repetition is a learning technique that involves increasing intervals of time between subsequent review of previously learned material.\"",
            "explanation": "This creates another note (let's call it 18c3d)."
        },
        {
            "title": "Create a note with a direct link",
            "command": "zettl new \"Using spaced repetition with the Feynman Technique enhances recall.\" --tag learning --link 22a4b",
            "explanation": "This creates a new note with a tag and links it directly to the Feynman Technique note."
        },
        {
            "title": "Link these two notes",
            "command": "zettl link 22a4b 18c3d",
            "explanation": "This creates a connection between the Feynman Technique note and the Spaced Repetition note."
        },
        {
            "title": "Add tags to your notes",
            "command": "zettl tags 22a4b \"learning-technique\"",
            "explanation": "This adds a tag to the first note for better organization."
        },
        {
            "title": "View note details",
            "command": "zettl show 22a4b",
            "explanation": "This displays the full content of the note, along with any tags."
        },
        {
            "title": "List all recent notes with full content",
            "command": "zettl list --full",
            "explanation": "This shows all your recent notes with their full content and tags."
        },
        {
            "title": "Find related notes",
            "command": "zettl related 22a4b",
            "explanation": "This shows notes connected to the Feynman Technique note."
        },
        {
            "title": "Generate AI suggestions",
            "command": "zettl llm 22a4b --action tags",
            "explanation": "This uses Claude AI to suggest relevant tags for your note."
        },
        {
            "title": "Visualize your note network",
            "command": "zettl graph --output my_notes.json",
            "explanation": "This exports a graph of your notes and their connections, which you can visualize with various tools."
        },
        {
            "title": "Search your notes with tags",
            "command": "zettl search \"technique\" --full",
            "explanation": "This finds all notes containing the word 'technique' and shows full content including tags."
        },
        {
            "title": "Merge related notes",
            "command": "zettl merge 22a4b 18c3d",
            "explanation": "This combines two related notes into one, preserving all tags and links from both."
        },
        {
            "title": "Manage todos with filtering",
            "command": "zettl todos --all --tag learning",
            "explanation": "This shows all todos (active and completed) that have the 'learning' tag."
        }
    ]
    
    for i, step in enumerate(steps, 1):
        click.echo(f"{BOLD}{YELLOW}Step {i}: {step['title']}{RESET}")
        click.echo(f"  {BLUE}Command:{RESET} {CYAN}{step['command']}{RESET}")
        click.echo(f"  {BLUE}What it does:{RESET} {step['explanation']}")
        click.echo("")
    
    click.echo(f"{BOLD}{GREEN}Additional Tips:{RESET}")
    click.echo("• Use the AI capabilities to find connections between notes you might have missed")
    click.echo("• Keep notes atomic - one idea per note")
    click.echo("• Focus on creating meaningful connections between notes")
    click.echo("• Use tags sparingly for high-level categorization")
    click.echo("• Regularly review and refine your note network")

@cli.command()
@click.argument('content', required=False)
@click.option('--today', '-t', is_flag=True, help='Show today\'s nutrition summary')
@click.option('--history', '-i', is_flag=True, help='Show nutrition history')
@click.option('--days', '-d', default=7, help='Number of days to show in history')
@click.option('--past', '-p', help='Date for new entry (YYYY-MM-DD format)')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def nutrition(content, today, history, days, past, help):

    if help:
        click.echo(CommandHelp.get_command_help("nutrition"))
        return


    """Track and analyze nutrition data (calories and protein).
    
    If called with content in quotes, adds a new entry.
    With --today/-t, shows today's summary.
    With --history/-i, shows history for the specified days.
    """
    tracker = NutritionTracker()
    
    # Determine what action to take based on provided options
    if today:
        # Show today's summary
        try:
            summary = tracker.format_today_summary()
            click.echo(summary)
        except Exception as e:
            click.echo(ZettlFormatter.error(str(e)), err=True)
    elif history:
        # Show history
        try:
            history_output = tracker.format_history(days=days)
            click.echo(history_output)
        except Exception as e:
            click.echo(ZettlFormatter.error(str(e)), err=True)
    elif content:
        # Add new entry (default behavior when content is provided)
        try:
            data = tracker.parse_nutrition_data(content)
            if not data:
                click.echo(ZettlFormatter.error("Invalid nutrition data format. Use 'cal: XXX prot: YYY'"))
                return
                
            # Get current calories/protein values
            calories = data.get('calories', 0)
            protein = data.get('protein', 0)
            
            # Create the note, with optional past date
            note_id = tracker.add_entry(content, past_date=past)
            
            # Determine what day to show in the message
            date_label = f"for {past}" if past else ""
            click.echo(f"Added nutrition entry #{note_id} {date_label}")
            
            # Show today's totals if no past date was specified
            if not past:
                try:
                    today_entries = tracker.get_today_entries()
                    
                    total_calories = sum(entry['nutrition_data'].get('calories', 0) for entry in today_entries)
                    total_protein = sum(entry['nutrition_data'].get('protein', 0) for entry in today_entries)
                    
                    click.echo(f"\nToday's totals so far:")
                    click.echo(f"Calories: {total_calories:.1f}")
                    click.echo(f"Protein: {total_protein:.1f}g")
                except Exception as e:
                    click.echo(f"\nEntry added with:")
                    click.echo(f"Calories: {calories:.1f}")
                    click.echo(f"Protein: {protein:.1f}g")
            else:
                # Just show the entry's values
                click.echo(f"\nEntry added with:")
                click.echo(f"Calories: {calories:.1f}")
                click.echo(f"Protein: {protein:.1f}g")
        except Exception as e:
            click.echo(ZettlFormatter.error(str(e)), err=True)
    else:
        # If no options specified, show today's summary as default behavior
        try:
            summary = tracker.format_today_summary()
            click.echo(summary)
        except Exception as e:
            click.echo(ZettlFormatter.error(str(e)), err=True)

# Add alias 'nut' for nutrition command
@cli.command('nut')
@click.argument('content', required=False)
@click.option('--today', '-t', is_flag=True, help='Show today\'s nutrition summary')
@click.option('--history', '-i', is_flag=True, help='Show nutrition history')
@click.option('--days', '-d', default=7, help='Number of days to show in history')
@click.option('--past', '-p', help='Date for new entry (YYYY-MM-DD format)')
@click.option('--help', '-h', is_flag=True, help='Show detailed help for this command')
def nut_cmd(content, today, history, days, past, help):
    """Alias for nutrition command."""
    # Call the implementation from the nutrition command
    ctx = click.get_current_context()
    return ctx.invoke(nutrition, content=content, today=today, history=history, days=days, past=past, help=help)

if __name__ == '__main__':
    cli()