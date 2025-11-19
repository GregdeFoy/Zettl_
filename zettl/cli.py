# cli.py
import click
import os
import sys
import tempfile
import subprocess
import shutil
from datetime import datetime
import time
from typing import Optional
from zettl.notes import Notes
from zettl.graph import NoteGraph
from zettl.llm import LLMHelper
from zettl.config import APP_NAME, APP_VERSION
from zettl.formatting import ZettlFormatter, console
from rich.markdown import Markdown
import re
import random
from zettl.help import CommandHelp
from zettl.auth import auth as zettl_auth
from datetime import datetime as dt

# Ensure formatter is in CLI mode
ZettlFormatter.set_mode('cli')

# Get authenticated components
def get_notes_manager():
    """Get an authenticated Notes manager."""
    api_key = zettl_auth.require_auth()
    return Notes(api_key=api_key)

def get_graph_manager():
    """Get a graph manager (doesn't need auth currently)."""
    return NoteGraph()

def get_llm_helper():
    """Get an authenticated LLM helper."""
    api_key = zettl_auth.require_auth()
    return LLMHelper(api_key=api_key)

# Define the function that both commands will use
def create_new_note(content, tag, link=None, custom_id=None, auto_tags=None):
    """Create a new note with the given content and optional tags.

    Args:
        content: The note content
        tag: Tuple of tags to add
        link: Tuple of note IDs to link to (from -l flag)
        custom_id: Custom ID for the note
        auto_tags: List of automatic tags (e.g., ['todo'], ['idea'])
    """
    try:
        notes_manager = get_notes_manager()

        # Create note with custom ID if provided
        if custom_id:
            # Use create_note_with_timestamp to set custom ID
            now = dt.now().isoformat()
            note_id = notes_manager.create_note_with_timestamp(content, now, custom_id)
        else:
            note_id = notes_manager.create_note(content)

        click.echo(f"Created note #{note_id}")

        # Collect all tags to add
        all_tags = []
        if auto_tags:
            all_tags.extend(auto_tags)
        if tag:
            all_tags.extend(tag)

        # Batch add all tags at once
        if all_tags:
            try:
                notes_manager.add_tags_batch(note_id, all_tags)
                for t in all_tags:
                    click.echo(f"Added tag '{t}' to note #{note_id}")
            except Exception as e:
                # If batch fails, fall back to individual tags
                click.echo(f"Warning: Batch tag insertion failed, trying individually: {str(e)}", err=True)
                for t in all_tags:
                    try:
                        notes_manager.add_tag(note_id, t)
                        click.echo(f"Added tag '{t}' to note #{note_id}")
                    except Exception as e:
                        click.echo(f"Warning: Could not add tag '{t}': {str(e)}", err=True)

        # Create links if provided via -l option (now supports multiple)
        if link:
            for link_id in link:
                try:
                    notes_manager.create_link(note_id, link_id)
                    click.echo(f"Created link from #{note_id} to #{link_id}")
                except Exception as e:
                    click.echo(f"Warning: Could not create link to note #{link_id}: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Error creating note: {str(e)}", err=True)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=APP_VERSION)
def cli():
    """A Zettelkasten-style note-taking CLI tool."""
    pass

@cli.group(context_settings={'help_option_names': ['-h', '--help']})
def auth():
    """Authentication commands."""
    pass

def show_auth_help_callback(ctx, param, value):
    """Callback to show auth help and exit."""
    if value and not ctx.resilient_parsing:
        from rich.text import Text
        help_text = CommandHelp.get_command_help("auth")
        console.print(Text.from_markup(help_text))
        ctx.exit()

@auth.command()
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_auth_help_callback, help='Show detailed help for this command')
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
            console.print(ZettlFormatter.success("✓ API key saved successfully!"))
            click.echo("You can now use the Zettl CLI.")
        else:
            console.print(ZettlFormatter.error("✗ Failed to save API key"))
    else:
        console.print(ZettlFormatter.error("✗ Invalid API key. Please check and try again."))

@auth.command()
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_auth_help_callback, help='Show detailed help for this command')
def status():
    """Check authentication status."""
    api_key = zettl_auth.get_api_key()
    if api_key:
        if zettl_auth.test_api_key(api_key):
            console.print(ZettlFormatter.success("✓ Authenticated"))
        else:
            console.print(ZettlFormatter.error("✗ API key is invalid or expired"))
    else:
        console.print(ZettlFormatter.warning("⚠ Not authenticated. Run 'zettl auth setup'"))

def show_main_help_callback(ctx, param, value):
    """Callback to show main help and exit."""
    if value and not ctx.resilient_parsing:
        from rich.text import Text
        help_text = CommandHelp.get_main_help()
        console.print(Text.from_markup(help_text))
        ctx.exit()

@cli.command()
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_main_help_callback, help='Show detailed help for this command')
def commands():
    """Show all available commands with examples."""
    # The commands command itself shows the main help, so if --help is passed, show the same
    from rich.text import Text
    help_text = CommandHelp.get_main_help()
    console.print(Text.from_markup(help_text))

def show_help_callback(ctx, param, value):
    """Callback to show help and exit."""
    if value and not ctx.resilient_parsing:
        from rich.text import Text
        help_text = CommandHelp.get_command_help(ctx.info_name)
        console.print(Text.from_markup(help_text))
        ctx.exit()


