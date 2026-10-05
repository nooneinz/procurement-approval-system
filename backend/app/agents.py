"""وكيلا الذكاء الاصطناعي:

* وكيل المشتريات: يقرأ ملف عرض السعر (PDF/صورة) عبر Claude ويقارنه بالميزانية وسجل الموردين.
* وكيل التدقيق: قواعد صارمة تكشف الطلبات المكررة والمجزأة والمشبوهة (تعمل بدون مفتاح).

لو لم يُضبط ANTHROPIC_API_KEY تعمل قراءة الملفات بالقواعد فقط ويُعلن ذلك بوضوح في النتيجة.
"""
import base64
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import PurchaseRequest, AuditFlag, Quote
from .services import budget_status

MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def ai_enabled() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _json_from(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
_TOTAL_RE = re.compile(r"(?:الإجمالي|الاجمالي|المجموع|الصافي|grand\s*total|total)[^\d\n]{0,40}([\d][\d,\.]*)", re.I)


def _read_pdf_locally(path: Path, entered: float) -> dict | None:
    """قراءة PDF نصّي بدون ذكاء اصطناعي: استخراج الإجمالي والتحقق من ذكر الضريبة."""
    try:
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        return None
    text = text.translate(_AR_DIGITS)
    if len(text.strip()) < 20:
        return None
    totals = []
    for m in _TOTAL_RE.finditer(text):
        try:
            totals.append(float(m.group(1).replace(",", "").rstrip(".")))
        except ValueError:
            pass
    flags = []
    out = {"mode": "pdf_text", "total": None, "matches_entered_amount": None, "red_flags": flags}
    if totals:
        out["total"] = totals[-1]
        out["matches_entered_amount"] = abs(totals[-1] - entered) <= max(0.5, entered * 0.01)
    else:
        flags.append("لم يُعثر على سطر الإجمالي في الملف")
    if not re.search(r"vat|ضريبة|الضريبة", text, re.I):
        flags.append("لا يوجد ذكر لضريبة القيمة المضافة (VAT) في العرض")
    if re.search(r"(?:valid|صالح|صلاحية)[^\n]{0,30}", text, re.I) is None:
        flags.append("لا توجد مدة صلاحية للعرض")
    return out


# ---------- قراءة ملف عرض السعر ----------
def analyze_quote_file(quote: Quote) -> dict:
    if not quote.file_path:
        return {"mode": "none", "note": "لا يوجد ملف مرفق مع هذا العرض."}
    path = Path(quote.file_path)
    if not ai_enabled():
        if path.suffix.lower() == ".pdf" and path.exists():
            local = _read_pdf_locally(path, quote.amount)
            if local:
                return local
        return {"mode": "rules", "note": "هذا الملف (صورة أو PDF ممسوح) يحتاج مفتاح ANTHROPIC_API_KEY لقراءته. تمت المقارنة بالأرقام المُدخلة فقط."}
    media = MEDIA.get(path.suffix.lower())
    if not media or not path.exists():
        return {"mode": "error", "note": "نوع الملف غير مدعوم أو الملف غير موجود."}
    data = base64.standard_b64encode(path.read_bytes()).decode()
    block_type = "document" if media == "application/pdf" else "image"
    prompt = (
        "هذا عرض سعر من مورّد. استخرج البيانات وأجب بـ JSON فقط بدون أي شرح بالشكل: "
        '{"vendor_name": str, "total": number, "currency": str, "valid_until": str|null, '
        '"items": [{"name": str, "quantity": number, "unit_price": number}], "red_flags": [str]}. '
        "red_flags: أي شيء غير سليم في العرض (مجموع لا يطابق البنود، غياب الضريبة، تاريخ منتهٍ، إلخ). "
        "إن لم تجد قيمة فاستخدم null."
    )
    try:
        resp = _client().messages.create(
            model=config.AI_MODEL, max_tokens=1500,
            messages=[{"role": "user", "content": [
                {"type": block_type, "source": {"type": "base64", "media_type": media, "data": data}},
                {"type": "text", "text": prompt},
            ]}],
        )
        out = _json_from("".join(b.text for b in resp.content if b.type == "text"))
    except Exception as e:  # noqa: BLE001
        return {"mode": "error", "note": f"تعذّرت القراءة التلقائية: {type(e).__name__}"}
    total = out.get("total")
    out["mode"] = "ai"
    out["matches_entered_amount"] = (abs(float(total) - quote.amount) <= max(1.0, quote.amount * 0.01)) if total not in (None, "") else None
    return out


# ---------- وكيل التدقيق ----------
def run_audit_agent(db: Session, req: PurchaseRequest) -> list[AuditFlag]:
    flags: list[tuple[str, str, str]] = []
    selected = next((q for q in req.quotes if q.id == req.selected_quote_id), None)
    since30 = datetime.utcnow() - timedelta(days=30)
    since14 = datetime.utcnow() - timedelta(days=14)
    others = list(db.execute(
        select(PurchaseRequest).where(PurchaseRequest.id != req.id, PurchaseRequest.status.in_(["pending", "approved"]))
    ).scalars())

    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower())  # noqa: E731
    for o in others:
        if o.department_id != req.department_id or o.created_at < since30:
            continue
        same_title = norm(o.title) == norm(req.title)
        same_vendor_amount = bool(selected) and o.selected_quote_id and any(
            q.id == o.selected_quote_id and q.vendor_id == selected.vendor_id and abs(q.amount - selected.amount) < 0.01
            for q in o.quotes)
        if same_title or same_vendor_amount:
            flags.append(("DUPLICATE", "high", f"يشبه الطلب {o.number} (نفس القسم خلال 30 يوماً: {'نفس العنوان' if same_title else 'نفس المورد والمبلغ'})."))
            break

    mine = [o for o in others if o.requester_id == req.requester_id and o.department_id == req.department_id and o.created_at >= since14]
    if mine and req.amount < config.LEVEL_FINANCE_FROM:
        combined = req.amount + sum(o.amount for o in mine)
        if combined >= config.LEVEL_FINANCE_FROM and all(o.amount < config.LEVEL_FINANCE_FROM for o in mine):
            flags.append(("SPLIT_PURCHASE", "high", f"اشتباه تجزئة مشتريات: {len(mine) + 1} طلبات من نفس مقدّم الطلب خلال 14 يوماً مجموعها {combined:,.3f} ر.ع يتجاوز حد المدير المالي."))

    for t in (config.LEVEL_FINANCE_FROM, config.LEVEL_GM_FROM):
        if t * 0.95 <= req.amount < t:
            flags.append(("NEAR_THRESHOLD", "medium", f"المبلغ {req.amount:,.3f} أقل بقليل من حد الموافقة {t:,.3f} ر.ع."))

    if len(req.quotes) < 2 and req.amount >= config.SINGLE_QUOTE_LIMIT:
        flags.append(("SINGLE_QUOTE", "medium", "عرض سعر واحد فقط لمبلغ يتطلب مقارنة بين عروض."))

    b = budget_status(db, req.department_id, exclude_request_id=req.id)
    if req.amount > b["remaining"]:
        flags.append(("OVER_BUDGET", "high", f"المبلغ يتجاوز المتبقي من ميزانية القسم ({b['remaining']:,.3f} ر.ع)."))

    items_total = sum(i.quantity * i.unit_price for i in req.items)
    if items_total > 0 and selected and abs(items_total - selected.amount) > items_total * 0.15:
        flags.append(("QUOTE_MISMATCH", "medium", f"إجمالي البنود ({items_total:,.3f}) يختلف عن العرض المختار ({selected.amount:,.3f}) بأكثر من 15%."))

    if selected and len(req.quotes) > 1:
        lowest = min(req.quotes, key=lambda q: q.amount)
        if lowest.id != selected.id and len(req.justification.strip()) < 20:
            flags.append(("NOT_LOWEST", "medium", f"تم اختيار عرض أعلى من الأقل ({lowest.vendor.name}: {lowest.amount:,.3f}) بدون مبرر مكتوب كافٍ."))

    for q in req.quotes:
        a = q.analysis or {}
        if a.get("matches_entered_amount") is False:
            flags.append(("FILE_MISMATCH", "high", f"مبلغ عرض {q.vendor.name} المُدخل لا يطابق المبلغ المقروء من الملف ({a.get('total')})."))
        for rf in a.get("red_flags") or []:
            flags.append(("QUOTE_FILE_ISSUE", "medium", f"{q.vendor.name}: {rf}"))

    # استبدال التنبيهات غير المعالجة السابقة بالنتيجة الحالية
    for old in [f for f in req.flags if not f.resolved]:
        req.flags.remove(old)
    new = [AuditFlag(request_id=req.id, code=c, severity=s, message=m) for c, s, m in flags]
    req.flags.extend(new)
    return new


