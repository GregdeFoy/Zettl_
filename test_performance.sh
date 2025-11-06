#!/bin/bash

# ============================================================================
# Performance Testing Script for Zettl
# ============================================================================
# This script tests the performance impact of the optimizations
# ============================================================================

echo "============================================================================"
echo "Zettl Performance Test Suite"
echo "============================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing current performance...${NC}"
echo ""

echo "1. Testing list command (basic):"
time python -m zettl.cli list --limit 10
echo ""

echo "2. Testing list with full content and tags:"
time python -m zettl.cli list --full --limit 5
echo ""

echo "3. Testing note creation with multiple tags:"
TEST_ID="perf$(date +%s)"
time python -m zettl.cli task "Performance test note" --id "$TEST_ID" --tag test --tag performance --tag benchmark
echo ""

echo "4. Testing tag-based search:"
time python -m zettl.cli tags
echo ""

echo "5. Testing note deletion:"
time python -m zettl.cli delete "$TEST_ID" --force
echo ""

echo "============================================================================"
echo -e "${GREEN}Performance Test Results:${NC}"
echo ""
echo "Expected timings after all optimizations:"
echo "  • List (basic): ~100-150ms"
echo "  • List (full with tags): ~150-200ms"
echo "  • Create with tags: ~100-150ms"
echo "  • Tag listing: ~50-100ms"
echo "  • Delete (force): ~50-100ms"
echo ""
echo "If times are significantly higher, ensure:"
echo "  1. Auth cache is warm (run any command twice)"
echo "  2. Database indexes are applied (./apply_performance_indexes.sh)"
echo "  3. Database is not under heavy load"
echo "============================================================================"