# Idea command with shortcut 'i'
@cli.command(name='idea')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all ideas (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled ideas')
@click.option('--tag', '-t', multiple=True, help='Filter ideas by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the idea (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def idea_cmd(content, show_all, cancel, tag, link, custom_id):
    """Create or list ideas.

    CREATE MODE (when content provided):
        zt idea "New app concept" -t tech
        zt idea "Feature idea" -l myproject -t important

    LIST MODE (when no content provided):
        zt idea                    # List all active ideas
        zt idea -l myproject       # List ideas linked to note
        zt idea -t tech            # List ideas with tag
    """
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE: has content
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['idea'])
            return

        # LIST MODE: no content
        notes_manager = get_notes_manager()

        # Get all notes tagged with 'idea' along with ALL their tags efficiently
        idea_notes = notes_manager.get_notes_with_all_tags_by_tag('idea')

        if not idea_notes:
            console.print(ZettlFormatter.warning("No ideas found."))
            return

        # Filter by linked notes if -l provided
        if link:
            # Get all notes linked to each specified note
            link_filtered_notes = []
            for link_id in link:
                # Get notes linked to this note
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}

                    # Filter ideas to only those linked to this note
                    for note in idea_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    # If note doesn't exist or has no links, continue
                    pass

            idea_notes = link_filtered_notes

            if not idea_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No ideas found linked to: '{links_str}'."))
                return

        # Apply filters if specified - now using pre-loaded tags
        if tag:
            filters = [f.lower() for f in tag]
            filtered_notes = []

            for note in idea_notes:
                note_tags_lower = [t.lower() for t in note.get('all_tags', [])]

                # Check if all filters are in the note's tags
                if all(f in note_tags_lower for f in filters):
                    filtered_notes.append(note)

            idea_notes = filtered_notes

            if not idea_notes:
                filter_str = "', '".join(tag)
                console.print(ZettlFormatter.warning(f"No ideas found with all tags: '{filter_str}'."))
                return

        # Group notes by their tags (categories) - using pre-loaded tags
        active_ideas_by_category = {}
        done_ideas_by_category = {}
        canceled_ideas_by_category = {}
        uncategorized_active = []
        uncategorized_done = []
        uncategorized_canceled = []

        # Track unique note IDs to count them at the end
        unique_active_ids = set()
        unique_done_ids = set()
        unique_canceled_ids = set()

        for note in idea_notes:
            note_id = note['id']
            note_tags = note.get('all_tags', [])
            tags_lower = [t.lower() for t in note_tags]

            # Check if this is a done idea
            is_done = 'done' in tags_lower

            # Check if this is a canceled idea
            is_canceled = 'cancel' in tags_lower

            # Skip done ideas if not explicitly included
            if is_done and not show_all:
                continue

            # Skip canceled ideas if not explicitly requested
            if is_canceled and not cancel:
                continue

            # Track unique IDs
            if is_canceled:
                unique_canceled_ids.add(note_id)
            elif is_done:
                unique_done_ids.add(note_id)
            else:
                unique_active_ids.add(note_id)

            # Find category tags (everything except 'idea', 'done', 'cancel', and the filter tags)
            excluded_tags = ['idea', 'done', 'cancel']
            if tag:
                excluded_tags.extend([f.lower() for f in tag])

            categories = [t for t in note_tags if t.lower() not in excluded_tags]

            if not categories:
                # This idea has no category tags
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
                    if combined_category not in canceled_ideas_by_category:
                        canceled_ideas_by_category[combined_category] = []
                    canceled_ideas_by_category[combined_category].append(note)
                elif is_done:
                    if combined_category not in done_ideas_by_category:
                        done_ideas_by_category[combined_category] = []
                    done_ideas_by_category[combined_category].append(note)
                else:
                    if combined_category not in active_ideas_by_category:
                        active_ideas_by_category[combined_category] = []
                    active_ideas_by_category[combined_category].append(note)

        # Build the header message
        header_parts = ["Ideas"]
        if tag:
            filter_str = "', '".join(tag)
            header_parts.append(f"tagged with '{filter_str}'")

        # Display ideas by category
        if (not active_ideas_by_category and not uncategorized_active and
            (not show_all or (not done_ideas_by_category and not uncategorized_done)) and
            (not cancel or (not canceled_ideas_by_category and not uncategorized_canceled))):
            console.print(ZettlFormatter.warning("No ideas match your criteria."))
            return

        # Helper function to display a group of ideas
        def display_ideas_group(category_dict, uncategorized_list, header_text):
            if header_text:
                console.print(header_text)

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
                        console.print(f"\n{category_display} ({len(notes)})")
                    else:
                        # For single categories, use the original format
                        console.print(f"\n{ZettlFormatter.tag(category)} ({len(notes)})")

                    for note in notes:
                        formatted_id = ZettlFormatter.note_id(note['id'])

                        # Print note ID on its own line
                        console.print(f"  {formatted_id}:")

                        # Render markdown content
                        content = note['content']
                        md = Markdown(content)
                        console.print(md)
                        console.print("")  # Add an empty line between notes

            if uncategorized_list:
                console.print("\nUncategorized")
                for note in uncategorized_list:
                    formatted_id = ZettlFormatter.note_id(note['id'])

                    # Print note ID on its own line
                    console.print(f"  {formatted_id}:")

                    # Render markdown content
                    content = note['content']
                    md = Markdown(content)
                    console.print(md)
                    console.print("")  # Add an empty line between notes

        # Display active ideas first
        if active_ideas_by_category or uncategorized_active:
            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
            display_ideas_group(active_ideas_by_category, uncategorized_active, active_header)

        # Display all done ideas if requested
        if show_all and (done_ideas_by_category or uncategorized_done):
            done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids)} total)")
            console.print(f"\n{done_header}")
            display_ideas_group(done_ideas_by_category, uncategorized_done, "")

        # Display canceled ideas if requested
        if cancel and (canceled_ideas_by_category or uncategorized_canceled):
            canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
            console.print(f"\n{canceled_header}")
            display_ideas_group(canceled_ideas_by_category, uncategorized_canceled, "")

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Shortcut for idea
@cli.command(name='i')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all ideas (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled ideas')
@click.option('--tag', '-t', multiple=True, help='Filter ideas by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the idea (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def i_cmd(content, show_all, cancel, tag, link, custom_id):
    """Shortcut for 'idea' command."""
    # Duplicate the full idea_cmd logic to avoid Click command invocation issues
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['idea'])
            return

        # LIST MODE
        notes_manager = get_notes_manager()
        idea_notes = notes_manager.get_notes_with_all_tags_by_tag('idea')

        if not idea_notes:
            console.print(ZettlFormatter.warning("No ideas found."))
            return

        # Apply filtering logic
        if link:
            link_filtered_notes = []
            for link_id in link:
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}
                    for note in idea_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    pass
            idea_notes = link_filtered_notes
            if not idea_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No ideas found linked to: '{links_str}'."))
                return

        if tag:
            filters = [f.lower() for f in tag]
            filtered_notes = [note for note in idea_notes if all(f in [t.lower() for t in note.get('all_tags', [])] for f in filters)]
            idea_notes = filtered_notes
            if not idea_notes:
                filter_str = "', '".join(tag)
                console.print(ZettlFormatter.warning(f"No ideas found with all tags: '{filter_str}'."))
                return

        # Call idea_cmd's callback directly by extracting and reusing logic
        # For simplicity, just manually display using same logic as idea_cmd
        # (This avoids the Click command invocation complexity)

        active_ideas = [n for n in idea_notes if 'done' not in [t.lower() for t in n.get('all_tags', [])] and 'cancel' not in [t.lower() for t in n.get('all_tags', [])]]
        if not show_all:
            idea_notes = active_ideas

        if not idea_notes and not cancel:
            console.print(ZettlFormatter.warning("No ideas match your criteria."))
            return

        # Simple display for shortcut
        console.print(ZettlFormatter.header(f"Ideas ({len(idea_notes)} total)"))
        for note in idea_notes:
            formatted_id = ZettlFormatter.note_id(note['id'])
            console.print(f"\n{formatted_id}:")
            md = Markdown(note['content'])
            console.print(md)

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Note command with shortcut 'n'
@cli.command(name='note')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all notes (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled notes')
@click.option('--tag', '-t', multiple=True, help='Filter notes by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the note (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def note_cmd(content, show_all, cancel, tag, link, custom_id):
    """Create or list notes.

    CREATE MODE (when content provided):
        zt note "Meeting notes" -t work
        zt note "Research findings" -l myproject -t research

    LIST MODE (when no content provided):
        zt note                    # List all active notes
        zt note -l myproject       # List notes linked to note
        zt note -t work            # List notes with tag
    """
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE: has content
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['note'])
            return

        # LIST MODE: no content
        notes_manager = get_notes_manager()

        # Get all notes tagged with 'note' along with ALL their tags efficiently
        note_notes = notes_manager.get_notes_with_all_tags_by_tag('note')

        if not note_notes:
            console.print(ZettlFormatter.warning("No notes found."))
            return

        # Filter by linked notes if -l provided
        if link:
            # Get all notes linked to each specified note
            link_filtered_notes = []
            for link_id in link:
                # Get notes linked to this note
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}

                    # Filter notes to only those linked to this note
                    for note in note_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    # If note doesn't exist or has no links, continue
                    pass

            note_notes = link_filtered_notes

            if not note_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No notes found linked to: '{links_str}'."))
                return

        # Apply filters if specified - now using pre-loaded tags
        if tag:
            filters = [f.lower() for f in tag]
            filtered_notes = []

            for note in note_notes:
                note_tags_lower = [t.lower() for t in note.get('all_tags', [])]

                # Check if all filters are in the note's tags
                if all(f in note_tags_lower for f in filters):
                    filtered_notes.append(note)

            note_notes = filtered_notes

            if not note_notes:
                filter_str = "', '".join(tag)
                console.print(ZettlFormatter.warning(f"No notes found with all tags: '{filter_str}'."))
                return

        # Group notes by their tags (categories) - using pre-loaded tags
        active_notes_by_category = {}
        done_notes_by_category = {}
        canceled_notes_by_category = {}
        uncategorized_active = []
        uncategorized_done = []
        uncategorized_canceled = []

        # Track unique note IDs to count them at the end
        unique_active_ids = set()
        unique_done_ids = set()
        unique_canceled_ids = set()

        for note in note_notes:
            note_id = note['id']
            note_tags = note.get('all_tags', [])
            tags_lower = [t.lower() for t in note_tags]

            # Check if this is a done note
            is_done = 'done' in tags_lower

            # Check if this is a canceled note
            is_canceled = 'cancel' in tags_lower

            # Skip done notes if not explicitly included
            if is_done and not show_all:
                continue

            # Skip canceled notes if not explicitly requested
            if is_canceled and not cancel:
                continue

            # Track unique IDs
            if is_canceled:
                unique_canceled_ids.add(note_id)
            elif is_done:
                unique_done_ids.add(note_id)
            else:
                unique_active_ids.add(note_id)

            # Find category tags (everything except 'note', 'done', 'cancel', and the filter tags)
            excluded_tags = ['note', 'done', 'cancel']
            if tag:
                excluded_tags.extend([f.lower() for f in tag])

            categories = [t for t in note_tags if t.lower() not in excluded_tags]

            if not categories:
                # This note has no category tags
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
                    if combined_category not in canceled_notes_by_category:
                        canceled_notes_by_category[combined_category] = []
                    canceled_notes_by_category[combined_category].append(note)
                elif is_done:
                    if combined_category not in done_notes_by_category:
                        done_notes_by_category[combined_category] = []
                    done_notes_by_category[combined_category].append(note)
                else:
                    if combined_category not in active_notes_by_category:
                        active_notes_by_category[combined_category] = []
                    active_notes_by_category[combined_category].append(note)

        # Build the header message
        header_parts = ["Notes"]
        if tag:
            filter_str = "', '".join(tag)
            header_parts.append(f"tagged with '{filter_str}'")

        # Display notes by category
        if (not active_notes_by_category and not uncategorized_active and
            (not show_all or (not done_notes_by_category and not uncategorized_done)) and
            (not cancel or (not canceled_notes_by_category and not uncategorized_canceled))):
            console.print(ZettlFormatter.warning("No notes match your criteria."))
            return

        # Helper function to display a group of notes
        def display_notes_group(category_dict, uncategorized_list, header_text):
            if header_text:
                console.print(header_text)

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
                        console.print(f"\n{category_display} ({len(notes)})")
                    else:
                        # For single categories, use the original format
                        console.print(f"\n{ZettlFormatter.tag(category)} ({len(notes)})")

                    for note in notes:
                        formatted_id = ZettlFormatter.note_id(note['id'])

                        # Print note ID on its own line
                        console.print(f"  {formatted_id}:")

                        # Render markdown content
                        content = note['content']
                        md = Markdown(content)
                        console.print(md)
                        console.print("")  # Add an empty line between notes

            if uncategorized_list:
                console.print("\nUncategorized")
                for note in uncategorized_list:
                    formatted_id = ZettlFormatter.note_id(note['id'])

                    # Print note ID on its own line
                    console.print(f"  {formatted_id}:")

                    # Render markdown content
                    content = note['content']
                    md = Markdown(content)
                    console.print(md)
                    console.print("")  # Add an empty line between notes

        # Display active notes first
        if active_notes_by_category or uncategorized_active:
            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
            display_notes_group(active_notes_by_category, uncategorized_active, active_header)

        # Display all done notes if requested
        if show_all and (done_notes_by_category or uncategorized_done):
            done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids)} total)")
            console.print(f"\n{done_header}")
            display_notes_group(done_notes_by_category, uncategorized_done, "")

        # Display canceled notes if requested
        if cancel and (canceled_notes_by_category or uncategorized_canceled):
            canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
            console.print(f"\n{canceled_header}")
            display_notes_group(canceled_notes_by_category, uncategorized_canceled, "")

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Shortcut for note
@cli.command(name='n')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all notes (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled notes')
@click.option('--tag', '-t', multiple=True, help='Filter notes by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the note (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def n_cmd(content, show_all, cancel, tag, link, custom_id):
    """Shortcut for 'note' command."""
    # Duplicate the full note_cmd logic to avoid Click command invocation issues
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['note'])
            return

        # LIST MODE
        notes_manager = get_notes_manager()
        note_notes = notes_manager.get_notes_with_all_tags_by_tag('note')

        if not note_notes:
            console.print(ZettlFormatter.warning("No notes found."))
            return

        # Apply filtering logic
        if link:
            link_filtered_notes = []
            for link_id in link:
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}
                    for note in note_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    pass
            note_notes = link_filtered_notes
            if not note_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No notes found linked to: '{links_str}'."))
                return

        if tag:
            filters = [f.lower() for f in tag]
            filtered_notes = [note for note in note_notes if all(f in [t.lower() for t in note.get('all_tags', [])] for f in filters)]
            note_notes = filtered_notes
            if not note_notes:
                filter_str = "', '".join(tag)
                console.print(ZettlFormatter.warning(f"No notes found with all tags: '{filter_str}'."))
                return

        # Filter by status
        active_notes = [n for n in note_notes if 'done' not in [t.lower() for t in n.get('all_tags', [])] and 'cancel' not in [t.lower() for t in n.get('all_tags', [])]]
        if not show_all:
            note_notes = active_notes

        if not note_notes and not cancel:
            console.print(ZettlFormatter.warning("No notes match your criteria."))
            return

        # Simple display for shortcut
        console.print(ZettlFormatter.header(f"Notes ({len(note_notes)} total)"))
        for note in note_notes:
            formatted_id = ZettlFormatter.note_id(note['id'])
            console.print(f"\n{formatted_id}:")
            md = Markdown(note['content'])
            console.print(md)

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

