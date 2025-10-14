// auth-service/index.js (Redis-free version)
const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { encrypt, decrypt } = require('./encryption');

// Load environment and secrets
const app = express();
const PORT = process.env.AUTH_PORT || 3001;

// JWT secret from file
const JWT_SECRET = process.env.JWT_SECRET_FILE 
  ? fs.readFileSync(process.env.JWT_SECRET_FILE, 'utf8').trim()
  : process.env.JWT_SECRET || crypto.randomBytes(64).toString('hex');

const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';
const JWT_REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_EXPIRES_IN || '7d';

// Database connection
const pool = new Pool({
  host: process.env.DB_HOST || 'postgresql',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'zettl_auth',
  password: process.env.DB_PASSWORD_FILE 
    ? fs.readFileSync(process.env.DB_PASSWORD_FILE, 'utf8').trim()
    : process.env.DB_PASSWORD,
  database: process.env.DB_NAME || 'zettl'
});

// Middleware
app.set('trust proxy', true); // Trust proxy headers (for Docker/nginx)
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : '*',
  credentials: true
}));
app.use(express.json());

// Rate limiting
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 requests per window
  message: 'Too many authentication attempts, please try again later'
});

const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 60 // 60 requests per minute
});

app.use('/api/', apiLimiter);
app.use('/api/auth/login', authLimiter);
app.use('/api/auth/register', authLimiter);

