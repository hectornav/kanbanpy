"""
push.py - Web Push (VAPID) sending. No-op if VAPID keys aren't configured.
"""
import json

from . import db
from .config import settings

try:
    from pywebpush import WebPushException, webpush
    _HAS_PYWEBPUSH = True
except ImportError:  # pragma: no cover
    _HAS_PYWEBPUSH = False


def configured() -> bool:
    return bool(_HAS_PYWEBPUSH and settings.vapid_public_key and settings.vapid_private_key)


def notify_users(user_ids: list[int], payload: dict) -> None:
    """Blocking send to every subscription of the given users (run off-thread)."""
    if not configured():
        return
    for row in db.get_subscriptions_for_users(user_ids):
        try:
            webpush(
                subscription_info=json.loads(row["data"]),
                data=json.dumps(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
        except WebPushException as exc:
            # 404/410 mean the subscription is dead — clean it up.
            resp = getattr(exc, "response", None)
            if resp is not None and resp.status_code in (404, 410):
                db.delete_push_subscription(row["endpoint"])
        except Exception:
            pass