def display_project_detail(project_note, project_id, notes_manager, show_all, full, tag_filter):
    """Display detailed project view with categorized linked notes."""
    # Header
    console.print("═" * 63)
    console.print(f"  PROJECT: {project_note['content'].split(chr(10))[0][:40]} (#{project_id})")
    console.print("═" * 63)
    console.print()

    # Project content
    console.print(ZettlFormatter.format_note_display(project_note, notes_manager))

    # Tags
    try:
        tags = notes_manager.get_tags(project_id)
        if tags:
            click.echo(f"Tags: {', '.join(tags)}")
    except Exception:
        pass

    # Get linked notes (bidirectional)
    try:
        linked_notes = notes_manager.get_related_notes(project_id)

        if not linked_notes:
            console.print(ZettlFormatter.warning("No notes linked to this project."))
            return

        # Ensure each note has tags loaded
        for note in linked_notes:
            if 'all_tags' not in note or not note['all_tags']:
                try:
                    note['all_tags'] = notes_manager.get_tags(note['id'])
                except Exception:
                    note['all_tags'] = []

        # Categorize by note type with priority: todo > idea > note
        # This prevents double-counting notes with multiple type tags
        todos = []
        ideas = []
        notes = []

        for n in linked_notes:
            tags_lower = [t.lower() for t in n.get('all_tags', [])]
            if 'todo' in tags_lower:
                todos.append(n)
            elif 'idea' in tags_lower:
                ideas.append(n)
            elif 'note' in tags_lower:
                notes.append(n)

        # Apply tag filter if specified
        if tag_filter:
            filters = [f.lower() for f in tag_filter]
            todos = [n for n in todos if all(f in [t.lower() for t in n.get('all_tags', [])] for f in filters)]
            ideas = [n for n in ideas if all(f in [t.lower() for t in n.get('all_tags', [])] for f in filters)]
            notes = [n for n in notes if all(f in [t.lower() for t in n.get('all_tags', [])] for f in filters)]

        # Categorize by status
        def categorize_by_status(note_list):
            active = []
            done = []
            canceled = []
            for n in note_list:
                tags_lower = [t.lower() for t in n.get('all_tags', [])]
                if 'cancel' in tags_lower:
                    canceled.append(n)
                elif 'done' in tags_lower:
                    done.append(n)
                else:
                    active.append(n)
            return active, done, canceled

        todos_active, todos_done, todos_canceled = categorize_by_status(todos)
        ideas_active, ideas_done, ideas_canceled = categorize_by_status(ideas)
        notes_active, notes_done, notes_canceled = categorize_by_status(notes)

        # Statistics section
        click.echo()
        console.print("─" * 63)
        console.print("  📊 STATISTICS")
        console.print("─" * 63)
        console.print(f"  📋 Todos:  {len(todos_active)} active, {len(todos_done)} done, {len(todos_canceled)} canceled")
        console.print(f"  💡 Ideas:  {len(ideas_active)} active, {len(ideas_done)} done, {len(ideas_canceled)} canceled")
        console.print(f"  📝 Notes:  {len(notes_active)} active, {len(notes_done)} done, {len(notes_canceled)} canceled")
        console.print(f"  {'─' * 9}")
        total_active = len(todos_active) + len(ideas_active) + len(notes_active)
        total_done = len(todos_done) + len(ideas_done) + len(notes_done)
        total_canceled = len(todos_canceled) + len(ideas_canceled) + len(notes_canceled)
        console.print(f"  Total:     {total_active} active, {total_done} done, {total_canceled} canceled")

        # Helper function to group notes by tags
        def group_by_tags(note_list, exclude_tags):
            by_category = {}
            uncategorized = []

            for note in note_list:
                note_tags = note.get('all_tags', [])
                excluded = [t.lower() for t in exclude_tags]

                categories = [t for t in note_tags if t.lower() not in excluded]

                if not categories:
                    uncategorized.append(note)
                else:
                    combined_category = " - ".join(sorted(categories))
                    if combined_category not in by_category:
                        by_category[combined_category] = []
                    by_category[combined_category].append(note)

            return by_category, uncategorized

        # Helper function to display a group of notes
        def display_note_group(note_list, header, emoji, type_tag):
            if not note_list and not show_all:
                return

            click.echo()
            console.print("━" * 63)
            console.print(f"{emoji} {header}")
            console.print("━" * 63)
            click.echo()

            # Exclude tags for grouping
            exclude_tags = [type_tag, 'done', 'cancel', 'project']
            if tag_filter:
                exclude_tags.extend([f.lower() for f in tag_filter])

            by_category, uncategorized = group_by_tags(note_list, exclude_tags)

            # Display categorized notes
            if by_category:
                for category, notes_in_cat in sorted(by_category.items()):
                    # Format category
                    if " - " in category:
                        tags = category.split(" - ")
                        formatted_tags = [ZettlFormatter.tag(t) for t in tags]
                        category_display = " - ".join(formatted_tags)
                        console.print(f"  {category_display} ({len(notes_in_cat)})")
                    else:
                        console.print(f"  {ZettlFormatter.tag(category)} ({len(notes_in_cat)})")

                    for note in notes_in_cat:
                        formatted_id = ZettlFormatter.note_id(note['id'])
                        console.print(f"    {formatted_id}:")

                        if full:
                            # Full content
                            content = note['content']
                            md = Markdown(content)
                            console.print(md)
                            click.echo()
                        else:
                            # Preview
                            content_preview = note['content'][:60] + "..." if len(note['content']) > 60 else note['content']
                            console.print(f"    {content_preview}")

                    click.echo()

            # Display uncategorized
            if uncategorized:
                console.print("  Uncategorized")
                for note in uncategorized:
                    formatted_id = ZettlFormatter.note_id(note['id'])
                    console.print(f"    {formatted_id}:")

                    if full:
                        content = note['content']
                        md = Markdown(content)
                        console.print(md)
                        click.echo()
                    else:
                        content_preview = note['content'][:60] + "..." if len(note['content']) > 60 else note['content']
                        console.print(f"    {content_preview}")

                click.echo()

        # Helper function to display done/canceled sections
        def display_status_section(note_list, status_label):
            if not note_list:
                return

            console.print(f"  ─ {status_label} ({len(note_list)}) ─")
            for note in note_list:
                formatted_id = ZettlFormatter.note_id(note['id'])
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                console.print(f"    {formatted_id}: {content_preview}")
            click.echo()

        # Display todos
        if todos_active or (show_all and (todos_done or todos_canceled)):
            display_note_group(todos_active, f"TODOS ({len(todos_active)} active)", "📋", "todo")

            if show_all:
                if todos_done:
                    display_status_section(todos_done, "Completed")
                if todos_canceled:
                    display_status_section(todos_canceled, "Canceled")

        # Display ideas
        if ideas_active or (show_all and (ideas_done or ideas_canceled)):
            display_note_group(ideas_active, f"IDEAS ({len(ideas_active)})", "💡", "idea")

            if show_all:
                if ideas_done:
                    display_status_section(ideas_done, "Completed")
                if ideas_canceled:
                    display_status_section(ideas_canceled, "Canceled")

        # Display notes
        if notes_active or (show_all and (notes_done or notes_canceled)):
            display_note_group(notes_active, f"NOTES ({len(notes_active)})", "📝", "note")

            if show_all:
                if notes_done:
                    display_status_section(notes_done, "Completed")
                if notes_canceled:
                    display_status_section(notes_canceled, "Canceled")

    except Exception as e:
        console.print(ZettlFormatter.error(f"Error displaying project details: {str(e)}"))