// Initialize database tables
async function initDatabase() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) DEFAULT 'user',
        api_key VARCHAR(255) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT true,
        metadata JSONB DEFAULT '{}'
      );

      CREATE TABLE IF NOT EXISTS refresh_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(500) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address VARCHAR(45),
        user_agent TEXT
      );

      CREATE TABLE IF NOT EXISTS api_keys (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        key_hash VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255),
        permissions JSONB DEFAULT '[]',
        last_used TIMESTAMP,
        expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      -- Create PostgreSQL roles for PostgREST
      DO $$ 
      BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_anon') THEN
          CREATE ROLE web_anon NOLOGIN;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
          CREATE ROLE authenticated NOLOGIN;
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticator') THEN
          CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD 'authenticator_pass';
          GRANT web_anon TO authenticator;
          GRANT authenticated TO authenticator;
        END IF;
      END $$;
    `);

    console.log('Database initialized successfully');
  } catch (error) {
    console.error('Database initialization error:', error);
    throw error;
  }
}

// Helper functions
function generateApiKey() {
  return 'zettl_' + crypto.randomBytes(32).toString('hex');
}

function hashApiKey(apiKey) {
  return crypto.createHash('sha256').update(apiKey).digest('hex');
}

function generateTokens(userId, username, role) {
  const accessToken = jwt.sign(
    { 
      sub: userId, 
      username, 
      role,
      iat: Math.floor(Date.now() / 1000)
    },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES_IN }
  );

  const refreshToken = jwt.sign(
    { 
      sub: userId,
      type: 'refresh',
      iat: Math.floor(Date.now() / 1000)
    },
    JWT_SECRET,
    { expiresIn: JWT_REFRESH_EXPIRES_IN }
  );

  return { accessToken, refreshToken };
}

// Middleware to verify JWT (simplified - no Redis blacklist)
async function verifyToken(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader) {
      return res.status(401).json({ error: 'No authorization header' });
    }

    const token = authHeader.replace('Bearer ', '');
    
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(401).json({ error: 'Invalid token' });
  }
}

// Middleware to verify API key (now CLI tokens)
async function verifyApiKey(req, res, next) {
  try {
    const apiKey = req.headers['x-api-key'];

    if (!apiKey) {
      return verifyToken(req, res, next); // Fall back to JWT auth
    }

    const keyHash = hashApiKey(apiKey);

    const result = await pool.query(
      `SELECT u.id, u.username, u.role
       FROM cli_tokens ct
       JOIN users u ON ct.user_id = u.id
       WHERE ct.token_hash = $1
         AND ct.is_active = true
         AND (ct.expires_at IS NULL OR ct.expires_at > NOW())`,
      [keyHash]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    // Update last used timestamp
    await pool.query(
      'UPDATE cli_tokens SET last_used = CURRENT_TIMESTAMP WHERE token_hash = $1',
      [keyHash]
    );

    req.user = {
      sub: result.rows[0].id,
      username: result.rows[0].username,
      role: result.rows[0].role
    };

    next();
  } catch (error) {
    console.error('API key verification error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// User registration
app.post('/api/auth/register', async (req, res) => {
  const { username, email, password } = req.body;

  if (!username || !email || !password) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  if (password.length < 8) {
    return res.status(400).json({ error: 'Password must be at least 8 characters' });
  }

  try {
    // Check if user already exists
    const existingUser = await pool.query(
      'SELECT id FROM users WHERE username = $1 OR email = $2',
      [username, email]
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: 'Username or email already exists' });
    }

    // Hash password
    const passwordHash = await bcrypt.hash(password, 10);

    // Create user
    const result = await pool.query(
      `INSERT INTO users (username, email, password_hash) 
       VALUES ($1, $2, $3) 
       RETURNING id, username, email, role, created_at`,
      [username, email, passwordHash]
    );

    const user = result.rows[0];
    const tokens = generateTokens(user.id, user.username, user.role);

    // Store refresh token
    await pool.query(
      `INSERT INTO refresh_tokens (user_id, token, expires_at, ip_address, user_agent) 
       VALUES ($1, $2, $3, $4, $5)`,
      [
        user.id,
        tokens.refreshToken,
        new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        req.ip,
        req.get('User-Agent')
      ]
    );

    res.status(201).json({
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role
      },
      ...tokens
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// User login
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Missing username or password' });
  }

  try {
    // Find user by username or email
    const result = await pool.query(
      `SELECT id, username, email, password_hash, role, is_active 
       FROM users 
       WHERE (username = $1 OR email = $1) AND is_active = true`,
      [username]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const user = result.rows[0];

    // Verify password
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate tokens
    const tokens = generateTokens(user.id, user.username, user.role);

    // Store refresh token
    await pool.query(
      `INSERT INTO refresh_tokens (user_id, token, expires_at, ip_address, user_agent) 
       VALUES ($1, $2, $3, $4, $5)`,
      [
        user.id,
        tokens.refreshToken,
        new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        req.ip,
        req.get('User-Agent')
      ]
    );

    // Update last login
    await pool.query(
      'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
      [user.id]
    );

    res.json({
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role
      },
      ...tokens
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Token refresh
app.post('/api/auth/refresh', async (req, res) => {
  const { refreshToken } = req.body;

  if (!refreshToken) {
    return res.status(400).json({ error: 'Refresh token required' });
  }

  try {
    // Verify refresh token exists and is valid
    const tokenResult = await pool.query(
      `SELECT rt.user_id, u.username, u.role 
       FROM refresh_tokens rt 
       JOIN users u ON rt.user_id = u.id 
       WHERE rt.token = $1 AND rt.expires_at > NOW()`,
      [refreshToken]
    );

    if (tokenResult.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid refresh token' });
    }

    const tokenData = tokenResult.rows[0];

    // Generate new access token
    const accessToken = jwt.sign(
      { 
        sub: tokenData.user_id, 
        username: tokenData.username, 
        role: tokenData.role,
        iat: Math.floor(Date.now() / 1000)
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    res.json({ accessToken });
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Refresh token expired' });
    }
    console.error('Token refresh error:', error);
    res.status(500).json({ error: 'Token refresh failed' });
  }
});

// Logout (simplified - just remove refresh tokens)
app.post('/api/auth/logout', verifyToken, async (req, res) => {
  try {
    // Remove refresh tokens for this user
    await pool.query(
      'DELETE FROM refresh_tokens WHERE user_id = $1',
      [req.user.sub]
    );

    res.json({ message: 'Logged out successfully' });
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({ error: 'Logout failed' });
  }
});

// Generate CLI token
app.post('/api/auth/api-key', verifyToken, async (req, res) => {
  const { name, permissions, expiresIn } = req.body;

  try {
    const apiKey = generateApiKey();
    const keyHash = hashApiKey(apiKey);

    const expiresAt = expiresIn
      ? new Date(Date.now() + expiresIn * 1000)
      : null;

    await pool.query(
      `INSERT INTO cli_tokens (user_id, token_hash, name, permissions, expires_at, is_active)
       VALUES ($1, $2, $3, $4, $5, true)`,
      [req.user.sub, keyHash, name || 'API Key', permissions || [], expiresAt]
    );

    res.json({
      apiKey, // Only returned once!
      name: name || 'API Key',
      expiresAt
    });
  } catch (error) {
    console.error('CLI token generation error:', error);
    res.status(500).json({ error: 'Failed to generate API key' });
  }
});

// List user's CLI tokens
app.get('/api/auth/api-keys', verifyToken, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT id, name, permissions, last_used, expires_at, created_at
       FROM cli_tokens
       WHERE user_id = $1 AND is_active = true
       ORDER BY created_at DESC`,
      [req.user.sub]
    );

    res.json(result.rows);
  } catch (error) {
    console.error('CLI tokens fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch API keys' });
  }
});

