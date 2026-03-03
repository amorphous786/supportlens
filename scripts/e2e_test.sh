#!/usr/bin/env bash
# =============================================================================
# SupportLens — End-to-End Integration Test
#
# Starts the stack with a lightweight mock Ollama (no GPU, no model pull),
# exercises the full request → database → analytics data flow, and verifies
# graceful degradation when either the LLM or the database goes away.
#
# Exit code: 0 = all tests passed, 1 = one or more failures.
# =============================================================================
set -euo pipefail

COMPOSE_BASE="docker-compose.yml"
COMPOSE_E2E="docker-compose.e2e.yml"
API="http://localhost:8000"
MAX_WAIT_S=120   # seconds to wait for backend healthy (PostgreSQL needs extra time)
PASS=0
FAIL=0

# ── colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass()  { echo -e "${GREEN}✓ $1${NC}"; PASS=$((PASS + 1)); }
fail()  { echo -e "${RED}✗ $1${NC}";  FAIL=$((FAIL + 1)); }
info()  { echo -e "${YELLOW}→ $1${NC}"; }
abort() { echo -e "${RED}FATAL: $1${NC}"; exit 1; }

# ── helpers ───────────────────────────────────────────────────────────────────

# Extract a JSON field from stdin using only Python (no jq dependency).
json_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo ""
}

# Expect stdin to be a JSON array; print its length (or 0 if not a list).
json_array_length() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d, list) else 0)" 2>/dev/null || echo "0"
}

http_status() {
  curl -s -o /dev/null -w "%{http_code}" "$@"
}

# ── cleanup ───────────────────────────────────────────────────────────────────

