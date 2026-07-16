"""
api_client.py - REST client the PyQt6 desktop app uses to talk to the
Kanbanpy Pro backend (the shared core of the hybrid "Option C" architecture).

The base URL comes from the KANBAN_API_URL environment variable, e.g.
    KANBAN_API_URL=http://your-nas.ts.net:8000
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = os.getenv("KANBAN_API_URL", "http://localhost:8000")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class KanbanClient:
    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    # ── low-level request ──
    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list | None:
        url = f"{self.base_url}/api{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.reason
            try:
                detail = json.loads(e.read()).get("detail", detail)
            except Exception:
                pass
            raise ApiError(str(detail), e.code)
        except urllib.error.URLError as e:
            raise ApiError(f"No se pudo conectar al servidor ({self.base_url}): {e.reason}")

    # ── auth ──
    def login(self, username: str, password: str) -> dict:
        res = self._request("POST", "/auth/login", {"username": username, "password": password})
        self.token = res["access_token"]
        return res["user"]

    def register(self, username: str, password: str, security_q: str, security_a: str) -> dict:
        return self._request("POST", "/auth/register", {
            "username": username, "password": password,
            "security_q": security_q, "security_a": security_a,
        })

    def security_question(self, username: str) -> str:
        return self._request("GET", f"/auth/security-question?username={urllib.parse.quote(username)}")["security_q"]

    def reset_password(self, username: str, answer: str, new_password: str) -> None:
        self._request("POST", "/auth/reset-password", {
            "username": username, "answer": answer, "new_password": new_password,
        })

    # ── board / tasks ──
    def board(self) -> dict:
        return self._request("GET", "/board")

    def users(self) -> list:
        return self._request("GET", "/users")

    def create_task(self, task: dict) -> int:
        return self._request("POST", "/tasks", task)["id"]

    def update_task(self, task_id: int, task: dict) -> None:
        self._request("PUT", f"/tasks/{task_id}", task)

    def move_task(self, task_id: int, column_name: str) -> None:
        self._request("POST", f"/tasks/{task_id}/move", {"column_name": column_name})

    def delete_task(self, task_id: int) -> None:
        self._request("DELETE", f"/tasks/{task_id}")

    def task_shares(self, task_id: int) -> list:
        return self._request("GET", f"/tasks/{task_id}/shares")["shared_user_ids"]
