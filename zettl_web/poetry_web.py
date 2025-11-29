"""
Poetry Companion - Literary text exploration with AI assistance
"""

import os
import json
import logging
import requests
from flask import Blueprint, request, jsonify, render_template, session
from functools import wraps
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Create Blueprint
poetry_bp = Blueprint('poetry', __name__)

# PostgREST configuration
POSTGREST_URL = os.getenv('POSTGREST_URL', 'http://postgrest:3000')

# JWT validation decorator (reuse from main app)
def jwt_required(f):
    """Simplified JWT check - assumes session has access_token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ===== ROUTES =====

@poetry_bp.route('/')
@jwt_required
def index():
    """Main poetry companion page"""
    return render_template('poetry.html')


@poetry_bp.route('/api/texts', methods=['GET', 'POST'])
@jwt_required
def texts_api():
    """List or create texts"""
    try:
        token = session.get('access_token')
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        if request.method == 'GET':
            # List texts for current user
            response = requests.get(
                f'{POSTGREST_URL}/texts',
                headers=headers,
                params={'order': 'created_at.desc'}
            )
            return jsonify(response.json()), response.status_code

        elif request.method == 'POST':
            # Create new text
            data = request.json
            logger.info(f"Creating text: {data.get('title')}")

            # Parse content into structured format
            content = data.get('content', '')
            metadata = parse_text_structure(content, data.get('text_type', 'poem'))

            text_data = {
                'title': data.get('title'),
                'author': data.get('author'),
                'source_language': data.get('source_language', 'en'),
                'text_type': data.get('text_type', 'poem'),
                'content': content,
                'metadata': json.dumps(metadata),
                'source': data.get('source'),
                'year': data.get('year')
            }

            logger.info(f"Sending to PostgREST: {POSTGREST_URL}/texts")

            # Add Prefer header to get the created record back
            headers['Prefer'] = 'return=representation'

            response = requests.post(
                f'{POSTGREST_URL}/texts',
                headers=headers,
                json=text_data
            )

            logger.info(f"PostgREST response: {response.status_code} - {response.text}")

            if response.status_code == 201:
                # Successfully created
                if response.text:
                    return jsonify(response.json()), response.status_code
                else:
                    # Empty response, return success with text_data
                    return jsonify([text_data]), 201
            else:
                # Error response
                if response.text:
                    return jsonify(response.json()), response.status_code
                else:
                    return jsonify({'error': 'Unknown error'}), response.status_code

    except Exception as e:
        logger.error(f"Error in texts_api: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@poetry_bp.route('/api/texts/<text_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def text_detail(text_id):
    """Get, update, or delete a specific text"""
    token = session.get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if request.method == 'GET':
        response = requests.get(
            f'{POSTGREST_URL}/texts',
            headers=headers,
            params={'id': f'eq.{text_id}'}
        )
        data = response.json()
        return jsonify(data[0] if data else None), response.status_code

    elif request.method == 'PUT':
        response = requests.patch(
            f'{POSTGREST_URL}/texts',
            headers=headers,
            params={'id': f'eq.{text_id}'},
            json=request.json
        )
        return jsonify(response.json()), response.status_code

    elif request.method == 'DELETE':
        response = requests.delete(
            f'{POSTGREST_URL}/texts',
            headers=headers,
            params={'id': f'eq.{text_id}'}
        )
        return '', response.status_code


@poetry_bp.route('/api/texts/<text_id>/conversations', methods=['GET', 'POST'])
@jwt_required
def text_conversations(text_id):
    """List or create conversations for a text"""
    token = session.get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if request.method == 'GET':
        response = requests.get(
            f'{POSTGREST_URL}/text_conversations',
            headers=headers,
            params={
                'text_id': f'eq.{text_id}',
                'order': 'created_at.desc'
            }
        )
        return jsonify(response.json()), response.status_code

    elif request.method == 'POST':
        data = request.json
        conversation_data = {
            'text_id': text_id,
            'title': data.get('title', f'Conversation {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        }

        response = requests.post(
            f'{POSTGREST_URL}/text_conversations',
            headers=headers,
            json=conversation_data
        )

        return jsonify(response.json()), response.status_code


@poetry_bp.route('/api/conversations/<conversation_id>/messages', methods=['GET', 'POST'])
@jwt_required
def conversation_messages(conversation_id):
    """Get or send messages in a conversation"""
    token = session.get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if request.method == 'GET':
        response = requests.get(
            f'{POSTGREST_URL}/text_messages',
            headers=headers,
            params={
                'conversation_id': f'eq.{conversation_id}',
                'order': 'created_at.asc'
            }
        )
        return jsonify(response.json()), response.status_code

    elif request.method == 'POST':
        data = request.json
        message = data.get('message')
        selected_range = data.get('selected_range')

        # Get conversation and text details
        conv_response = requests.get(
            f'{POSTGREST_URL}/text_conversations',
            headers=headers,
            params={'id': f'eq.{conversation_id}'}
        )

        if not conv_response.json():
            return jsonify({'error': 'Conversation not found'}), 404

        conversation = conv_response.json()[0]
        text_id = conversation['text_id']

        # Get full text
        text_response = requests.get(
            f'{POSTGREST_URL}/texts',
            headers=headers,
            params={'id': f'eq.{text_id}'}
        )

        if not text_response.json():
            return jsonify({'error': 'Text not found'}), 404

        text = text_response.json()[0]

        # Get conversation history
        history_response = requests.get(
            f'{POSTGREST_URL}/text_messages',
            headers=headers,
            params={
                'conversation_id': f'eq.{conversation_id}',
                'order': 'created_at.asc',
                'limit': '50'
            }
        )
        history = history_response.json()

        # Build context and call LLM
        assistant_response = process_literary_message(
            message=message,
            text=text,
            selected_range=selected_range,
            history=history
        )

        # Save user message
        user_msg_data = {
            'conversation_id': conversation_id,
            'role': 'user',
            'content': message,
            'selected_range': json.dumps(selected_range) if selected_range else None
        }

        requests.post(
            f'{POSTGREST_URL}/text_messages',
            headers=headers,
            json=user_msg_data
        )

        # Save assistant message
        assistant_msg_data = {
            'conversation_id': conversation_id,
            'role': 'assistant',
            'content': assistant_response
        }

        requests.post(
            f'{POSTGREST_URL}/text_messages',
            headers=headers,
            json=assistant_msg_data
        )

        return jsonify({'response': assistant_response})


# ===== HELPER FUNCTIONS =====

def parse_text_structure(content, text_type):
    """Parse text content into structured metadata"""
    lines = content.split('\n')

    metadata = {
        'total_lines': len(lines),
        'type': text_type
    }

    if text_type == 'poem':
        # Detect stanzas (separated by blank lines)
        stanzas = []
        current_stanza = []

        for i, line in enumerate(lines):
            if line.strip():
                current_stanza.append(i + 1)
            elif current_stanza:
                stanzas.append(current_stanza)
                current_stanza = []

        if current_stanza:
            stanzas.append(current_stanza)

        metadata['stanzas'] = stanzas
        metadata['stanza_count'] = len(stanzas)

    return metadata


def process_literary_message(message, text, selected_range, history):
    """Process a message about a literary text using Claude"""
    from anthropic import Anthropic
    from flask import session as flask_session

    # Get auth service URL
    AUTH_URL = os.getenv('AUTH_URL', 'http://auth-service:3001')

    # Build system prompt
    system_prompt = build_literary_system_prompt(text, selected_range)

    # Build conversation history for Claude
    claude_messages = []
    for msg in history:
        claude_messages.append({
            'role': msg['role'],
            'content': msg['content']
        })

    # Add current user message
    if selected_range:
        user_content = f"[Selected lines {selected_range['start']}-{selected_range['end']}]\n\n{message}"
    else:
        user_content = message

    claude_messages.append({
        'role': 'user',
        'content': user_content
    })

    # Call Claude
    try:
        # Get JWT token from session
        jwt_token = flask_session.get('access_token')

        # Fetch Claude API key from auth service
        claude_api_key = None
        try:
            url = f'{AUTH_URL}/api/auth/settings/claude-key'
            logger.info(f"Fetching Claude API key from: {url}")
            response = requests.get(
                url,
                headers={'Authorization': f'Bearer {jwt_token}'},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                claude_api_key = data.get('claude_api_key')
                logger.info(f"Claude API key fetched: {'YES' if claude_api_key else 'NO'}")
            else:
                logger.warning(f"Failed to fetch Claude key: {response.status_code}")
        except Exception as e:
            logger.error(f"Could not fetch Claude API key: {e}")
            return f"I apologize, but I couldn't retrieve the API key: {str(e)}"

        if not claude_api_key:
            return "I apologize, but no Claude API key is configured. Please add your API key in Settings."

        # Initialize Anthropic client with the API key
        client = Anthropic(api_key=claude_api_key)

        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=system_prompt,
            messages=claude_messages,
            temperature=0.7
        )

        # Extract text from response
        text_blocks = []
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                text_blocks.append(content_block.text)

        if text_blocks:
            return "\n".join(text_blocks)
        else:
            return "I apologize, but I couldn't generate a response."

    except Exception as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        return f"I apologize, but I encountered an error processing your message: {str(e)}"


def build_literary_system_prompt(text, selected_range):
    """Build system prompt for literary analysis"""

    prompt = f"""You are a knowledgeable and insightful literary companion. Your role is to help readers deeply explore and appreciate poetry, speeches, and literary texts across languages and cultures.

**Text being discussed:**
Title: {text['title']}
Author: {text['author'] or 'Unknown'}
Language: {text['source_language']}
Type: {text['text_type']}
"""

    if text.get('year'):
        prompt += f"Year: {text['year']}\n"
    if text.get('source'):
        prompt += f"Source: {text['source']}\n"

    prompt += f"""
**Full text:**
{text['content']}

---

**Your approach:**
- Provide cultural, historical, and linguistic context
- Explain archaic, obscure, or culturally-specific language
- Illuminate literary devices (metaphor, alliteration, imagery, etc.)
- Discuss themes, symbolism, and meaning
- Help non-native readers bridge language and cultural gaps
- Be conversational yet insightful
- Point out beauty and artistry in the language
- Reference specific line numbers when relevant

"""

    if selected_range:
        lines = text['content'].split('\n')
        start = selected_range['start'] - 1
        end = selected_range['end']
        selected_text = '\n'.join(lines[start:end])

        prompt += f"""
**The reader has selected lines {selected_range['start']}-{selected_range['end']}:**
{selected_text}

Focus your response on this selection while maintaining awareness of the full text's context.
"""

    return prompt


# ===== UTILITY ROUTES =====

@poetry_bp.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'poetry-companion'})
