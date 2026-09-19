#!/bin/bash
echo "=== FINAL QA TEST - Orchestrateur IA ==="

# Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ CRITICAL: Login failed"
  exit 1
fi
echo "✅ Login successful"

# Get active projects
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/" \
  | python3 -c "import sys, json; items=[i for i in json.load(sys.stdin).get('items', []) if i['status'] == 'ACTIVE']; print(items[0]['id'] if items else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ CRITICAL: No active projects found"
  exit 1
fi
echo "✅ Found active project: $PROJECT_ID"

# Test 1: Maturity Analysis
echo ""
echo "TEST 1: /projects/$PROJECT_ID/maturity-analysis"
MATURITY=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/maturity-analysis")
HTTP_STATUS=$(echo "$MATURITY" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$MATURITY" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  HAS_SCORE=$(echo "$BODY" | python3 -c "import sys, json; print('maturity_score' in json.load(sys.stdin))" 2>/dev/null)
  if [ "$HAS_SCORE" = "True" ]; then
    echo "✅ Maturity Analysis: OK"
    echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Score: {d.get('maturity_score', 'N/A')}\")" 2>/dev/null
  else
    echo "❌ Maturity Analysis: Response missing maturity_score"
    echo "$BODY" | head -5
  fi
else
  echo "❌ Maturity Analysis: HTTP $HTTP_STATUS"
  echo "$BODY" | head -10
fi

# Test 2: Critical Path
echo ""
echo "TEST 2: /projects/$PROJECT_ID/critical-path"
CP=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/critical-path")
HTTP_STATUS=$(echo "$CP" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$CP" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Critical Path: OK"
  echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Total duration: {d.get('total_duration', 0)}h\"); print(f\"  Ordered tasks: {len(d.get('ordered_tasks', []))}\")" 2>/dev/null
else
  echo "❌ Critical Path: HTTP $HTTP_STATUS"
  echo "$BODY" | head -10
fi

# Test 3: Tasks Stats
echo ""
echo "TEST 3: /tasks/stats/service"
STATS=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/stats/service")
HTTP_STATUS=$(echo "$STATS" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$STATS" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Tasks Stats: OK"
  echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))" 2>/dev/null
else
  echo "❌ Tasks Stats: HTTP $HTTP_STATUS"
fi

# Test 4: Daily Report
echo ""
echo "TEST 4: /reports/daily/latest"
REPORT=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/reports/daily/latest")
HTTP_STATUS=$(echo "$REPORT" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$REPORT" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Daily Report: OK"
  echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Total tasks: {d.get('total_tasks', 'N/A')}\"); print(f\"  Active projects: {d.get('active_projects', 'N/A')}\"); print(f\"  Completed today: {d.get('completed_today', 'N/A')}\")" 2>/dev/null
else
  echo "❌ Daily Report: HTTP $HTTP_STATUS"
  echo "$BODY" | head -10
fi

echo ""
echo "=== QA TEST COMPLETED ==="
