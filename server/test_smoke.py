"""
Smoke test for the Kanbanpy Pro API (boards + archive + activity model).
Run: python test_smoke.py
"""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["KANBAN_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["KANBAN_SECRET_KEY"] = "test-secret-key-not-for-production"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)


def check(label, cond):
    print(f"  {'OK' if cond else 'XX'}  {label}")
    assert cond, label


with c:
    check("health ok", c.get("/api/health").json()["status"] == "ok")

    # ── auth ──
    c.post("/api/auth/register", json={"username": "alice", "password": "secret1",
                                       "security_q": "Pet?", "security_a": "Rex"})
    c.post("/api/auth/register", json={"username": "bob", "password": "secret2"})
    hdr = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'username': 'alice', 'password': 'secret1'}).json()['access_token']}"}
    bob = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'username': 'bob', 'password': 'secret2'}).json()['access_token']}"}

    # ── boards ──
    print("boards")
    boards = c.get("/api/boards", headers=hdr).json()
    check("default board auto-created", len(boards) == 1 and boards[0]["is_owner"])
    b0 = boards[0]["id"]
    b1 = c.post("/api/boards", headers=hdr, json={"name": "Casa", "color": "#3ecf8e"}).json()["id"]
    check("second board created", len(c.get("/api/boards", headers=hdr).json()) == 2)
    check("bob sees only his own board", all(x["id"] not in (b0, b1) for x in c.get("/api/boards", headers=bob).json()))

    # ── tasks on a board ──
    print("tasks")
    tid = c.post(f"/api/boards/{b1}/tasks", headers=hdr,
                 json={"text": "Comprar pintura", "priority": "High", "tags": ["reforma"], "column_name": "ToDo"}).json()["id"]
    board = c.get(f"/api/boards/{b1}/tasks", headers=hdr).json()
    check("task appears on board", len(board["ToDo"]) == 1 and board["ToDo"][0]["tags"] == ["reforma"])
    check("bob cannot read alice's board", c.get(f"/api/boards/{b1}/tasks", headers=bob).status_code == 403)

    check("move to Done", c.post(f"/api/tasks/{tid}/move", headers=hdr, json={"column_name": "Done"}).status_code == 200)

    # ── archive / restore ──
    print("archive + history")
    check("archive", c.post(f"/api/tasks/{tid}/archive", headers=hdr).status_code == 200)
    check("gone from active board", sum(len(v) for v in c.get(f"/api/boards/{b1}/tasks", headers=hdr).json().values()) == 0)
    arch = c.get(f"/api/boards/{b1}/tasks?archived=true", headers=hdr).json()
    check("appears in archive", len(arch["archived"]) == 1)
    check("restore", c.post(f"/api/tasks/{tid}/restore", headers=hdr).status_code == 200)
    check("back on active board", sum(len(v) for v in c.get(f"/api/boards/{b1}/tasks", headers=hdr).json().values()) == 1)

    # ── activity log ──
    activity = c.get(f"/api/boards/{b1}/activity", headers=hdr).json()
    actions = [a["action"] for a in activity]
    check("activity recorded", {"created", "moved", "archived", "restored"} <= set(actions))
    check("activity has usernames", all(a["username"] == "alice" for a in activity))

    # ── board sharing ──
    print("board sharing")
    c.put(f"/api/boards/{b1}", headers=hdr, json={"member_ids": [c.get('/api/users', headers=hdr).json()[0]['id']]})
    check("bob now sees the shared board", any(x["id"] == b1 for x in c.get("/api/boards", headers=bob).json()))
    check("bob can view its tasks", c.get(f"/api/boards/{b1}/tasks", headers=bob).status_code == 200)
    check("bob (member) can add a task", c.post(f"/api/boards/{b1}/tasks", headers=bob, json={"text": "Añadida por bob"}).status_code == 201)

    # ── push subscription ──
    print("push")
    check("public key endpoint", c.get("/api/push/public-key").status_code == 200)
    check("subscribe stores endpoint", c.post("/api/push/subscribe", headers=hdr,
          json={"endpoint": "https://example.com/x", "keys": {"p256dh": "k", "auth": "a"}}).status_code == 200)
    check("unsubscribe", c.post("/api/push/unsubscribe", headers=hdr,
          json={"endpoint": "https://example.com/x"}).status_code == 200)

    # ── login rate limiting ──
    print("rate limiting")
    for _ in range(6):
        c.post("/api/auth/login", json={"username": "ratetest", "password": "wrong"})
    c.post("/api/auth/register", json={"username": "ratetest", "password": "goodpass1"})
    check("locked after repeated failures",
          c.post("/api/auth/login", json={"username": "ratetest", "password": "goodpass1"}).status_code == 429)

    # ── deletion rules ──
    print("deletion")
    check("board owner can delete member's task",
          c.delete(f"/api/tasks/{tid}", headers=hdr).status_code == 200)
    check("non-owner cannot delete the board", c.delete(f"/api/boards/{b1}", headers=bob).status_code == 403)
    check("owner deletes the board", c.delete(f"/api/boards/{b1}", headers=hdr).status_code == 200)

print("\nALL SMOKE TESTS PASSED ✓")
