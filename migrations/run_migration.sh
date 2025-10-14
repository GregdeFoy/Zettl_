#!/bin/bash
# Run database migration for hidden_buttons column

echo "Running migration: add_hidden_buttons.sql"
echo "=================================="

# Check if running in Docker or local
if [ -f "/.dockerenv" ]; then
    # Inside Docker container
    psql -U postgres -d zettl -f /app/migrations/add_hidden_buttons.sql
else
    # Outside Docker - use docker exec
    docker exec -i zettl-postgres psql -U postgres -d zettl < migrations/add_hidden_buttons.sql
fi

echo "=================================="
echo "Migration complete!"
echo ""
echo "If successful, you should see: 'Added hidden_buttons column to user_settings table'"
echo "Now restart the auth service: docker-compose restart auth-service"
