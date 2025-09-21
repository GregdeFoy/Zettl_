#!/bin/bash
# 02-set-auth-password.sh
# Place this in config/postgresql/init/

set -e

# Read the auth password from secrets file
if [ -f "/run/secrets/db_auth_password" ]; then
  AUTH_PASSWORD=$(cat /run/secrets/db_auth_password | tr -d '\n\r')
  echo "Setting password for zettl_auth user..."

  # Connect to the zettl database and set the password
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "zettl" <<-EOSQL
        ALTER ROLE zettl_auth PASSWORD '$AUTH_PASSWORD';
        GRANT ALL PRIVILEGES ON SCHEMA public TO zettl_auth;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO zettl_auth;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO zettl_auth;
EOSQL

  echo "Password set successfully for zettl_auth user"
else
  echo "Warning: No db_auth_password file found at /run/secrets/db_auth_password"
  echo "Creating zettl_auth user with a default password - CHANGE THIS IN PRODUCTION!"

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "zettl" <<-EOSQL
        ALTER ROLE zettl_auth PASSWORD 'default_auth_password';
        GRANT ALL PRIVILEGES ON SCHEMA public TO zettl_auth;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO zettl_auth;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO zettl_auth;
EOSQL
fi
