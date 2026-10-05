"""
End-to-end integration test verifying that the full Docker stack
(frontend, api backend, postgres db, redis cache) is operating correctly.
"""
import requests
import json
import sys

def main():
    print("========================================")
    print("Testing Full Docker Stack Integration")
    print("========================================")

    # 1. Test frontend root on port 3000
    try:
        r = requests.get("http://localhost:3000")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "<div id=\"root\"></div>" in r.text, "Root element missing"
        print("[PASS] 1. Frontend serves on http://localhost:3000")
    except Exception as e:
        print(f"[FAIL] 1. Frontend on 3000: {e}")
        return 1

    # 2. Test port 5173 alias
    try:
        r = requests.get("http://localhost:5173")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        print("[PASS] 2. Frontend serves on http://localhost:5173 (alias)")
    except Exception as e:
        print(f"[FAIL] 2. Frontend on 5173: {e}")
        return 1

    # 3. Test SPA client-side routing fallback (e.g. /tournaments)
    try:
        r = requests.get("http://localhost:3000/tournaments")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "<div id=\"root\"></div>" in r.text, "SPA fallback missing index.html"
        print("[PASS] 3. Nginx SPA fallback for /tournaments routing works")
    except Exception as e:
        print(f"[FAIL] 3. SPA fallback: {e}")
        return 1

    # 4. Test backend API proxy via frontend container (/api/health)
    try:
        r = requests.get("http://localhost:3000/api/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data.get("status") == "ok", f"Health status was {data.get('status')}"
        assert data["components"]["database"]["status"] == "ok"
        assert data["components"]["cache"]["status"] == "ok"
        print("[PASS] 4. Reverse proxy to FastAPI /api/health works (DB & Cache ok)")
    except Exception as e:
        print(f"[FAIL] 4. API proxy health: {e}")
        return 1

    # 5. Test direct backend access on port 8000
    try:
        r = requests.get("http://localhost:8000/api/health")
        assert r.status_code == 200
        print("[PASS] 5. Direct backend access on http://localhost:8000 works")
    except Exception as e:
        print(f"[FAIL] 5. Direct backend: {e}")
        return 1

    # 6. Test authentication login through frontend proxy
    try:
        r = requests.post("http://localhost:3000/api/auth/login", json={
            "username": "admin",
            "password": "admin123!"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        auth_data = r.json()
        token = auth_data.get("access_token")
        assert token, "Token not returned"
        print("[PASS] 6. Authentication login (admin/admin123!) via frontend proxy works")
    except Exception as e:
        print(f"[FAIL] 6. Auth login: {e}")
        return 1

    # 7. Test authenticated request to protected route
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get("http://localhost:3000/api/tournaments", headers=headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        tourneys = r.json()
        print(f"[PASS] 7. Protected route /api/tournaments accessible ({len(tourneys)} tournaments listed)")
    except Exception as e:
        print(f"[FAIL] 7. Protected route: {e}")
        return 1

    print("========================================")
    print("ALL 7 CHECKS PASSED: Full Docker Stack Verified!")
    print("========================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
