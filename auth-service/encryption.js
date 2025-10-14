// encryption.js - Utility for encrypting/decrypting sensitive data
const crypto = require('crypto');
const fs = require('fs');

// Algorithm configuration
const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16; // 16 bytes for AES
const AUTH_TAG_LENGTH = 16; // 16 bytes for GCM auth tag
const SALT_LENGTH = 64; // 64 bytes salt

/**
 * Get encryption key from environment or file
 */
function getEncryptionKey() {
  // Try to get from file first (Docker secret)
  if (process.env.ENCRYPTION_KEY_FILE) {
    try {
      return fs.readFileSync(process.env.ENCRYPTION_KEY_FILE, 'utf8').trim();
    } catch (error) {
      console.error('Failed to read encryption key from file:', error);
    }
  }

  // Fall back to environment variable
  const key = process.env.ENCRYPTION_KEY;

  if (!key) {
    throw new Error('ENCRYPTION_KEY or ENCRYPTION_KEY_FILE must be set in environment');
  }

  return key;
}

/**
 * Derive a 32-byte key from the encryption key using PBKDF2
 */
function deriveKey(encryptionKey, salt) {
  return crypto.pbkdf2Sync(
    encryptionKey,
    salt,
    100000, // iterations
    32, // key length (256 bits)
    'sha256'
  );
}

/**
 * Encrypt a string value
 * @param {string} plaintext - The value to encrypt
 * @returns {string} - Base64-encoded encrypted value with format: salt:iv:authTag:ciphertext
 */
function encrypt(plaintext) {
  if (!plaintext) {
    return null;
  }

  try {
    const encryptionKey = getEncryptionKey();

    // Generate random salt and IV
    const salt = crypto.randomBytes(SALT_LENGTH);
    const iv = crypto.randomBytes(IV_LENGTH);

    // Derive encryption key from the master key
    const key = deriveKey(encryptionKey, salt);

    // Create cipher
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

    // Encrypt the plaintext
    let encrypted = cipher.update(plaintext, 'utf8', 'base64');
    encrypted += cipher.final('base64');

    // Get the auth tag
    const authTag = cipher.getAuthTag();

    // Combine salt, IV, auth tag, and encrypted data
    // Format: salt:iv:authTag:ciphertext
    const result = [
      salt.toString('base64'),
      iv.toString('base64'),
      authTag.toString('base64'),
      encrypted
    ].join(':');

    return result;
  } catch (error) {
    console.error('Encryption error:', error);
    throw new Error('Failed to encrypt data');
  }
}

/**
 * Decrypt an encrypted string
 * @param {string} encryptedData - Base64-encoded encrypted value with format: salt:iv:authTag:ciphertext
 * @returns {string} - The decrypted plaintext
 */
function decrypt(encryptedData) {
  if (!encryptedData) {
    return null;
  }

  try {
    const encryptionKey = getEncryptionKey();

    // Parse the encrypted data
    const parts = encryptedData.split(':');

    if (parts.length !== 4) {
      throw new Error('Invalid encrypted data format');
    }

    const salt = Buffer.from(parts[0], 'base64');
    const iv = Buffer.from(parts[1], 'base64');
    const authTag = Buffer.from(parts[2], 'base64');
    const encrypted = parts[3];

    // Derive the same key
    const key = deriveKey(encryptionKey, salt);

    // Create decipher
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    // Decrypt
    let decrypted = decipher.update(encrypted, 'base64', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  } catch (error) {
    console.error('Decryption error:', error);
    throw new Error('Failed to decrypt data');
  }
}

/**
 * Generate a random encryption key (for initial setup)
 * @returns {string} - A random 64-character hex string
 */
function generateEncryptionKey() {
  return crypto.randomBytes(32).toString('hex');
}

module.exports = {
  encrypt,
  decrypt,
  generateEncryptionKey,
  getEncryptionKey
};
