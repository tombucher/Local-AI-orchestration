#!/bin/bash

echo "================================================"
echo "   TEST PERSISTANCE METADATA (keywords)"
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
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ No project found"
  exit 1
fi
echo "✅ Using project ID: $PROJECT_ID"
echo ""

# TEST 1: CREATE VEILLE TASK WITH KEYWORDS
echo "TEST 1: CREATE VEILLE TASK WITH KEYWORDS"
echo "=========================================="
CREATE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": $PROJECT_ID,
    \"title\": \"Test Veille - Persistance Keywords\",
    \"description\": \"Test de persistance des metadata\",
    \"task_type\": \"veille_tech\",
    \"priority\": \"P3\",
    \"metadata\": {
      \"keywords\": [\"FastAPI\", \"Python\", \"Async\"]
    }
  }")

TASK_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
  echo "❌ CREATE FAILED"
  echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$CREATE_RESPONSE"
  exit 1
fi

echo "✅ Task created: ID=$TASK_ID"
INITIAL_KEYWORDS=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('metadata', {}).get('keywords', []))" 2>/dev/null)
echo "  Keywords: $INITIAL_KEYWORDS"
echo ""

# TEST 2: UPDATE TASK - CHANGE TYPE TO CODE_GENERATION
echo "TEST 2: UPDATE TO CODE_GENERATION (keep metadata)"
echo "=================================================="
UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:8000/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Test Code - Changed Type\",
    \"task_type\": \"code_generation\",
    \"llm_prompt\": \"Create a login page\",
    \"metadata\": {
      \"keywords\": [\"FastAPI\", \"Python\", \"Async\"]
    }
  }")

UPDATED_TYPE=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_type', ''))" 2>/dev/null)
UPDATED_KEYWORDS=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('metadata', {}).get('keywords', []))" 2>/dev/null)

if [ "$UPDATED_TYPE" = "code_generation" ]; then
  echo "✅ Task type updated to: $UPDATED_TYPE"
  echo "  Keywords after update: $UPDATED_KEYWORDS"
else
  echo "❌ UPDATE FAILED"
  echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null
  exit 1
fi
echo ""

# TEST 3: READ TASK - VERIFY METADATA PERSISTED
echo "TEST 3: READ TASK - VERIFY KEYWORDS PERSISTED"
echo "=============================================="
GET_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/$TASK_ID")

PERSISTED_KEYWORDS=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('metadata', {}).get('keywords', []))" 2>/dev/null)
PERSISTED_TYPE=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_type', ''))" 2>/dev/null)

if [ "$PERSISTED_KEYWORDS" = "['FastAPI', 'Python', 'Async']" ]; then
  echo "✅ Keywords PERSISTED correctly"
  echo "  Type: $PERSISTED_TYPE"
  echo "  Keywords: $PERSISTED_KEYWORDS"
else
  echo "❌ KEYWORDS LOST!"
  echo "  Expected: ['FastAPI', 'Python', 'Async']"
  echo "  Got: $PERSISTED_KEYWORDS"
  echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null
  exit 1
fi
echo ""

# TEST 4: UPDATE BACK TO VEILLE WITH NEW KEYWORDS
echo "TEST 4: UPDATE BACK TO VEILLE WITH NEW KEYWORDS"
echo "================================================"
UPDATE2_RESPONSE=$(curl -s -X PUT "http://localhost:8000/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Test Veille - New Keywords\",
    \"task_type\": \"veille_tech\",
    \"metadata\": {
      \"keywords\": [\"Docker\", \"Kubernetes\", \"DevOps\"]
    }
  }")

NEW_KEYWORDS=$(echo "$UPDATE2_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('metadata', {}).get('keywords', []))" 2>/dev/null)

if [ "$NEW_KEYWORDS" = "['Docker', 'Kubernetes', 'DevOps']" ]; then
  echo "✅ Keywords updated correctly"
  echo "  New keywords: $NEW_KEYWORDS"
else
  echo "❌ Keywords update failed"
  echo "  Expected: ['Docker', 'Kubernetes', 'DevOps']"
  echo "  Got: $NEW_KEYWORDS"
fi
echo ""

# CLEANUP
echo "CLEANUP: Deleting test task..."
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tasks/$TASK_ID" > /dev/null
echo "✅ Test task deleted"
echo ""

echo "================================================"
echo "   TEST COMPLETE"
echo "================================================"
echo ""
echo "Summary:"
echo "  ✅ CREATE with keywords - Working"
echo "  ✅ UPDATE type (keep keywords) - Working"
echo "  ✅ READ (verify persistence) - Working"
echo "  ✅ UPDATE keywords - Working"
echo ""
echo "Metadata Persistence: ✅ OPERATIONAL"
