"""محادثة الوكلاء: تسأل الوكيل بالعربية فيستدعي أدوات النظام (للقراءة فقط) ويجيب.

* مع ANTHROPIC_API_KEY: Claude يقرر الأدوات ويستدعيها في حلقة (tool use) ثم يصيغ الإجابة.
* بدون مفتاح: موجّه نوايا محلي يفهم الأسئلة الشائعة ويستدعي نفس الأدوات.
الأدوات لا تغيّر أي بيانات، والموافقة والرفض تبقى بيد المدراء، وكل أداة تحترم صلاحيات المستخدم.
"""
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .agents import ai_enabled, vendor_history
from .models import PurchaseRequest, User, Vendor
from .services import budget_status

AUDIT = ("admin", "finance_manager", "general_manager")


def _visible(db: Session, user: User):
    from .main import can_view
    return [r for r in db.execute(select(PurchaseRequest).order_by(PurchaseRequest.id.desc())).scalars() if can_view(user, r)]


def _find(db: Session, user: User, number: str):
    number = (number or "").strip().upper()
    return next((r for r in _visible(db, user) if r.number == number), None)


def t_pending_requests(db, user, a):
    return [{"الرقم": r.number, "العنوان": r.title, "القسم": r.department.name, "المبلغ": r.amount, "عند": r.approvals[r.current_level].role if r.current_level < len(r.approvals) else None,
             "تنبيهات_مفتوحة": len([f for f in r.flags if not f.resolved]), "توصية_الوكيل": (r.ai_recommendation or {}).get("recommendation")}
            for r in _visible(db, user) if r.status == "pending"][:15]


def t_request_details(db, user, a):
    r = _find(db, user, a.get("number"))
    if not r:
        return {"خطأ": "لم أجد طلباً بهذا الرقم ضمن صلاحياتك"}
    rec = r.ai_recommendation or {}
    return {"الرقم": r.number, "العنوان": r.title, "الحالة": r.status, "القسم": r.department.name, "مقدم_الطلب": r.requester.name, "المبلغ": r.amount,
            "البنود": [{"البند": i.name, "الكمية": i.quantity, "سعر_الوحدة": i.unit_price} for i in r.items],
            "العروض": [{"المورد": q.vendor.name, "المبلغ": q.amount, "التوريد_يوم": q.delivery_days, "مختار": q.id == r.selected_quote_id} for q in r.quotes],
            "تنبيهات_التدقيق": [{"الخطورة": f.severity, "الرسالة": f.message, "معالج": f.resolved} for f in r.flags],
            "توصية_وكيل_المشتريات": {"التوصية": rec.get("recommendation"), "السبب": rec.get("reasoning")} if rec else None,
            "الموافقات": [{"المستوى": x.role, "القرار": x.decision, "المعتمد": x.approver.name if x.approver else None} for x in r.approvals]}


def t_compare_quotes(db, user, a):
    r = _find(db, user, a.get("number"))
    if not r:
        return {"خطأ": "لم أجد طلباً بهذا الرقم ضمن صلاحياتك"}
    if not r.quotes:
        return {"خطأ": "لا توجد عروض على هذا الطلب"}
    low = min(q.amount for q in r.quotes)
    return [{"المورد": q.vendor.name, "المبلغ": q.amount, "الفرق_عن_الأقل": round(q.amount - low, 3), "الفرق_%": round((q.amount - low) / low * 100, 1) if low else 0,
             "التوريد_يوم": q.delivery_days, "سجل_المورد": vendor_history(db, q.vendor_id)} for q in sorted(r.quotes, key=lambda x: x.amount)]


def t_budget_status(db, user, a):
    from .models import Department
    out = []
    for d in db.execute(select(Department).order_by(Department.name)).scalars():
        if user.role in ("employee", "dept_manager") and d.id != user.department_id:
            continue
        if a.get("department") and a["department"] not in d.name:
            continue
        out.append({"القسم": d.name, **{k: v for k, v in zip(["الميزانية", "المصروف", "المحجوز", "المتبقي"], budget_status(db, d.id).values())}})
    return out


