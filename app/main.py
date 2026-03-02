from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.db import get_session, init_db
from app.models import (
    Asset,
    AssetStatus,
    Assignment,
    AuditLog,
    CheckoutTransaction,
    CheckoutType,
    IntegrationConnection,
    Location,
    User,
)

app = FastAPI(title="ITAM", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

POLICY_TEXT = "I accept responsibility for this company IT asset and agree to return it upon request or separation."


class AssetCreate(BaseModel):
    asset_tag: str
    serial_number: str
    model: str | None = None
    manufacturer: str | None = None
    status: AssetStatus = AssetStatus.IN_STOCK


class CheckoutRequest(BaseModel):
    asset_id: str
    user_id: str
    initiated_by_user_id: str | None = None
    due_date: datetime | None = None
    condition_notes: str | None = None
    signature_blob_ref: str | None = None
    policy_version: str = Field(default="v1")


def normalize_serial(serial: str) -> str:
    return serial.strip().upper()


def add_audit(action: str, object_type: str, object_id: str, before: dict | None, after: dict | None, reason: str | None = None) -> None:
    with get_session() as session:
        session.add(
            AuditLog(
                action=action,
                object_type=object_type,
                object_id=object_id,
                before_json=json.dumps(before) if before else None,
                after_json=json.dumps(after) if after else None,
                reason=reason,
            )
        )
        session.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()
    with get_session() as session:
        if not session.query(User).count():
            admin = User(email="admin@company.com", display_name="IT Admin", role="it_admin")
            tech = User(email="tech@company.com", display_name="IT Tech", role="it_technician")
            employee = User(email="employee@company.com", display_name="Taylor Employee", role="employee")
            hq = Location(name="HQ", code="HQ")
            session.add_all([admin, tech, employee, hq])
            session.commit()
        if not session.query(IntegrationConnection).count():
            session.add_all([
                IntegrationConnection(provider="kandji", status="connected"),
                IntegrationConnection(provider="abm", status="connected"),
            ])
            session.commit()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    with get_session() as session:
        stats = {
            "total": session.query(func.count(Asset.id)).scalar() or 0,
            "checked_out": session.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.CHECKED_OUT).scalar() or 0,
            "in_stock": session.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.IN_STOCK).scalar() or 0,
            "in_repair": session.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.IN_REPAIR).scalar() or 0,
            "lost": session.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.LOST).scalar() or 0,
        }
        overdue = session.query(Assignment).filter(Assignment.state == "overdue").all()
        return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats, "overdue": overdue})


@app.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request, q: str | None = None, status: AssetStatus | None = None):
    with get_session() as session:
        query = session.query(Asset)
        if q:
            like = f"%{q}%"
            query = query.filter((Asset.asset_tag.like(like)) | (Asset.serial_number.like(like)) | (Asset.model.like(like)))
        if status:
            query = query.filter(Asset.status == status)
        assets = query.order_by(Asset.created_at.desc()).all()
        return templates.TemplateResponse("assets.html", {"request": request, "assets": assets, "statuses": list(AssetStatus)})


@app.post("/assets/create")
def assets_create(asset_tag: str = Form(...), serial_number: str = Form(...), model: str = Form(""), manufacturer: str = Form("")):
    with get_session() as session:
        normalized = normalize_serial(serial_number)
        if session.query(Asset).filter(Asset.serial_number == normalized).first():
            raise HTTPException(status_code=400, detail="Serial number must be unique")
        if session.query(Asset).filter(Asset.asset_tag == asset_tag).first():
            raise HTTPException(status_code=400, detail="Asset tag must be unique")
        asset = Asset(
            asset_tag=asset_tag,
            serial_number=normalized,
            model=model or None,
            manufacturer=manufacturer or None,
            status=AssetStatus.IN_STOCK,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        add_audit("asset.created", "asset", asset.id, None, {"asset_tag": asset.asset_tag, "status": asset.status.value})
    return RedirectResponse("/assets", status_code=303)


@app.get("/assets/{asset_id}", response_class=HTMLResponse)
def asset_detail(request: Request, asset_id: str):
    with get_session() as session:
        asset = session.get(Asset, asset_id)
        if not asset:
            raise HTTPException(404)
        assignments = session.query(Assignment).filter(Assignment.asset_id == asset_id).order_by(Assignment.assigned_at.desc()).all()
        return templates.TemplateResponse("asset_detail.html", {"request": request, "asset": asset, "assignments": assignments})


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request):
    with get_session() as session:
        assets = session.query(Asset).filter(Asset.status.in_([AssetStatus.IN_STOCK, AssetStatus.ASSIGNED, AssetStatus.PENDING_ENROLLMENT])).all()
        users = session.query(User).filter(User.role == "employee").all()
        techs = session.query(User).filter(User.role.in_(["it_admin", "it_technician"])).all()
        return templates.TemplateResponse("checkout.html", {"request": request, "assets": assets, "users": users, "techs": techs, "policy": POLICY_TEXT})


