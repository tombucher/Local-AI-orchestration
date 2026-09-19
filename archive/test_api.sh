#!/bin/bash

# Test des endpoints critiques

echo "=== Testing Orchestrateur IA API ==="
echo ""

# 1. Login
echo "1. Login..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | jq -r '.access_token // empty')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Got token: ${TOKEN:0:20}..."
echo ""

# 2. Get projects
echo "2. Getting projects..."
PROJECTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/")

PROJECT_COUNT=$(echo "$PROJECTS" | jq '.items | length')
echo "Found $PROJECT_COUNT projects"

if [ "$PROJECT_COUNT" -eq 0 ]; then
  echo "⚠️  No projects found. Creating test project..."
  # Create a test project
  NEW_PROJECT=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "http://localhost:8000/api/v1/projects/" \
    -d '{"name":"Test Project","description":"Test","type":"personal","features":{"code_gen":true,"veille":false,"git_auto":false}}')

  PROJECT_ID=$(echo "$NEW_PROJECT" | jq -r '.id')
  echo "✅ Created project ID: $PROJECT_ID"
else
  PROJECT_ID=$(echo "$PROJECTS" | jq -r '.items[0].id')
  echo "Using project ID: $PROJECT_ID"
fi

echo ""

# 3. Test maturity-analysis
echo "3. Testing /projects/$PROJECT_ID/maturity-analysis..."
MATURITY=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/maturity-analysis")

STATUS=$(echo "$MATURITY" | jq -r 'if .maturity_score then "✅ OK" else "❌ ERROR" end')
echo "$STATUS"
echo "$MATURITY" | jq '.' | head -20
echo ""

# 4. Test critical-path
echo "4. Testing /projects/$PROJECT_ID/critical-path..."
CRITICAL_PATH=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID/critical-path")

STATUS=$(echo "$CRITICAL_PATH" | jq -r 'if .total_duration != null then "✅ OK" else "❌ ERROR" end')
echo "$STATUS"
echo "$CRITICAL_PATH" | jq '.' | head -20
echo ""

# 5. Test tasks stats
echo "5. Testing /tasks/stats/service..."
TASK_STATS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/stats/service")

echo "$TASK_STATS" | jq '.'
echo ""

# 6. Test daily report
echo "6. Testing /reports/daily/latest..."
DAILY_REPORT=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/reports/daily/latest")

echo "$DAILY_REPORT" | jq '.' | head -30
echo ""

echo "=== Tests completed ==="
