import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from . import config
from .agents import ai_enabled, analyze_quote_file, run_audit_agent, run_procurement_agent
from .db import Base, engine, get_db, SessionLocal
from .models import (ROLES, Approval, AuditFlag, AuditLog, Department, Notification, PurchaseRequest,
                     Quote, RequestItem, User, Vendor)
from .services import (ROLE_LABELS, approval_chain, audit, budget_status, current_user, hash_password, make_token,
                       next_number, notify, require_roles, users_with_role, verify_audit_chain, verify_password)

app = FastAPI(title="Procurement & Approval System", docs_url="/api/docs", openapi_url="/api/openapi.json")

_redis = None
if config.REDIS_URL:
    try:
        import redis
        _redis = redis.from_url(config.REDIS_URL, socket_connect_timeout=1)
        _redis.ping()
    except Exception:  # noqa: BLE001
        _redis = None


def cache_get(key):
    if _redis:
        try:
            v = _redis.get(key)
            return json.loads(v) if v else None
        except Exception:  # noqa: BLE001
            return None


def cache_set(key, value, ttl=15):
    if _redis:
        try:
            _redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception:  # noqa: BLE001
            pass


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.execute(select(func.count(User.id))).scalar() == 0:
            if not config.ADMIN_PASSWORD:
                print("!! لم يُضبط ADMIN_PASSWORD في .env — لن يُنشأ حساب المشرف الأول.")
                return
            admin = User(name=config.ADMIN_NAME, email=config.ADMIN_EMAIL.lower(),
                         password_hash=hash_password(config.ADMIN_PASSWORD), role="admin")
            db.add(admin)
            db.flush()
            audit(db, admin, "system.bootstrap", "user", admin.id, "إنشاء حساب المشرف الأول")
            db.commit()


# ====================== العرض (Serializers) ======================
def u_out(u: User | None):
    if not u:
        return None
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "role_label": ROLE_LABELS.get(u.role, u.role),
            "department_id": u.department_id, "department": u.department.name if u.department else None, "active": u.active}


def q_out(q: Quote):
    return {"id": q.id, "vendor_id": q.vendor_id, "vendor": q.vendor.name, "amount": q.amount, "delivery_days": q.delivery_days,
            "notes": q.notes, "file_name": q.file_name, "has_file": bool(q.file_path), "analysis": q.analysis}


def r_out(r: PurchaseRequest, full=False):
    d = {"id": r.id, "number": r.number, "title": r.title, "amount": r.amount, "status": r.status,
         "department": r.department.name, "department_id": r.department_id, "requester": r.requester.name,
         "requester_id": r.requester_id, "current_level": r.current_level,
         "waiting_role": (r.approvals[r.current_level].role if r.status == "pending" and r.current_level < len(r.approvals) else None),
         "created_at": r.created_at.isoformat(), "flags_open": len([f for f in r.flags if not f.resolved])}
    if full:
        d.update({
            "justification": r.justification, "selected_quote_id": r.selected_quote_id, "ai_recommendation": r.ai_recommendation,
            "items": [{"id": i.id, "name": i.name, "quantity": i.quantity, "unit_price": i.unit_price} for i in r.items],
            "quotes": [q_out(q) for q in r.quotes],
            "approvals": [{"level": a.level, "role": a.role, "role_label": ROLE_LABELS[a.role], "decision": a.decision,
                           "approver": a.approver.name if a.approver else None, "comment": a.comment,
                           "decided_at": a.decided_at.isoformat() if a.decided_at else None} for a in r.approvals],
            "flags": [{"id": f.id, "code": f.code, "severity": f.severity, "message": f.message, "resolved": f.resolved} for f in r.flags],
        })
    return d


def get_request(db: Session, rid: int, user: User) -> PurchaseRequest:
    r = db.get(PurchaseRequest, rid)
    if not r or not can_view(user, r):
        raise HTTPException(404, "الطلب غير موجود")
    return r


def can_view(user: User, r: PurchaseRequest) -> bool:
    if user.role in ("admin", "finance_manager", "general_manager"):
        return True
    if user.role == "dept_manager":
        return r.department_id == user.department_id
    return r.requester_id == user.id


