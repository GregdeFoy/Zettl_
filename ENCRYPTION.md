# Claude API Key Encryption

## Overview

Claude API keys are now encrypted in the database using AES-256-GCM encryption. This adds a layer of security so that API keys are not stored in plaintext.

## How It Works

### Encryption
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2 with SHA-256 (100,000 iterations)
- **Storage Format**: `salt:iv:authTag:ciphertext` (all base64 encoded)
- **Master Key**: Stored in `.env` file as `ENCRYPTION_KEY`

### Security Features
- **Unique encryption** for each API key (random salt and IV)
- **Authenticated encryption** (GCM mode prevents tampering)
- **Key derivation** adds additional security layer
- **Automatic decryption** when API keys are retrieved

## Setup

### 1. Environment Configuration

The encryption key is stored in the `.env` file:

```bash
# Encryption key for sensitive data (Claude API keys, etc.)
# IMPORTANT: Keep this secret! Used to encrypt/decrypt Claude API keys in the database
ENCRYPTION_KEY=edf723d6563d3dcdc5968a21b353bf734e37216ebda3c1a6372a77a3f4cf8fbf
```

**Important**:
- Never commit this key to version control
- Keep backups of this key in a secure location
- If the key is lost, existing encrypted API keys cannot be recovered

### 2. Migrate Existing Keys

If you have existing plaintext API keys in your database, run the migration script:

```bash
cd auth-service
node migrate-encrypt-keys.js
```

This script will:
- Find all user_settings with Claude API keys
- Check if each key is already encrypted
- Encrypt any plaintext keys
- Update the database

The migration is idempotent (safe to run multiple times).

### 3. Docker Deployment (Optional)

For production environments using Docker secrets:

1. Create a Docker secret file:
   ```bash
   echo "your-encryption-key-here" > encryption.key
   ```

2. Update `docker-compose.yml`:
   ```yaml
   services:
     auth-service:
       environment:
         - ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
       secrets:
         - encryption_key

   secrets:
     encryption_key:
       file: ./encryption.key
   ```

## Implementation Details

### Files Modified
- `auth-service/encryption.js` - Encryption utilities
- `auth-service/index.js` - Updated to encrypt/decrypt API keys
- `.env` - Added ENCRYPTION_KEY

### Files Created
- `auth-service/migrate-encrypt-keys.js` - Migration script
- `ENCRYPTION.md` - This documentation

### Endpoints Updated
- `POST /api/auth/settings/claude-key` - Encrypts before storing
- `GET /api/auth/settings/claude-key` - Decrypts before returning
- `GET /api/auth/settings` - Decrypts before returning

## Security Considerations

### Current Security Level
✓ API keys encrypted in database
✓ Encryption key stored in environment file
✓ Not committed to version control

### Limitations
⚠ Encryption key is in plaintext in `.env` file (acceptable for single-user app)
⚠ Server has access to decryption key (necessary for functionality)

### Potential Improvements (if needed)
- Use hardware security module (HSM) for key storage
- Implement key rotation mechanism
- Use separate encryption keys per user
- Implement client-side encryption (keys never leave user's browser)

## Troubleshooting

### API Key Not Working After Migration
If the LLM features stop working after encryption:

1. Check auth-service logs for decryption errors
2. Verify `ENCRYPTION_KEY` is set in `.env`
3. Re-save your API key in the settings page
4. Run migration script again if needed

### Migration Script Errors
- **Database connection error**: Check database credentials in `.env`
- **Decryption error**: Some keys may be corrupted; re-save them via settings
- **Permission error**: Ensure database user has UPDATE permissions on user_settings

### Generating a New Encryption Key
If you need to generate a new encryption key:

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

**Warning**: Changing the encryption key will invalidate all existing encrypted API keys!

## Backup Recommendations

1. **Backup .env file** (especially ENCRYPTION_KEY)
2. **Before key rotation**, decrypt all API keys first
3. **Regular database backups** (encrypted keys are in the database)
