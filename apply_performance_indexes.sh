#!/bin/bash

# ============================================================================
# Apply Performance Indexes Migration
# ============================================================================
# This script applies the performance optimization indexes to your Zettl database
# ============================================================================

set -e

echo "============================================================================"
echo "Zettl Performance Optimization - Database Indexing"
echo "============================================================================"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is required but not installed."
    exit 1
fi

# Check if the PostgreSQL container is running
if ! docker-compose ps | grep -q "zettl-postgres.*Up"; then
    echo "Error: PostgreSQL container is not running."
    echo "Please start it with: docker-compose up -d postgresql"
    exit 1
fi

echo "Applying performance indexes migration..."
echo ""

# Apply the migration
docker-compose exec -T postgresql psql -U postgres -d zettl \
    -f /docker-entrypoint-initdb.d/../migrations/004_performance_indexes.sql \
    2>&1 | grep -v "^NOTICE:" || true

echo ""
echo "============================================================================"
echo "Migration completed successfully!"
echo "============================================================================"
echo ""
echo "To verify the indexes were created, run:"
echo "  docker-compose exec postgresql psql -U postgres -d zettl -c '\di+'"
echo ""
echo "To see the performance improvement, compare before/after with:"
echo "  time zettl list --full --limit 20"
echo ""
echo "To refresh the tag counts materialized view (do this periodically):"
echo "  docker-compose exec postgresql psql -U postgres -d zettl -c 'REFRESH MATERIALIZED VIEW CONCURRENTLY tag_counts;'"
echo ""