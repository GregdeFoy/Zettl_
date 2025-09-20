// auth-service/index.js
const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const Redis = require('ioredis');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

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

// Redis connection for session management
const redis = new Redis({
  host: process.env.REDIS_HOST || 'redis',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD_FILE
    ? fs.readFileSync(process.env.REDIS_PASSWORD_FILE, 'utf8').trim()
    : process.env.REDIS_PASSWORD
});

// Middleware
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

// Middleware to verify JWT
async function verifyToken(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader) {
      return res.status(401).json({ error: 'No authorization header' });
    }

    const token = authHeader.replace('Bearer ', '');
    
    // Check if token is blacklisted in Redis
    const isBlacklisted = await redis.get(`blacklist:${token}`);
    if (isBlacklisted) {
      return res.status(401).json({ error: 'Token has been revoked' });
    }

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

// Middleware to verify API key
async function verifyApiKey(req, res, next) {
  try {
    const apiKey = req.headers['x-api-key'];
    
    if (!apiKey) {
      return verifyToken(req, res, next); // Fall back to JWT auth
    }

    const keyHash = hashApiKey(apiKey);
    
    const result = await pool.query(
      `SELECT u.*, ak.permissions, ak.expires_at 
       FROM api_keys ak 
       JOIN users u ON ak.user_id = u.id 
       WHERE ak.key_hash = $1 AND u.is_active = true`,
      [keyHash]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    const keyData = result.rows[0];
    
    if (keyData.expires_at && new Date(keyData.expires_at) < new Date()) {
      return res.status(401).json({ error: 'API key expired' });
    }

    // Update last_used timestamp
    await pool.query(
      'UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE key_hash = $1',
      [keyHash]
    );

    req.user = {
      sub: keyData.id,
      username: keyData.username,
      role: keyData.role,
      permissions: keyData.permissions
    };

    next();
  } catch (error) {
    console.error('API key verification error:', error);
    res.status(500).json({ error: 'Authentication error' });
  }
}

// Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'auth', timestamp: new Date() });
});

// Register new user
app.post('/api/auth/register', async (req, res) => {
  const { username, email, password } = req.body;

  if (!username || !email || !password) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  if (password.length < 8) {
    return res.status(400).json({ error: 'Password must be at least 8 characters' });
  }

  try {
    // Check if user exists
    const existingUser = await pool.query(
      'SELECT id FROM users WHERE username = $1 OR email = $2',
      [username, email]
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: 'User already exists' });
    }

    // Hash password
    const passwordHash = await bcrypt.hash(password, 10);

    // Create user
    const result = await pool.query(
      `INSERT INTO users (username, email, password_hash) 
       VALUES ($1, $2, $3) 
       RETURNING id, username, role`,
      [username, email, passwordHash]
    );

    const user = result.rows[0];
    const { accessToken, refreshToken } = generateTokens(user.id, user.username, user.role);

    // Store refresh token
    await pool.query(
      `INSERT INTO refresh_tokens (user_id, token, expires_at, ip_address, user_agent)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        user.id,
        refreshToken,
        new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        req.ip,
        req.headers['user-agent']
      ]
    );

    res.status(201).json({
      user: {
        id: user.id,
        username: user.username,
        email: email,
        role: user.role
      },
      accessToken,
      refreshToken
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Missing credentials' });
  }

  try {
    // Get user
    const result = await pool.query(
      'SELECT * FROM users WHERE (username = $1 OR email = $1) AND is_active = true',
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

    // Update last login
    await pool.query(
      'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
      [user.id]
    );

    // Generate tokens
    const { accessToken, refreshToken } = generateTokens(user.id, user.username, user.role);

    // Store refresh token
    await pool.query(
      `INSERT INTO refresh_tokens (user_id, token, expires_at, ip_address, user_agent)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        user.id,
        refreshToken,
        new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        req.ip,
        req.headers['user-agent']
      ]
    );

    res.json({
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role
      },
      accessToken,
      refreshToken
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Refresh token
app.post('/api/auth/refresh', async (req, res) => {
  const { refreshToken } = req.body;

  if (!refreshToken) {
    return res.status(400).json({ error: 'Refresh token required' });
  }

  try {
    // Verify refresh token
    const decoded = jwt.verify(refreshToken, JWT_SECRET);
    
    if (decoded.type !== 'refresh') {
      return res.status(401).json({ error: 'Invalid token type' });
    }

    // Check if token exists in database
    const tokenResult = await pool.query(
      `SELECT rt.*, u.username, u.role 
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

// Logout (revoke tokens)
app.post('/api/auth/logout', verifyToken, async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    const token = authHeader.replace('Bearer ', '');
    
    // Blacklist the current access token
    await redis.set(
      `blacklist:${token}`,
      '1',
      'EX',
      24 * 60 * 60 // 24 hours
    );

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

// Generate API key
app.post('/api/auth/api-key', verifyToken, async (req, res) => {
  const { name, permissions, expiresIn } = req.body;

  try {
    const apiKey = generateApiKey();
    const keyHash = hashApiKey(apiKey);
    
    const expiresAt = expiresIn 
      ? new Date(Date.now() + expiresIn * 1000)
      : null;

    await pool.query(
      `INSERT INTO api_keys (user_id, key_hash, name, permissions, expires_at)
       VALUES ($1, $2, $3, $4, $5)`,
      [req.user.sub, keyHash, name || 'API Key', permissions || [], expiresAt]
    );

    res.json({
      apiKey, // Only returned once!
      name: name || 'API Key',
      expiresAt
    });
  } catch (error) {
    console.error('API key generation error:', error);
    res.status(500).json({ error: 'Failed to generate API key' });
  }
});

// List API keys
app.get('/api/auth/api-keys', verifyToken, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT id, name, permissions, last_used, expires_at, created_at
       FROM api_keys
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [req.user.sub]
    );

    res.json(result.rows);
  } catch (error) {
    console.error('API key listing error:', error);
    res.status(500).json({ error: 'Failed to list API keys' });
  }
});

// Revoke API key
app.delete('/api/auth/api-key/:id', verifyToken, async (req, res) => {
  try {
    const result = await pool.query(
      'DELETE FROM api_keys WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.sub]
    );

    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'API key not found' });
    }

    res.json({ message: 'API key revoked' });
  } catch (error) {
    console.error('API key revocation error:', error);
    res.status(500).json({ error: 'Failed to revoke API key' });
  }
});

// Get user profile
app.get('/api/auth/profile', verifyApiKey, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT id, username, email, role, created_at, last_login FROM users WHERE id = $1',
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

// Validate token endpoint (for other services)
app.post('/api/auth/validate', async (req, res) => {
  const { token } = req.body;

  if (!token) {
    return res.status(400).json({ valid: false, error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Check if token is blacklisted
    const isBlacklisted = await redis.get(`blacklist:${token}`);
    if (isBlacklisted) {
      return res.status(401).json({ valid: false, error: 'Token has been revoked' });
    }

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

// Start server
async function start() {
  try {
    await initDatabase();
    
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`Auth service running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start auth service:', error);
    process.exit(1);
  }
}

start();

module.exports = app;
