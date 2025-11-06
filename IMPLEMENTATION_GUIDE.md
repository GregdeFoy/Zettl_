# Neo-Brutalist Theme Implementation Guide

## Overview
This guide outlines how to integrate the neo-brutalist design as an optional theme alongside the existing CLI interface in the Zettl web application.

## Implementation Approach

### 1. Theme System Architecture

```javascript
// Theme manager to be added to index.html
const ThemeManager = {
    themes: {
        cli: {
            name: 'CLI Classic',
            cssFile: null, // Uses existing inline styles
            layout: 'terminal'
        },
        neo: {
            name: 'Neo-Brutalist',
            cssFile: '/static/neo-brutalist.css',
            layout: 'grid'
        }
    },

    current: localStorage.getItem('zettl-theme') || 'cli',

    switch(themeName) {
        if (this.themes[themeName]) {
            this.current = themeName;
            localStorage.setItem('zettl-theme', themeName);
            this.apply();
        }
    },

    apply() {
        document.body.setAttribute('data-theme', this.current);
        document.body.setAttribute('data-layout', this.themes[this.current].layout);

        // Load theme-specific CSS if needed
        if (this.themes[this.current].cssFile) {
            this.loadCSS(this.themes[this.current].cssFile);
        }

        // Trigger layout rebuild
        this.rebuildLayout();
    }
};
```

### 2. Database Schema Addition

Add a user preference for theme selection:

```sql
-- Add to users table or create preferences table
ALTER TABLE users ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'cli';

-- Or create a dedicated preferences table
CREATE TABLE user_preferences (
    user_id INTEGER REFERENCES users(id),
    preference_key VARCHAR(50),
    preference_value TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, preference_key)
);
```

### 3. Flask Backend Updates

#### Add theme endpoints to `zettl_web.py`:

```python
@app.route('/api/settings/theme', methods=['GET', 'POST'])
@jwt_required
def handle_theme():
    user_id = get_jwt_identity()

    if request.method == 'GET':
        # Fetch current theme preference
        theme = get_user_theme(user_id)
        return jsonify({'theme': theme or 'cli'})

    elif request.method == 'POST':
        data = request.get_json()
        theme = data.get('theme', 'cli')

        if theme not in ['cli', 'neo']:
            return jsonify({'error': 'Invalid theme'}), 400

        # Save theme preference
        set_user_theme(user_id, theme)
        return jsonify({'success': True, 'theme': theme})

@app.route('/static/neo-brutalist.css')
def serve_neo_css():
    """Serve the neo-brutalist CSS file"""
    return send_file('static/neo-brutalist.css', mimetype='text/css')
```

### 4. Template Structure Updates

#### Modify `index.html` structure:

```html
<!-- Add theme switcher to header -->
<div class="header" id="header">
    <div class="header-left">
        <span class="logo">zettl</span>
        <div class="theme-switcher">
            <button class="theme-btn" data-theme="cli">CLI</button>
            <button class="theme-btn" data-theme="neo">NEO</button>
        </div>
    </div>
    <!-- ... rest of header ... -->
</div>

<!-- Conditional layout rendering -->
<div id="app-container" data-theme="cli" data-layout="terminal">
    <!-- Terminal Layout (existing) -->
    <div class="terminal-layout">
        <!-- Current terminal interface -->
    </div>

    <!-- Grid Layout (neo-brutalist) -->
    <div class="grid-layout" style="display: none;">
        <aside class="nav-panel">
            <!-- Navigation -->
        </aside>
        <main class="main-panel">
            <!-- Main content -->
        </main>
        <aside class="context-panel">
            <!-- Context/Chat -->
        </aside>
    </div>
</div>
```

### 5. CSS Organization

Create a modular CSS structure:

```css
/* base.css - Shared across themes */
:root {
    --transition-speed: 0.3s;
    --border-radius: 0; /* Neo-brutalist: 0, CLI: 4px */
}

/* cli-theme.css - Terminal theme variables */
[data-theme="cli"] {
    --bg-primary: #1a1a1a;
    --text-primary: #f0f0f0;
    --accent: #90ee90;
    /* ... existing CLI theme ... */
}

/* neo-theme.css - Neo-brutalist theme variables */
[data-theme="neo"] {
    --bg-primary: #FFFEF2;
    --bg-secondary: #000000;
    --accent-1: #FF6B6B;
    --accent-2: #4ECDC4;
    --accent-3: #FFE66D;
    --text-primary: #000000;
    --text-secondary: #FFFFFF;
    --border: #000000;
    --border-width: 4px;
    --shadow-offset: 8px;
}

/* Layout-specific styles */
[data-layout="terminal"] .terminal-layout {
    display: flex;
}

[data-layout="terminal"] .grid-layout {
    display: none;
}

[data-layout="grid"] .terminal-layout {
    display: none;
}

[data-layout="grid"] .grid-layout {
    display: grid;
    grid-template-columns: 250px 1fr 350px;
    gap: 20px;
}
```

