import hashlib
import json
from datetime import datetime

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import AuditLog, Notification, User, PurchaseRequest, Department

ROLE_LABELS = {
    "employee": "موظف",
    "dept_manager": "مدير قسم",
    "finance_manager": "مدير مالي",
    "general_manager": "مدير عام",
    "admin": "مشرف النظام",
}


# ---------- كلمات المرور و JWT ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    exp = datetime.utcnow().timestamp() + config.JWT_HOURS * 3600
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "غير مصرح")
    try:
        data = jwt.decode(authorization[7:], config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "انتهت الجلسة، سجّل الدخول من جديد")
    user = db.get(User, int(data["sub"]))
    if not user or not user.active:
        raise HTTPException(401, "الحساب غير فعّال")
    return user


def require_roles(*roles):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "لا تملك صلاحية لهذا الإجراء")
        return user
    return dep


# ---------- سجل التدقيق (سلسلة تجزئة تكشف أي تعديل) ----------
def _digest(prev: str, ts: datetime, user_id, action, entity, entity_id, details) -> str:
    raw = json.dumps([prev, ts.isoformat(), user_id, action, entity, entity_id, details], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def audit(db: Session, user: User | None, action: str, entity: str = "", entity_id: int | None = None, details: str = ""):
    last = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else ""
    ts = datetime.utcnow().replace(microsecond=0)
    row = AuditLog(
        ts=ts, user_id=user.id if user else None, user_name=user.name if user else "النظام",
        action=action, entity=entity, entity_id=entity_id, details=details, prev_hash=prev,
        hash=_digest(prev, ts, user.id if user else None, action, entity, entity_id, details),
    )
    db.add(row)
    db.flush()


def verify_audit_chain(db: Session) -> dict:
    prev = ""
    count = 0
    for row in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        expected = _digest(prev, row.ts, row.user_id, row.action, row.entity, row.entity_id, row.details)
        if row.prev_hash != prev or row.hash != expected:
            return {"valid": False, "broken_at": row.id, "checked": count}
        prev = row.hash
        count += 1
    return {"valid": True, "checked": count}


# ---------- التنبيهات ----------
def notify(db: Session, user_ids, message: str, request_id: int | None = None):
    for uid in set(user_ids):
        db.add(Notification(user_id=uid, message=message, request_id=request_id))


def users_with_role(db: Session, role: str, department_id: int | None = None):
    q = select(User).where(User.role == role, User.active == True)  # noqa: E712
    if department_id is not None:
        q = q.where(User.department_id == department_id)
    return list(db.execute(q).scalars())


# ---------- مسار الموافقات والميزانية ----------
def approval_chain(amount: float) -> list[str]:
    chain = ["dept_manager"]
    if amount >= config.LEVEL_FINANCE_FROM:
        chain.append("finance_manager")
    if amount >= config.LEVEL_GM_FROM:
        chain.append("general_manager")
    return chain


def budget_status(db: Session, department_id: int, exclude_request_id: int | None = None) -> dict:
    dept = db.get(Department, department_id)
    year_start = datetime(datetime.utcnow().year, 1, 1)

    def total(status):
        q = select(func.coalesce(func.sum(PurchaseRequest.amount), 0)).where(
            PurchaseRequest.department_id == department_id,
            PurchaseRequest.status == status,
            PurchaseRequest.created_at >= year_start,
        )
        if exclude_request_id:
            q = q.where(PurchaseRequest.id != exclude_request_id)
        return float(db.execute(q).scalar())

    spent, committed = total("approved"), total("pending")
    budget = dept.annual_budget if dept else 0
    return {"budget": budget, "spent": spent, "committed": committed, "remaining": budget - spent - committed}


def next_number(db: Session) -> str:
    n = db.execute(select(func.count(PurchaseRequest.id))).scalar() + 1
    return f"PR-{datetime.utcnow().year}-{n:04d}"