def t_vendor_history(db, user, a):
    v = next((x for x in db.execute(select(Vendor)).scalars() if a.get("name") and a["name"] in x.name), None)
    if not v:
        return {"خطأ": "لم أجد مورداً بهذا الاسم"}
    return {"المورد": v.name, **{k: x for k, x in zip(["عروض_مقدمة", "طلبات_معتمدة", "متوسط_المبلغ_المعتمد"], vendor_history(db, v.id).values())}}


def t_open_flags(db, user, a):
    if user.role not in AUDIT:
        return {"خطأ": "تنبيهات التدقيق للمدير المالي والمدير العام والمشرف"}
    return [{"الطلب": r.number, "العنوان": r.title, "الخطورة": f.severity, "النوع": f.code, "التنبيه": f.message}
            for r in _visible(db, user) for f in r.flags if not f.resolved][:25]


def t_spend_summary(db, user, a):
    by = {}
    for r in _visible(db, user):
        d = by.setdefault(r.department.name, {"القسم": r.department.name, "معتمد": 0.0, "معلّق": 0.0, "مرفوض": 0})
        if r.status == "approved":
            d["معتمد"] += r.amount
        elif r.status == "pending":
            d["معلّق"] += r.amount
        elif r.status == "rejected":
            d["مرفوض"] += 1
    return list(by.values())


TOOLS = {
    "pending_requests": (t_pending_requests, "طلبات الشراء المعلّقة الظاهرة للمستخدم مع توصية الوكيل والتنبيهات.", {}),
    "request_details": (t_request_details, "تفاصيل طلب شراء: البنود والعروض وتنبيهات التدقيق والتوصية والموافقات.", {"number": "رقم الطلب مثل PR-2026-0001"}),
    "compare_quotes": (t_compare_quotes, "مقارنة عروض أسعار طلب وسجل كل مورد.", {"number": "رقم الطلب"}),
    "budget_status": (t_budget_status, "ميزانية القسم: المصروف والمحجوز والمتبقي بالريال العماني.", {"department": "اسم القسم (اختياري)"}),
    "vendor_history": (t_vendor_history, "سجل مورد: عدد عروضه وطلباته المعتمدة ومتوسط المبلغ.", {"name": "اسم المورد أو جزء منه"}),
    "open_flags": (t_open_flags, "تنبيهات وكيل التدقيق المفتوحة (للمدير المالي والمدير العام والمشرف).", {}),
    "spend_summary": (t_spend_summary, "ملخص الإنفاق المعتمد والمعلّق حسب القسم.", {}),
}

AGENTS = {
    "procurement": {
        "name": "وكيل المشتريات",
        "tools": ["pending_requests", "request_details", "compare_quotes", "budget_status", "vendor_history"],
        "prompt": "أنت وكيل المشتريات في نظام المشتريات والموافقات لشركة في سلطنة عُمان (العملة الريال العماني ر.ع بثلاث خانات عشرية). تقارن عروض الأسعار بالميزانية وسجل الموردين وتوصي المدير بالموافقة أو الرفض أو المراجعة مع السبب. لا تغيّر أي بيانات ولا تتخذ قرار الموافقة؛ توصيتك استشارية. أجب بالعربية وباختصار، واعتمد على نتائج الأدوات فقط ولا تخترع أرقاماً.",
        "chips": ["ما الطلبات المعلّقة؟", "ما ميزانية أقسامنا المتبقية؟", "قارن عروض الطلب PR-2026-0001", "ما سجل المورد شركة مسقط؟"],
    },
    "audit": {
        "name": "وكيل التدقيق",
        "tools": ["open_flags", "request_details", "spend_summary", "pending_requests"],
        "prompt": "أنت وكيل التدقيق في نظام المشتريات والموافقات لشركة في سلطنة عُمان (الريال العماني). ترصد الطلبات المكررة والمجزأة والقريبة من حدود الموافقة وتجاوز الميزانية، وتشرح للمدققين سبب كل تنبيه وما يلزم. لا تتهم أحداً؛ اذكر الوقائع كما هي في الأدوات. لا تغيّر أي بيانات. أجب بالعربية وباختصار ولا تخترع أرقاماً.",
        "chips": ["ما تنبيهات التدقيق المفتوحة؟", "لخّص الإنفاق حسب القسم", "اشرح الطلب PR-2026-0001"],
    },
}