# ====================== المصادقة ======================
class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        audit(db, None, "auth.login_failed", "user", None, f"محاولة دخول فاشلة: {body.email[:80]}")
        db.commit()
        raise HTTPException(401, "البريد أو كلمة المرور غير صحيحة")
    audit(db, user, "auth.login", "user", user.id)
    db.commit()
    return {"token": make_token(user), "user": u_out(user)}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return u_out(user)


# ====================== المستخدمون ======================
class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str
    department_id: int | None = None


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    department_id: int | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


@app.get("/api/users")
def list_users(user: User = Depends(require_roles("admin", "finance_manager", "general_manager")), db: Session = Depends(get_db)):
    return [u_out(u) for u in db.execute(select(User).order_by(User.id)).scalars()]


@app.post("/api/users")
def create_user(body: UserIn, admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, "دور غير صحيح")
    if body.role in ("employee", "dept_manager") and not body.department_id:
        raise HTTPException(400, "يجب تحديد القسم لهذا الدور")
    if db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none():
        raise HTTPException(409, "البريد مستخدم من قبل")
    u = User(name=body.name, email=body.email.lower(), password_hash=hash_password(body.password), role=body.role, department_id=body.department_id)
    db.add(u)
    db.flush()
    audit(db, admin, "user.create", "user", u.id, f"{u.name} — {ROLE_LABELS[u.role]}")
    db.commit()
    return u_out(u)


@app.patch("/api/users/{uid}")
def patch_user(uid: int, body: UserPatch, admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "المستخدم غير موجود")
    changes = []
    if body.name is not None:
        u.name = body.name
        changes.append("الاسم")
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(400, "دور غير صحيح")
        u.role = body.role
        changes.append(f"الدور→{ROLE_LABELS[body.role]}")
    if body.department_id is not None:
        u.department_id = body.department_id
        changes.append("القسم")
    if body.active is not None:
        if u.id == admin.id and not body.active:
            raise HTTPException(400, "لا يمكنك تعطيل حسابك")
        u.active = body.active
        changes.append("تفعيل" if body.active else "تعطيل")
    if body.password:
        u.password_hash = hash_password(body.password)
        changes.append("كلمة المرور")
    audit(db, admin, "user.update", "user", u.id, "، ".join(changes))
    db.commit()
    return u_out(u)


# ====================== الأقسام والميزانيات ======================
class DeptIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    annual_budget: float = Field(ge=0)


@app.get("/api/departments")
def list_departments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for d in db.execute(select(Department).order_by(Department.name)).scalars():
        if user.role in ("employee", "dept_manager") and d.id != user.department_id:
            continue
        out.append({"id": d.id, "name": d.name, **budget_status(db, d.id)})
    return out


@app.post("/api/departments")
def create_department(body: DeptIn, user: User = Depends(require_roles("admin", "finance_manager")), db: Session = Depends(get_db)):
    if db.execute(select(Department).where(Department.name == body.name)).scalar_one_or_none():
        raise HTTPException(409, "القسم موجود")
    d = Department(name=body.name, annual_budget=body.annual_budget)
    db.add(d)
    db.flush()
    audit(db, user, "department.create", "department", d.id, f"{d.name} — ميزانية {d.annual_budget:,.3f}")
    db.commit()
    return {"id": d.id, "name": d.name, **budget_status(db, d.id)}


@app.patch("/api/departments/{did}")
def update_department(did: int, body: DeptIn, user: User = Depends(require_roles("admin", "finance_manager")), db: Session = Depends(get_db)):
    d = db.get(Department, did)
    if not d:
        raise HTTPException(404, "القسم غير موجود")
    audit(db, user, "department.update", "department", d.id, f"الميزانية {d.annual_budget:,.3f} → {body.annual_budget:,.3f}")
    d.name, d.annual_budget = body.name, body.annual_budget
    db.commit()
    return {"id": d.id, "name": d.name, **budget_status(db, d.id)}


# ====================== الموردون ======================
class VendorIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    tax_number: str = ""
    email: str = ""
    phone: str = ""


@app.get("/api/vendors")
def list_vendors(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": v.id, "name": v.name, "tax_number": v.tax_number, "email": v.email, "phone": v.phone, "active": v.active}
            for v in db.execute(select(Vendor).order_by(Vendor.name)).scalars()]


