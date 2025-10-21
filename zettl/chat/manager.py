"""
Chat Manager

Handles conversation and message persistence for the LLM chat interface.
"""

import random
import string
import time
from typing import List, Dict, Any, Optional
from zettl.database import Database


class ChatManager:
    """Manages chat conversations and messages"""

    def __init__(self, jwt_token: str):
        """
        Initialize chat manager

        Args:
            jwt_token: JWT token for database authentication
        """
        self.db = Database(jwt_token=jwt_token)

    def generate_id(self) -> str:
        """Generate a unique ID for conversations and messages"""
        timestamp = str(int(time.time()))[-6:]
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{timestamp}{random_chars}"

    def create_conversation(
        self,
        title: Optional[str] = None,
        context_note_ids: Optional[List[str]] = None
    ) -> str:
        """
        Create a new conversation

        Args:
            title: Optional title for the conversation
            context_note_ids: List of note IDs that are in context

        Returns:
            Conversation ID
        """
        import logging
        logger = logging.getLogger(__name__)

        conversation_id = self.generate_id()

        # Convert note IDs list to PostgreSQL array format
        note_ids_array = context_note_ids if context_note_ids else []

        conversation_data = {
            "id": conversation_id,
            "title": title or "New Conversation",
            "context_note_ids": note_ids_array
        }

        try:
            logger.info(f"Creating conversation with data: {conversation_data}")
            logger.info(f"JWT token present: {bool(self.db.jwt_token)}")
            logger.info(f"JWT token preview: {self.db.jwt_token[:50] if self.db.jwt_token else 'None'}...")

            response = self.db._make_request('POST', 'conversations', data=conversation_data)

            logger.info(f"PostgREST response status: {response.status_code}")
            logger.info(f"PostgREST response headers: {dict(response.headers)}")
            logger.info(f"PostgREST response body: {response.text}")

            if response.status_code != 201:
                raise Exception(f"Failed to create conversation: {response.text}")
            return conversation_id
        except Exception as e:
            logger.error(f"Exception creating conversation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"Failed to create conversation: {str(e)}")

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None
    ) -> str:
        """
        Add a message to a conversation

        Args:
            conversation_id: ID of the conversation
            role: Message role ('user' or 'assistant')
            content: Message content
            tool_calls: Optional list of tool calls made

        Returns:
            Message ID
        """
        message_id = self.generate_id()

        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls
        }

        try:
            response = self.db._make_request('POST', 'messages', data=message_data)
            if response.status_code != 201:
                raise Exception(f"Failed to add message: {response.text}")
            return message_id
        except Exception as e:
            raise Exception(f"Failed to add message: {str(e)}")

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation

        Args:
            conversation_id: ID of the conversation

        Returns:
            List of messages ordered by creation time
        """
        try:
            params = {
                'conversation_id': f'eq.{conversation_id}',
                'order': 'created_at.asc'
            }
            response = self.db._make_request('GET', 'messages', params=params)
            return response.json() or []
        except Exception as e:
            raise Exception(f"Failed to get messages: {str(e)}")

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation details

        Args:
            conversation_id: ID of the conversation

        Returns:
            Conversation data
        """
        try:
            params = {'id': f'eq.{conversation_id}'}
            response = self.db._make_request('GET', 'conversations', params=params)
            data = response.json()
            if not data:
                raise Exception(f"Conversation {conversation_id} not found")
            return data[0]
        except Exception as e:
            raise Exception(f"Failed to get conversation: {str(e)}")

    def list_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent conversations

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversations ordered by updated time
        """
        try:
            params = {
                'order': 'updated_at.desc',
                'limit': str(limit)
            }
            response = self.db._make_request('GET', 'conversations', params=params)
            return response.json() or []
        except Exception as e:
            raise Exception(f"Failed to list conversations: {str(e)}")

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        """
        Update conversation title

        Args:
            conversation_id: ID of the conversation
            title: New title
        """
        try:
            params = {'id': f'eq.{conversation_id}'}
            response = self.db._make_request(
                'PATCH',
                'conversations',
                data={'title': title},
                params=params
            )
            if response.status_code not in [200, 204]:
                raise Exception(f"Failed to update conversation: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to update conversation title: {str(e)}")
