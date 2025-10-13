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

    def invalidate_cache(self, prefix=None):
        """Instance method that calls the module-level function."""
        invalidate_cache(prefix)

    def _get_jwt_from_api_key(self):
        """Convert API key to JWT token via auth service."""
        if not self.api_key:
            return

        try:
            response = requests.post(f'{self.auth_url}/token-from-key',
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

    def create_note_with_timestamp(self, content: str, timestamp: str, note_id: str = None) -> str:
        """
        Create a new note in the database with a specific timestamp and optionally a specific ID.

        Args:
            content: The note content
            timestamp: The timestamp to use (ISO format)
            note_id: Optional specific ID to use

        Returns:
            The ID of the created note
        """
        if note_id is None:
            note_id = self.generate_id()

        # Insert the note with the provided timestamp
        note_data = {
            "id": note_id,
            "content": content,
            "created_at": timestamp,
            "modified_at": timestamp
        }

        try:
            response = self._make_request('POST', 'notes', data=note_data)
        except Exception as e:
            raise Exception(f"Failed to create note with custom timestamp - Request failed: {str(e)}")

        # PostgREST returns 201 Created with empty body on successful creation
        if response.status_code != 201:
            raise Exception(f"Failed to create note with custom timestamp - Unexpected status: {response.status_code}, Response: {response.text}")

        # Invalidate relevant caches
        invalidate_cache("list_notes")

        return note_id

    def update_note(self, note_id: str, content: str) -> None:
        """
        Update the content of an existing note.

        Args:
            note_id: ID of the note to update
            content: New content for the note

        Returns:
            None

        Raises:
            Exception: If note update fails
        """
        # Verify the note exists first
        self.get_note(note_id)

        # Get current time
        now = self._get_iso_timestamp()

        # Update the note content and modified_at timestamp
        update_data = {
            "content": content,
            "modified_at": now
        }

        params = {'id': f'eq.{note_id}'}

        try:
            response = self._make_request('PATCH', 'notes', data=update_data, params=params)
        except Exception as e:
            raise Exception(f"Failed to update note - Request failed: {str(e)}")

        # Invalidate relevant caches
        invalidate_cache(f"note:{note_id}")
        invalidate_cache("list_notes")

        return None

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

        try:
            response = self._make_request('POST', 'links', data=link_data)
        except Exception as e:
            raise Exception(f"Failed to create link - Request failed: {str(e)}")

        # PostgREST returns 201 Created with empty body on successful creation
        if response.status_code != 201:
            raise Exception(f"Failed to create link - Unexpected status: {response.status_code}, Response: {response.text}")

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

        # Normalize tag
        normalized_tag = tag.lower().strip()

        # Check if tag already exists for this note
        existing_tags = self.get_tags(note_id)
        if normalized_tag in existing_tags:
            # Tag already exists, return silently (idempotent operation)
            return None

        # Get current time
        now = self._get_iso_timestamp()

        tag_data = {
            "note_id": note_id,
            "tag": normalized_tag,
            "created_at": now
        }

        try:
            response = self._make_request('POST', 'tags', data=tag_data)
        except requests.exceptions.HTTPError as e:
            # Handle 409 Conflict - tag already exists (race condition)
            if e.response.status_code == 409:
                # Tag was added between our check and insert, treat as success
                invalidate_cache(f"tags:{note_id}")
                return None
            raise Exception(f"Failed to add tag - Request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to add tag - Request failed: {str(e)}")

        # PostgREST returns 201 Created with empty body on successful creation
        if response.status_code != 201:
            raise Exception(f"Failed to add tag - Unexpected status: {response.status_code}, Response: {response.text}")

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

            # Build URL manually to support multiple filters on same field
            url = f"{self.postgrest_url}/notes"
            query_params = f"created_at=gte.{start_timestamp}&created_at=lte.{end_timestamp}&order=created_at.desc"
            full_url = f"{url}?{query_params}"

            # Add authorization headers
            headers = {}
            if self.api_key and not self.jwt_token:
                self._get_jwt_from_api_key()
            if self.jwt_token:
                headers['Authorization'] = f'Bearer {self.jwt_token}'

            response = self.session.get(full_url, headers=headers)
            response.raise_for_status()

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

    def get_notes_with_all_tags_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes that have a specific tag, along with ALL their tags using a PostgreSQL view."""
        cache_key = f"notes_with_all_tags_by_tag:{tag.lower().strip()}"

        # Check if in cache
        cached_result = get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # Use the PostgreSQL view that aggregates all tags
        # Filter for notes that contain the specified tag in their all_tags_array
        params = {
            'all_tags_array': f'cs.{{{tag.lower().strip()}}}',  # PostgreSQL array contains operator
            'select': 'id,content,created_at,all_tags_str,all_tags_array',
            'order': 'created_at.desc'
        }

        response = self._make_request('GET', 'notes_with_tags', params=params)
        notes_data = response.json()

        # Transform to the format we want
        result = []
        for note_data in notes_data:
            note = {
                'id': note_data['id'],
                'content': note_data['content'],
                'created_at': note_data['created_at'],
                'all_tags': note_data.get('all_tags_array', []) if note_data.get('all_tags_array') else []
            }
            result.append(note)

        set_in_cache(cache_key, result, ttl=300)
        return result

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

    def get_tags_created_today(self, tag: str) -> List[str]:
        """Get note IDs for tags created today."""
        from datetime import datetime, timezone

        # Get today's date range
        today = datetime.now(timezone.utc)
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Format as ISO strings
        start_timestamp = start_of_day.isoformat().replace('+00:00', 'Z')
        end_timestamp = end_of_day.isoformat().replace('+00:00', 'Z')

        # Build URL manually to support multiple filters on same field
        url = f"{self.postgrest_url}/tags"
        query_params = f"tag=eq.{tag.lower().strip()}&created_at=gte.{start_timestamp}&created_at=lte.{end_timestamp}&select=note_id,created_at"
        full_url = f"{url}?{query_params}"

        # Add authorization headers
        headers = {}
        if self.api_key and not self.jwt_token:
            self._get_jwt_from_api_key()
        if self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'

        try:
            response = self.session.get(full_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if data else []
        except Exception:
            return []

    def merge_notes(self, note_ids: List[str]) -> str:
        """
        Merge multiple notes into a single note.

        This will:
        1. Combine the content of all notes (ordered by creation date)
        2. Collect all unique tags from all notes
        3. Preserve all external links (updating them to point to the new note)
        4. Delete the old notes

        Args:
            note_ids: List of note IDs to merge (must have at least 2 notes)

        Returns:
            The ID of the newly created merged note

        Raises:
            Exception: If merge fails or invalid input
        """
        # Validate input
        if not note_ids or len(note_ids) < 2:
            raise Exception("Must provide at least 2 notes to merge")

        # Remove duplicates while preserving order
        unique_ids = []
        seen = set()
        for note_id in note_ids:
            if note_id not in seen:
                unique_ids.append(note_id)
                seen.add(note_id)
        note_ids = unique_ids

        if len(note_ids) < 2:
            raise Exception("Must provide at least 2 unique notes to merge")

        # Fetch all notes to merge
        notes_to_merge = []
        for note_id in note_ids:
            try:
                note = self.get_note(note_id)
                notes_to_merge.append(note)
            except Exception as e:
                raise Exception(f"Failed to fetch note {note_id}: {str(e)}")

        # Sort notes by creation date (oldest first)
        notes_to_merge.sort(key=lambda x: x['created_at'])

        # Combine content
        merged_content_parts = [note['content'] for note in notes_to_merge]
        merged_content = "\n\n".join(merged_content_parts)

        # Collect all unique tags
        all_tags = set()
        for note_id in note_ids:
            try:
                tags = self.get_tags(note_id)
                all_tags.update(tags)
            except Exception:
                # If we can't get tags, continue without them
                pass

        # Collect all external links
        # Links are external if they connect to notes NOT in the merge set
        note_ids_set = set(note_ids)
        external_links = []

        for note_id in note_ids:
            # Get outgoing links
            params = {'source_id': f'eq.{note_id}', 'select': 'target_id,context'}
            try:
                response = self._make_request('GET', 'links', params=params)
                outgoing = response.json()
                if outgoing:
                    for link in outgoing:
                        # Only keep if target is external
                        if link['target_id'] not in note_ids_set:
                            external_links.append({
                                'type': 'outgoing',
                                'target_id': link['target_id'],
                                'context': link.get('context', '')
                            })
            except Exception:
                pass

            # Get incoming links
            params = {'target_id': f'eq.{note_id}', 'select': 'source_id,context'}
            try:
                response = self._make_request('GET', 'links', params=params)
                incoming = response.json()
                if incoming:
                    for link in incoming:
                        # Only keep if source is external
                        if link['source_id'] not in note_ids_set:
                            external_links.append({
                                'type': 'incoming',
                                'source_id': link['source_id'],
                                'context': link.get('context', '')
                            })
            except Exception:
                pass

        # Remove duplicate links (same source, target, and context)
        unique_links = []
        seen_links = set()
        for link in external_links:
            if link['type'] == 'outgoing':
                key = ('outgoing', link['target_id'], link['context'])
            else:
                key = ('incoming', link['source_id'], link['context'])

            if key not in seen_links:
                unique_links.append(link)
                seen_links.add(key)

        # Create the new merged note
        merged_note_id = self.create_note(merged_content)

        # Add all tags to the new note
        for tag in all_tags:
            try:
                self.add_tag(merged_note_id, tag)
            except Exception:
                # If tag addition fails, continue
                pass

        # Add all external links to the new note
        for link in unique_links:
            try:
                if link['type'] == 'outgoing':
                    self.create_link(merged_note_id, link['target_id'], link['context'])
                else:  # incoming
                    self.create_link(link['source_id'], merged_note_id, link['context'])
            except Exception:
                # If link creation fails, continue
                pass

        # Delete all old notes (with cascade to clean up any remaining data)
        for note_id in note_ids:
            try:
                self.delete_note(note_id, cascade=True)
            except Exception as e:
                # If deletion fails, we should still try to delete the others
                # but we should report this error
                raise Exception(f"Failed to delete note {note_id} during merge: {str(e)}")

        # Invalidate relevant caches
        invalidate_cache("list_notes")
        for note_id in note_ids:
            invalidate_cache(f"note:{note_id}")
            invalidate_cache(f"tags:{note_id}")
            invalidate_cache(f"related_notes:{note_id}")

        return merged_note_id