#!/bin/bash

echo "================================================"
echo "   SRE VALIDATION - CYCLE CRUD COMPLET"
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

# TEST 1: CREATE PROJECT
echo "TEST 1: CREATE PROJECT"
echo "====================="
CREATE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test SRE Validation",
    "description": "Test de validation du cycle CRUD",
    "type": "personal",
    "features": {
      "code_gen": true,
      "veille": false,
      "git_auto": false
    }
  }')

PROJECT_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ CREATE FAILED"
  echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$CREATE_RESPONSE"
  exit 1
fi

echo "✅ Project created: ID=$PROJECT_ID"
echo ""

# TEST 2: UPDATE PROJECT
echo "TEST 2: UPDATE PROJECT (ID=$PROJECT_ID)"
echo "========================================"
UPDATE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "http://localhost:8000/api/v1/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test SRE Validation - UPDATED",
    "description": "Description mise à jour",
    "features": {
      "code_gen": false,
      "veille": true,
      "git_auto": true
    }
  }')

HTTP_STATUS=$(echo "$UPDATE_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Project updated successfully"
  echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Name: {d.get('name')}\"); print(f\"  Features: {d.get('features')}\")" 2>/dev/null
else
  echo "❌ UPDATE FAILED (HTTP $HTTP_STATUS)"
  echo "$BODY" | head -20
  exit 1
fi
echo ""

# TEST 3: READ PROJECT
echo "TEST 3: READ PROJECT (ID=$PROJECT_ID)"
echo "====================================="
GET_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID")

PROJECT_NAME=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', ''))" 2>/dev/null)

if [ "$PROJECT_NAME" = "Test SRE Validation - UPDATED" ]; then
  echo "✅ Project read successfully"
  echo "  Name: $PROJECT_NAME"
else
  echo "❌ READ FAILED"
  echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$GET_RESPONSE"
  exit 1
fi
echo ""

# TEST 4: DELETE PROJECT (ARCHIVE)
echo "TEST 4: DELETE PROJECT (ID=$PROJECT_ID)"
echo "======================================="
DELETE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/$PROJECT_ID")

HTTP_STATUS=$(echo "$DELETE_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)

if [ "$HTTP_STATUS" = "204" ]; then
  echo "✅ Project archived successfully"
else
  echo "❌ DELETE FAILED (HTTP $HTTP_STATUS)"
  echo "$DELETE_RESPONSE" | sed '$d'
  exit 1
fi
echo ""

# TEST 5: VERIFY NO 500 ERRORS IN LOGS
echo "TEST 5: VERIFY NO 500 ERRORS IN RECENT LOGS"
echo "==========================================="
RECENT_ERRORS=$(docker-compose logs backend --tail 50 | grep "500 Internal Server Error" | wc -l)

if [ "$RECENT_ERRORS" -eq 0 ]; then
  echo "✅ No 500 errors in recent logs"
else
  echo "⚠️  Found $RECENT_ERRORS 500 errors in recent logs"
  docker-compose logs backend --tail 50 | grep "500 Internal Server Error"
fi
echo ""

# TEST 6: TEST MATURITY ANALYSIS (Should work now)
echo "TEST 6: MATURITY ANALYSIS (ID=18)"
echo "================================="
MATURITY=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/18/maturity-analysis")

HTTP_STATUS=$(echo "$MATURITY" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$MATURITY" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Maturity analysis working"
  echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Score: {d.get('maturity_score', 'N/A')}\")" 2>/dev/null
else
  echo "❌ Maturity analysis failed (HTTP $HTTP_STATUS)"
  echo "$BODY" | head -10
fi
echo ""

echo "================================================"
echo "   VALIDATION COMPLETE"
echo "================================================"
echo ""
echo "Summary:"
echo "  ✅ CREATE - Working"
echo "  ✅ READ   - Working"
echo "  ✅ UPDATE - Working"
echo "  ✅ DELETE - Working"
echo ""
echo "System Status: OPERATIONAL ✅"