# ---------- وكيل المشتريات ----------
def vendor_history(db: Session, vendor_id: int) -> dict:
    qs = list(db.execute(select(Quote).where(Quote.vendor_id == vendor_id)).scalars())
    won = [q for q in qs if q.request_id and (r := db.get(PurchaseRequest, q.request_id)) and r.selected_quote_id == q.id and r.status == "approved"]
    return {"quotes_submitted": len(qs), "orders_approved": len(won), "avg_amount": (sum(q.amount for q in won) / len(won)) if won else None}


def run_procurement_agent(db: Session, req: PurchaseRequest) -> dict:
    b = budget_status(db, req.department_id, exclude_request_id=req.id)
    rows = []
    for q in req.quotes:
        rows.append({"quote_id": q.id, "vendor": q.vendor.name, "amount": q.amount, "delivery_days": q.delivery_days,
                     "history": vendor_history(db, q.vendor_id), "file_check": q.analysis})
    if not rows:
        return {"mode": "rules", "recommendation": "review", "reasoning": "لا توجد عروض أسعار لتقييمها.", "best_quote_id": None, "budget": b}

    best = min(rows, key=lambda r: (r["amount"], r["delivery_days"] or 999))
    high = [f for f in req.flags if f.severity == "high" and not f.resolved]
    sel = req.amount if req.amount else best["amount"]

    if best["amount"] > b["remaining"]:
        rec, why = "reject", f"أقل عرض ({best['amount']:,.3f} ر.ع) يتجاوز المتبقي من ميزانية القسم ({b['remaining']:,.3f} ر.ع)."
    elif high:
        rec, why = "review", "توجد تنبيهات تدقيق عالية الخطورة تستدعي مراجعة بشرية قبل الموافقة."
    else:
        rec, why = "approve", f"أقل عرض هو {best['vendor']} بمبلغ {best['amount']:,.3f} ر.ع ضمن الميزانية المتاحة ولا توجد تنبيهات عالية الخطورة."
    result = {"mode": "rules", "recommendation": rec, "reasoning": why, "best_quote_id": best["quote_id"], "budget": b, "quotes": rows, "risks": [f.message for f in high]}

    if ai_enabled():
        try:
            ctx = {"request": {"title": req.title, "amount": sel, "justification": req.justification},
                   "budget": b, "quotes": rows, "audit_flags": [{"severity": f.severity, "message": f.message} for f in req.flags]}
            prompt = ("أنت وكيل مشتريات لشركة. بناءً على المعطيات التالية قدّم توصية مستقلة للمدير. "
                      'أجب JSON فقط: {"recommendation": "approve|reject|review", "best_quote_id": int|null, "reasoning": str (عربي، 3 جمل كحد أقصى), "risks": [str]}.\n'
                      + json.dumps(ctx, ensure_ascii=False, default=str))
            resp = _client().messages.create(model=config.AI_MODEL, max_tokens=800, messages=[{"role": "user", "content": prompt}])
            out = _json_from("".join(b.text for b in resp.content if b.type == "text"))
            if out.get("recommendation") in ("approve", "reject", "review"):
                result.update({"mode": "ai", "recommendation": out["recommendation"], "reasoning": out.get("reasoning", why),
                               "best_quote_id": out.get("best_quote_id", best["quote_id"]), "risks": out.get("risks", result["risks"])})
        except Exception as e:  # noqa: BLE001
            result["ai_error"] = type(e).__name__
    result["generated_at"] = datetime.utcnow().isoformat()
    return result