@app.post("/api/vendors")
def create_vendor(body: VendorIn, user: User = Depends(require_roles("admin", "finance_manager", "dept_manager")), db: Session = Depends(get_db)):
    if db.execute(select(Vendor).where(Vendor.name == body.name)).scalar_one_or_none():
        raise HTTPException(409, "المورد موجود")
    v = Vendor(**body.model_dump())
    db.add(v)
    db.flush()
    audit(db, user, "vendor.create", "vendor", v.id, v.name)
    db.commit()
    return {"id": v.id, "name": v.name}


# ====================== طلبات الشراء ======================
class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class RequestIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    justification: str = ""
    items: list[ItemIn] = Field(min_length=1)


@app.get("/api/requests")
def list_requests(scope: str = "visible", user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(PurchaseRequest).order_by(PurchaseRequest.id.desc())
    rows = [r for r in db.execute(q).scalars() if can_view(user, r)]
    if scope == "mine":
        rows = [r for r in rows if r.requester_id == user.id]
    elif scope == "to_approve":
        rows = [r for r in rows if awaiting_me(user, r)]
    return [r_out(r) for r in rows]


def awaiting_me(user: User, r: PurchaseRequest) -> bool:
    if r.status != "pending" or r.requester_id == user.id or r.current_level >= len(r.approvals):
        return False
    lvl = r.approvals[r.current_level]
    if lvl.role != user.role:
        return False
    return user.role != "dept_manager" or user.department_id == r.department_id


@app.post("/api/requests")
def create_request(body: RequestIn, user: User = Depends(require_roles("employee", "dept_manager")), db: Session = Depends(get_db)):
    if not user.department_id:
        raise HTTPException(400, "حسابك غير مرتبط بقسم")
    r = PurchaseRequest(number=next_number(db), title=body.title, justification=body.justification,
                        department_id=user.department_id, requester_id=user.id,
                        amount=sum(i.quantity * i.unit_price for i in body.items))
    r.items = [RequestItem(**i.model_dump()) for i in body.items]
    db.add(r)
    db.flush()
    audit(db, user, "request.create", "request", r.id, f"{r.number} — {r.title}")
    db.commit()
    return r_out(get_request(db, r.id, user), full=True)


@app.get("/api/requests/{rid}")
def request_detail(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    out = r_out(r, full=True)
    out["budget"] = budget_status(db, r.department_id, exclude_request_id=r.id)
    out["can_decide"] = awaiting_me(user, r)
    out["can_edit"] = r.status == "draft" and r.requester_id == user.id
    return out


def _editable(r: PurchaseRequest, user: User):
    if r.status != "draft" or r.requester_id != user.id:
        raise HTTPException(403, "لا يمكن تعديل هذا الطلب")


ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


@app.post("/api/requests/{rid}/quotes")
async def add_quote(rid: int, vendor_id: int = Form(...), amount: float = Form(..., gt=0), delivery_days: int = Form(0),
                    notes: str = Form(""), file: UploadFile | None = File(None),
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    _editable(r, user)
    vendor = db.get(Vendor, vendor_id)
    if not vendor or not vendor.active:
        raise HTTPException(400, "المورد غير صحيح")
    if any(q.vendor_id == vendor_id for q in r.quotes):
        raise HTTPException(409, "يوجد عرض من هذا المورد بالفعل")
    q = Quote(request_id=r.id, vendor_id=vendor_id, amount=amount, delivery_days=delivery_days, notes=notes)
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, "المسموح: PDF أو صورة (PNG/JPG/WEBP)")
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "حجم الملف أكبر من 10 ميغابايت")
        path = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
        path.write_bytes(content)
        q.file_name, q.file_path = Path(file.filename).name[:200], str(path)
    db.add(q)
    db.flush()
    q.vendor = vendor
    q.analysis = analyze_quote_file(q)
    r.quotes.append(q) if q not in r.quotes else None
    audit(db, user, "quote.add", "request", r.id, f"{vendor.name} — {amount:,.3f} ر.ع")
    db.commit()
    return q_out(q)


@app.delete("/api/requests/{rid}/quotes/{qid}")
def delete_quote(rid: int, qid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    _editable(r, user)
    q = next((x for x in r.quotes if x.id == qid), None)
    if not q:
        raise HTTPException(404, "العرض غير موجود")
    if r.selected_quote_id == qid:
        r.selected_quote_id = None
    r.quotes.remove(q)
    audit(db, user, "quote.delete", "request", r.id, q.vendor.name)
    db.commit()
    return {"ok": True}


@app.get("/api/quotes/{qid}/file")
def quote_file(qid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.get(Quote, qid)
    if not q or not q.file_path:
        raise HTTPException(404, "الملف غير موجود")
    get_request(db, q.request_id, user)
    return FileResponse(q.file_path, filename=q.file_name)


class SelectIn(BaseModel):
    quote_id: int
    justification: str | None = None


@app.post("/api/requests/{rid}/select-quote")
def select_quote(rid: int, body: SelectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    _editable(r, user)
    q = next((x for x in r.quotes if x.id == body.quote_id), None)
    if not q:
        raise HTTPException(404, "العرض غير موجود")
    r.selected_quote_id, r.amount = q.id, q.amount
    if body.justification is not None:
        r.justification = body.justification
    audit(db, user, "quote.select", "request", r.id, f"{q.vendor.name} — {q.amount:,.3f} ر.ع")
    db.commit()
    return {"ok": True}


@app.post("/api/requests/{rid}/submit")
def submit_request(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    _editable(r, user)
    if not r.quotes:
        raise HTTPException(400, "أضف عرض سعر واحداً على الأقل قبل الإرسال")
    if not r.selected_quote_id:
        raise HTTPException(400, "اختر عرض السعر المقترح قبل الإرسال")
    r.status, r.current_level, r.submitted_at = "pending", 0, datetime.utcnow()
    r.approvals.clear()
    for lvl, role in enumerate(approval_chain(r.amount)):
        r.approvals.append(Approval(level=lvl, role=role))
    db.flush()
    new_flags = run_audit_agent(db, r)
    db.flush()
    r.ai_recommendation = run_procurement_agent(db, r)
    _log_agents(db, r, new_flags)
    audit(db, user, "request.submit", "request", r.id,
          f"{r.number} — {r.amount:,.3f} ر.ع — مسار: {' ← '.join(ROLE_LABELS[a.role] for a in r.approvals)}"
          + (f" — تنبيهات تدقيق: {len(new_flags)}" if new_flags else ""))
    notify(db, [u.id for u in users_with_role(db, "dept_manager", r.department_id)], f"طلب جديد بانتظار موافقتك: {r.number} — {r.title}", r.id)
    if any(f.severity == "high" for f in new_flags):
        notify(db, [u.id for u in users_with_role(db, "finance_manager")], f"وكيل التدقيق رصد تنبيهاً عالي الخطورة في {r.number}", r.id)
    db.commit()
    return r_out(r, full=True)


class DecisionIn(BaseModel):
    decision: str
    comment: str = ""


@app.post("/api/requests/{rid}/decision")
def decide(rid: int, body: DecisionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "قرار غير صحيح")
    if not awaiting_me(user, r):
        raise HTTPException(403, "هذا الطلب ليس بانتظار قرارك")
    if body.decision == "rejected" and len(body.comment.strip()) < 3:
        raise HTTPException(400, "سبب الرفض مطلوب")
    a = r.approvals[r.current_level]
    a.decision, a.approver_id, a.approver, a.comment, a.decided_at = body.decision, user.id, user, body.comment, datetime.utcnow()
    label = ROLE_LABELS[a.role]
    if body.decision == "rejected":
        r.status = "rejected"
        notify(db, [r.requester_id], f"تم رفض طلبك {r.number} من {label}: {body.comment}", r.id)
    else:
        r.current_level += 1
        if r.current_level >= len(r.approvals):
            r.status = "approved"
            notify(db, [r.requester_id], f"تمت الموافقة النهائية على طلبك {r.number}", r.id)
            notify(db, [u.id for u in users_with_role(db, "finance_manager")], f"طلب معتمد جاهز للصرف: {r.number} — {r.amount:,.3f} ر.ع", r.id)
        else:
            nxt = r.approvals[r.current_level].role
            notify(db, [u.id for u in users_with_role(db, nxt, r.department_id if nxt == "dept_manager" else None)],
                   f"طلب بانتظار موافقتك: {r.number} — {r.title}", r.id)
            notify(db, [r.requester_id], f"وافق {label} على طلبك {r.number}", r.id)
    audit(db, user, f"request.{body.decision}", "request", r.id, f"{r.number} — {label}" + (f" — {body.comment}" if body.comment else ""))
    db.commit()
    return r_out(r, full=True)


@app.post("/api/requests/{rid}/cancel")
def cancel(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    if r.requester_id != user.id or r.status not in ("draft", "pending"):
        raise HTTPException(403, "لا يمكن إلغاء هذا الطلب")
    r.status = "cancelled"
    audit(db, user, "request.cancel", "request", r.id, r.number)
    db.commit()
    return r_out(r)


@app.post("/api/requests/{rid}/reanalyze")
def reanalyze(rid: int, user: User = Depends(require_roles("dept_manager", "finance_manager", "general_manager", "admin")), db: Session = Depends(get_db)):
    r = get_request(db, rid, user)
    for q in r.quotes:
        q.analysis = analyze_quote_file(q)
    run_audit_agent(db, r)
    db.flush()
    r.ai_recommendation = run_procurement_agent(db, r)
    _log_agents(db, r, [f for f in r.flags if not f.resolved])
    audit(db, user, "agent.reanalyze", "request", r.id, f"{r.number} — أعاد {user.name} تشغيل الوكلاء")
    db.commit()
    return r_out(r, full=True)


# ====================== التدقيق ======================
AUDIT_ROLES = ("admin", "finance_manager", "general_manager")


@app.get("/api/audit/logs")
def audit_logs(limit: int = 200, user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)):
    rows = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))).scalars()
    return [{"id": a.id, "ts": a.ts.isoformat(), "user": a.user_name, "action": a.action, "entity": a.entity,
             "entity_id": a.entity_id, "details": a.details} for a in rows]


@app.get("/api/audit/verify")
def audit_verify(user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)):
    return verify_audit_chain(db)


@app.get("/api/audit/flags")
def audit_flags(user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)):
    rows = db.execute(select(AuditFlag).order_by(AuditFlag.id.desc())).scalars()
    out = []
    for f in rows:
        r = db.get(PurchaseRequest, f.request_id)
        out.append({"id": f.id, "request_id": f.request_id, "number": r.number if r else "", "title": r.title if r else "",
                    "code": f.code, "severity": f.severity, "message": f.message, "resolved": f.resolved, "created_at": f.created_at.isoformat()})
    return out


