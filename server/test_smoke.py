"""
Smoke test for the Kanbanpy Pro API. Exercises the full flow against a
throwaway database using FastAPI's TestClient. Run: python test_smoke.py
"""
import os
import tempfile

# Use an isolated temp DB and a fixed dev key before importing the app.
_tmp = tempfile.mkdtemp()
os.environ["KANBAN_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["KANBAN_SECRET_KEY"] = "test-secret-key-not-for-production"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)


def check(label, cond):
    print(f"  {'✓' if cond else '✗'} {label}")
    assert cond, label


with c:
    print("health")
    check("health ok", c.get("/api/health").json()["status"] == "ok")

    print("register + login")
    r = c.post("/api/auth/register", json={"username": "alice", "password": "secret1",
                                           "security_q": "Pet?", "security_a": "Rex"})
    check("register 201", r.status_code == 201)
    check("duplicate 409", c.post("/api/auth/register",
          json={"username": "alice", "password": "x1234"}).status_code == 409)
    c.post("/api/auth/register", json={"username": "bob", "password": "secret2"})

    r = c.post("/api/auth/login", json={"username": "alice", "password": "secret1"})
    check("login ok", r.status_code == 200)
    token = r.json()["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}
    check("wrong password 401",
          c.post("/api/auth/login", json={"username": "alice", "password": "nope"}).status_code == 401)
    check("no token 401", c.get("/api/board").status_code == 401)

    print("board + tasks")
    board = c.get("/api/board", headers=hdr).json()
    check("empty board", board == {"ToDo": [], "Doing": [], "Done": []})

    r = c.post("/api/tasks", headers=hdr, json={"text": "Buy groceries", "priority": "High",
                                                "tags": ["home"], "column_name": "ToDo"})
    check("create 201", r.status_code == 201)
    tid = r.json()["id"]

    board = c.get("/api/board", headers=hdr).json()
    check("task appears", len(board["ToDo"]) == 1 and board["ToDo"][0]["tags"] == ["home"])

    print("move + reorder")
    check("move ok", c.post(f"/api/tasks/{tid}/move", headers=hdr,
          json={"column_name": "Doing"}).status_code == 200)
    board = c.get("/api/board", headers=hdr).json()
    check("moved to Doing", len(board["Doing"]) == 1 and len(board["ToDo"]) == 0)

    print("authorization")
    rb = c.post("/api/auth/login", json={"username": "bob", "password": "secret2"})
    bob_hdr = {"Authorization": f"Bearer {rb.json()['access_token']}"}
    check("bob cannot delete alice's task",
          c.delete(f"/api/tasks/{tid}", headers=bob_hdr).status_code == 403)
    check("bob cannot see private task",
          len(c.get("/api/board", headers=bob_hdr).json()["Doing"]) == 0)

    print("sharing")
    c.put(f"/api/tasks/{tid}", headers=hdr, json={"text": "Buy groceries", "column_name": "Doing",
          "is_shared": True})
    check("bob sees globally-shared task",
          len(c.get("/api/board", headers=bob_hdr).json()["Doing"]) == 1)

    print("password reset")
    check("reset ok", c.post("/api/auth/reset-password",
          json={"username": "alice", "answer": "rex", "new_password": "newpass1"}).status_code == 200)
    check("login with new password",
          c.post("/api/auth/login", json={"username": "alice", "password": "newpass1"}).status_code == 200)

    print("delete")
    check("owner deletes", c.delete(f"/api/tasks/{tid}", headers=hdr).status_code == 200)

print("\nALL SMOKE TESTS PASSED ✓")
