#!/bin/bash

TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

echo "Testing stream..."
curl -N -X POST "http://localhost:8000/api/v1/ideation/send-stream/80" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Dis-moi juste bonjour en 3 mots"}' 2>&1 | head -30
