# notes.py
from typing import List, Dict, Any
from zettl.database import Database

class Notes:
    def __init__(self, jwt_token=None, api_key=None):
        self.db = Database(jwt_token=jwt_token, api_key=api_key)
    
    def create_note(self, content: str) -> str:
        """Create a new note with the given content."""
        note_id = self.db.create_note(content)
        return note_id
        
    def create_note_with_timestamp(self, content: str, timestamp: str, note_id: str = None) -> str:
        """Create a new note with a specific timestamp and optionally a specific ID."""
        note_id = self.db.create_note_with_timestamp(content, timestamp, note_id)
        return note_id
        
    def get_note(self, note_id: str) -> Dict[str, Any]:
        """Get a note by its ID."""
        return self.db.get_note(note_id)
        
    def list_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent notes, with the newest first."""
        return self.db.list_notes(limit)
        
    def create_link(self, source_id: str, target_id: str, context: str = "") -> None:
        """Create a link between two notes."""
        return self.db.create_link(source_id, target_id, context)
        
    def get_related_notes(self, note_id: str) -> List[Dict[str, Any]]:
        """Get all notes linked to the given note."""
        return self.db.get_related_notes(note_id)
        
    def add_tag(self, note_id: str, tag: str) -> str:
        """Add a tag to a note."""
        return self.db.add_tag(note_id, tag)

    def add_tags_batch(self, note_id: str, tags: List[str]) -> None:
        """Add multiple tags to a note in a single request."""
        return self.db.add_tags_batch(note_id, tags)
        
    def get_tags(self, note_id: str) -> List[str]:
        """Get all tags for a note."""
        return self.db.get_tags(note_id)
        
    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search for notes containing the query string."""
        return self.db.search_notes(query)
        
    def search_notes_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Search for notes created on a specific date (YYYY-MM-DD format)."""
        return self.db.search_notes_by_date(date_str)
        
    def format_timestamp(self, date_str: str) -> str:
        """Format a timestamp for display."""
        return self.db.format_timestamp(date_str)
    
    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes that have a specific tag."""
        return self.db.get_notes_by_tag(tag)

    def get_notes_with_all_tags_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes that have a specific tag, along with ALL their tags in one or two efficient queries."""
        return self.db.get_notes_with_all_tags_by_tag(tag)

    def get_all_tags_with_counts(self) -> List[Dict[str, Any]]:
        """Get all tags with the count of notes associated with each tag."""
        return self.db.get_all_tags_with_counts()

    def get_tags_created_today(self, tag: str) -> List[str]:
        """Get note IDs for tags created today."""
        return self.db.get_tags_created_today(tag)

    def delete_note(self, note_id: str, cascade: bool = True, force: bool = False) -> None:
        """Delete a note and optionally its associated tags and links."""
        return self.db.delete_note(note_id, cascade, force)
        
    def delete_note_tags(self, note_id: str) -> None:
        """Delete all tags associated with a note."""
        return self.db.delete_note_tags(note_id)
        
    def delete_note_links(self, note_id: str) -> None:
        """Delete all links involving a note."""
        return self.db.delete_note_links(note_id)
        
    def delete_tag(self, note_id: str, tag: str) -> None:
        """Delete a specific tag from a note."""
        return self.db.delete_tag(note_id, tag)
        
    def delete_link(self, source_id: str, target_id: str) -> None:
        """Delete a specific link between two notes."""
        return self.db.delete_link(source_id, target_id)

    def merge_notes(self, note_ids: List[str]) -> str:
        """
        Merge multiple notes into a single note.

        Args:
            note_ids: List of note IDs to merge

        Returns:
            ID of the newly created merged note
        """
        return self.db.merge_notes(note_ids)

    def update_note(self, note_id: str, content: str) -> None:
        """Update the content of a note."""
        return self.db.update_note(note_id, content)

    def append_to_note(self, note_id: str, text: str) -> None:
        """Append text to the end of a note."""
        note = self.db.get_note(note_id)
        current_content = note['content']
        new_content = f"{current_content}\n{text}"
        return self.db.update_note(note_id, new_content)

    def prepend_to_note(self, note_id: str, text: str) -> None:
        """Prepend text to the beginning of a note."""
        note = self.db.get_note(note_id)
        current_content = note['content']
        new_content = f"{text}\n{current_content}"
        return self.db.update_note(note_id, new_content)
