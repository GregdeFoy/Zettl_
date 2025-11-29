# Verse - Poetry Companion - Setup Guide

## Overview

**Verse** is a new feature for Zettl that allows you to explore literary texts (poems, speeches, prose) with AI assistance. It features a split-screen interface with the text on the left and a conversational AI chat on the right.

Access it via the **VERSE** button in the main Zettl header - seamlessly toggle between note-taking and literary exploration.

## Architecture

### File Structure
```
zettl_web/
├── zettl_web.py           # Main Flask app (includes poetry blueprint registration)
├── poetry_web.py          # NEW: Poetry companion routes & logic
└── templates/
    └── poetry.html        # NEW: Poetry companion UI
```

### Database Tables
- `texts` - Literary texts (poems, speeches, etc.)
- `text_conversations` - Conversations about specific texts
- `text_messages` - Messages within conversations

## Setup Instructions

### 1. Run the Database Migration

```bash
# Navigate to migrations directory
cd /home/greg/zettl/migrations

# Run the migration
./run_migration.sh add_poetry_tables.sql
```

Or manually:
```bash
psql -U postgres -d zettl -f migrations/add_poetry_tables.sql
```

### 2. Verify the Blueprint Registration

The blueprint is already registered in `zettl_web.py` at lines 76-79:
```python
from poetry_web import poetry_bp
app.register_blueprint(poetry_bp, url_prefix='/poetry')
```

### 3. Restart the Web Service

If using Docker:
```bash
docker-compose restart zettl-web
```

Or restart your Flask development server.

### 4. Access Verse

- **From Zettl Notes**: Click the **VERSE** button in the header
- **Direct URL**: `http://localhost:8080/poetry` (or your configured domain)
- **From Verse**: Click **NOTES** to return to the main app

The integration is seamless - both apps share the same authentication session.

## Features

### Text Management
- **Add Text**: Click "NEW TEXT" button to open a light-touch bottom sheet
- **Paste Content**: Copy/paste poems, speeches, or prose preserving line breaks
- **Metadata**: Add title, author, language, year, source

### Text Display
- **Beautiful Typography**: Uses Crimson Text serif font for literary texts
- **Line Numbers**: Subtle line numbers on the left
- **Stanza Separation**: Blank lines create visual stanza breaks
- **Selection**: Click and drag to select lines

### Selection Mechanism
- **Line-first**: Clicking selects full lines (to line break)
- **Multi-line**: Click and drag to select multiple lines
- **Selection Menu**: Popup menu appears on selection with "Discuss this passage" button

### Conversations
- **Multiple Conversations**: Have several conversations about the same text
- **Conversation Selector**: Tabs above chat area to switch between conversations
- **New Conversation**: Click "+" button to create a new conversation
- **Context-aware**: AI has access to full text and conversation history

### AI Chat
- **Literary Analysis**: AI provides context, explains language, discusses themes
- **Selection Context**: When you select text, it's included in your message
- **Line References**: AI can reference specific line numbers
- **Cultural/Historical Context**: Helps bridge language and cultural gaps

## Usage Example

1. Click "NEW TEXT" button
2. Fill in:
   - Title: "The Raven"
   - Author: "Edgar Allan Poe"
   - Language: English
   - Type: Poem
   - Year: 1845
   - Paste the full poem in the content area
3. Click "Add Text"
4. Select lines from the poem
5. Click "Discuss this passage"
6. Ask questions in the chat about the selected lines

## API Endpoints

### Texts
- `GET /poetry/api/texts` - List all texts
- `POST /poetry/api/texts` - Create new text
- `GET /poetry/api/texts/:id` - Get specific text
- `PUT /poetry/api/texts/:id` - Update text
- `DELETE /poetry/api/texts/:id` - Delete text

### Conversations
- `GET /poetry/api/texts/:id/conversations` - List conversations for text
- `POST /poetry/api/texts/:id/conversations` - Create new conversation
- `GET /poetry/api/conversations/:id/messages` - Get conversation messages
- `POST /poetry/api/conversations/:id/messages` - Send message

## Customization

### Styling
Edit `templates/poetry.html` CSS variables:
```css
--purple: #9D4EDD;  /* Header color */
--cyan: #00D9FF;    /* User messages */
--yellow: #FFCC00;  /* Selection highlight */
```

### Fonts
Currently uses:
- **UI**: JetBrains Mono (monospace)
- **Poetry**: Crimson Text (serif)
- **Headers**: Space Grotesk (sans-serif)

### LLM Prompt
Edit the system prompt in `poetry_web.py` function `build_literary_system_prompt()` to customize AI behavior.

## Next Steps

Potential enhancements:
1. Text library/browser view
2. Import from Project Gutenberg API
3. Export annotations/conversations
4. Sharing texts with other users
5. Public text repository
6. Audio reading integration
7. Translation features
8. Citation generation

## Troubleshooting

### "Authentication required" error
- Make sure you're logged into Zettl
- The poetry companion uses the same authentication as the notes app

### Blueprint not found error
- Ensure `poetry_web.py` is in the same directory as `zettl_web.py`
- Check the import path in `zettl_web.py`

### Database errors
- Run the migration: `migrations/add_poetry_tables.sql`
- Check that RLS policies are properly configured
- Verify user_id is being set correctly in JWT claims

### Selection not working
- Ensure JavaScript is enabled
- Check browser console for errors
- Try refreshing the page

## Development Notes

### Separation from Main App
The Poetry Companion is intentionally separated into its own blueprint to:
- Keep code modular and maintainable
- Allow independent development
- Share infrastructure (auth, database, LLM) with Zettl
- Enable easy feature toggling

### Shared Resources
- Authentication service
- PostgreSQL database
- PostgREST API
- Claude API key from settings
- Nginx/Cloudflare infrastructure

### Design Philosophy
- Neo-brutalist aesthetic matching Zettl
- Keyboard-friendly (though less vim-like)
- Mobile-responsive split-screen
- Light-touch interfaces (bottom sheets)
- Fast, minimal dependencies