@app.post("/checkout")
def checkout_submit(
    asset_id: str = Form(...),
    user_id: str = Form(...),
    initiated_by_user_id: str = Form(...),
    due_date: str = Form(""),
    condition_notes: str = Form(""),
    signature: str = Form(...),
):
    with get_session() as session:
        asset = session.get(Asset, asset_id)
        if not asset:
            raise HTTPException(404, "Asset not found")
        if asset.status in [AssetStatus.RETIRED, AssetStatus.LOST, AssetStatus.IN_REPAIR]:
            raise HTTPException(400, "Asset cannot be checked out in current state")

        due = datetime.fromisoformat(due_date) if due_date else None
        if due and due < datetime.utcnow():
            raise HTTPException(400, "Due date cannot be in the past")

        before = {"status": asset.status.value, "assigned_user_id": asset.assigned_user_id}
        asset.status = AssetStatus.CHECKED_OUT
        asset.assigned_user_id = user_id

        assignment = Assignment(asset_id=asset.id, user_id=user_id, expected_return_at=due, state="active")
        transaction = CheckoutTransaction(
            type=CheckoutType.CHECKOUT,
            initiated_by_user_id=initiated_by_user_id,
            subject_user_id=user_id,
            asset_id=asset.id,
            acknowledged_at=datetime.utcnow(),
            due_date=due,
            condition_notes=condition_notes or None,
            signature_blob_ref=signature,
            policy_version="v1",
        )
        session.add_all([assignment, transaction])
        session.commit()
        add_audit("checkout.completed", "asset", asset.id, before, {"status": asset.status.value, "assigned_user_id": user_id})
    return RedirectResponse(f"/assets/{asset_id}", status_code=303)


@app.get("/checkin", response_class=HTMLResponse)
def checkin_page(request: Request):
    with get_session() as session:
        assignments = session.query(Assignment).filter(Assignment.state == "active").all()
        return templates.TemplateResponse("checkin.html", {"request": request, "assignments": assignments})


@app.post("/checkin")
def checkin_submit(assignment_id: str = Form(...), condition_notes: str = Form(""), damaged: bool = Form(False)):
    with get_session() as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment or assignment.state != "active":
            raise HTTPException(404, "Active assignment not found")
        asset = session.get(Asset, assignment.asset_id)
        before = {"status": asset.status.value, "assigned_user_id": asset.assigned_user_id}
        assignment.state = "closed"
        assignment.returned_at = datetime.utcnow()
        asset.assigned_user_id = None
        asset.status = AssetStatus.IN_REPAIR if damaged else AssetStatus.IN_STOCK
        tx = CheckoutTransaction(
            type=CheckoutType.CHECKIN,
            initiated_by_user_id=None,
            subject_user_id=assignment.user_id,
            asset_id=asset.id,
            acknowledged_at=datetime.utcnow(),
            condition_notes=condition_notes or None,
        )
        session.add(tx)
        session.commit()
        add_audit("checkin.completed", "asset", asset.id, before, {"status": asset.status.value, "assigned_user_id": None})
    return RedirectResponse(f"/assets/{asset.id}", status_code=303)


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    with get_session() as session:
        users = session.query(User).all()
        return templates.TemplateResponse("users.html", {"request": request, "users": users})


