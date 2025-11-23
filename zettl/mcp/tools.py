"""
MCP Tools for Zettl
Tools for accessing and modifying note data via Model Context Protocol
"""

from typing import List, Dict, Any
from zettl.database import Database


class ZettlMCPTools:
    """
    Collection of MCP tools for Zettl (read and write operations)

    All tools use the existing Database class to ensure
    consistent behavior with the rest of the application.
    """

    def __init__(self, jwt_token: str):
        """
        Initialize tools with authentication

        Args:
            jwt_token: JWT token for database authentication
        """
        self.db = Database(jwt_token=jwt_token)

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for notes containing the query string

        Args:
            query: Search query string

        Returns:
            List of notes matching the query
        """
        try:
            results = self.db.search_notes(query)
            # Format for better MCP consumption
            return [{
                'id': note['id'],
                'content': note['content'][:500] + ('...' if len(note['content']) > 500 else ''),
                'created_at': self.db.format_timestamp(note['created_at']),
                'full_content': note['content']
            } for note in results]
        except Exception as e:
            return {'error': str(e)}

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """
        Get a specific note by ID

        Args:
            note_id: Note ID

        Returns:
            Note data including content, timestamps, tags, and links
        """
        try:
            note = self.db.get_note(note_id)

            # Get tags and links
            tags = self.db.get_tags(note_id)
            related_notes = self.db.get_related_notes(note_id)

            return {
                'id': note['id'],
                'content': note['content'],
                'created_at': self.db.format_timestamp(note['created_at']),
                'modified_at': self.db.format_timestamp(note['modified_at']),
                'tags': tags,
                'linked_notes': [n['id'] for n in related_notes]
            }
        except Exception as e:
            return {'error': str(e)}

    def list_recent_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent notes

        Args:
            limit: Maximum number of notes to return (default 10, max 50)

        Returns:
            List of recent notes
        """
        try:
            # Cap limit at 50 to avoid overwhelming responses
            limit = min(limit, 50)

            notes = self.db.list_notes(limit=limit)

            return [{
                'id': note['id'],
                'content': note['content'][:200] + ('...' if len(note['content']) > 200 else ''),
                'created_at': self.db.format_timestamp(note['created_at'])
            } for note in notes]
        except Exception as e:
            return {'error': str(e)}

    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get all notes with a specific tag

        Args:
            tag: Tag to search for

        Returns:
            List of notes with the tag
        """
        try:
            notes = self.db.get_notes_with_all_tags_by_tag(tag)

            return [{
                'id': note['id'],
                'content': note['content'][:200] + ('...' if len(note['content']) > 200 else ''),
                'created_at': self.db.format_timestamp(note['created_at']),
                'tags': note.get('all_tags', [])
            } for note in notes]
        except Exception as e:
            return {'error': str(e)}

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags with their usage counts

        Returns:
            List of tags with counts
        """
        try:
            tags = self.db.get_all_tags_with_counts()
            return tags
        except Exception as e:
            return {'error': str(e)}

    def get_related_notes(self, note_id: str) -> List[Dict[str, Any]]:
        """
        Get all notes linked to a specific note

        Args:
            note_id: Note ID

        Returns:
            List of related notes
        """
        try:
            related = self.db.get_related_notes(note_id)

            return [{
                'id': note['id'],
                'content': note['content'][:200] + ('...' if len(note['content']) > 200 else ''),
                'created_at': self.db.format_timestamp(note['created_at'])
            } for note in related]
        except Exception as e:
            return {'error': str(e)}

    def search_notes_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Search for notes created on a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of notes created on that date
        """
        try:
            notes = self.db.search_notes_by_date(date)

            return [{
                'id': note['id'],
                'content': note['content'][:200] + ('...' if len(note['content']) > 200 else ''),
                'created_at': self.db.format_timestamp(note['created_at'])
            } for note in notes]
        except Exception as e:
            return {'error': str(e)}

    # WRITE OPERATIONS

    def create_note(self, content: str, tags: List[str] = None) -> Dict[str, Any]:
        """
        Create a new note

        Args:
            content: Note content
            tags: Optional list of tags to add

        Returns:
            Dict with note_id and success status
        """
        try:
            note_id = self.db.create_note(content)

            # Add tags if provided
            if tags:
                for tag in tags:
                    self.db.add_tag(note_id, tag)

            return {
                'success': True,
                'note_id': note_id,
                'message': f'Created note {note_id}' + (f' with tags: {", ".join(tags)}' if tags else '')
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def append_to_note(self, note_id: str, content: str) -> Dict[str, Any]:
        """
        Append content to an existing note

        Args:
            note_id: ID of the note to append to
            content: Content to append

        Returns:
            Dict with success status
        """
        try:
            # Get current note
            note = self.db.get_note(note_id)

            # Append new content
            updated_content = note['content'] + '\n' + content

            # Update note
            self.db.update_note(note_id, updated_content)

            return {
                'success': True,
                'note_id': note_id,
                'message': f'Appended content to note {note_id}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_tags_to_note(self, note_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Add tags to an existing note

        Args:
            note_id: ID of the note
            tags: List of tags to add

        Returns:
            Dict with success status
        """
        try:
            added_tags = []
            for tag in tags:
                self.db.add_tag(note_id, tag)
                added_tags.append(tag)

            return {
                'success': True,
                'note_id': note_id,
                'tags_added': added_tags,
                'message': f'Added tags to note {note_id}: {", ".join(added_tags)}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_link_between_notes(self, source_id: str, target_id: str, context: str = "") -> Dict[str, Any]:
        """
        Create a link between two notes

        Args:
            source_id: ID of the source note
            target_id: ID of the target note
            context: Optional context for the link

        Returns:
            Dict with success status
        """
        try:
            self.db.create_link(source_id, target_id, context)

            return {
                'success': True,
                'source_id': source_id,
                'target_id': target_id,
                'message': f'Created link from {source_id} to {target_id}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_note_content(self, note_id: str, content: str) -> Dict[str, Any]:
        """
        Update/replace the entire content of a note

        Args:
            note_id: ID of the note
            content: New content for the note

        Returns:
            Dict with success status
        """
        try:
            self.db.update_note(note_id, content)

            return {
                'success': True,
                'note_id': note_id,
                'message': f'Updated content of note {note_id}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # Tool definitions for MCP protocol
    TOOL_DEFINITIONS = [
        {
            "name": "search_notes",
            "description": """Search for notes containing a query string using case-insensitive pattern matching.

This is the primary tool for finding notes when you don't know the exact note ID. The search looks through the full content of all notes and returns matches with their IDs and preview text.

Use this when:
- Looking for notes about a specific topic or keyword
- Finding notes that mention a particular concept, person, or project
- Exploring what notes exist on a subject

Returns: List of matching notes with their IDs, truncated content previews (first 500 chars), creation timestamps, and full content. Notes are not sorted by relevance - consider reading multiple results to find the best match.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string. Matches anywhere in note content (case-insensitive). Use specific keywords for better results."
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_note",
            "description": """Retrieve complete information about a specific note by its ID.

This is the primary tool for reading a note's full content once you know its ID (from search results, tag queries, or related notes).

Use this when:
- You have a note ID and need to read the full content
- You need to see all tags on a specific note
- You want to know what other notes are linked to this one
- You need creation/modification timestamps

Returns: Complete note object containing:
- Full untruncated content
- All tags associated with the note
- IDs of all linked notes (bidirectional connections)
- Created and modified timestamps
- Note ID

This is more detailed than search results which only show previews.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The unique ID of the note to retrieve (e.g., '5d3ab', '42xyz'). IDs are short alphanumeric strings."
                    }
                },
                "required": ["note_id"]
            }
        },
        {
            "name": "list_recent_notes",
            "description": """List the most recently created notes in reverse chronological order (newest first).

This is useful for getting an overview of recent activity in the knowledge base without knowing specific keywords or tags.

Use this when:
- Getting oriented in a new knowledge base
- Seeing what was captured recently
- Finding notes when you remember roughly when they were created
- Getting a quick overview of recent work

Returns: List of recent notes with IDs, content previews (first 200 chars), and creation timestamps. Use get_note() to read the full content of interesting notes.

Note: This shows creation date, not modification date. Modified notes won't appear at the top unless they were recently created.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return. Default is 10, maximum is 50. Start with smaller values for faster responses.",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_notes_by_tag",
            "description": """Retrieve all notes that have been tagged with a specific tag.

Tags are used to categorize and organize notes by topic, project, status, or any other classification. This is one of the primary ways to find related notes in the system.

Use this when:
- Finding all notes about a specific project, topic, or category
- Gathering notes marked with a status (e.g., 'todo', 'idea', 'done')
- Exploring a particular area of the knowledge base
- You know the tag but not the specific note IDs

Returns: List of notes with that tag, including:
- Note IDs and content previews (first 200 chars)
- ALL tags on each note (not just the searched tag)
- Creation timestamps
- Sorted by creation date (newest first)

Tags are case-insensitive and normalized to lowercase. Use get_all_tags() to discover available tags.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "The tag to search for (case-insensitive). Common patterns: project names, topic keywords, status markers (todo/idea/done), or custom categories."
                    }
                },
                "required": ["tag"]
            }
        },
        {
            "name": "get_all_tags",
            "description": """Get a complete list of all tags used in the system with their usage counts.

This is essential for discovering what categories and topics exist in the knowledge base. Tags reveal the organization and structure of the notes.

Use this when:
- Exploring a new or unfamiliar knowledge base
- Discovering what topics/projects are documented
- Finding the most common or popular tags
- Deciding what tag to search for with get_notes_by_tag()
- Understanding the scope and coverage of the notes

Returns: List of all unique tags with usage counts, sorted by count (most used first, then alphabetically). Each entry shows:
- The tag name (normalized to lowercase)
- How many notes have that tag

This helps you understand what tags are available before querying specific ones.""",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_related_notes",
            "description": """Find all notes that are linked to a specific note (bidirectional connections).

Notes can be explicitly linked together to form a knowledge graph. This returns ALL notes connected to the given note, regardless of link direction (both incoming and outgoing links).

Use this when:
- Exploring connections and relationships between ideas
- Following the knowledge graph from one note to related notes
- Finding context around a specific note
- Understanding what other notes reference or are referenced by this note
- Discovering related topics and ideas

Returns: List of all connected notes with:
- Note IDs and content previews (first 200 chars)
- Creation timestamps

Note: This is bidirectional - if note A links to note B, both will see each other as related. Links are explicit connections created by users or tools, not automatic associations.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to find connections for. Will return both notes this one links to AND notes that link to this one."
                    }
                },
                "required": ["note_id"]
            }
        },
        {
            "name": "search_notes_by_date",
            "description": """Find all notes created on a specific date.

This is useful for finding notes when you remember the day they were created but not their content or tags.

Use this when:
- Looking for notes from a specific day
- Reviewing what was captured on a particular date
- Finding notes from a meeting or event on a known date
- Temporal navigation of the knowledge base

Returns: List of notes created on that date with:
- Note IDs and content previews (first 200 chars)
- Creation timestamps (will all be on the specified date)
- Sorted by creation time (newest first)

Note: This searches creation date only, not modification date. The date is matched in UTC timezone.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (e.g., '2025-01-15'). Must be a valid date. Timezone is UTC."
                    }
                },
                "required": ["date"]
            }
        },
        # WRITE OPERATIONS
        {
            "name": "create_note",
            "description": """Create a new note with text content and optional tags.

This is the primary way to add new information to the knowledge base. Each note is automatically assigned a unique ID and timestamped.

Use this when:
- Capturing new ideas, thoughts, or information
- Creating a new entry in the knowledge base
- Storing information you want to retrieve later
- Starting a new topic or concept

Returns: Success status with the generated note ID. Save this ID if you need to reference, link, or modify this note later.

Notes:
- The note ID is auto-generated (short alphanumeric string)
- Content can be any length and can include markdown formatting
- Tags are optional but recommended for organization
- Tags will be normalized to lowercase
- Duplicate tags are automatically ignored
- Both created_at and modified_at timestamps are set to now

After creation, you can:
- Add more tags with add_tags_to_note()
- Append additional content with append_to_note()
- Link to other notes with create_link_between_notes()""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content of the note. Can be any length. Markdown formatting is preserved. This is the main body of the note that will be searchable."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags for categorization (e.g., ['project-x', 'todo', 'meeting']). Tags are case-insensitive. Good tags help with later retrieval via get_notes_by_tag()."
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "append_to_note",
            "description": """Add new content to the end of an existing note without replacing what's already there.

This is useful for adding updates, follow-ups, or additional information to a note over time while preserving the original content and context.

Use this when:
- Adding a follow-up thought or update to an existing note
- Appending meeting notes from a continuation of the same meeting
- Adding new information related to an existing note
- Building up content incrementally

Returns: Success status with confirmation message.

Notes:
- New content is added on a new line after existing content
- Original content and tags are preserved
- The modified_at timestamp is updated
- Tags are NOT modified (use add_tags_to_note() for that)
- This is safer than update_note_content() for incremental additions

Example use case: Original note says "Project kickoff meeting scheduled for Monday." Later you can append "Meeting completed. Key decisions: ..." to build a chronological record.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to append to. The note must already exist."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to append. Will be added on a new line at the end of the existing note content."
                    }
                },
                "required": ["note_id", "content"]
            }
        },
        {
            "name": "add_tags_to_note",
            "description": """Add one or more tags to an existing note for better organization and discoverability.

Tags are the primary organizational structure in Zettl. Adding relevant tags makes notes easier to find later using get_notes_by_tag().

Use this when:
- Categorizing a note after creation
- Adding a note to a project or topic
- Marking a note with status (todo, done, idea, etc.)
- Associating a note with multiple categories
- Improving note organization and discoverability

Returns: Success status listing which tags were added.

Notes:
- Tags are normalized to lowercase automatically
- Duplicate tags are silently ignored (idempotent operation)
- Existing tags on the note are preserved
- Each tag is added individually
- Use descriptive, consistent tag names for best results
- Common tag patterns: project names (project-x), status (todo, done), topics (meeting, design, research)

After adding tags, the note will appear in results for get_notes_by_tag() queries using those tags.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to add tags to. The note must already exist."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of tag strings to add (e.g., ['important', 'review', 'project-x']). Tags are case-insensitive. Use get_all_tags() to see existing tags in the system."
                    }
                },
                "required": ["note_id", "tags"]
            }
        },
        {
            "name": "create_link_between_notes",
            "description": """Create an explicit bidirectional connection between two notes to build a knowledge graph.

Links represent relationships between concepts, ideas, or information. They're essential for building a connected knowledge base where related ideas can be discovered through graph traversal.

Use this when:
- Two notes discuss related topics or concepts
- One note provides context or background for another
- Connecting cause and effect, problem and solution
- Building concept hierarchies or relationships
- Creating a web of interconnected knowledge

Returns: Success status confirming the link was created.

Notes:
- Links are BIDIRECTIONAL: both notes will show each other as related
- The context parameter is optional but recommended for explaining the relationship
- Both notes must exist before linking
- Duplicate links (same source, target, context) are handled gracefully
- After linking, both notes will appear in each other's get_related_notes() results

Link directionality:
- While stored as source→target, queries treat them as bidirectional
- Use source/target to indicate the relationship direction if it matters
- Context can explain the relationship (e.g., "builds upon", "contradicts", "example of")

Example: Link a note about "Python decorators" to "Python functions" with context "advanced usage of" to show the relationship.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "The ID of the source note (the 'from' note in the relationship). Must be an existing note."
                    },
                    "target_id": {
                        "type": "string",
                        "description": "The ID of the target note (the 'to' note in the relationship). Must be an existing note."
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional explanation of the relationship between the notes (e.g., 'builds upon', 'contradicts', 'example of', 'related to'). Helps understand why these notes are linked."
                    }
                },
                "required": ["source_id", "target_id"]
            }
        },
        {
            "name": "update_note_content",
            "description": """Replace the entire content of an existing note with new content.

⚠️  WARNING: This OVERWRITES all existing content. The original content is permanently lost. Use append_to_note() if you want to add to the note instead.

Use this when:
- Completely rewriting a note with corrected or updated information
- Replacing draft content with final version
- Fixing major errors in a note
- Consolidating information where the old content is no longer relevant

DO NOT use this when:
- Adding to a note (use append_to_note() instead)
- Making small edits (consider append with corrections instead)
- Unsure about losing the old content

Returns: Success status confirming the update.

Notes:
- ALL original content is replaced
- Tags and links are preserved (only content changes)
- The modified_at timestamp is updated
- The created_at timestamp is preserved
- There is no undo or version history
- Consider appending " EDITED: [new info]" with append_to_note() for non-destructive updates

Safety tip: Read the note with get_note() first to confirm you have the right note before overwriting.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to update. The note must exist. Double-check this is the correct note before updating."
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content that will completely replace the existing note content. The old content will be permanently lost."
                    }
                },
                "required": ["note_id", "content"]
            }
        }
    ]