// Delete a CLI token
app.delete('/api/auth/api-keys/:keyId', verifyToken, async (req, res) => {
  const { keyId } = req.params;

  try {
    const result = await pool.query(
      'UPDATE cli_tokens SET is_active = false WHERE id = $1 AND user_id = $2 RETURNING id',
      [keyId, req.user.sub]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'API key not found' });
    }

    res.json({ message: 'API key deleted successfully' });
  } catch (error) {
    console.error('CLI token deletion error:', error);
    res.status(500).json({ error: 'Failed to delete API key' });
  }
});

// Convert CLI token to JWT token (for CLI usage)
app.post('/api/auth/token-from-key', async (req, res) => {
  const apiKey = req.headers['x-api-key'];

  if (!apiKey) {
    return res.status(401).json({ error: 'API key required' });
  }

  try {
    const keyHash = hashApiKey(apiKey);

    const result = await pool.query(
      `SELECT u.id, u.username, u.role
       FROM cli_tokens ct
       JOIN users u ON ct.user_id = u.id
       WHERE ct.token_hash = $1
         AND ct.is_active = true
         AND (ct.expires_at IS NULL OR ct.expires_at > NOW())`,
      [keyHash]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid or expired API key' });
    }

    const user = result.rows[0];

    // Update last_used timestamp
    await pool.query(
      'UPDATE cli_tokens SET last_used = CURRENT_TIMESTAMP WHERE token_hash = $1',
      [keyHash]
    );

    // Generate a JWT token
    const token = jwt.sign(
      {
        sub: user.id,
        username: user.username,
        role: user.role,
        iat: Math.floor(Date.now() / 1000)
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        role: user.role
      }
    });
  } catch (error) {
    console.error('API key to token conversion error:', error);
    res.status(500).json({ error: 'Token generation failed' });
  }
});

