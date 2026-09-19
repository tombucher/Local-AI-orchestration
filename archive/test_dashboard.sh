#!/bin/bash

TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

echo "Generating new daily report..."
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/reports/daily/generate" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Total tasks: {d.get('total_tasks', 'N/A')}\"); print(f\"Active projects: {d.get('active_projects', 'N/A')}\"); print(f\"Projects:\"  ); [print(f\"  - {p.get('project_name')}: {p.get('total_tasks')} tasks\") for p in d.get('projects', [])]" 2>&1

echo ""
echo "Verifying task count in DB..."
docker-compose exec postgres psql -U orchestrator_user -d orchestrator -c "SELECT status, COUNT(*) FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE status != 'ARCHIVED' AND user_id = 7) GROUP BY status;"