def _run_tool(db, user, name, args):
    try:
        return TOOLS[name][0](db, user, args or {})
    except Exception as e:  # noqa: BLE001
        return {"خطأ": f"تعذّر تنفيذ الأداة ({type(e).__name__})"}


def _tool_specs(agent_key):
    return [{"name": n, "description": TOOLS[n][1], "input_schema": {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in TOOLS[n][2].items()}}}
            for n in AGENTS[agent_key]["tools"]]


def _chat_claude(db, user, agent_key, history, message):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = AGENTS[agent_key]["prompt"] + f"\nالمستخدم: {user.name} ({user.role})."
    msgs = [{"role": h["role"], "content": h["content"]} for h in history[-10:] if h.get("role") in ("user", "assistant")] + [{"role": "user", "content": message}]
    trace = []
    for _ in range(6):
        resp = client.messages.create(model=config.AI_MODEL, max_tokens=1200, system=system, tools=_tool_specs(agent_key), messages=msgs)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip(), trace
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = _run_tool(db, user, b.name, b.input) if b.name in AGENTS[agent_key]["tools"] else {"خطأ": "أداة غير مسموحة"}
                trace.append({"tool": b.name, "input": b.input, "result": out})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, ensure_ascii=False, default=str)[:6000]})
        msgs.append({"role": "user", "content": results})
    return "تعذّر إكمال الإجابة ضمن حد الخطوات.", trace


def _omr(n) -> str:
    return f"{float(n):,.3f} ر.ع"


_REC = {"approve": "الموافقة", "reject": "الرفض", "review": "المراجعة البشرية"}
_SEV = {"high": "عالية", "medium": "متوسطة", "low": "منخفضة"}