@app.post("/api/audit/scan")
def audit_scan(user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)):
    total = 0
    for r in db.execute(select(PurchaseRequest).where(PurchaseRequest.status == "pending")).scalars():
        total += len(run_audit_agent(db, r))
    audit(db, user, "agent.audit_scan", "system", None, f"فحص الطلبات المعلّقة — تنبيهات: {total}")
    db.commit()
    return {"flags_found": total}


class ResolveIn(BaseModel):
    note: str = Field(min_length=3)


@app.post("/api/audit/flags/{fid}/resolve")
def resolve_flag(fid: int, body: ResolveIn, user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)):
    f = db.get(AuditFlag, fid)
    if not f:
        raise HTTPException(404, "التنبيه غير موجود")
    f.resolved = True
    audit(db, user, "flag.resolve", "request", f.request_id, f"{f.code} — {body.note}")
    db.commit()
    return {"ok": True}


# ====================== لوحة التحكم والتنبيهات ======================
@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    key = f"dash:{user.id}"
    cached = cache_get(key)
    if cached:
        return cached
    rows = [r for r in db.execute(select(PurchaseRequest)).scalars() if can_view(user, r)]
    by = lambda s: [r for r in rows if r.status == s]  # noqa: E731
    out = {
        "counts": {s: len(by(s)) for s in ("draft", "pending", "approved", "rejected", "cancelled")},
        "approved_total": sum(r.amount for r in by("approved")),
        "pending_total": sum(r.amount for r in by("pending")),
        "to_approve": len([r for r in rows if awaiting_me(user, r)]),
        "open_flags": sum(1 for r in rows for f in r.flags if not f.resolved) if user.role in AUDIT_ROLES else None,
        "agents": {"ai_enabled": ai_enabled()},
    }
    cache_set(key, out)
    return out


