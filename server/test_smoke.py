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

    # ── task detail: assign, subtasks, comments ──
    print("task detail")
    bob_id = c.get("/api/users", headers=hdr).json()[0]["id"]
    c.put(f"/api/tasks/{tid}", headers=hdr, json={"text": "Comprar pintura", "column_name": "ToDo", "assignee_id": bob_id})
    detail = c.get(f"/api/tasks/{tid}", headers=hdr).json()
    check("assignee stored", detail["assignee_id"] == bob_id)
    tasks_view = c.get(f"/api/boards/{b1}/tasks", headers=hdr).json()
    check("assignee username on board", any(t.get("assignee_username") == "bob" for col in tasks_view.values() for t in col))

    s1 = c.post(f"/api/tasks/{tid}/subtasks", headers=hdr, json={"text": "Comprar rodillo"}).json()["id"]
    c.post(f"/api/tasks/{tid}/subtasks", headers=hdr, json={"text": "Tapar muebles"})
    check("subtask toggle done", c.put(f"/api/subtasks/{s1}", headers=hdr, json={"done": True}).status_code == 200)
    detail = c.get(f"/api/tasks/{tid}", headers=hdr).json()
    check("2 subtasks, 1 done", len(detail["subtasks"]) == 2 and sum(s["done"] for s in detail["subtasks"]) == 1)
    tasks_view = c.get(f"/api/boards/{b1}/tasks", headers=hdr).json()
    tcard = next(t for col in tasks_view.values() for t in col if t["id"] == tid)
    check("board card subtask counts", tcard["subtask_total"] == 2 and tcard["subtask_done"] == 1)

    cid_alice = c.post(f"/api/tasks/{tid}/comments", headers=hdr, json={"body": "¡Manos a la obra!"}).json()["id"]
    cid_bob = c.post(f"/api/tasks/{tid}/comments", headers=bob, json={"body": "Voy yo"}).json()["id"]
    detail = c.get(f"/api/tasks/{tid}", headers=hdr).json()
    check("2 comments with authors", len(detail["comments"]) == 2 and detail["comments"][0]["username"] == "alice")
    check("member cannot delete others' comment",
          c.delete(f"/api/comments/{cid_alice}", headers=bob).status_code == 403)
    check("board owner can delete any comment",
          c.delete(f"/api/comments/{cid_bob}", headers=hdr).status_code == 200)

    # ── recurring tasks ──
    print("recurring")
    rec = c.post(f"/api/boards/{b1}/tasks", headers=hdr,
                 json={"text": "Sacar la basura", "due_date": "2026-07-10", "recurrence": "weekly", "column_name": "Doing"}).json()["id"]
    before = sum(len(v) for v in c.get(f"/api/boards/{b1}/tasks", headers=hdr).json().values())
    c.post(f"/api/tasks/{rec}/move", headers=hdr, json={"column_name": "Done"})
    view = c.get(f"/api/boards/{b1}/tasks", headers=hdr).json()
    after = sum(len(v) for v in view.values())
    check("completing a recurring task spawns a new one", after == before + 1)
    nextocc = next((t for t in view["ToDo"] if t["text"] == "Sacar la basura"), None)
    check("next occurrence date advanced +7d", nextocc and nextocc["due_date"] == "2026-07-17" and nextocc["recurrence"] == "weekly")

    # ── due-date reminders ──
    print("reminders")
    import datetime as _dt
    from app import reminders
    today = _dt.date.today().isoformat()
    c.post(f"/api/boards/{b1}/tasks", headers=hdr, json={"text": "Entregar informe", "due_date": today, "column_name": "ToDo"})
    n = reminders.run_due_reminders(today)
    check("reminder processed due-today task", n >= 1)
    check("not reminded twice for same day", reminders.run_due_reminders(today) == 0)

    # ── AI planner (unconfigured in tests) ──
    print("ai planner")
    check("ai status endpoint", c.get("/api/ai/status").json()["enabled"] is False)
    check("ai-plan 503 when unconfigured",
          c.post(f"/api/boards/{b1}/ai-plan", headers=hdr, json={"idea": "Build a blog"}).status_code == 503)

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
