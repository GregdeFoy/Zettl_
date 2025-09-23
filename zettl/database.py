# database.py
import random
import string
import time
import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from zettl.config import POSTGREST_URL, AUTH_URL
from functools import wraps

# Singleton client
_http_session = None

# Global cache
_global_cache = {}
_global_cache_ttl = {}
_default_ttl = 300  # 5 minutes

def get_http_session():
    """Get or create the HTTP session singleton."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    return _http_session

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
    def __init__(self, jwt_token=None, api_key=None):
        self.session = get_http_session()
        self.postgrest_url = POSTGREST_URL
        self.auth_url = AUTH_URL
        self.jwt_token = jwt_token
        self.api_key = api_key
        # Keep this for backward compatibility with any code that might access it
        self._cache = {}
        self._cache_ttl = {}
        self._default_ttl = _default_ttl

    def invalidate_cache(self, prefix=None):
        """Instance method that calls the module-level function."""
        invalidate_cache(prefix)

    def _get_jwt_from_api_key(self):
        """Convert API key to JWT token via auth service."""
        if not self.api_key:
            return

        try:
            response = requests.post(f'{self.auth_url}/api/auth/token-from-key',
                                   headers={'X-API-Key': self.api_key},
                                   timeout=5)
            if response.status_code == 200:
                self.jwt_token = response.json().get('token')
        except requests.RequestException:
            # API key authentication failed, will result in 401 errors
            pass

    def _get_iso_timestamp(self) -> str:
        """Generate a properly formatted ISO timestamp for database operations."""
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]

    def format_timestamp(self, date_str: str) -> str:
        """Format a timestamp for display."""
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
        timestamp = str(int(time.time()))[-2:]  # Last 2 digits of current timestamp
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
        return f"{timestamp}{random_chars}"

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request to PostgREST API."""
        url = f"{self.postgrest_url}/{endpoint}"

        kwargs = {}
        if data:
            kwargs['json'] = data
        if params:
            kwargs['params'] = params

        # Add authorization headers
        headers = kwargs.get('headers', {})

        # If we have an API key but no JWT token, get one
        if self.api_key and not self.jwt_token:
            self._get_jwt_from_api_key()

        # Add JWT authorization header if token is available
        if self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'

        if headers:
            kwargs['headers'] = headers

        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def create_note(self, content: str) -> str:
        """Create a new note in the database."""
        note_id = self.generate_id()

        # Get current time
        now = self._get_iso_timestamp()

        # Insert the note
        note_data = {
            "id": note_id,
            "content": content,
            "created_at": now,
            "modified_at": now
        }

        try:
            response = self._make_request('POST', 'notes', data=note_data)
        except Exception as e:
            raise Exception(f"Failed to create note - Request failed: {str(e)}")

        # PostgREST returns 201 Created with empty body on successful creation
        if response.status_code != 201:
            raise Exception(f"Failed to create note - Unexpected status: {response.status_code}, Response: {response.text}")

        # Invalidate relevant caches
        invalidate_cache("list_notes")

        return note_id

    def create_note_with_timestamp(self, content: str, timestamp: str) -> str:
        """
        Create a new note in the database with a specific timestamp.

        Args:
            content: The note content
            timestamp: The timestamp to use (ISO format)

        Returns:
            The ID of the created note
        """
        note_id = self.generate_id()

        # Insert the note with the provided timestamp
        note_data = {
            "id": note_id,
            "content": content,
            "created_at": timestamp,
            "modified_at": timestamp
        }

        response = self._make_request('POST', 'notes', data=note_data)

        if not response.text:
            raise Exception("Failed to create note with custom timestamp")

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
        params = {'id': f'eq.{note_id}'}
        response = self._make_request('GET', 'notes', params=params)

        data = response.json()
        if not data:
            raise Exception(f"Note {note_id} not found")

        note = data[0]

        # Store in cache
        set_in_cache(cache_key, note, ttl=600)

        return note

    def list_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent notes with caching."""
        cache_key = f"list_notes:{limit}"

        # Check if list is in cache
        cached_list = get_from_cache(cache_key)
        if cached_list:
            return cached_list

        # Not in cache, fetch from database
        params = {
            'order': 'created_at.desc',
            'limit': str(limit)
        }
        response = self._make_request('GET', 'notes', params=params)

        notes = response.json() or []

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

        link_data = {
            "source_id": source_id,
            "target_id": target_id,
            "context": context,
            "created_at": now
        }

        response = self._make_request('POST', 'links', data=link_data)

        if not response.text:
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
        params = {'source_id': f'eq.{note_id}', 'select': 'target_id'}
        outgoing_response = self._make_request('GET', 'links', params=params)

        # Get incoming links
        params = {'target_id': f'eq.{note_id}', 'select': 'source_id'}
        incoming_response = self._make_request('GET', 'links', params=params)

        related_ids = []

        # Extract IDs from outgoing links
        outgoing_data = outgoing_response.json()
        if outgoing_data:
            related_ids.extend([link['target_id'] for link in outgoing_data])

        # Extract IDs from incoming links
        incoming_data = incoming_response.json()
        if incoming_data:
            related_ids.extend([link['source_id'] for link in incoming_data])

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

        tag_data = {
            "note_id": note_id,
            "tag": tag.lower().strip(),
            "created_at": now
        }

        response = self._make_request('POST', 'tags', data=tag_data)

        if not response.text:
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

        params = {'note_id': f'eq.{note_id}', 'select': 'tag'}
        response = self._make_request('GET', 'tags', params=params)

        data = response.json()
        if not data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []

        tags = [tag_data['tag'] for tag_data in data]

        # Cache the result
        set_in_cache(cache_key, tags, ttl=300)

        return tags

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search for notes containing the query string."""
        params = {'content': f'ilike.*{query}*'}
        response = self._make_request('GET', 'notes', params=params)

        data = response.json()
        if not data:
            return []

        return data

    def search_notes_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Search for notes created on a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of notes created on the specified date
        """
        try:
            # Parse the date to ensure it's valid
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            # Create start and end timestamps for the date (in UTC)
            start_timestamp = f"{date_str}T00:00:00Z"
            end_timestamp = f"{date_str}T23:59:59.999Z"

            # Query notes created between these timestamps
            params = {
                'created_at': f'gte.{start_timestamp}',
                'created_at': f'lte.{end_timestamp}',
                'order': 'created_at.desc'
            }
            response = self._make_request('GET', 'notes', params=params)

            data = response.json()
            if not data:
                return []

            return data

        except ValueError:
            # Invalid date format
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")
        except Exception as e:
            # Re-raise any other exceptions
            raise Exception(f"Error searching notes by date: {str(e)}")

    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes that have a specific tag with caching."""
        cache_key = f"notes_by_tag:{tag.lower().strip()}"

        # Check if in cache
        cached_notes = get_from_cache(cache_key)
        if cached_notes is not None:
            return cached_notes

        # Find all note_ids with this tag
        params = {'tag': f'eq.{tag.lower().strip()}', 'select': 'note_id'}
        response = self._make_request('GET', 'tags', params=params)

        tag_data = response.json()
        if not tag_data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []

        note_ids = [item['note_id'] for item in tag_data]

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
        params = {'select': 'tag,note_id'}
        response = self._make_request('GET', 'tags', params=params)

        data = response.json()
        if not data:
            # Cache empty result
            set_in_cache(cache_key, [], ttl=300)
            return []

        # Count occurrences of each tag
        tag_counts = {}
        for item in data:
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
        params = {'id': f'eq.{note_id}'}
        response = self._make_request('DELETE', 'notes', params=params)

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
        params = {'note_id': f'eq.{note_id}'}
        self._make_request('DELETE', 'tags', params=params)

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
        params = {'source_id': f'eq.{note_id}', 'select': 'target_id'}
        outgoing_response = self._make_request('GET', 'links', params=params)
        outgoing_data = outgoing_response.json()
        if outgoing_data:
            connected_notes.update([link['target_id'] for link in outgoing_data])

        # Get incoming links
        params = {'target_id': f'eq.{note_id}', 'select': 'source_id'}
        incoming_response = self._make_request('GET', 'links', params=params)
        incoming_data = incoming_response.json()
        if incoming_data:
            connected_notes.update([link['source_id'] for link in incoming_data])

        # Delete all outgoing links from this note
        params = {'source_id': f'eq.{note_id}'}
        self._make_request('DELETE', 'links', params=params)

        # Delete all incoming links to this note
        params = {'target_id': f'eq.{note_id}'}
        self._make_request('DELETE', 'links', params=params)

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
        params = {'note_id': f'eq.{note_id}', 'tag': f'eq.{tag.lower().strip()}'}
        response = self._make_request('DELETE', 'tags', params=params)

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
        params = {'source_id': f'eq.{source_id}', 'target_id': f'eq.{target_id}'}
        response = self._make_request('DELETE', 'links', params=params)

        # Invalidate relevant caches
        invalidate_cache(f"related_notes:{source_id}")
        invalidate_cache(f"related_notes:{target_id}")

        return None