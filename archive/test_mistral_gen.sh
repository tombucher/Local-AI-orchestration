#!/bin/bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/projects/" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

echo "Creating task..."
TASK_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\": $PROJECT_ID, \"title\": \"Test Mistral - Add Function\", \"description\": \"Simple add function\", \"task_type\": \"code_generation\", \"priority\": \"P2\", \"llm_prompt\": \"Create a Python function add(a, b) that returns a + b.\"}")

TASK_ID=$(echo "$TASK_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo "Task ID: $TASK_ID"

echo "Setting to READY..."
curl -s -X PUT "http://localhost:8000/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "ready"}' > /dev/null

echo "Triggering generation..."
curl -s -X POST "http://localhost:8000/api/v1/tasks/$TASK_ID/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" > /dev/null

echo "Waiting 25s for generation..."
sleep 25

echo ""
echo "Checking result..."
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/tasks/$TASK_ID" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Status: {d.get(\"status\")}'); print(f'Code length: {len(d.get(\"generated_code\", \"\"))} chars'); code=d.get('generated_code', ''); print(f'\\nGenerated Code:\\n{code if code else \"(empty)\"}') if code else print('No code generated')"

echo ""
echo "Backend logs:"
docker-compose logs backend --tail 100 2>&1 | grep -E "(TASK-$TASK_ID|mistral)" | tail -20
