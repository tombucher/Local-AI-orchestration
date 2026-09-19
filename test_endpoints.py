#!/usr/bin/env python3
"""
Script de test pour valider les endpoints critiques
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# Credentials par défaut (à adapter selon votre config)
EMAIL = "admin@example.com"
PASSWORD = "admin123"

def get_token():
    """Obtenir un token d'authentification"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def test_endpoint(name, url, token, method="GET", data=None):
    """Tester un endpoint"""
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Method: {method}")

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return False

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ SUCCESS")
            result = response.json()
            print(f"Response preview: {json.dumps(result, indent=2)[:200]}...")
            return True
        elif response.status_code == 404:
            print(f"❌ FAILED - 404 Not Found")
            print(f"Response: {response.text}")
            return False
        elif response.status_code == 500:
            print(f"❌ FAILED - 500 Internal Server Error")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"⚠️  Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def main():
    print("🔍 Testing Orchestrateur IA Endpoints")
    print("="*60)

    # 1. Get token
    print("\n1. Authenticating...")
    token = get_token()
    if not token:
        print("❌ Cannot proceed without authentication")
        sys.exit(1)
    print(f"✅ Got token: {token[:20]}...")

    # 2. Get projects
    print("\n2. Getting projects...")
    response = requests.get(f"{BASE_URL}/projects/", headers={"Authorization": f"Bearer {token}"})
    projects = response.json().get("items", [])
    print(f"Found {len(projects)} projects")

    if not projects:
        print("⚠️  No projects found. Some tests will be skipped.")
        project_id = None
    else:
        project_id = projects[0]["id"]
        print(f"Using project ID: {project_id}")

    # 3. Test critical endpoints
    results = {}

    # Projects
    results["projects_list"] = test_endpoint(
        "List Projects",
        f"{BASE_URL}/projects/",
        token
    )

    results["start_chat"] = test_endpoint(
        "Start Project Chat",
        f"{BASE_URL}/projects/start-chat",
        token,
        method="POST",
        data={}
    )

    if project_id:
        results["project_detail"] = test_endpoint(
            f"Project Detail (ID: {project_id})",
            f"{BASE_URL}/projects/{project_id}",
            token
        )

        results["maturity_analysis"] = test_endpoint(
            "Maturity Analysis",
            f"{BASE_URL}/projects/{project_id}/maturity-analysis",
            token
        )

        results["critical_path"] = test_endpoint(
            "Critical Path",
            f"{BASE_URL}/projects/{project_id}/critical-path",
            token
        )

        results["project_stats"] = test_endpoint(
            "Project Stats",
            f"{BASE_URL}/projects/{project_id}/stats",
            token
        )

    # Tasks
    results["tasks_list"] = test_endpoint(
        "List Tasks",
        f"{BASE_URL}/tasks/",
        token
    )

    results["tasks_stats"] = test_endpoint(
        "Tasks Service Stats",
        f"{BASE_URL}/tasks/stats/service",
        token
    )

    # Reports
    results["daily_report"] = test_endpoint(
        "Daily Report Latest",
        f"{BASE_URL}/reports/daily/latest",
        token
    )

    # Ideation
    results["ideation_start"] = test_endpoint(
        "Ideation Start",
        f"{BASE_URL}/ideation/start",
        token,
        method="POST",
        data={"project_id": project_id if project_id else 1}
    )

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\nTotal tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print("\n❌ Failed tests:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")

    print("\n" + "="*60)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