@app.get("/locations", response_class=HTMLResponse)
def locations_page(request: Request):
    with get_session() as session:
        locations = session.query(Location).all()
        return templates.TemplateResponse("locations.html", {"request": request, "locations": locations})


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    with get_session() as session:
        by_user = session.query(User.display_name, func.count(Asset.id)).join(Asset, Asset.assigned_user_id == User.id, isouter=True).group_by(User.id).all()
        overdue = session.query(Assignment).filter(Assignment.state == "overdue").all()
        return templates.TemplateResponse("reports.html", {"request": request, "by_user": by_user, "overdue": overdue})


@app.get("/integrations", response_class=HTMLResponse)
def integrations_page(request: Request):
    with get_session() as session:
        connections = session.query(IntegrationConnection).all()
        return templates.TemplateResponse("integrations.html", {"request": request, "connections": connections})


@app.post("/integrations/{provider}/sync")
def sync_provider(provider: str):
    with get_session() as session:
        conn = session.query(IntegrationConnection).filter_by(provider=provider).first()
        if not conn:
            raise HTTPException(404)
        conn.last_success_at = datetime.utcnow()
        session.commit()
        add_audit("integration.sync", "integration", conn.id, None, {"provider": provider, "synced_at": conn.last_success_at.isoformat()})
    return RedirectResponse("/integrations", status_code=303)


@app.get("/audit-log", response_class=HTMLResponse)
def audit_page(request: Request):
    with get_session() as session:
        logs = session.query(AuditLog).order_by(AuditLog.event_ts.desc()).limit(200).all()
        return templates.TemplateResponse("audit_log.html", {"request": request, "logs": logs})


@app.get("/api/assets")
def api_assets():
    with get_session() as session:
        assets = session.query(Asset).all()
        return [{"id": a.id, "asset_tag": a.asset_tag, "serial_number": a.serial_number, "status": a.status.value} for a in assets]


@app.post("/api/assets")
def api_create_asset(payload: AssetCreate):
    with get_session() as session:
        serial = normalize_serial(payload.serial_number)
        if session.query(Asset).filter(Asset.serial_number == serial).first():
            raise HTTPException(400, "Serial number must be unique")
        if session.query(Asset).filter(Asset.asset_tag == payload.asset_tag).first():
            raise HTTPException(400, "Asset tag must be unique")
        asset = Asset(
            asset_tag=payload.asset_tag,
            serial_number=serial,
            model=payload.model,
            manufacturer=payload.manufacturer,
            status=payload.status,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        add_audit("asset.created", "asset", asset.id, None, {"asset_tag": asset.asset_tag, "status": asset.status.value})
        return {"id": asset.id}


@app.post("/api/checkout")
def api_checkout(payload: CheckoutRequest):
    with get_session() as session:
        asset = session.get(Asset, payload.asset_id)
        if not asset:
            raise HTTPException(404, "Asset not found")
        if asset.status in [AssetStatus.RETIRED, AssetStatus.LOST, AssetStatus.IN_REPAIR]:
            raise HTTPException(400, "Asset cannot be checked out")
        if payload.due_date and payload.due_date < datetime.utcnow():
            raise HTTPException(400, "Due date cannot be in the past")

        before = {"status": asset.status.value}
        asset.status = AssetStatus.CHECKED_OUT
        asset.assigned_user_id = payload.user_id
        session.add(Assignment(asset_id=asset.id, user_id=payload.user_id, expected_return_at=payload.due_date, state="active"))
        session.add(
            CheckoutTransaction(
                type=CheckoutType.CHECKOUT,
                initiated_by_user_id=payload.initiated_by_user_id,
                subject_user_id=payload.user_id,
                asset_id=asset.id,
                due_date=payload.due_date,
                condition_notes=payload.condition_notes,
                signature_blob_ref=payload.signature_blob_ref,
                policy_version=payload.policy_version,
                acknowledged_at=datetime.utcnow(),
            )
        )
        session.commit()
        add_audit("checkout.completed", "asset", asset.id, before, {"status": asset.status.value})
        return {"ok": True, "asset_status": asset.status.value}
