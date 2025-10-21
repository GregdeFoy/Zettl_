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
            "description": "Search for notes containing a query string. Returns matching notes with their content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_note",
            "description": "Get a specific note by its ID. Returns full note content, tags, and linked notes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to retrieve"
                    }
                },
                "required": ["note_id"]
            }
        },
        {
            "name": "list_recent_notes",
            "description": "List recent notes in chronological order. Useful for getting an overview of recent activity.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default 10, max 50)",
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
            "description": "Get all notes that have a specific tag. Returns notes with their tags.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "The tag to search for"
                    }
                },
                "required": ["tag"]
            }
        },
        {
            "name": "get_all_tags",
            "description": "Get all tags in the system with their usage counts. Useful for discovering topics and themes.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_related_notes",
            "description": "Get all notes linked to a specific note. Shows the knowledge graph connections.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to find connections for"
                    }
                },
                "required": ["note_id"]
            }
        },
        {
            "name": "search_notes_by_date",
            "description": "Search for notes created on a specific date.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"]
            }
        },
        # WRITE OPERATIONS
        {
            "name": "create_note",
            "description": "Create a new note with content and optional tags. Returns the ID of the created note.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content of the note"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags to add to the note"
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "append_to_note",
            "description": "Append content to an existing note. The new content will be added on a new line at the end of the note.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to append to"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to append"
                    }
                },
                "required": ["note_id", "content"]
            }
        },
        {
            "name": "add_tags_to_note",
            "description": "Add one or more tags to an existing note. Tags help organize and categorize notes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags to add"
                    }
                },
                "required": ["note_id", "tags"]
            }
        },
        {
            "name": "create_link_between_notes",
            "description": "Create a bidirectional link between two notes to build knowledge connections.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "The ID of the source note"
                    },
                    "target_id": {
                        "type": "string",
                        "description": "The ID of the target note"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context explaining the relationship"
                    }
                },
                "required": ["source_id", "target_id"]
            }
        },
        {
            "name": "update_note_content",
            "description": "Replace the entire content of a note. Use with caution as this overwrites the existing content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "The ID of the note to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content for the note"
                    }
                },
                "required": ["note_id", "content"]
            }
        }
    ]