# Project command with shortcut 'p'
@cli.command(name='project')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all notes including done and canceled')
@click.option('--full', '-f', is_flag=True, help='Show full content instead of previews')
@click.option('--tag', '-t', multiple=True, help='Filter linked notes by tag (detail mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Project ID to view details (must be a project)')
@click.option('--id', 'custom_id', help='Custom ID for the project (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def project_cmd(content, show_all, full, tag, link, custom_id):
    """Create, list, or view project details.

    CREATE MODE (when content provided):
        zt project "New Project" -t active
        zt project "Research Phase" --id research-2024

    LIST MODE (when no content and no -l):
        zt project                 # List all projects

    DETAIL VIEW (when -l provided):
        zt project -l myproject    # Show project details with linked notes
        zt project -l myproject -a # Include done/canceled notes
        zt project -l myproject -f # Show full content
    """
    try:
        notes_manager = get_notes_manager()

        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on -l flag and content
        if link:
            # DETAIL VIEW MODE: -l project_id provided
            if len(link) > 1:
                console.print(ZettlFormatter.warning("Please specify only one project to view details."))
                return

            project_id = link[0]
            try:
                # Try to get the project by ID
                project_note = notes_manager.get_note(project_id)
                project_tags = [t.lower() for t in project_note.get('all_tags', [])] if 'all_tags' in project_note else [t.lower() for t in notes_manager.get_tags(project_id)]

                # Verify it's a project
                if 'project' not in project_tags:
                    console.print(ZettlFormatter.error(f"Note '{project_id}' is not a project. Use 'zt show {project_id}' to view it."))
                    return

                # Show detail view
                display_project_detail(project_note, project_id, notes_manager, show_all, full, tag)
                return
            except Exception as e:
                console.print(ZettlFormatter.error(f"Project '{project_id}' not found."))
                return

        if not content_string:
            # LIST MODE: show all projects
            projects = notes_manager.get_notes_with_all_tags_by_tag('project')

            if not projects:
                console.print(ZettlFormatter.warning("No projects found."))
                return

            console.print(ZettlFormatter.header(f"Active Projects ({len(projects)} total)"))
            click.echo()

            # Get all project stats at once from the view
            try:
                all_stats = notes_manager.db.get_project_stats()
                stats_dict = {s['project_id']: s for s in all_stats}
            except Exception as e:
                stats_dict = {}

            for project in projects:
                project_id = project['id']

                # Get stats from the view
                stats_data = stats_dict.get(project_id, {'active_todos': 0, 'active_ideas': 0, 'active_notes': 0})
                todos_count = stats_data.get('active_todos', 0)
                ideas_count = stats_data.get('active_ideas', 0)
                notes_count = stats_data.get('active_notes', 0)

                stats = f"({todos_count} todos, {ideas_count} ideas, {notes_count} notes)"

                # Get content preview
                content_preview = project['content'].split('\n')[0][:60]
                if len(project['content']) > 60:
                    content_preview += "..."

                formatted_id = ZettlFormatter.note_id(project_id)
                console.print(f"  {formatted_id} {stats}: {content_preview}")

            return

        # CREATE MODE: has content
        create_new_note(content_string, tag, (), custom_id=custom_id, auto_tags=['project'])

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Shortcut for project
@cli.command(name='p')
@click.argument('content', nargs=-1, required=False)
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all notes including done and canceled')
@click.option('--full', '-f', is_flag=True, help='Show full content instead of previews')
@click.option('--tag', '-t', multiple=True, help='Filter linked notes by tag (detail mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Project ID to view details (must be a project)')
@click.option('--id', 'custom_id', help='Custom ID for the project (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def p_cmd(content, show_all, full, tag, link, custom_id):
    """Shortcut for 'project' command."""
    # Duplicate the project_cmd logic to avoid Click invocation issues
    try:
        notes_manager = get_notes_manager()

        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on -l flag and content
        if link:
            # DETAIL VIEW MODE: -l project_id provided
            if len(link) > 1:
                console.print(ZettlFormatter.warning("Please specify only one project to view details."))
                return

            project_id = link[0]
            try:
                # Try to get the project by ID
                project_note = notes_manager.get_note(project_id)
                project_tags = [t.lower() for t in project_note.get('all_tags', [])] if 'all_tags' in project_note else [t.lower() for t in notes_manager.get_tags(project_id)]

                # Verify it's a project
                if 'project' not in project_tags:
                    console.print(ZettlFormatter.error(f"Note '{project_id}' is not a project. Use 'zt show {project_id}' to view it."))
                    return

                # Show detail view
                display_project_detail(project_note, project_id, notes_manager, show_all, full, tag)
                return
            except Exception as e:
                console.print(ZettlFormatter.error(f"Project '{project_id}' not found."))
                return

        if not content_string:
            # LIST MODE: simplified for shortcut
            console.print(ZettlFormatter.warning("Use 'zt project' to list all projects"))
            return

        # CREATE MODE: has content
        create_new_note(content_string, tag, (), custom_id=custom_id, auto_tags=['project'])

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Update the list command
@cli.command()
@click.option('--limit', '-l', default=10, help='Number of notes to display')
@click.option('--full', '-f', is_flag=True, help='Show full content of notes')
@click.option('--compact', '-c', is_flag=True, help='Show very compact list (IDs only)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def list(limit, full, compact):
    """List recent notes with formatting options."""

    try:
        notes_manager = get_notes_manager()
        notes = notes_manager.list_notes(limit)
        if not notes:
            click.echo("No notes found.")
            return

        console.print(ZettlFormatter.header(f"Recent Notes (showing {len(notes)} of {len(notes)})"))

        # If full mode, batch fetch all tags for all notes at once
        notes_tags = {}
        if full:
            # Get all note IDs
            note_ids = [note['id'] for note in notes]
            # Batch fetch all tags for these notes
            if note_ids:
                try:
                    all_tags = notes_manager.db.get_tags_for_notes(note_ids)
                    # Group tags by note_id
                    for tag_data in all_tags:
                        note_id = tag_data['note_id']
                        if note_id not in notes_tags:
                            notes_tags[note_id] = []
                        notes_tags[note_id].append(tag_data['tag'])
                except Exception:
                    pass  # Fall back to no tags if batch fetch fails

        for note in notes:
            note_id = note['id']
            created_at = notes_manager.format_timestamp(note['created_at'])

            if compact:
                # Very compact mode - just IDs
                console.print(ZettlFormatter.note_id(note_id))
            elif full:
                # Full content mode
                console.print(ZettlFormatter.format_note_display(note, notes_manager))

                # Add tags if there are any (already fetched)
                tags = notes_tags.get(note_id, [])
                if tags:
                    console.print(f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")

                click.echo()  # Extra line between notes
            else:
                # Default mode - ID, timestamp, and preview
                formatted_id = ZettlFormatter.note_id(note_id)
                formatted_time = ZettlFormatter.timestamp(created_at)
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                console.print(f"{formatted_id} [{formatted_time}]: {content_preview}")
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.argument('note_id')
@click.option('--related', '-r', is_flag=True, help='Show full details of related/connected notes')
@click.option('--full', '-f', is_flag=True, help='Show full content of related notes (only with --related)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def show(note_id, related, full):
    """Display note content, optionally with related notes."""
    try:
        note = get_notes_manager().get_note(note_id)

        # If showing related notes, add a header for the source note
        if related:
            console.print(ZettlFormatter.header(f"Source Note"))

        console.print(ZettlFormatter.format_note_display(note, get_notes_manager()))

        # Show tags if any
        try:
            tags = get_notes_manager().get_tags(note_id)
            if tags:
                click.echo(f"Tags: {', '.join(tags)}")
        except Exception:
            pass

        # Show linked notes
        try:
            linked_notes = get_notes_manager().get_related_notes(note_id)
            if linked_notes:
                if related:
                    # Show full related notes with content
                    click.echo("\n")  # Extra space after source note
                    console.print(ZettlFormatter.header(f"Connected Notes ({len(linked_notes)} total)"))

                    for note in linked_notes:
                        if full:
                            # Full content mode
                            console.print(ZettlFormatter.format_note_display(note, get_notes_manager()))
                            click.echo()  # Extra line between notes
                        else:
                            # Preview mode
                            content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                            formatted_id = ZettlFormatter.note_id(note['id'])
                            console.print(f"{formatted_id}: {content_preview}")
                else:
                    # Just show IDs (original behavior)
                    linked_ids = [note['id'] for note in linked_notes]
                    click.echo(f"Links: {', '.join(linked_ids)}")
        except Exception:
            pass
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.argument('source_id')
@click.argument('target_id')
@click.option('--context', '-c', default="", help='Optional context for the link')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def link(source_id, target_id, context):
    """Create link between notes."""
    try:
        get_notes_manager().create_link(source_id, target_id, context)
        click.echo(f"Created link from #{source_id} to #{target_id}")
    except Exception as e:
        click.echo(f"Error creating link: {str(e)}", err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.argument('tag_string', required=False)
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def tags(note_id, tag_string):
    """Show or add tags to a note. If no note_id is provided, list all tags.

    Usage:
        zt tags                            - List all tags with their counts
        zt tags xyz12                      - Show all tags for note xyz12
        zt tags xyz12 "tag1"               - Add tag1 to note xyz12
        zt tags xyz12 "tag1 tag2 tag3..." - Add multiple tags to note xyz12 (space-separated in quotes)
    """
    try:
        # Handle different argument patterns
        if not note_id:
            # No arguments - list all tags
            tags_with_counts = get_notes_manager().get_all_tags_with_counts()
            if tags_with_counts:
                console.print(ZettlFormatter.header(f"All Tags (showing {len(tags_with_counts)})"))
                for tag_info in tags_with_counts:
                    formatted_tag = ZettlFormatter.tag(tag_info['tag'])
                    console.print(f"{formatted_tag} ({tag_info['count']} notes)")
            else:
                console.print(ZettlFormatter.warning("No tags found."))
            return

        # If tag_string was provided, parse and add tags
        if tag_string:
            # Split the tag string by spaces to get individual tags
            tags = tag_string.split()

            if len(tags) == 1:
                # Single tag - use existing add_tag method
                get_notes_manager().add_tag(note_id, tags[0])
                click.echo(f"Added tag '{tags[0]}' to note #{note_id}")
            else:
                # Multiple tags - use batch method
                get_notes_manager().add_tags_batch(note_id, tags)
                click.echo(f"Added {len(tags)} tags to note #{note_id}: {', '.join(tags)}")

        # Show all tags for the note
        note_tags = get_notes_manager().get_tags(note_id)
        if note_tags:
            console.print(f"Tags for note #{note_id}: {', '.join([ZettlFormatter.tag(t) for t in note_tags])}")
        else:
            click.echo(f"No tags for note #{note_id}")
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.argument('query', required=False)
@click.option('--tag', '-t', multiple=True, help='Search for notes with this tag (can specify multiple, must have ALL)')
@click.option('--exclude-tag', '+t', multiple=True, help='Exclude notes with this tag (can specify multiple, excludes ANY)')
@click.option('--date', '-d', help='Search for notes created on a specific date (YYYY-MM-DD format)')
@click.option('--full', '-f', is_flag=True, help='Show full content of matching notes')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def search(query, tag, exclude_tag, date, full):
    """Search for notes containing text, with specific tags, or by date.

    Multiple tags can be specified:
    - Multiple -t tags: Note must have ALL specified tags (AND logic)
    - Multiple +t tags: Note must not have ANY specified tags (OR logic for exclusion)
    """
    try:
        notes_manager = get_notes_manager()
        results = []
        search_description = []

        # Step 1: Get initial result set based on primary criteria
        if date:
            # Search by date
            try:
                results = notes_manager.search_notes_by_date(date)
                if not results:
                    console.print(ZettlFormatter.warning(f"No notes found for date '{date}'"))
                    return
                search_description.append(f"created on '{date}'")
            except ValueError as e:
                console.print(ZettlFormatter.error(str(e)))
                return
        elif query:
            # Search by content
            results = notes_manager.search_notes(query)
            if not results:
                console.print(ZettlFormatter.warning(f"No notes found containing '{query}'"))
                return
            search_description.append(f"containing '{query}'")
        else:
            # No primary search criteria - start with all notes
            # If we have any tag filters, we need to search ALL notes
            if tag or exclude_tag:
                results = notes_manager.list_notes(limit=10000)
            else:
                # No filters at all - just list recent notes
                results = notes_manager.list_notes(limit=50)
                console.print(ZettlFormatter.header(f"Listing notes (showing {len(results)}):"))

        # Step 2: Apply include tag filters (must have ALL specified tags)
        if tag:
            # Get note IDs for each required tag
            tag_note_sets = []
            for t in tag:
                tag_notes = notes_manager.get_notes_by_tag(t)
                tag_note_ids = {note['id'] for note in tag_notes}
                tag_note_sets.append(tag_note_ids)

            # Find intersection - notes that have ALL required tags
            if tag_note_sets:
                required_ids = set.intersection(*tag_note_sets) if tag_note_sets else set()

                # Filter results to only include notes with ALL required tags
                original_count = len(results)
                results = [note for note in results if note['id'] in required_ids]

                tags_str = "', '".join(tag)
                search_description.append(f"with tags '{tags_str}'")

                if not results and original_count > 0:
                    console.print(ZettlFormatter.warning(f"No notes found with all tags: '{tags_str}'"))
                    return

        # Step 3: Apply exclude tag filters (must not have ANY excluded tags)
        if exclude_tag:
            # Get note IDs for each excluded tag
            excluded_ids = set()
            for et in exclude_tag:
                excluded_notes = notes_manager.get_notes_by_tag(et)
                excluded_ids.update(note['id'] for note in excluded_notes)

            # Filter out notes with ANY excluded tag
            original_count = len(results)
            results = [note for note in results if note['id'] not in excluded_ids]

            excluded_tags_str = "', '".join(exclude_tag)

            if original_count != len(results):
                console.print(ZettlFormatter.info(f"Excluded {original_count - len(results)} notes with tags: '{excluded_tags_str}'"))
        
        # Build and display search header
        if search_description or tag or exclude_tag:
            header_msg = f"Found {len(results)} notes"
            if search_description:
                header_msg += f" {' and '.join(search_description)}"
            console.print(ZettlFormatter.header(header_msg))

        # Display the final results
        if not results:
            console.print(ZettlFormatter.warning("No notes match your criteria after filtering."))
            return

        for note in results:
            if full:
                # Full content mode
                console.print(ZettlFormatter.format_note_display(note, get_notes_manager()))
                
                # Add tags if there are any
                try:
                    tags = get_notes_manager().get_tags(note['id'])
                    if tags:
                        console.print(f"Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
                except Exception:
                    pass
                
                click.echo()  # Extra line between notes
            else:
                # Preview mode
                content_preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                if query:
                    # Highlight the query in the preview with bold yellow
                    pattern = re.compile(re.escape(query), re.IGNORECASE)
                    content_preview = pattern.sub(r"[bold yellow]\g<0>[/bold yellow]", content_preview)

                formatted_id = ZettlFormatter.note_id(note['id'])
                console.print(f"{formatted_id}: {content_preview}")
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.argument('note_id', required=False)
@click.option('--output', '-o', default='zettl_graph.json', help='Output file for graph data')
@click.option('--depth', '-d', default=2, help='How many levels of connections to include')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def graph(note_id, output, depth):
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
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def llm(note_id, action, count, show_source):
    """Use Claude AI to analyze and enhance notes."""
    try:
        # Show the source note if requested
        if show_source:
            try:
                source_note = get_notes_manager().get_note(note_id)
                console.print(ZettlFormatter.header("Source Note"))
                console.print(ZettlFormatter.format_note_display(source_note, get_notes_manager()))
                click.echo("\n")  # Extra space after source note
            except Exception as e:
                console.print(ZettlFormatter.warning(f"Could not display source note: {str(e)}"))
        
        if action == 'summarize':
            console.print(ZettlFormatter.header(f"AI Summary for Note #{note_id}"))
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating summary') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                summary = get_llm_helper().summarize_note(note_id)

            console.print()
            md = Markdown(summary)
            console.print(md)
            
        elif action == 'connect':
            console.print(ZettlFormatter.header(f"AI-Suggested Connections for Note #{note_id}"))

            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Finding connections') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                connections = get_llm_helper().generate_connections(note_id, count)

            if not connections:
                console.print(ZettlFormatter.warning("No potential connections found."))
                return

            for conn in connections:
                conn_id = conn['note_id']
                formatted_id = ZettlFormatter.note_id(conn_id)
                console.print(f"\n{formatted_id}")
                # Render explanation as markdown with indentation
                explanation_md = Markdown(conn['explanation'])
                console.print(explanation_md)

                # Try to show a preview of the connected note
                try:
                    conn_note = get_notes_manager().get_note(conn_id)
                    content_preview = conn_note['content'][:100] + "..." if len(conn_note['content']) > 100 else conn_note['content']
                    console.print(f"  [cyan]Preview:[/cyan] {content_preview}")

                    # Add option to link notes
                    if click.confirm(f"\nCreate link from #{note_id} to #{conn_id}?"):
                        get_notes_manager().create_link(note_id, conn_id, conn['explanation'])
                        console.print(ZettlFormatter.success(f"Created link from #{note_id} to #{conn_id}"))
                except Exception:
                    pass
            
        elif action == 'tags':
            console.print(ZettlFormatter.header(f"AI-Suggested Tags for Note #{note_id}"))
            
            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating tags') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                tags = get_llm_helper().suggest_tags(note_id, count)
            
            if not tags:
                console.print(ZettlFormatter.warning("No tags suggested."))
                return
                
            click.echo("\nSuggested tags:")
            for tag in tags:
                formatted_tag = ZettlFormatter.tag(tag)
                console.print(f"{formatted_tag}")
                
            # Ask if user wants to add these tags
            if click.confirm("\nWould you like to add these tags to the note?"):
                for tag in tags:
                    try:
                        get_notes_manager().add_tag(note_id, tag)
                        console.print(ZettlFormatter.success(f"Added tag '{tag}' to note #{note_id}"))
                    except Exception as e:
                        console.print(ZettlFormatter.error(f"Error adding tag '{tag}': {str(e)}"), err=True)

        elif action == 'expand':
            console.print(ZettlFormatter.header(f"AI-Expanded Version of Note #{note_id}"))

            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Expanding note') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                expanded_content = get_llm_helper().expand_note(note_id)

            console.print()
            md = Markdown(expanded_content)
            console.print(md)
            
            # Ask if user wants to create a new note with the expanded content
            if click.confirm("\nCreate a new note with this expanded content?"):
                try:
                    # Create new note with expanded content
                    new_note_id = get_notes_manager().create_note(expanded_content)
                    console.print(ZettlFormatter.success(f"Created expanded note #{new_note_id}"))
                    
                    # Create link from original to expanded note
                    get_notes_manager().create_link(note_id, new_note_id, "Expanded version")
                    console.print(ZettlFormatter.success(f"Linked original #{note_id} to expanded #{new_note_id}"))
                    
                    # Copy tags from original note to new note
                    try:
                        original_tags = get_notes_manager().get_tags(note_id)
                        for tag in original_tags:
                            get_notes_manager().add_tag(new_note_id, tag)
                        if original_tags:
                            console.print(ZettlFormatter.success(f"Copied {len(original_tags)} tags to new note"))
                    except Exception:
                        pass
                except Exception as e:
                    console.print(ZettlFormatter.error(f"Error creating expanded note: {str(e)}"), err=True)
        
        elif action == 'concepts':
            console.print(ZettlFormatter.header(f"Key Concepts from Note #{note_id}"))

            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Extracting concepts') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                concepts = get_llm_helper().extract_key_concepts(note_id, count)

            if not concepts:
                console.print(ZettlFormatter.warning("No key concepts identified."))
                return

            for i, concept in enumerate(concepts, 1):
                console.print(f"\n[bold cyan]{i}. {concept['concept']}[/bold cyan]")
                # Render explanation as markdown
                explanation_md = Markdown(concept['explanation'])
                console.print(explanation_md)
                
                # Ask if user wants to create a new note for this concept
                if click.confirm(f"\nCreate a new note for the concept '{concept['concept']}'?"):
                    try:
                        # Prepare content for the new note
                        concept_content = f"{concept['concept']}\n\n{concept['explanation']}"
                        
                        # Create new note
                        new_note_id = get_notes_manager().create_note(concept_content)
                        console.print(ZettlFormatter.success(f"Created concept note #{new_note_id}"))
                        
                        # Create link from original to concept note
                        get_notes_manager().create_link(note_id, new_note_id, f"Concept: {concept['concept']}")
                        console.print(ZettlFormatter.success(f"Linked original #{note_id} to concept #{new_note_id}"))
                    except Exception as e:
                        console.print(ZettlFormatter.error(f"Error creating concept note: {str(e)}"), err=True)
        
        elif action == 'questions':
            console.print(ZettlFormatter.header(f"Thought-Provoking Questions from Note #{note_id}"))

            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Generating questions') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                questions = get_llm_helper().generate_question_note(note_id, count)

            if not questions:
                console.print(ZettlFormatter.warning("No questions generated."))
                return

            for i, question in enumerate(questions, 1):
                console.print(f"\n[bold cyan]{i}. {question['question']}[/bold cyan]")
                # Render explanation as markdown
                explanation_md = Markdown(question['explanation'])
                console.print(explanation_md)
                
                # Ask if user wants to create a new note for this question
                if click.confirm(f"\nCreate a new note for this question?"):
                    try:
                        # Prepare content for the new note
                        question_content = f"{question['question']}\n\n{question['explanation']}"
                        
                        # Create new note
                        new_note_id = get_notes_manager().create_note(question_content)
                        console.print(ZettlFormatter.success(f"Created question note #{new_note_id}"))
                        
                        # Create link from original to question note
                        get_notes_manager().create_link(note_id, new_note_id, "Question derived from this note")
                        console.print(ZettlFormatter.success(f"Linked original #{note_id} to question #{new_note_id}"))
                    except Exception as e:
                        console.print(ZettlFormatter.error(f"Error creating question note: {str(e)}"), err=True)
        
        elif action == 'critique':
            console.print(ZettlFormatter.header(f"AI Critique of Note #{note_id}"))

            # Show a spinner while the LLM is working
            with click.progressbar(length=100, label='Analyzing note') as bar:
                for i in range(100):
                    bar.update(1)
                    time.sleep(0.01)
                critique = get_llm_helper().critique_note(note_id)

            # Display strengths
            if critique['strengths']:
                console.print(f"\n[bold green]Strengths:[/bold green]")
                for strength in critique['strengths']:
                    console.print(f"  • {strength}")

            # Display weaknesses
            if critique['weaknesses']:
                console.print(f"\n[bold yellow]Areas for Improvement:[/bold yellow]")
                for weakness in critique['weaknesses']:
                    console.print(f"  • {weakness}")

            # Display suggestions
            if critique['suggestions']:
                console.print(f"\n[bold cyan]Suggestions:[/bold cyan]")
                for suggestion in critique['suggestions']:
                    console.print(f"  • {suggestion}")

            # If no structured feedback was generated
            if not (critique['strengths'] or critique['weaknesses'] or critique['suggestions']):
                console.print(ZettlFormatter.warning("Could not generate structured feedback for this note."))
                
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.argument('note_id')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.option('--keep-links', is_flag=True, help='Keep links to and from this note')
@click.option('--keep-tags', is_flag=True, help='Keep tags associated with this note')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def delete(note_id, force, keep_links, keep_tags):
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
            console.print(ZettlFormatter.header(f"Note to delete: #{note_id}"))
            content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
            click.echo(f"Content: {content_preview}")
            click.echo(f"Associated tags: {tag_count}")
            click.echo(f"Connected notes: {link_count}")
            
        except Exception as e:
            if not force:
                console.print(ZettlFormatter.warning(f"Could not retrieve note: {str(e)}"))
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
        
        console.print(ZettlFormatter.success(f"Deleted note #{note_id}"))
        
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error deleting note: {str(e)}"), err=True)

@cli.command()
@click.argument('note_id')
@click.argument('tag')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def untag(note_id, tag):
    """Remove a tag from a note."""
    try:
        get_notes_manager().delete_tag(note_id, tag)
        console.print(ZettlFormatter.success(f"Removed tag '{tag}' from note #{note_id}"))
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error removing tag: {str(e)}"), err=True)

@cli.command()
@click.argument('source_id')
@click.argument('target_id')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def unlink(source_id, target_id):
    """Remove a link between two notes."""
    try:
        get_notes_manager().delete_link(source_id, target_id)
        console.print(ZettlFormatter.success(f"Removed link from note #{source_id} to note #{target_id}"))
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error removing link: {str(e)}"), err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.argument('text', required=False)
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def append(note_id, text):
    """Append text to the end of a note."""
    if not note_id or not text:
        console.print(ZettlFormatter.error("Error: Missing required arguments NOTE_ID and TEXT"), err=True)
        click.echo("Usage: zettl append NOTE_ID TEXT")
        click.echo("Try 'zettl append -h' for help")
        return

    try:
        notes_manager = get_notes_manager()
        notes_manager.append_to_note(note_id, text)
        console.print(ZettlFormatter.success(f"Appended text to note #{note_id}"))
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error appending to note: {str(e)}"), err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.argument('text', required=False)
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def prepend(note_id, text):
    """Prepend text to the beginning of a note."""
    if not note_id or not text:
        console.print(ZettlFormatter.error("Error: Missing required arguments NOTE_ID and TEXT"), err=True)
        click.echo("Usage: zettl prepend NOTE_ID TEXT")
        click.echo("Try 'zettl prepend -h' for help")
        return

    try:
        notes_manager = get_notes_manager()
        notes_manager.prepend_to_note(note_id, text)
        console.print(ZettlFormatter.success(f"Prepended text to note #{note_id}"))
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error prepending to note: {str(e)}"), err=True)

@cli.command()
@click.argument('note_id', required=False)
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def edit(note_id):
    """Edit a note using your system's default editor."""
    if not note_id:
        console.print(ZettlFormatter.error("Error: Missing required argument NOTE_ID"), err=True)
        click.echo("Usage: zettl edit NOTE_ID")
        click.echo("Try 'zettl edit -h' for help")
        return

    try:
        notes_manager = get_notes_manager()

        # Get the current note
        note = notes_manager.db.get_note(note_id)
        current_content = note['content']

        # Platform-specific editing
        if sys.platform == 'win32':
            # Windows: Use notepad
            editor = os.environ.get('EDITOR', 'notepad')

            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                temp_path = f.name
                f.write(current_content)

            try:
                # Run editor
                if editor == 'notepad':
                    subprocess.call([editor, temp_path])
                else:
                    # Handle editors with arguments
                    subprocess.call(editor + ' ' + temp_path, shell=True)

                # Read edited content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    new_content = f.read()
            finally:
                # Clean up temp file
                os.unlink(temp_path)
        else:
            # Unix/Linux/Mac: Try nvim first, then nano
            if shutil.which('nvim'):
                editor = 'nvim'
            elif shutil.which('nano'):
                editor = 'nano'
            else:
                raise FileNotFoundError("No suitable editor found. Please install nvim or nano.")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                temp_path = f.name
                f.write(current_content)

            try:
                # Run editor
                subprocess.call([editor, temp_path])

                # Read edited content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    new_content = f.read()
            finally:
                # Clean up temp file
                os.unlink(temp_path)

        # Check if content changed
        if new_content.strip() == current_content.strip():
            console.print(ZettlFormatter.info("No changes made"))
            return

        # Update the note
        notes_manager.update_note(note_id, new_content)
        console.print(ZettlFormatter.success(f"Updated note #{note_id}"))

    except FileNotFoundError:
        console.print(ZettlFormatter.error(f"Editor not found. Set EDITOR environment variable."), err=True)
    except Exception as e:
        console.print(ZettlFormatter.error(f"Error editing note: {str(e)}"), err=True)

@cli.command()
@click.argument('note_ids', nargs=-1, required=False)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def merge(note_ids, force):
    """Merge multiple notes into a single note.

    This command combines the content of multiple notes, preserves all tags
    and external links, and deletes the original notes.

    Usage: zettl merge NOTE_ID1 NOTE_ID2 [NOTE_ID3 ...]
    """

    try:
        # Validate we have at least 2 notes
        if not note_ids or len(note_ids) < 2:
            console.print(ZettlFormatter.error("Must provide at least 2 notes to merge"))
            return

        # Show preview of notes to be merged
        console.print(ZettlFormatter.header(f"Notes to merge ({len(note_ids)} total):"))
        notes_manager = get_notes_manager()

        all_tags = set()
        for note_id in note_ids:
            try:
                note = notes_manager.get_note(note_id)
                content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                formatted_id = ZettlFormatter.note_id(note_id)
                console.print(f"\n{formatted_id}")
                click.echo(f"  {content_preview}")

                # Show tags
                try:
                    tags = notes_manager.get_tags(note_id)
                    if tags:
                        all_tags.update(tags)
                        console.print(f"  Tags: {', '.join([ZettlFormatter.tag(t) for t in tags])}")
                except Exception:
                    pass

            except Exception as e:
                console.print(ZettlFormatter.error(f"Error fetching note {note_id}: {str(e)}"), err=True)
                return

        # Show what will be preserved
        if all_tags:
            console.print(f"\n{ZettlFormatter.header('Tags that will be added to merged note:')}")
            console.print(f"{', '.join([ZettlFormatter.tag(t) for t in sorted(all_tags)])}")

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

        console.print(ZettlFormatter.success(f"\nSuccessfully merged {len(note_ids)} notes into #{merged_note_id}"))
        click.echo(f"\nView merged note with: zettl show {merged_note_id}")

    except Exception as e:
        console.print(ZettlFormatter.error(f"Error merging notes: {str(e)}"), err=True)

@cli.command(name='todo')
@click.argument('content', nargs=-1, required=False)
@click.option('--donetoday', '-dt', is_flag=True, help='List todos that were completed today')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all todos (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled todos')
@click.option('--tag', '-t', multiple=True, help='Filter todos by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the todo (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def todo_cmd(content, donetoday, show_all, cancel, tag, link, custom_id):
    """Create or list todos.

    CREATE MODE (when content provided):
        zt todo "Buy milk" -t shopping
        zt todo "Fix bug" -l myproject -t urgent

    LIST MODE (when no content provided):
        zt todo                    # List all active todos
        zt todo -l myproject       # List todos linked to note
        zt todo -t urgent          # List todos with tag
    """
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE: has content
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['todo'])
            return

        # LIST MODE: no content
        notes_manager = get_notes_manager()

        # Get all notes tagged with 'todo' along with ALL their tags efficiently
        todo_notes = notes_manager.get_notes_with_all_tags_by_tag('todo')

        if not todo_notes:
            console.print(ZettlFormatter.warning("No todos found."))
            return

        # Filter for todos completed today if requested
        if donetoday:
            done_today_data = notes_manager.get_tags_created_today('done')
            if not done_today_data:
                console.print(ZettlFormatter.warning("No todos completed today."))
                return

            # Extract note IDs from the done today data
            done_today_ids = {item['note_id'] for item in done_today_data}

            # Filter todo_notes to only include those completed today
            todo_notes = [note for note in todo_notes if note['id'] in done_today_ids]

            if not todo_notes:
                console.print(ZettlFormatter.warning("No todos completed today."))
                return

        # Filter by linked notes if -l provided
        if link:
            # Get all notes linked to each specified note
            link_filtered_notes = []
            for link_id in link:
                # Get notes linked to this note
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}

                    # Filter todos to only those linked to this note
                    for note in todo_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    # If note doesn't exist or has no links, continue
                    pass

            todo_notes = link_filtered_notes

            if not todo_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No todos found linked to: '{links_str}'."))
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
                console.print(ZettlFormatter.warning(f"No todos found with all tags: '{filter_str}'."))
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
            console.print(ZettlFormatter.warning("No todos match your criteria."))
            return

        # Helper function to display a group of todos
        def display_todos_group(category_dict, uncategorized_list, header_text):
            if header_text:
                console.print(header_text)

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
                        console.print(f"\n{category_display} ({len(notes)})")
                    else:
                        # For single categories, use the original format
                        console.print(f"\n{ZettlFormatter.tag(category)} ({len(notes)})")

                    for note in notes:
                        formatted_id = ZettlFormatter.note_id(note['id'])

                        # Print note ID on its own line
                        console.print(f"  {formatted_id}:")

                        # Render markdown content
                        content = note['content']
                        md = Markdown(content)
                        console.print(md)
                        console.print("")  # Add an empty line between notes

            if uncategorized_list:
                console.print("\nUncategorized")
                for note in uncategorized_list:
                    formatted_id = ZettlFormatter.note_id(note['id'])

                    # Print note ID on its own line
                    console.print(f"  {formatted_id}:")

                    # Render markdown content
                    content = note['content']
                    md = Markdown(content)
                    console.print(md)
                    console.print("")  # Add an empty line between notes

        # Display active todos first
        if active_todos_by_category or uncategorized_active:
            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
            display_todos_group(active_todos_by_category, uncategorized_active, active_header)

        # Display all done todos if requested
        if (show_all or donetoday) and (done_todos_by_category or uncategorized_done):
            done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids)} total)")
            console.print(f"\n{done_header}")
            display_todos_group(done_todos_by_category, uncategorized_done, "")

        # Display canceled todos if requested
        if cancel and (canceled_todos_by_category or uncategorized_canceled):
            canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
            console.print(f"\n{canceled_header}")
            display_todos_group(canceled_todos_by_category, uncategorized_canceled, "")

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

# Shortcut for todo
@cli.command(name='t')
@click.argument('content', nargs=-1, required=False)
@click.option('--donetoday', '-dt', is_flag=True, help='List todos that were completed today')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all todos (both active and completed)')
@click.option('--cancel', '-c', is_flag=True, help='Show canceled todos')
@click.option('--tag', '-t', multiple=True, help='Filter todos by tag (list mode) or add tags (create mode)')
@click.option('--link', '-l', multiple=True, help='Note ID to link to (create mode) or filter by (list mode)')
@click.option('--id', 'custom_id', help='Custom ID for the todo (create mode only, must be unique)')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def t_cmd(content, donetoday, show_all, cancel, tag, link, custom_id):
    """Shortcut for 'todo' command."""
    try:
        # Join content into a string
        content_string = ' '.join(content) if content else ''

        # Determine mode based on content
        if content_string:
            # CREATE MODE: has content
            create_new_note(content_string, tag, link, custom_id=custom_id, auto_tags=['todo'])
            return

        # LIST MODE: no content
        notes_manager = get_notes_manager()

        # Get all notes tagged with 'todo' along with ALL their tags efficiently
        todo_notes = notes_manager.get_notes_with_all_tags_by_tag('todo')

        if not todo_notes:
            console.print(ZettlFormatter.warning("No todos found."))
            return

        # Filter for todos completed today if requested
        if donetoday:
            done_today_data = notes_manager.get_tags_created_today('done')
            if not done_today_data:
                console.print(ZettlFormatter.warning("No todos completed today."))
                return

            # Extract note IDs from the done today data
            done_today_ids = {item['note_id'] for item in done_today_data}

            # Filter todo_notes to only include those completed today
            todo_notes = [note for note in todo_notes if note['id'] in done_today_ids]

            if not todo_notes:
                console.print(ZettlFormatter.warning("No todos completed today."))
                return

        # Filter by linked notes if -l provided
        if link:
            # Get all notes linked to each specified note
            link_filtered_notes = []
            for link_id in link:
                # Get notes linked to this note
                try:
                    linked_notes = notes_manager.get_related_notes(link_id)
                    linked_note_ids = {note['id'] for note in linked_notes}

                    # Filter todos to only those linked to this note
                    for note in todo_notes:
                        if note['id'] in linked_note_ids:
                            if note not in link_filtered_notes:
                                link_filtered_notes.append(note)
                except Exception:
                    # If note doesn't exist or has no links, continue
                    pass

            todo_notes = link_filtered_notes

            if not todo_notes:
                links_str = "', '".join(link)
                console.print(ZettlFormatter.warning(f"No todos found linked to: '{links_str}'."))
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
                console.print(ZettlFormatter.warning(f"No todos found with all tags: '{filter_str}'."))
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
            console.print(ZettlFormatter.warning("No todos match your criteria."))
            return

        # Helper function to display a group of todos
        def display_todos_group(category_dict, uncategorized_list, header_text):
            if header_text:
                console.print(header_text)

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
                        console.print(f"\n{category_display} ({len(notes)})")
                    else:
                        # For single categories, use the original format
                        console.print(f"\n{ZettlFormatter.tag(category)} ({len(notes)})")

                    for note in notes:
                        formatted_id = ZettlFormatter.note_id(note['id'])

                        # Print note ID on its own line
                        console.print(f"  {formatted_id}:")

                        # Render markdown content
                        content = note['content']
                        md = Markdown(content)
                        console.print(md)
                        console.print("")  # Add an empty line between notes

            if uncategorized_list:
                console.print("\nUncategorized")
                for note in uncategorized_list:
                    formatted_id = ZettlFormatter.note_id(note['id'])

                    # Print note ID on its own line
                    console.print(f"  {formatted_id}:")

                    # Render markdown content
                    content = note['content']
                    md = Markdown(content)
                    console.print(md)
                    console.print("")  # Add an empty line between notes

        # Display active todos first
        if active_todos_by_category or uncategorized_active:
            active_header = ZettlFormatter.header(f"Active {' '.join(header_parts)} ({len(unique_active_ids)} total)")
            display_todos_group(active_todos_by_category, uncategorized_active, active_header)

        # Display all done todos if requested
        if (show_all or donetoday) and (done_todos_by_category or uncategorized_done):
            done_header = ZettlFormatter.header(f"Completed {' '.join(header_parts)} ({len(unique_done_ids)} total)")
            console.print(f"\n{done_header}")
            display_todos_group(done_todos_by_category, uncategorized_done, "")

        # Display canceled todos if requested
        if cancel and (canceled_todos_by_category or uncategorized_canceled):
            canceled_header = ZettlFormatter.header(f"Canceled {' '.join(header_parts)} ({len(unique_canceled_ids)} total)")
            console.print(f"\n{canceled_header}")
            display_todos_group(canceled_todos_by_category, uncategorized_canceled, "")

    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))

@cli.command()
@click.option('--source', '-s', is_flag=True, help='Show the source note ID')
@click.option('--help', '-h', is_flag=True, is_eager=True, expose_value=False, callback=show_help_callback, help='Show detailed help for this command')
def rules(source):
    """Display a random rule from notes tagged with 'rules'."""
    try:
        # Get all notes tagged with 'rules'
        rules_notes = get_notes_manager().get_notes_by_tag('rules')
        
        if not rules_notes:
            console.print(ZettlFormatter.warning("No notes found with tag 'rules'"))
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
            console.print(ZettlFormatter.warning("Couldn't extract any rules from the notes"))
            return
            
        # Select a random rule
        random_rule = random.choice(all_rules)
        
        # Display the rule
        console.print(ZettlFormatter.header("Random Rule"))

        if source:
            # Show the source note ID
            console.print(f"Source: {ZettlFormatter.note_id(random_rule['note_id'])}\n")

        # Always show the full rule with markdown rendering
        md = Markdown(random_rule['full_text'])
        console.print(md)
            
    except Exception as e:
        console.print(ZettlFormatter.error(str(e)))


if __name__ == '__main__':
    cli()