#!/bin/bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

echo "Triggering generation for task 98..."
curl -s -X POST "http://localhost:8000/api/v1/tasks/98/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Status: {d.get('status')}, ID: {d.get('id')}\")"

echo ""
echo "Check logs with: docker-compose logs -f backend"
