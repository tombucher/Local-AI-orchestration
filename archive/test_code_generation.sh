#!/bin/bash

echo "================================================"
echo "   TEST GÉNÉRATION DE CODE"
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

# Get or create a project
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/projects/" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); items=data.get('items', []); print(items[0]['id'] if items else '')" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "❌ No project found"
  exit 1
fi
echo "✅ Using project ID: $PROJECT_ID"
echo ""

# TEST 1: Create a code generation task
echo "TEST 1: CREATE CODE GENERATION TASK"
echo "====================================="
CREATE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": $PROJECT_ID,
    \"title\": \"Test Génération - Calculatrice\",
    \"description\": \"Créer une calculatrice simple\",
    \"task_type\": \"code_generation\",
    \"priority\": \"P2\",
    \"llm_prompt\": \"Crée une fonction Python calculator() qui prend deux nombres et une opération (+, -, *, /) et retourne le résultat. Ajoute la gestion des erreurs.\"
  }")

TASK_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
  echo "❌ Task creation failed"
  echo "$CREATE_RESPONSE"
  exit 1
fi

echo "✅ Task created: ID=$TASK_ID"
TASK_STATUS=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
echo "  Status: $TASK_STATUS"
echo ""

# TEST 2: Set task to READY status (required for generation)
if [ "$TASK_STATUS" != "ready" ]; then
  echo "TEST 2: SET TASK TO READY"
  echo "========================="
  UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:8000/api/v1/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"status": "ready"}')

  NEW_STATUS=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
  echo "✅ Task status updated to: $NEW_STATUS"
  echo ""
fi

# TEST 3: Trigger code generation
echo "TEST 3: TRIGGER CODE GENERATION"
echo "================================"
echo "Starting generation..."
echo ""

START_TIME=$(date +%s)

GENERATE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
  "http://localhost:8000/api/v1/tasks/$TASK_ID/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

HTTP_STATUS=$(echo "$GENERATE_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$GENERATE_RESPONSE" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Generation triggered successfully"
  GEN_STATUS=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
  echo "  Task status: $GEN_STATUS"
else
  echo "❌ Generation trigger failed (HTTP $HTTP_STATUS)"
  echo "$BODY" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$BODY"
  exit 1
fi
echo ""

# TEST 4: Poll task status until completion (max 120s)
echo "TEST 4: WAIT FOR GENERATION COMPLETION"
echo "======================================="
echo "Polling task status every 3 seconds..."
echo ""

MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep 3
  ELAPSED=$((ELAPSED + 3))

  CHECK_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/tasks/$TASK_ID")

  CURRENT_STATUS=$(echo "$CHECK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)

  echo "  [${ELAPSED}s] Status: $CURRENT_STATUS"

  if [ "$CURRENT_STATUS" = "manual_review" ]; then
    END_TIME=$(date +%s)
    TOTAL_TIME=$((END_TIME - START_TIME))
    echo ""
    echo "✅ Generation completed in ${TOTAL_TIME}s"
    echo ""

    # Display generated code
    echo "Generated Code:"
    echo "---------------"
    echo "$CHECK_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); code=d.get('generated_code', 'N/A'); print(code if len(code) < 500 else code[:500] + '\n... (truncated)')" 2>/dev/null
    echo ""

    # Cleanup
    echo "CLEANUP: Deleting test task..."
    curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
      "http://localhost:8000/api/v1/tasks/$TASK_ID" > /dev/null
    echo "✅ Test task deleted"
    echo ""

    echo "================================================"
    echo "   TEST COMPLETE"
    echo "================================================"
    echo ""
    echo "Génération de Code: ✅ OPERATIONAL"
    exit 0
  fi

  if [ "$CURRENT_STATUS" = "failed" ]; then
    echo ""
    echo "❌ Generation FAILED"
    echo ""
    echo "Task details:"
    echo "$CHECK_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null | head -30
    exit 1
  fi
done

echo ""
echo "⏱️  TIMEOUT: Generation did not complete in ${MAX_WAIT}s"
echo ""
echo "Current status: $CURRENT_STATUS"
echo ""
echo "Check backend logs for details:"
echo "  docker-compose logs backend --tail 50"