@app.get("/api/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(30)).scalars()
    return [{"id": n.id, "message": n.message, "request_id": n.request_id, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@app.post("/api/notifications/read")
def notifications_read(user: User = Depends(current_user), db: Session = Depends(get_db)):
    for n in db.execute(select(Notification).where(Notification.user_id == user.id, Notification.read == False)).scalars():  # noqa: E712
        n.read = True
    db.commit()
    return {"ok": True}


REC_AR = {"approve": "الموافقة", "reject": "الرفض", "review": "المراجعة البشرية"}


def _log_agents(db: Session, r: PurchaseRequest, flags):
    audit(db, None, "agent.audit", "request", r.id,
          f"{r.number}: " + (f"رصد {len(flags)} تنبيه ({', '.join(sorted({f.code for f in flags}))})" if flags else "لا توجد مخالفات"),
          actor="وكيل التدقيق")
    rec = r.ai_recommendation or {}
    audit(db, None, "agent.procurement", "request", r.id,
          f"{r.number}: توصية بـ{REC_AR.get(rec.get('recommendation'), '—')} ({'ذكاء اصطناعي' if rec.get('mode') == 'ai' else 'قواعد'}) — {rec.get('reasoning', '')}",
          actor="وكيل المشتريات")


class ChatIn(BaseModel):
    agent: str
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []


@app.post("/api/agents/chat")
def agents_chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .agent_chat import chat, AGENTS
    if body.agent not in AGENTS:
        raise HTTPException(404, "وكيل غير معروف")
    out = chat(db, user, body.agent, body.message, body.history)
    audit(db, user, "agent.chat", "agent", None, f"{AGENTS[body.agent]['name']}: {body.message[:120]}", actor=user.name)
    db.commit()
    return out


@app.get("/api/agents/catalog")
def agents_catalog(user: User = Depends(current_user)):
    from .agent_chat import AGENTS
    return [{"key": k, "name": v["name"], "chips": v["chips"], "tools": v["tools"]} for k, v in AGENTS.items()]


@app.get("/api/agents/overview")
def agents_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = [r for r in db.execute(select(PurchaseRequest).order_by(PurchaseRequest.id.desc())).scalars() if can_view(user, r)]
    analyzed = [r for r in rows if r.ai_recommendation]
    recs = {"approve": 0, "review": 0, "reject": 0}
    for r in analyzed:
        recs[r.ai_recommendation.get("recommendation", "review")] += 1
    files = {"ai": 0, "pdf_text": 0, "unread": 0}
    for r in rows:
        for q in r.quotes:
            if q.file_path:
                m = (q.analysis or {}).get("mode")
                files["ai" if m == "ai" else "pdf_text" if m == "pdf_text" else "unread"] += 1
    by_code: dict[str, int] = {}
    open_flags = 0
    for r in rows:
        for f in r.flags:
            if not f.resolved:
                open_flags += 1
                by_code[f.code] = by_code.get(f.code, 0) + 1
    activity = []
    if user.role in AUDIT_ROLES or user.role == "dept_manager":
        ids = {r.id for r in rows}
        for a in db.execute(select(AuditLog).where(AuditLog.action.like("agent.%")).order_by(AuditLog.id.desc()).limit(60)).scalars():
            if user.role in AUDIT_ROLES or a.entity_id in ids:
                activity.append({"id": a.id, "ts": a.ts.isoformat(), "agent": a.user_name, "details": a.details})
    return {
        "ai_enabled": ai_enabled(), "model": config.AI_MODEL if ai_enabled() else None,
        "analyzed": len(analyzed), "recs": recs, "files": files, "open_flags": open_flags, "flags_by_code": by_code,
        "pending": [{"id": r.id, "number": r.number, "title": r.title, "amount": r.amount,
                     "recommendation": r.ai_recommendation.get("recommendation") if r.ai_recommendation else None,
                     "mode": r.ai_recommendation.get("mode") if r.ai_recommendation else None,
                     "flags_open": len([f for f in r.flags if not f.resolved])} for r in rows if r.status == "pending"],
        "activity": activity[:25],
        "thresholds": {"finance_from": config.LEVEL_FINANCE_FROM, "general_manager_from": config.LEVEL_GM_FROM},
    }


@app.get("/api/agents/status")
def agents_status(user: User = Depends(current_user)):
    return {"ai_enabled": ai_enabled(), "model": config.AI_MODEL if ai_enabled() else None, "redis": bool(_redis),
            "thresholds": {"finance_from": config.LEVEL_FINANCE_FROM, "general_manager_from": config.LEVEL_GM_FROM}}


# ====================== الواجهة (React مبنية) ======================
DIST = config.BASE_DIR.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
