"""
push_routes.py - Endpoints for the PWA to register/unregister for Web Push.
"""
import json

from fastapi import APIRouter, Body, Depends, HTTPException, status

from . import db
from .config import settings
from .deps import get_current_user

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/public-key")
def public_key():
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe")
def subscribe(subscription: dict = Body(...), current=Depends(get_current_user)):
    endpoint = subscription.get("endpoint")
    if not endpoint:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid subscription.")
    db.save_push_subscription(current["id"], endpoint, json.dumps(subscription))
    return {"detail": "subscribed"}


@router.post("/unsubscribe")
def unsubscribe(body: dict = Body(...), current=Depends(get_current_user)):
    endpoint = body.get("endpoint")
    if endpoint:
        db.delete_push_subscription(endpoint)
    return {"detail": "unsubscribed"}
