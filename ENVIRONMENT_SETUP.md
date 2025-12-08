# Environment Configuration Setup

This project uses environment variables for sensitive configuration like API keys and database passwords.

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual values:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Add your API keys:**
   - **OpenAI API Key**: Get from https://platform.openai.com/api-keys
   - Replace `your_openai_api_key_here` with your actual key

4. **Update database passwords:**
   - Change `ADMIN_PASSWORD` to a strong password
   - Update other credentials as needed

5. **Verify paths:**
   - Check that `SNAPSHOT_DIR` points to your OpenAlex snapshot location
   - Verify `PARSING_DIR` and `LOG_DIR` are correct for your system

## Important Security Notes

⚠️ **NEVER commit the `.env` file to git!**

- The `.env` file contains sensitive secrets and passwords
- It's already in `.gitignore` to prevent accidental commits
- Only commit `.env.example` (which has placeholder values)

### Best Practices

1. **File Permissions**: Restrict access to your `.env` file
   ```bash
   chmod 600 .env
   ```

2. **Strong Passwords**: Use passwords with at least 16 characters including:
   - Uppercase and lowercase letters
   - Numbers
   - Special characters

3. **API Key Security**:
   - Rotate API keys regularly
   - Never share your `.env` file
   - If a key is exposed, revoke it immediately and generate a new one

4. **Backup**: Keep a secure backup of your `.env` file
   - Store it separately from your code
   - Encrypt backups containing credentials

## Environment Variables

### Database Configuration
- `DB_HOST` - Database host (192.168.1.162 for local, 'postgres' for Docker)
- `DB_PORT` - Database port (55432 for external, 5432 for Docker)
- `DB_NAME` - Database name (oadbv5)
- `DB_USER` - Database user (admin)
- `ADMIN_PASSWORD` - Admin password (CHANGE THIS!)

### API Keys
- `OPENAI_API_KEY` - Required for ChatGPT-based gender inference

### File Paths
- `SNAPSHOT_DIR` - Location of OpenAlex snapshot data
- `PARSING_DIR` - Parsing scripts directory
- `LOG_DIR` - Log files directory

### Performance Settings
- `BATCH_SIZE` - Records to batch before database insert
- `PARALLEL_PARSERS` - Number of parallel parsing processes
- `PROGRESS_INTERVAL` - Progress logging frequency

## Docker vs Local Development

### Local Mac Development
```bash
DB_HOST=192.168.1.162
DB_PORT=55432
SNAPSHOT_DIR=/Volumes/Series/25NOV2025/data
```

### Docker Container
```bash
DB_HOST=postgres
DB_PORT=5432
SNAPSHOT_DIR=/data
```

The code automatically uses environment variables, so the same code works in both environments.

## Troubleshooting

### "OPENAI_API_KEY not set" warning
- This warning appears if the API key is missing
- It's only critical if you're running ChatGPT-based inference scripts
- Add your key to `.env` to resolve

### Connection refused errors
- Verify `DB_HOST` and `DB_PORT` are correct
- Check that PostgreSQL is running
- Ensure firewall allows connections

### Module not found: dotenv
```bash
pip install -r requirements.txt
```

## Getting API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key and add it to your `.env` file
5. Store the key securely - you can't view it again!

## For Team Members

If you're collaborating on this project:
1. Never share `.env` files directly
2. Use secure channels (password manager, encrypted email) to share credentials
3. Each team member should have their own `.env` file
4. Document any new environment variables in `.env.example`
