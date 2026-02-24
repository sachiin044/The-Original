import requests
import time
import uuid
import json

BASE_URL = "http://localhost:8000"
results_data = []

def hit(method, endpoint, json=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    start = time.time()

    result_entry = {
        "method": method,
        "endpoint": endpoint,
        "status": None,
        "time_ms": None,
        "response": None,
        "error": None
    }

    try:
        response = requests.request(method, url, json=json, headers=headers)
        duration = round((time.time() - start) * 1000, 2)

        print("=" * 70)
        print(f"{method} {endpoint}")
        print("Ran:", "YES" if response.ok else "FAILED")
        print("Status:", response.status_code)
        print("Time (ms):", duration)
        print("Response:", response.text[:300])

        result_entry["status"] = response.status_code
        result_entry["time_ms"] = duration
        try:
            result_entry["response"] = response.json()
        except:
            result_entry["response"] = response.text
        results_data.append(result_entry)

        return response
    except Exception as e:
        print(f"{method} {endpoint}")
        print("Ran: ERROR")
        print("Error:", str(e))
        
        result_entry["error"] = str(e)
        results_data.append(result_entry)
        return None


def create_api_key():
    email = f"test_{uuid.uuid4().hex[:6]}@test.com"

    response = hit(
        "POST",
        "/api-keys",
        json={
        "email": "testuser@example.com",
        "name": "prod-key",
        "environment": "prod",
        "scopes": ["repo:read", "repo:explain", "issues:chat"],
        "expires_at": "2027-01-01T00:00:00Z",
        "ip_allowlist": ["127.0.0.1", "172.17.0.1"]
        }
    )

    if response and response.status_code == 200:
        data = response.json()
        return data.get("api_key")

    return None


def main():
    print("\n🚀 Starting Integration Test\n")

    # 1️⃣ Health
    hit("GET", "/health")

    # 2️⃣ Create API key
    api_key = create_api_key()

    if not api_key:
        print("\n❌ Could not create API key. Stopping.")
        return

    headers_auth = {
        "Authorization": f"Bearer {api_key}"
    }

    # 3️⃣ Register repo
    repo_response = hit("POST", "/repos/register", json={
    "provider":"github",
    "repo_url":"https://github.com/abhigyanpatwari/GitNexus",
    "branch":"main",
    "visibility":"public",
    "credential_id": "235be2a3-a3e4-4d35-ac3a-95fdf64c08f6"
    })

    repo_id = None
    if repo_response and repo_response.status_code == 200:
        repo_id = repo_response.json().get("repo_id")

    if not repo_id:
        repo_id = str(uuid.uuid4())[:12]  # fallback for endpoint coverage

    # 4️⃣ Index repo
    hit("POST", f"/repos/{repo_id}/index")

    # 5️⃣ Repo status
    hit("GET", f"/repos/{repo_id}/status")

    # 6️⃣ Repo tree
    hit("GET", f"/repos/{repo_id}/tree")

    # 7️⃣ Repo file
    hit("GET", f"/repos/{repo_id}/files?path=README.md")

    # 8️⃣ Chat
    hit("POST", "/chat", json={
        "message": "Explain this repo",
        "repo_id": repo_id
    }, headers=headers_auth)

    # 9️⃣ Issue chat
    hit("POST", "/issues/chat", json={
        "data": {
            "repo_id": repo_id,
            "message": "issues related to security"
        }
    }, headers=headers_auth)

    # 🔟 PR chat
    hit("POST", "/pull-requests/chat", json={
        "data": {
            "repo_id": repo_id,
            "message": "PRs related to security",
        }
    }, headers=headers_auth)

    # 11️⃣ List keys
    hit("GET", "/api-keys", headers=headers_auth)

    # 12️⃣ Manage keys
    hit("GET", "/manage-keys", headers=headers_auth)

    with open("integration_results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=4)

    print("\n✅ Integration Test Completed\n")


if __name__ == "__main__":
    main()