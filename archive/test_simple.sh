#!/bin/bash
echo "=== Testing Critical Endpoints ==="

# Login
echo "1. Login..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login"
  exit 1
fi
echo "✅ Logged in"

# Get project
echo ""
echo "2. Getting first project..."
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/" \
  | python3 -c "import sys, json; items=json.load(sys.stdin).get('items', []); print(items[0]['id'] if items else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ No projects found"
  exit 1
fi
echo "✅ Using project ID: $PROJECT_ID"

# Test maturity-analysis
echo ""
echo "3. Testing maturity-analysis..."
MATURITY_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/maturity-analysis")
echo "$MATURITY_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Status:', '✅ OK' if 'maturity_score' in d else '❌ ERROR'); print(json.dumps(d, indent=2)[:500])" 2>&1

echo ""
echo "4. Testing critical-path..."
CP_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/critical-path")
echo "$CP_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Status:', '✅ OK' if 'total_duration' in d or 'ordered_tasks' in d else '❌ ERROR'); print(json.dumps(d, indent=2)[:500])" 2>&1

echo ""
echo "5. Testing tasks stats..."
STATS_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/stats/service")
echo "$STATS_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))" 2>&1

echo ""
echo "6. Testing daily report..."
REPORT_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/reports/daily/latest")
echo "$REPORT_RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Total tasks:', d.get('total_tasks', 'N/A')); print('Active projects:', d.get('active_projects', 'N/A'))" 2>&1