// Get user profile
app.get('/api/auth/profile', verifyToken, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT id, username, email, role, created_at, updated_at, last_login, metadata 
       FROM users WHERE id = $1`,
      [req.user.sub]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Profile fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch profile' });
  }
});

// Update password
app.post('/api/auth/change-password', verifyToken, async (req, res) => {
  const { currentPassword, newPassword } = req.body;

  if (!currentPassword || !newPassword) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  if (newPassword.length < 8) {
    return res.status(400).json({ error: 'New password must be at least 8 characters' });
  }

  try {
    // Get current password hash
    const result = await pool.query(
      'SELECT password_hash FROM users WHERE id = $1',
      [req.user.sub]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Verify current password
    const validPassword = await bcrypt.compare(currentPassword, result.rows[0].password_hash);
    if (!validPassword) {
      return res.status(401).json({ error: 'Current password is incorrect' });
    }

    // Update password
    const newPasswordHash = await bcrypt.hash(newPassword, 10);
    await pool.query(
      'UPDATE users SET password_hash = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2',
      [newPasswordHash, req.user.sub]
    );

    // Revoke all refresh tokens (force re-login)
    await pool.query(
      'DELETE FROM refresh_tokens WHERE user_id = $1',
      [req.user.sub]
    );

    res.json({ message: 'Password updated successfully' });
  } catch (error) {
    console.error('Password change error:', error);
    res.status(500).json({ error: 'Failed to change password' });
  }
});

// Validate token endpoint (for other services) - simplified
app.post('/api/auth/validate', async (req, res) => {
  const { token } = req.body;

  if (!token) {
    return res.status(400).json({ valid: false, error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);

    res.json({
      valid: true,
      user: {
        id: decoded.sub,
        username: decoded.username,
        role: decoded.role
      }
    });
  } catch (error) {
    res.status(401).json({ valid: false, error: 'Invalid token' });
  }
});

// Get user settings and CLI tokens
app.get('/api/auth/settings', verifyToken, async (req, res) => {
  try {
    // Get user settings
    const settingsResult = await pool.query(
      'SELECT claude_api_key, hidden_buttons, created_at, updated_at FROM user_settings WHERE user_id = $1',
      [req.user.sub]
    );

    // Get CLI tokens (excluding the actual token values)
    const tokensResult = await pool.query(
      `SELECT id, name, last_used, created_at, expires_at, is_active
       FROM cli_tokens
       WHERE user_id = $1 AND is_active = true
       ORDER BY created_at DESC`,
      [req.user.sub]
    );

    // Decrypt the Claude API key if it exists
    const encryptedKey = settingsResult.rows[0]?.claude_api_key;
    let decryptedKey = null;

    if (encryptedKey) {
      try {
        decryptedKey = decrypt(encryptedKey);
      } catch (decryptError) {
        console.error('Failed to decrypt Claude API key:', decryptError);
        // Return null if decryption fails (key might be corrupted or using old format)
        decryptedKey = null;
      }
    }

    res.json({
      claude_api_key: decryptedKey,
      hidden_buttons: settingsResult.rows[0]?.hidden_buttons || [],
      cli_tokens: tokensResult.rows
    });
  } catch (error) {
    console.error('Settings fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch settings' });
  }
});

// Update Claude API key
app.post('/api/auth/settings/claude-key', verifyToken, async (req, res) => {
  const { api_key } = req.body;

  try {
    // Encrypt the API key before storing
    const encryptedKey = api_key ? encrypt(api_key) : null;

    // Check if user_settings row exists
    const existing = await pool.query(
      'SELECT user_id FROM user_settings WHERE user_id = $1',
      [req.user.sub]
    );

    if (existing.rows.length > 0) {
      // Update existing row
      await pool.query(
        'UPDATE user_settings SET claude_api_key = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2',
        [encryptedKey, req.user.sub]
      );
    } else {
      // Insert new row
      await pool.query(
        'INSERT INTO user_settings (user_id, claude_api_key) VALUES ($1, $2)',
        [req.user.sub, encryptedKey]
      );
    }

    res.json({ message: 'Claude API key updated successfully' });
  } catch (error) {
    console.error('Claude API key update error:', error);
    res.status(500).json({ error: 'Failed to update API key' });
  }
});

// Update hidden buttons preference
app.post('/api/auth/settings/hidden-buttons', verifyToken, async (req, res) => {
  const { hidden_buttons } = req.body;

  // Validate that hidden_buttons is an array
  if (!Array.isArray(hidden_buttons)) {
    return res.status(400).json({ error: 'hidden_buttons must be an array' });
  }

  try {
    // Check if user_settings row exists
    const existing = await pool.query(
      'SELECT user_id FROM user_settings WHERE user_id = $1',
      [req.user.sub]
    );

    if (existing.rows.length > 0) {
      // Update existing row
      await pool.query(
        'UPDATE user_settings SET hidden_buttons = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2',
        [JSON.stringify(hidden_buttons), req.user.sub]
      );
    } else {
      // Insert new row
      await pool.query(
        'INSERT INTO user_settings (user_id, hidden_buttons) VALUES ($1, $2)',
        [req.user.sub, JSON.stringify(hidden_buttons)]
      );
    }

    res.json({ message: 'Button preferences updated successfully' });
  } catch (error) {
    console.error('Hidden buttons update error:', error);
    res.status(500).json({ error: 'Failed to update button preferences' });
  }
});

// Generate CLI token
app.post('/api/auth/cli-token', verifyToken, async (req, res) => {
  const { name, expiresIn } = req.body;

  try {
    // Generate a CLI token (similar format to API keys)
    const token = 'zettl_' + crypto.randomBytes(32).toString('hex');
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

    const expiresAt = expiresIn
      ? new Date(Date.now() + expiresIn * 1000)
      : null;

    // Insert into cli_tokens table
    const result = await pool.query(
      `INSERT INTO cli_tokens (user_id, token_hash, name, expires_at, is_active)
       VALUES ($1, $2, $3, $4, true)
       RETURNING id, name, created_at, expires_at`,
      [req.user.sub, tokenHash, name || 'CLI Token', expiresAt]
    );

    res.json({
      token, // Only returned once!
      id: result.rows[0].id,
      name: result.rows[0].name,
      created_at: result.rows[0].created_at,
      expires_at: result.rows[0].expires_at
    });
  } catch (error) {
    console.error('CLI token generation error:', error);
    res.status(500).json({ error: 'Failed to generate CLI token' });
  }
});

// Delete/revoke a CLI token
app.delete('/api/auth/cli-token/:tokenId', verifyToken, async (req, res) => {
  const { tokenId } = req.params;

  try {
    // Soft delete by setting is_active to false
    const result = await pool.query(
      'UPDATE cli_tokens SET is_active = false WHERE id = $1 AND user_id = $2 RETURNING id',
      [tokenId, req.user.sub]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'CLI token not found' });
    }

    res.json({ message: 'CLI token revoked successfully' });
  } catch (error) {
    console.error('CLI token deletion error:', error);
    res.status(500).json({ error: 'Failed to revoke CLI token' });
  }
});

// Validate CLI token and update last_used
app.post('/api/auth/validate-cli-token', async (req, res) => {
  const cliToken = req.headers['x-api-key'] || req.body.token;

  if (!cliToken) {
    return res.status(401).json({ error: 'No CLI token provided' });
  }

  try {
    const tokenHash = crypto.createHash('sha256').update(cliToken).digest('hex');

    const result = await pool.query(
      `SELECT ct.id, ct.user_id, u.username, u.role
       FROM cli_tokens ct
       JOIN users u ON ct.user_id = u.id
       WHERE ct.token_hash = $1
         AND ct.is_active = true
         AND (ct.expires_at IS NULL OR ct.expires_at > NOW())`,
      [tokenHash]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid or expired CLI token' });
    }

    const tokenData = result.rows[0];

    // Update last_used timestamp
    await pool.query(
      'UPDATE cli_tokens SET last_used = CURRENT_TIMESTAMP WHERE id = $1',
      [tokenData.id]
    );

    res.json({
      valid: true,
      user: {
        id: tokenData.user_id,
        username: tokenData.username,
        role: tokenData.role
      }
    });
  } catch (error) {
    console.error('CLI token validation error:', error);
    res.status(500).json({ error: 'Token validation failed' });
  }
});

// Get Claude API key (accepts both JWT and CLI token auth)
app.get('/api/auth/settings/claude-key', async (req, res) => {
  try {
    let userId;

    // Check for JWT token first
    const authHeader = req.headers['authorization'];
    if (authHeader && authHeader.startsWith('Bearer ')) {
      const token = authHeader.substring(7);
      try {
        const decoded = jwt.verify(token, JWT_SECRET);
        userId = decoded.sub;
      } catch (err) {
        return res.status(401).json({ error: 'Invalid JWT token' });
      }
    }
    // Otherwise check for CLI token
    else {
      const cliToken = req.headers['x-api-key'];
      if (!cliToken) {
        return res.status(401).json({ error: 'No authentication provided' });
      }

      const tokenHash = crypto.createHash('sha256').update(cliToken).digest('hex');

      // Validate token and get user_id
      const tokenResult = await pool.query(
        `SELECT user_id FROM cli_tokens
         WHERE token_hash = $1
           AND is_active = true
           AND (expires_at IS NULL OR expires_at > NOW())`,
        [tokenHash]
      );

      if (tokenResult.rows.length === 0) {
        return res.status(401).json({ error: 'Invalid or expired CLI token' });
      }

      userId = tokenResult.rows[0].user_id;
    }

    // Get Claude API key
    const settingsResult = await pool.query(
      'SELECT claude_api_key FROM user_settings WHERE user_id = $1',
      [userId]
    );

    const encryptedKey = settingsResult.rows[0]?.claude_api_key || null;

    // Decrypt the API key if it exists
    let decryptedKey = null;
    if (encryptedKey) {
      try {
        decryptedKey = decrypt(encryptedKey);
      } catch (decryptError) {
        console.error('Failed to decrypt Claude API key:', decryptError);
        // Return null if decryption fails (key might be corrupted or using old format)
        decryptedKey = null;
      }
    }

    res.json({
      claude_api_key: decryptedKey
    });
  } catch (error) {
    console.error('Claude API key fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch Claude API key' });
  }
});

// Start server
async function start() {
  try {
    await initDatabase();
    
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`Auth service running on port ${PORT} (Redis-free!)`);
    });
  } catch (error) {
    console.error('Failed to start auth service:', error);
    process.exit(1);
  }
}

start();

module.exports = app;
