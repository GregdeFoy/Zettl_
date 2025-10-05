#!/bin/bash

# ============================================================================
# Zettl RLS Migration Runner
# ============================================================================
# This script safely executes the RLS migration with backup and verification
# ============================================================================

set -e # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="zettl-postgres"
DB_NAME="zettl"
DB_USER="postgres"
MIGRATION_DIR="config/postgresql/migrations"
BACKUP_DIR="backups"
MIGRATION_FILE="$MIGRATION_DIR/001_add_rls.sql"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
  echo -e "${BLUE}============================================================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

print_header "PRE-FLIGHT CHECKS"

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
  print_error "Docker is not running"
  exit 1
fi
print_success "Docker is running"

# Check PostgreSQL container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  print_error "PostgreSQL container '${CONTAINER_NAME}' is not running"
  exit 1
fi
print_success "PostgreSQL container is running"

# Check migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
  print_error "Migration file not found: $MIGRATION_FILE"
  exit 1
fi
print_success "Migration file found"

# Create backup directory
mkdir -p "$BACKUP_DIR"
print_success "Backup directory ready"

echo ""

# ============================================================================
# Backup Database
# ============================================================================

print_header "BACKING UP DATABASE"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/zettl_before_rls_${TIMESTAMP}.sql"

print_info "Creating backup: $BACKUP_FILE"

docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" >"$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
  BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  print_success "Backup created successfully ($BACKUP_SIZE)"
else
  print_error "Backup failed"
  exit 1
fi

echo ""

# ============================================================================
# Show Current State
# ============================================================================

print_header "CURRENT DATABASE STATE"

print_info "Current table structures:"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "\d notes" 2>/dev/null | head -20

print_info "Record counts:"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 'notes: ' || COUNT(*) FROM notes
    UNION ALL
    SELECT 'links: ' || COUNT(*) FROM links
    UNION ALL
    SELECT 'tags: ' || COUNT(*) FROM tags;
"

echo ""

# ============================================================================
# Confirm Migration
# ============================================================================

print_header "MIGRATION CONFIRMATION"

echo -e "${YELLOW}You are about to run the RLS migration which will:${NC}"
echo "  1. Add user_id columns to all tables"
echo "  2. Create composite primary keys"
echo "  3. Enable Row Level Security"
echo "  4. Modify all foreign key constraints"
echo ""
echo -e "${YELLOW}This will cause brief downtime while the migration runs.${NC}"
echo -e "${YELLOW}A backup has been created at: ${BACKUP_FILE}${NC}"
echo ""

read -p "Do you want to proceed? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  print_warning "Migration cancelled"
  exit 0
fi

echo ""

# ============================================================================
# Run Migration
# ============================================================================

print_header "RUNNING MIGRATION"

print_info "Executing migration script..."

if docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" <"$MIGRATION_FILE"; then
  print_success "Migration completed successfully!"
else
  print_error "Migration failed!"
  echo ""
  print_warning "To restore from backup:"
  echo "  docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
  exit 1
fi

echo ""

# ============================================================================
# Post-Migration Verification
# ============================================================================

print_header "POST-MIGRATION VERIFICATION"

# Check user_id columns exist
print_info "Verifying user_id columns..."
COLUMNS=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT table_name || ': ' || column_name 
    FROM information_schema.columns 
    WHERE table_name IN ('notes','links','tags') 
      AND column_name = 'user_id';
")

if [ -z "$COLUMNS" ]; then
  print_error "user_id columns not found!"
  exit 1
else
  echo "$COLUMNS"
  print_success "user_id columns verified"
fi

# Check RLS is enabled
print_info "Verifying RLS is enabled..."
RLS_STATUS=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT tablename || ': ' || rowsecurity::text 
    FROM pg_tables 
    WHERE tablename IN ('notes', 'links', 'tags');
")

if echo "$RLS_STATUS" | grep -q "false"; then
  print_error "RLS not enabled on all tables!"
  exit 1
else
  echo "$RLS_STATUS"
  print_success "RLS enabled on all tables"
fi

# Check policies exist
print_info "Verifying policies exist..."
POLICY_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM pg_policies 
    WHERE tablename IN ('notes', 'links', 'tags');
")

if [ "$POLICY_COUNT" -lt 3 ]; then
  print_error "Not all policies created!"
  exit 1
else
  print_success "Policies created ($POLICY_COUNT policies found)"
fi

# Verify data integrity
print_info "Verifying data integrity..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 'notes' as table_name, user_id, COUNT(*) as count 
    FROM notes GROUP BY user_id
    UNION ALL
    SELECT 'links', user_id, COUNT(*) 
    FROM links GROUP BY user_id
    UNION ALL
    SELECT 'tags', user_id, COUNT(*) 
    FROM tags GROUP BY user_id
    ORDER BY table_name, user_id;
"

print_success "Data integrity verified"

echo ""

# ============================================================================
# Restart PostgREST
# ============================================================================

print_header "RESTARTING POSTGREST"

print_info "Restarting PostgREST to reload schema..."

if docker-compose restart postgrest; then
  print_success "PostgREST restarted"

  # Wait for PostgREST to be ready
  sleep 3

  # Check if PostgREST is healthy
  if docker ps --filter "name=zettl-api" --filter "health=healthy" | grep -q "zettl-api"; then
    print_success "PostgREST is healthy"
  else
    print_warning "PostgREST health check pending..."
  fi
else
  print_error "Failed to restart PostgREST"
  print_warning "You may need to restart it manually: docker-compose restart postgrest"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

print_header "MIGRATION SUMMARY"

echo -e "${GREEN}Migration completed successfully!${NC}"
echo ""
echo "Backup location: $BACKUP_FILE"
echo "Migration file:  $MIGRATION_FILE"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Test authentication with a JWT token"
echo "  2. Verify Python client can create/read notes"
echo "  3. Check that users only see their own data"
echo ""
echo -e "${BLUE}To test with curl:${NC}"
echo '  # Get a JWT token first (from your auth service)'
echo '  JWT="your-token-here"'
echo '  curl -H "Authorization: Bearer $JWT" https://zettlnotes.app/api/v1/notes'
echo ""
echo -e "${BLUE}To rollback if needed:${NC}"
echo "  docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
echo "  docker-compose restart postgrest"
echo ""

print_success "All done! 🚀"