def _chat_local(db, user, agent_key, message):
    m = message.strip()
    num = re.search(r"PR-\d{4}-\d{4}", m, re.I)
    trace = []

    def call(name, **args):
        out = _run_tool(db, user, name, args)
        trace.append({"tool": name, "input": args, "result": out})
        return out

    allowed = AGENTS[agent_key]["tools"]
    if num and "request_details" in allowed:
        n = num.group(0).upper()
        if agent_key == "procurement" and any(w in m for w in ("قارن", "عروض", "مقارنة")):
            rows = call("compare_quotes", number=n)
            if isinstance(rows, dict):
                return rows["خطأ"], trace
            return f"مقارنة عروض {n}:\n" + "\n".join(f"• {r['المورد']}: {_omr(r['المبلغ'])} ({'الأقل' if r['الفرق_عن_الأقل'] == 0 else f'+{r['الفرق_%']}%'}) — توريد {r['التوريد_يوم']} يوم — اعتُمد له {r['سجل_المورد']['orders_approved']} طلب سابقاً" for r in rows), trace
        r = call("request_details", number=n)
        if "خطأ" in r:
            return r["خطأ"], trace
        lines = [f"{r['الرقم']} — {r['العنوان']} ({r['القسم']}): {_omr(r['المبلغ'])}، الحالة: {r['الحالة']}."]
        if r["توصية_وكيل_المشتريات"]:
            lines.append(f"توصية وكيل المشتريات: {_REC.get(r['توصية_وكيل_المشتريات']['التوصية'], '—')} — {r['توصية_وكيل_المشتريات']['السبب']}")
        lines += [f"⚑ [{_SEV.get(f['الخطورة'])}] {f['الرسالة']}" for f in r["تنبيهات_التدقيق"] if not f["معالج"]]
        return "\n".join(lines), trace

    if agent_key == "procurement":
        if "ميزاني" in m:
            rows = call("budget_status")
            return ("ميزانيات الأقسام:\n" + "\n".join(f"• {r['القسم']}: متبقٍ {_omr(r['المتبقي'])} من {_omr(r['الميزانية'])}" for r in rows)) if rows else "لا توجد أقسام ضمن صلاحياتك.", trace
        if "مورد" in m:
            name = re.sub(r".*(?:المورد|مورد)\s*", "", m).strip(" ؟?") or None
            if name:
                r = call("vendor_history", name=name)
                if "خطأ" in r:
                    return r["خطأ"], trace
                avg = _omr(r["متوسط_المبلغ_المعتمد"]) if r["متوسط_المبلغ_المعتمد"] else "—"
                return f"{r['المورد']}: قدّم {r['عروض_مقدمة']} عرضاً، واعتُمد له {r['طلبات_معتمدة']} طلباً بمتوسط {avg}.", trace
        if any(w in m for w in ("معلق", "معلّق", "بانتظار", "طلبات")):
            rows = call("pending_requests")
            return ("الطلبات المعلّقة:\n" + "\n".join(f"• {r['الرقم']} — {r['العنوان']} — {_omr(r['المبلغ'])} — توصية: {_REC.get(r['توصية_الوكيل'], '—')}" + (f" — ⚑ {r['تنبيهات_مفتوحة']}" if r["تنبيهات_مفتوحة"] else "") for r in rows)) if rows else "لا توجد طلبات معلّقة الآن.", trace
        return "أستطيع: عرض الطلبات المعلّقة، وميزانيات الأقسام المتبقية، ومقارنة عروض طلب (مثال: قارن عروض الطلب PR-2026-0001)، وسجل مورد (مثال: ما سجل المورد شركة مسقط؟).", trace

    if any(w in m for w in ("تنبيه", "مخالف", "مشبوه", "مكرر", "تجزئ", "تدقيق")):
        rows = call("open_flags")
        if isinstance(rows, dict):
            return rows["خطأ"], trace
        return ("التنبيهات المفتوحة:\n" + "\n".join(f"• {r['الطلب']} [{_SEV.get(r['الخطورة'])}] {r['التنبيه']}" for r in rows)) if rows else "لا توجد تنبيهات تدقيق مفتوحة.", trace
    if any(w in m for w in ("إنفاق", "انفاق", "صرف", "ملخص", "لخّص", "لخص")):
        rows = call("spend_summary")
        return ("الإنفاق حسب القسم:\n" + "\n".join(f"• {r['القسم']}: معتمد {_omr(r['معتمد'])} — معلّق {_omr(r['معلّق'])} — مرفوض {r['مرفوض']}" for r in rows)) if rows else "لا توجد بيانات إنفاق بعد.", trace
    if any(w in m for w in ("معلق", "معلّق", "طلبات")):
        rows = call("pending_requests")
        return ("الطلبات المعلّقة:\n" + "\n".join(f"• {r['الرقم']} — {r['العنوان']} — تنبيهات {r['تنبيهات_مفتوحة']}" for r in rows)) if rows else "لا توجد طلبات معلّقة.", trace
    return "أستطيع: عرض تنبيهات التدقيق المفتوحة، وتلخيص الإنفاق حسب القسم، وشرح طلب بالرقم (مثال: اشرح الطلب PR-2026-0001).", trace


def chat(db: Session, user: User, agent_key: str, message: str, history: list) -> dict:
    if agent_key not in AGENTS:
        raise ValueError("وكيل غير معروف")
    if ai_enabled():
        try:
            reply, trace = _chat_claude(db, user, agent_key, history, message)
            return {"reply": reply, "trace": trace, "mode": "ai"}
        except Exception:  # noqa: BLE001
            pass
    reply, trace = _chat_local(db, user, agent_key, message)
    return {"reply": reply, "trace": trace, "mode": "rules"}