### 6. Component Adaptation

Make existing components theme-aware:

```javascript
// Adapt command execution to work in both layouts
class CommandExecutor {
    constructor() {
        this.theme = ThemeManager.current;
    }

    execute(command) {
        if (this.theme === 'cli') {
            this.executeTerminal(command);
        } else {
            this.executeNeo(command);
        }
    }

    executeTerminal(command) {
        // Existing terminal-style output
        addToTerminal(formatOutput(result));
    }

    executeNeo(command) {
        // Neo-brutalist card-based output
        addNoteCard(result);
    }
}
```

### 7. Migration Path

#### Phase 1: Preparation (Week 1)
- [ ] Create theme CSS files
- [ ] Add theme preference to database
- [ ] Implement theme API endpoints

#### Phase 2: Dual Layout (Week 2)
- [ ] Build neo-brutalist layout HTML structure
- [ ] Implement theme switcher UI
- [ ] Create layout-specific JavaScript handlers

#### Phase 3: Feature Parity (Week 3)
- [ ] Ensure all CLI commands work in neo mode
- [ ] Adapt chat interface for both layouts
- [ ] Test responsive design in both themes

#### Phase 4: Polish & Launch (Week 4)
- [ ] Performance optimization
- [ ] User testing
- [ ] Documentation updates
- [ ] Gradual rollout with feature flag

### 8. Feature Flags

Use feature flags for gradual rollout:

```python
# In zettl_web.py
FEATURE_FLAGS = {
    'neo_theme': os.environ.get('ENABLE_NEO_THEME', 'false') == 'true'
}

@app.route('/api/features')
def get_features():
    return jsonify(FEATURE_FLAGS)
```

```javascript
// In index.html
async function initializeApp() {
    const features = await fetch('/api/features').then(r => r.json());

    if (features.neo_theme) {
        document.querySelector('.theme-switcher').style.display = 'flex';
        ThemeManager.init();
    }
}
```

### 9. Backwards Compatibility

Ensure zero disruption to existing users:

1. **Default to CLI theme** for all existing users
2. **Preserve all CLI functionality** in neo mode
3. **Share data layer** between themes (same API calls)
4. **Maintain keyboard shortcuts** in both modes
5. **Keep URL structure** consistent

### 10. Performance Considerations

```javascript
// Lazy load neo-brutalist assets
const loadNeoAssets = async () => {
    if (ThemeManager.current === 'neo' && !window.neoAssetsLoaded) {
        // Load neo-specific CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/neo-brutalist.css';
        document.head.appendChild(link);

        // Load neo-specific JavaScript modules
        await import('./neo-components.js');

        window.neoAssetsLoaded = true;
    }
};
```

### 11. Testing Strategy

#### Unit Tests
```python
def test_theme_persistence():
    """Test that theme preference persists across sessions"""
    user = create_test_user()
    set_user_theme(user.id, 'neo')
    assert get_user_theme(user.id) == 'neo'

def test_theme_api_validation():
    """Test that only valid themes are accepted"""
    response = client.post('/api/settings/theme',
                          json={'theme': 'invalid'})
    assert response.status_code == 400
```

#### E2E Tests
```javascript
describe('Theme Switcher', () => {
    it('should switch between CLI and Neo themes', () => {
        cy.visit('/');
        cy.get('[data-theme="neo"]').click();
        cy.get('body').should('have.attr', 'data-theme', 'neo');
        cy.reload();
        cy.get('body').should('have.attr', 'data-theme', 'neo');
    });
});
```

### 12. Rollback Plan

If issues arise:

1. **Quick disable**: Set `ENABLE_NEO_THEME=false` in environment
2. **Database revert**: `UPDATE users SET theme_preference = 'cli';`
3. **Cache clear**: Force browser cache refresh
4. **Communication**: Notify users of temporary theme unavailability

## Benefits of This Approach

1. **Non-disruptive**: Existing users see no change unless they opt-in
2. **Incremental**: Can be developed and tested in phases
3. **Reversible**: Easy rollback if needed
4. **Performant**: Lazy loading keeps initial load fast
5. **Maintainable**: Clear separation between themes
6. **Extensible**: Easy to add more themes in future

## Next Steps

1. Review this implementation plan with the team
2. Set up feature flag infrastructure
3. Create static CSS files for neo-brutalist theme
4. Begin Phase 1 implementation
5. Gather user feedback through beta testing

## Estimated Timeline

- **Total Duration**: 4 weeks
- **Development**: 3 weeks
- **Testing & Polish**: 1 week
- **Gradual Rollout**: 2 weeks after launch

This implementation ensures Zettl maintains its minimalist philosophy while offering users a more visually expressive option that better utilizes screen real estate.