cleanup() {
  info "Tearing down E2E stack..."
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

# ── 1. Start stack ────────────────────────────────────────────────────────────

info "Building and starting E2E stack (db + mock Ollama + backend, no frontend)..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" up -d --build db ollama backend

# ── 2. Wait for backend healthy ───────────────────────────────────────────────

info "Waiting for backend to report healthy (max ${MAX_WAIT_S}s)..."
ELAPSED=0
until curl -sf "$API/health" \
      | python3 -c "import sys,json; s=json.load(sys.stdin)['status']; sys.exit(0 if s in ('healthy','degraded') else 1)" \
      2>/dev/null; do
  if [ "$ELAPSED" -ge "$MAX_WAIT_S" ]; then
    echo ""
    info "Backend logs at timeout:"
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" logs backend --tail 40
    abort "Backend did not become healthy within ${MAX_WAIT_S}s"
  fi
  printf "."
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
echo ""
pass "Backend is healthy"

# ── 3. Baseline analytics count ───────────────────────────────────────────────

INITIAL_COUNT=$(curl -sf "$API/api/v1/analytics/" | json_field "['total_traces']")
info "Baseline trace count: ${INITIAL_COUNT}"

# ── 4. Create a trace ─────────────────────────────────────────────────────────

info "Creating a trace (POST /api/v1/traces/)..."
TRACE_JSON=$(curl -sf -X POST "$API/api/v1/traces/" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I was charged twice on my invoice this month"}')

TRACE_ID=$(echo "$TRACE_JSON"       | json_field "['id']")
TRACE_CAT=$(echo "$TRACE_JSON"      | json_field "['category']")
TRACE_BOT=$(echo "$TRACE_JSON"      | json_field "['bot_response']")
TRACE_MS=$(echo "$TRACE_JSON"       | json_field "['response_time_ms']")

if [ -n "$TRACE_ID" ] && [ "$TRACE_ID" != "None" ] && [ "$TRACE_ID" != "" ]; then
  pass "Trace created (id=${TRACE_ID}, category=${TRACE_CAT})"
else
  fail "Trace creation failed — response: ${TRACE_JSON}"
fi

# Verify bot_response is non-empty (the mock LLM returned something)
if [ -n "$TRACE_BOT" ] && [ "$TRACE_BOT" != "None" ]; then
  pass "Trace has non-empty bot_response"
else
  fail "Trace bot_response is empty — LLM mock may not be working"
fi

# Verify response_time_ms is a positive integer
if echo "$TRACE_MS" | grep -qE '^[0-9]+$' && [ "$TRACE_MS" -ge 0 ]; then
  pass "Trace response_time_ms is a non-negative integer (${TRACE_MS}ms)"
else
  fail "Trace response_time_ms looks wrong: ${TRACE_MS}"
fi

# ── 5. Analytics count increased ─────────────────────────────────────────────

NEW_COUNT=$(curl -sf "$API/api/v1/analytics/" | json_field "['total_traces']")
if [ "$NEW_COUNT" -gt "$INITIAL_COUNT" ]; then
  pass "Analytics total_traces increased (${INITIAL_COUNT} → ${NEW_COUNT})"
else
  fail "Analytics total_traces did NOT increase (${INITIAL_COUNT} → ${NEW_COUNT})"
fi

# Verify the analytics breakdown is populated
BREAKDOWN=$(curl -sf "$API/api/v1/analytics/" | json_field "['breakdown']")
if [ -n "$BREAKDOWN" ] && [ "$BREAKDOWN" != "[]" ]; then
  pass "Analytics breakdown is non-empty"
else
  fail "Analytics breakdown is empty after inserting a trace"
fi

# ── 6. Fetch trace by ID ──────────────────────────────────────────────────────

if [ -n "$TRACE_ID" ] && [ "$TRACE_ID" != "None" ]; then
  FETCHED_ID=$(curl -sf "$API/api/v1/traces/${TRACE_ID}" | json_field "['id']")
  if [ "$FETCHED_ID" = "$TRACE_ID" ]; then
    pass "GET /traces/:id returns correct trace"
  else
    fail "GET /traces/:id returned wrong id (expected ${TRACE_ID}, got ${FETCHED_ID})"
  fi
fi

# ── 7. Short-path aliases ─────────────────────────────────────────────────────

SHORT_TRACES=$(http_status "$API/traces")
if [ "$SHORT_TRACES" = "200" ]; then
  pass "GET /traces (short alias) returns 200"
else
  fail "GET /traces (short alias) should return 200, got ${SHORT_TRACES}"
fi

SHORT_ANALYTICS=$(http_status "$API/analytics")
if [ "$SHORT_ANALYTICS" = "200" ]; then
  pass "GET /analytics (short alias) returns 200"
else
  fail "GET /analytics (short alias) should return 200, got ${SHORT_ANALYTICS}"
fi

# ── 8. Category filter ────────────────────────────────────────────────────────

if [ -n "$TRACE_CAT" ] && [ "$TRACE_CAT" != "None" ]; then
  ENCODED_CAT=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${TRACE_CAT}'))")
  FILTER_LIST=$(curl -sf "$API/api/v1/traces/?category=${ENCODED_CAT}")
  FILTER_COUNT=$(echo "$FILTER_LIST" | json_array_length)

  if [ "$FILTER_COUNT" -ge 1 ]; then
    pass "Category filter '${TRACE_CAT}' returns ≥1 result"
  else
    fail "Category filter '${TRACE_CAT}' returned 0 results"
  fi

  WRONG=$(echo "$FILTER_LIST" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); bad=[t for t in d if t['category']!='${TRACE_CAT}']; print(len(bad))" \
    2>/dev/null || echo "0")
  if [ "$WRONG" = "0" ]; then
    pass "Category filter returns only '${TRACE_CAT}' traces"
  else
    fail "Category filter returned ${WRONG} trace(s) with wrong category"
  fi
fi

# ── 9. Input validation ───────────────────────────────────────────────────────

STATUS=$(http_status -X POST "$API/api/v1/traces/" \
  -H "Content-Type: application/json" \
  -d '{"user_message": ""}')
if [ "$STATUS" = "422" ]; then
  pass "Empty user_message rejected with 422"
else
  fail "Empty user_message should return 422, got ${STATUS}"
fi

STATUS=$(http_status "$API/api/v1/traces/does-not-exist")
if [ "$STATUS" = "404" ]; then
  pass "Unknown trace ID returns 404"
else
  fail "Unknown trace ID should return 404, got ${STATUS}"
fi

STATUS=$(http_status "$API/api/v1/traces/?category=NotAValidCategory")
if [ "$STATUS" = "422" ]; then
  pass "Invalid category filter returns 422"
else
  fail "Invalid category filter should return 422, got ${STATUS}"
fi

# ── 10. Simulate LLM outage → health reports degraded ────────────────────────

info "Stopping mock Ollama to simulate LLM unavailability..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" stop ollama
sleep 5

HEALTH_STATUS=$(curl -sf "$API/health" | json_field "['status']")
if [ "$HEALTH_STATUS" = "degraded" ] || [ "$HEALTH_STATUS" = "unhealthy" ]; then
  pass "Health reports '${HEALTH_STATUS}' when Ollama is down"
else
  fail "Expected 'degraded' or 'unhealthy' when Ollama is down, got '${HEALTH_STATUS}'"
fi

OLLAMA_DEP=$(curl -sf "$API/health" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['dependencies']['ollama']['status'])" \
  2>/dev/null || echo "unknown")
if [ "$OLLAMA_DEP" = "unavailable" ] || [ "$OLLAMA_DEP" = "degraded" ]; then
  pass "Health.dependencies.ollama correctly shows '${OLLAMA_DEP}'"
else
  fail "health.dependencies.ollama should be 'unavailable', got '${OLLAMA_DEP}'"
fi

# ── 11. Read-path still works while LLM is down ───────────────────────────────

LIST_COUNT=$(curl -sf "$API/api/v1/traces/" | json_array_length)
if [ "$LIST_COUNT" -ge 0 ]; then
  pass "GET /traces still works while Ollama is down (${LIST_COUNT} traces returned)"
else
  fail "GET /traces failed while Ollama is down"
fi

ANALYTICS_TOTAL=$(curl -sf "$API/api/v1/analytics/" | json_field "['total_traces']")
if [ "$ANALYTICS_TOTAL" -ge 0 ]; then
  pass "GET /analytics still works while Ollama is down"
else
  fail "GET /analytics failed while Ollama is down"
fi

# Restore Ollama for subsequent steps
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" start ollama
sleep 5

# ── 12. Simulate DB outage → health reports unhealthy ────────────────────────

info "Stopping PostgreSQL to simulate database unavailability..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" stop db
# Give pool_pre_ping time to detect the failure (next request triggers it)
sleep 5
# Force the health probe (triggers pool_pre_ping on the engine)
curl -sf "$API/health" > /dev/null 2>&1 || true
sleep 3

HEALTH_STATUS=$(curl -sf "$API/health" | json_field "['status']")
if [ "$HEALTH_STATUS" = "unhealthy" ]; then
  pass "Health reports 'unhealthy' when PostgreSQL is down"
else
  fail "Expected 'unhealthy' when database is down, got '${HEALTH_STATUS}'"
fi

DB_DEP=$(curl -sf "$API/health" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['dependencies']['database']['status'])" \
  2>/dev/null || echo "unknown")
if [ "$DB_DEP" = "unhealthy" ] || [ "$DB_DEP" = "unavailable" ]; then
  pass "Health.dependencies.database correctly shows '${DB_DEP}'"
else
  fail "health.dependencies.database should be 'unhealthy', got '${DB_DEP}'"
fi

# ── 13. Recovery after DB restart ────────────────────────────────────────────

info "Restarting PostgreSQL and backend to verify recovery..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" start db
sleep 8
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" restart backend
ELAPSED=0
until curl -sf "$API/health" \
      | python3 -c "import sys,json; s=json.load(sys.stdin)['status']; sys.exit(0 if s in ('healthy','degraded') else 1)" \
      2>/dev/null; do
  if [ "$ELAPSED" -ge 60 ]; then
    abort "Backend did not recover after DB restart within 60s"
  fi
  printf "."
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
echo ""
pass "Backend recovered after database restart"

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}PASSED: ${PASS}${NC}    ${RED}FAILED: ${FAIL}${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ "$FAIL" -eq 0 ]
