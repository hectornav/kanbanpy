"""
org.py - Organization admin routes: invite code, member list, activate/deactivate.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from . import db
from .deps import get_current_user, require_org_admin
from .schemas import OrgMemberOut, OrgOut, OrgRenameRequest, SetMemberActiveRequest

router = APIRouter(prefix="/api/org", tags=["org"])


@router.get("", response_model=OrgOut)
def get_org(current=Depends(require_org_admin)):
    org = db.get_organization(current["org_id"])
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")
    return OrgOut(**org)


@router.put("", response_model=OrgOut)
def rename_org(req: OrgRenameRequest, current=Depends(require_org_admin)):
    if not db.rename_organization(current["org_id"], req.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Organization name is required.")
    org = db.get_organization(current["org_id"])
    return OrgOut(**org)


@router.post("/invite/rotate", response_model=OrgOut)
def rotate_invite(current=Depends(require_org_admin)):
    code = db.rotate_invite_code(current["org_id"])
    if not code:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")
    org = db.get_organization(current["org_id"])
    return OrgOut(**org)


@router.get("/members", response_model=list[OrgMemberOut])
def list_members(current=Depends(require_org_admin)):
    return [OrgMemberOut(**m) for m in db.list_org_members(current["org_id"])]


@router.patch("/members/{member_id}", response_model=OrgMemberOut)
def set_member_active(member_id: int, req: SetMemberActiveRequest, current=Depends(require_org_admin)):
    ok, msg = db.set_member_active(current["org_id"], member_id, req.is_active, current["id"])
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)
    members = {m["id"]: m for m in db.list_org_members(current["org_id"])}
    member = members.get(member_id)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return OrgMemberOut(**member)
