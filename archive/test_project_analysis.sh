#!/bin/bash

echo "================================================"
echo "   TEST ANALYSE IA DE PROJET"
echo "================================================"
echo ""

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
echo ""

# Get active project
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); items=data.get('items', []); print(items[0]['id'] if items else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ No project found"
  exit 1
fi
echo "✅ Using project ID: $PROJECT_ID"
echo ""

# TEST: Analyze project
echo "TEST: ANALYZE PROJECT (with timeout 60s)"
echo "=========================================="
echo "Starting analysis... (this may take 30-60 seconds)"
echo ""

START_TIME=$(date +%s)

ANALYZE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 60)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

HTTP_STATUS=$(echo "$ANALYZE_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$ANALYZE_RESPONSE" | sed '$d')

echo "Response time: ${DURATION}s"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Analysis completed successfully"
  echo ""

  # Parse and display key metrics
  echo "Analysis Summary:"
  echo "$BODY" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Summary: {data.get('summary', 'N/A')[:100]}...\")
    print(f\"  Task suggestions: {len(data.get('task_suggestions', []))}\")
    print(f\"  Veille suggestions: {len(data.get('veille_suggestions', []))}\")
    print(f\"  Blockers detected: {len(data.get('blockers', []))}\")
    print(f\"  Estimated hours: {data.get('estimated_total_hours', 'N/A')}\")
    print()
    print('  Next actions:')
    for i, action in enumerate(data.get('next_actions', [])[:3], 1):
        print(f\"    {i}. {action}\")
except Exception as e:
    print(f'Error parsing response: {e}')
" 2>/dev/null

else
  echo "❌ Analysis failed (HTTP $HTTP_STATUS)"
  echo ""
  echo "Response body:"
  echo "$BODY" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$BODY" | head -20

  echo ""
  echo "Backend logs (last 30 lines):"
  docker-compose logs backend --tail 30 | grep -A 5 -B 5 "error\|Error\|ERROR\|Exception" | tail -20
  exit 1
fi
echo ""

echo "================================================"
echo "   TEST COMPLETE"
echo "================================================"
echo ""
echo "Analyse IA: ✅ OPERATIONAL"
