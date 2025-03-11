# database.py
import random
import string
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client
from zettl.config import SUPABASE_URL, SUPABASE_KEY
from functools import wraps

# Singleton client
_supabase_client = None

# Global cache
_global_cache = {}
_global_cache_ttl = {}
_default_ttl = 300  # 5 minutes

def get_supabase_client():
    """Get or create the Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

def get_from_cache(key):
    """Get a value from the global cache if it exists and is valid."""
    if key in _global_cache and time.time() < _global_cache_ttl.get(key, 0):
        return _global_cache[key]
    return None

def set_in_cache(key, value, ttl=None):
    """Set a value in the global cache with a TTL."""
    _global_cache[key] = value
    _global_cache_ttl[key] = time.time() + (ttl or _default_ttl)

def invalidate_cache(prefix=None):
    """Invalidate all cache entries or those with a specific prefix."""
    global _global_cache, _global_cache_ttl
    if prefix:
        keys_to_remove = [k for k in _global_cache.keys() if k.startswith(prefix)]
        for k in keys_to_remove:
            _global_cache.pop(k, None)
            _global_cache_ttl.pop(k, None)
    else:
        _global_cache.clear()
        _global_cache_ttl.clear()

class Database:
    def __init__(self):
        self.client = get_supabase_client()
        # Keep this for backward compatibility with any code that might access it
        self._cache = {}
        self._cache_ttl = {}
        self._default_ttl = _default_ttl
        
    def invalidate_cache(self, prefix=None):
        """Instance method that calls the module-level function."""
        invalidate_cache(prefix)
        
    def _get_iso_timestamp(self) -> str:
        """Generate a properly formatted ISO timestamp for database operations."""
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        
    def format_timestamp(self, date_str: str) -> str:
        """Format a timestamp for display."""
        # Existing implementation...
        try:
            # Handle ISO format with microseconds
            if '.' in date_str:
                main_part, microseconds = date_str.split('.')
                # Make sure microseconds have exactly 6 digits
                microseconds = microseconds.ljust(6, '0')[:6]
                if 'Z' in microseconds:
                    microseconds = microseconds.replace('Z', '')
                    date_str = f"{main_part}.{microseconds}Z"
                else:
                    date_str = f"{main_part}.{microseconds}"
            created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            return created_at
        except Exception:
            # Fallback if date parsing fails
            return "Unknown date"
    
    def generate_id(self) -> str:
        """Generate a Zettelkasten-style ID based on timestamp and random characters."""
        # Existing implementation...
        timestamp = str(int(time.time()))[-2:]  # Last 2 digits of current timestamp
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
        return f"{timestamp}{random_chars}"
    
    def create_note(self, content: str) -> str:
        """Create a new note in the database."""
        note_id = self.generate_id()
        
        # Get current time
        now = self._get_iso_timestamp()
        
        # Insert the note
        result = self.client.table('notes').insert({
            "id": note_id,
            "content": content,
            "created_at": now,
            "modified_at": now
        }).execute()
        
        if not result.data:
            raise Exception("Failed to create note")
            
        # Invalidate relevant caches
        invalidate_cache("list_notes")
        
        return note_id
    
    def get_note(self, note_id: str) -> Dict[str, Any]:
        """Get a note by its ID with caching."""
        cache_key = f"note:{note_id}"
        
        # Check if in cache
        cached_note = get_from_cache(cache_key)
        if cached_note:
            return cached_note
        
        # Not in cache, fetch from database
        result = self.client.table('notes').select('*').eq('id', note_id).execute()
        
        if not result.data:
            raise Exception(f"Note {note_id} not found")
        
        # Store in cache
        set_in_cache(cache_key, result.data[0], ttl=600)
        
        return result.data[0]
    
    def list_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent notes with caching."""
        cache_key = f"list_notes:{limit}"
        
        # Check if list is in cache
        cached_list = get_from_cache(cache_key)
        if cached_list:
            return cached_list
        
        # Not in cache, fetch from database
        result = self.client.table('notes').select('*').order('created_at', desc=True).limit(limit).execute()
        
        notes = result.data or []
        
        # Store the list in cache
        set_in_cache(cache_key, notes, ttl=60)
        
        # Also cache each individual note
        for note in notes:
            note_id = note['id']
            set_in_cache(f"note:{note_id}", note, ttl=600)
        
        return notes
    
    def create_link(self, source_id: str, target_id: str, context: str = "") -> None:
        """Create a link between two notes."""
        # Verify both notes exist (this will use cache if available)
        self.get_note(source_id)
        self.get_note(target_id)
        
        # Get current time
        now = self._get_iso_timestamp()
        
        result = self.client.table('links').insert({
            "source_id": source_id,
            "target_id": target_id,
            "context": context,
            "created_at": now
        }).execute()
        
        if not result.data:
            raise Exception("Failed to create link")
            
        # Invalidate related caches
        invalidate_cache(f"related_notes:{source_id}")
        invalidate_cache(f"related_notes:{target_id}")
            
        return None
    
    def get_related_notes(self, note_id: str) -> List[Dict[str, Any]]:
        """Get all notes linked to the given note with caching."""
        cache_key = f"related_notes:{note_id}"
        
        # Check if in cache
        cached_notes = get_from_cache(cache_key)
        if cached_notes is not None:
            return cached_notes
        
        # Get outgoing links
        outgoing_result = self.client.table('links').select('target_id').eq('source_id', note_id).execute()
        
        # Get incoming links
        incoming_result = self.client.table('links').select('source_id').eq('target_id', note_id).execute()
        
        related_ids = []
        
        # Extract IDs from outgoing links
        if outgoing_result.data:
            related_ids.extend([link['target_id'] for link in outgoing_result.data])
            
        # Extract IDs from incoming links
        if incoming_result.data:
            related_ids.extend([link['source_id'] for link in incoming_result.data])
            
        # Remove duplicates
        related_ids = list(set(related_ids))
        
        if not related_ids:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []
            
        # Fetch all related notes, using cache when possible
        related_notes = []
        for related_id in related_ids:
            try:
                note = self.get_note(related_id)
                related_notes.append(note)
            except Exception:
                continue
                
        # Cache the result
        set_in_cache(cache_key, related_notes, ttl=300)
        
        return related_notes
    
    def add_tag(self, note_id: str, tag: str) -> str:
        """Add a tag to a note."""
        # Verify note exists
        self.get_note(note_id)
        
        # Get current time
        now = self._get_iso_timestamp()
        
        result = self.client.table('tags').insert({
            "note_id": note_id,
            "tag": tag.lower().strip(),
            "created_at": now
        }).execute()
        
        if not result.data:
            raise Exception("Failed to add tag")
        
        # Invalidate related caches
        invalidate_cache(f"tags:{note_id}")
        
        return None

    def get_tags(self, note_id: str) -> List[str]:
        """Get all tags for a note with caching."""
        cache_key = f"tags:{note_id}"
        
        # Check if in cache
        cached_tags = get_from_cache(cache_key)
        if cached_tags is not None:
            return cached_tags
        
        result = self.client.table('tags').select('tag').eq('note_id', note_id).execute()
        
        if not result.data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []
        
        tags = [tag_data['tag'] for tag_data in result.data]
        
        # Cache the result
        set_in_cache(cache_key, tags, ttl=300)
        
        return tags

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search for notes containing the query string."""
        # This could be cached, but search results change frequently
        # and the search term could be anything, so caching is less effective
        result = self.client.table('notes').select('*').ilike('content', f'%{query}%').execute()
        
        if not result.data:
            return []
        
        return result.data

    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes that have a specific tag with caching."""
        cache_key = f"notes_by_tag:{tag.lower().strip()}"
        
        # Check if in cache
        cached_notes = get_from_cache(cache_key)
        if cached_notes is not None:
            return cached_notes
        
        # Find all note_ids with this tag
        tag_result = self.client.table('tags').select('note_id').eq('tag', tag.lower().strip()).execute()
        
        if not tag_result.data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []
        
        note_ids = [item['note_id'] for item in tag_result.data]
        
        # Fetch all the corresponding notes, using cache when possible
        notes = []
        for note_id in note_ids:
            try:
                note = self.get_note(note_id)
                notes.append(note)
            except Exception:
                continue
        
        # Cache the result
        set_in_cache(cache_key, notes, ttl=300)
        
        return notes

    def get_all_tags_with_counts(self) -> List[Dict[str, Any]]:
        """Get all tags with the count of notes associated with each tag."""
        cache_key = "all_tags_counts"
        
        # Check if in cache
        cached_result = get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get all tags with their note_ids
        result = self.client.table('tags').select('tag, note_id').execute()
        
        if not result.data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []
        
        # Count occurrences of each tag
        tag_counts = {}
        for item in result.data:
            tag = item['tag']
            if tag in tag_counts:
                tag_counts[tag] += 1
            else:
                tag_counts[tag] = 1
        
        # Format the result
        tags_with_counts = [
            {"tag": tag, "count": count} 
            for tag, count in tag_counts.items()
        ]
        
        # Sort by count in descending order
        tags_with_counts = sorted(tags_with_counts, key=lambda x: x['count'], reverse=True)
        
        # Cache the result
        set_in_cache(cache_key, tags_with_counts, ttl=300)
        
        return tags_with_counts

    def delete_note(self, note_id: str, cascade: bool = True) -> None:
        """
        Delete a note from the database.
        
        Args:
            note_id: ID of the note to delete
            cascade: If True, also delete associated tags and links
            
        Returns:
            None
            
        Raises:
            Exception: If note deletion fails
        """
        # First verify the note exists
        self.get_note(note_id)
        
        # If cascade is True, delete all associated data first
        if cascade:
            # Delete all tags associated with this note
            self.delete_note_tags(note_id)
            
            # Delete all links involving this note
            self.delete_note_links(note_id)
        
        # Delete the note itself
        result = self.client.table('notes').delete().eq('id', note_id).execute()
        
        if not result.data:
            raise Exception(f"Failed to delete note {note_id}")
        
        # Invalidate relevant caches
        invalidate_cache(f"note:{note_id}")
        invalidate_cache("list_notes")
        
        return None

    def delete_note_tags(self, note_id: str) -> None:
        """
        Delete all tags associated with a note.
        
        Args:
            note_id: ID of the note to delete tags for
            
        Returns:
            None
        """
        # Delete all tags for this note
        result = self.client.table('tags').delete().eq('note_id', note_id).execute()
        
        # Invalidate relevant caches
        invalidate_cache(f"tags:{note_id}")
        
        return None

    def delete_note_links(self, note_id: str) -> None:
        """
        Delete all links involving a note (both incoming and outgoing).
        
        Args:
            note_id: ID of the note to delete links for
            
        Returns:
            None
        """
        # First, get all notes connected to this one (to invalidate their caches later)
        connected_notes = set()
        
        # Get outgoing links
        outgoing_result = self.client.table('links').select('target_id').eq('source_id', note_id).execute()
        if outgoing_result.data:
            connected_notes.update([link['target_id'] for link in outgoing_result.data])
        
        # Get incoming links
        incoming_result = self.client.table('links').select('source_id').eq('target_id', note_id).execute()
        if incoming_result.data:
            connected_notes.update([link['source_id'] for link in incoming_result.data])
        
        # Delete all outgoing links from this note
        self.client.table('links').delete().eq('source_id', note_id).execute()
        
        # Delete all incoming links to this note
        self.client.table('links').delete().eq('target_id', note_id).execute()
        
        # Invalidate caches for connected notes
        for connected_id in connected_notes:
            invalidate_cache(f"related_notes:{connected_id}")
        
        # Invalidate cache for this note
        invalidate_cache(f"related_notes:{note_id}")
        
        return None

    def delete_tag(self, note_id: str, tag: str) -> None:
        """
        Delete a specific tag from a note.
        
        Args:
            note_id: ID of the note to remove the tag from
            tag: The tag to remove
            
        Returns:
            None
            
        Raises:
            Exception: If tag deletion fails
        """
        # Delete the specific tag
        result = self.client.table('tags').delete().eq('note_id', note_id).eq('tag', tag.lower().strip()).execute()
        
        if not result.data:
            raise Exception(f"Failed to delete tag '{tag}' from note {note_id}")
        
        # Invalidate relevant caches
        invalidate_cache(f"tags:{note_id}")
        
        return None

    def delete_link(self, source_id: str, target_id: str) -> None:
        """
        Delete a specific link between two notes.
        
        Args:
            source_id: ID of the source note
            target_id: ID of the target note
            
        Returns:
            None
            
        Raises:
            Exception: If link deletion fails
        """
        # Delete the specific link
        result = self.client.table('links').delete().eq('source_id', source_id).eq('target_id', target_id).execute()
        
        if not result.data:
            raise Exception(f"Failed to delete link from note {source_id} to note {target_id}")
        
        # Invalidate relevant caches
        invalidate_cache(f"related_notes:{source_id}")
        invalidate_cache(f"related_notes:{target_id}")
        
        return None


