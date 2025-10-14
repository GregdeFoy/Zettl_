#!/usr/bin/env node
/**
 * Migration script to encrypt existing plaintext Claude API keys
 *
 * This script:
 * 1. Fetches all user_settings with claude_api_key
 * 2. Checks if each key is already encrypted
 * 3. Encrypts plaintext keys and updates the database
 *
 * Usage: node migrate-encrypt-keys.js
 */

const { Pool } = require('pg');
const { encrypt, decrypt } = require('./encryption');
const fs = require('fs');
const path = require('path');

// Load environment from parent directory
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Database connection
let dbPassword;
if (process.env.DB_PASSWORD_FILE) {
  dbPassword = fs.readFileSync(process.env.DB_PASSWORD_FILE, 'utf8').trim();
} else if (process.env.DB_PASSWORD) {
  dbPassword = process.env.DB_PASSWORD;
} else {
  // Try default location for local development
  const defaultPasswordFile = path.join(__dirname, '..', 'secrets', 'db_auth_password');
  if (fs.existsSync(defaultPasswordFile)) {
    dbPassword = fs.readFileSync(defaultPasswordFile, 'utf8').trim();
  }
}

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'zettl_auth',
  password: dbPassword,
  database: process.env.DB_NAME || 'zettl'
});

/**
 * Check if a string is already encrypted
 */
function isEncrypted(value) {
  if (!value) return false;

  // Encrypted values have the format: salt:iv:authTag:ciphertext
  // All parts are base64 encoded, so we check for the presence of colons
  const parts = value.split(':');

  // Must have exactly 4 parts
  if (parts.length !== 4) {
    return false;
  }

  // Try to decrypt it to be sure
  try {
    decrypt(value);
    return true;
  } catch (error) {
    return false;
  }
}

async function migrateKeys() {
  console.log('Starting Claude API key encryption migration...\n');

  try {
    // Fetch all user_settings with claude_api_key
    const result = await pool.query(
      'SELECT user_id, claude_api_key FROM user_settings WHERE claude_api_key IS NOT NULL'
    );

    if (result.rows.length === 0) {
      console.log('No Claude API keys found in the database.');
      return;
    }

    console.log(`Found ${result.rows.length} user(s) with Claude API keys.\n`);

    let encryptedCount = 0;
    let alreadyEncryptedCount = 0;
    let errorCount = 0;

    for (const row of result.rows) {
      const { user_id, claude_api_key } = row;

      // Check if already encrypted
      if (isEncrypted(claude_api_key)) {
        console.log(`✓ User ${user_id}: API key already encrypted, skipping.`);
        alreadyEncryptedCount++;
        continue;
      }

      // Key is plaintext, encrypt it
      try {
        console.log(`⟳ User ${user_id}: Encrypting plaintext API key...`);

        const encryptedKey = encrypt(claude_api_key);

        // Update the database
        await pool.query(
          'UPDATE user_settings SET claude_api_key = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2',
          [encryptedKey, user_id]
        );

        console.log(`✓ User ${user_id}: Successfully encrypted API key.`);
        encryptedCount++;
      } catch (error) {
        console.error(`✗ User ${user_id}: Failed to encrypt API key:`, error.message);
        errorCount++;
      }
    }

    console.log('\n' + '='.repeat(60));
    console.log('Migration Summary:');
    console.log('='.repeat(60));
    console.log(`Total users:           ${result.rows.length}`);
    console.log(`Already encrypted:     ${alreadyEncryptedCount}`);
    console.log(`Newly encrypted:       ${encryptedCount}`);
    console.log(`Errors:                ${errorCount}`);
    console.log('='.repeat(60));

    if (encryptedCount > 0) {
      console.log('\n✓ Migration completed successfully!');
      console.log('All Claude API keys are now encrypted.');
    } else if (alreadyEncryptedCount > 0) {
      console.log('\n✓ All API keys were already encrypted. No changes made.');
    }

    if (errorCount > 0) {
      console.log('\n⚠ Warning: Some keys could not be encrypted. Please review the errors above.');
      process.exit(1);
    }

  } catch (error) {
    console.error('\n✗ Migration failed:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Run the migration
migrateKeys().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
