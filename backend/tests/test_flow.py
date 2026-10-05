"""اختبار دورة العمل الكاملة: طلب ← عروض ← موافقات متعددة المستويات ← سجل التدقيق."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/t.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def login(c, email, pw="pass-12345"):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_full_flow():
    with TestClient(app) as c:
        admin = login(c, "admin@company.local", "admin-pass-123")
        dept = c.post("/api/departments", json={"name": "تقنية المعلومات", "annual_budget": 200000}, headers=admin).json()
        for name, email, role in [("خالد", "emp@x.com", "employee"), ("منى", "dm@x.com", "dept_manager"),
                                  ("فهد", "fin@x.com", "finance_manager"), ("ليلى", "gm@x.com", "general_manager")]:
            body = {"name": name, "email": email, "password": "pass-12345", "role": role}
            if role in ("employee", "dept_manager"):
                body["department_id"] = dept["id"]
            assert c.post("/api/users", json=body, headers=admin).status_code == 200
        v1 = c.post("/api/vendors", json={"name": "مورد أ"}, headers=admin).json()
        v2 = c.post("/api/vendors", json={"name": "مورد ب"}, headers=admin).json()

        emp, dm, fin, gm = (login(c, e) for e in ("emp@x.com", "dm@x.com", "fin@x.com", "gm@x.com"))
        r = c.post("/api/requests", json={"title": "شراء خوادم", "justification": "", "items": [{"name": "خادم", "quantity": 2, "unit_price": 30000}]}, headers=emp).json()
        rid = r["id"]
        q1 = c.post(f"/api/requests/{rid}/quotes", data={"vendor_id": v1["id"], "amount": 58000, "delivery_days": 10}, headers=emp).json()
        c.post(f"/api/requests/{rid}/quotes", data={"vendor_id": v2["id"], "amount": 61000, "delivery_days": 5}, headers=emp)

        # لا إرسال بدون اختيار عرض
        assert c.post(f"/api/requests/{rid}/submit", headers=emp).status_code == 400
        c.post(f"/api/requests/{rid}/select-quote", json={"quote_id": q1["id"]}, headers=emp)
        sub = c.post(f"/api/requests/{rid}/submit", headers=emp).json()
        assert [a["role"] for a in sub["approvals"]] == ["dept_manager", "finance_manager", "general_manager"]
        assert sub["ai_recommendation"]["recommendation"] in ("approve", "review", "reject")
        assert sub["ai_recommendation"]["mode"] == "rules"

        # صلاحيات: الموظف لا يوافق، المدير العام لا يتخطى المستوى الأول
        assert c.post(f"/api/requests/{rid}/decision", json={"decision": "approved"}, headers=emp).status_code == 403
        assert c.post(f"/api/requests/{rid}/decision", json={"decision": "approved"}, headers=gm).status_code == 403
        for h in (dm, fin, gm):
            assert c.post(f"/api/requests/{rid}/decision", json={"decision": "approved", "comment": "تمام"}, headers=h).status_code == 200
        assert c.get(f"/api/requests/{rid}", headers=emp).json()["status"] == "approved"

        # طلب مجزّأ ومكرر يلتقطه وكيل التدقيق
        small = {"title": "شراء خوادم", "justification": "", "items": [{"name": "كابلات", "quantity": 1, "unit_price": 3000}]}
        r2 = c.post("/api/requests", json=small, headers=emp).json()
        c.post(f"/api/requests/{r2['id']}/quotes", data={"vendor_id": v1["id"], "amount": 3000}, headers=emp)
        qid = c.get(f"/api/requests/{r2['id']}", headers=emp).json()["quotes"][0]["id"]
        c.post(f"/api/requests/{r2['id']}/select-quote", json={"quote_id": qid}, headers=emp)
        d = c.post(f"/api/requests/{r2['id']}/submit", headers=emp).json()
        assert "DUPLICATE" in {f["code"] for f in d["flags"]}

        # رفض يتطلب سبباً
        assert c.post(f"/api/requests/{r2['id']}/decision", json={"decision": "rejected"}, headers=dm).status_code == 400
        assert c.post(f"/api/requests/{r2['id']}/decision", json={"decision": "rejected", "comment": "مكرر"}, headers=dm).status_code == 200

        # سلسلة سجل التدقيق سليمة
        assert c.get("/api/audit/verify", headers=fin).json()["valid"] is True
        assert c.get("/api/audit/logs", headers=emp).status_code == 403
        assert c.get("/api/notifications", headers=emp).json()


def test_agent_chat():
    with TestClient(app) as c:
        admin = login(c, "admin@company.local", "admin-pass-123")
        dept = c.post("/api/departments", json={"name": "العمليات", "annual_budget": 50000}, headers=admin).json()
        for name, email, role in [("علي", "ali2@x.om", "employee"), ("فهد", "fin2@x.om", "finance_manager")]:
            body = {"name": name, "email": email, "password": "pass-12345", "role": role}
            if role == "employee":
                body["department_id"] = dept["id"]
            c.post("/api/users", json=body, headers=admin)
        v = c.post("/api/vendors", json={"name": "شركة مسقط"}, headers=admin).json()
        emp, fin = login(c, "ali2@x.om"), login(c, "fin2@x.om")
        r = c.post("/api/requests", json={"title": "أجهزة", "justification": "", "items": [{"name": "حاسوب", "quantity": 1, "unit_price": 900}]}, headers=emp).json()
        c.post(f"/api/requests/{r['id']}/quotes", data={"vendor_id": v["id"], "amount": 900}, headers=emp)
        out = c.post("/api/agents/chat", json={"agent": "procurement", "message": f"قارن عروض الطلب {r['number']}"}, headers=emp).json()
        assert out["mode"] == "rules" and out["trace"][0]["tool"] == "compare_quotes" and "شركة مسقط" in out["reply"]
        out = c.post("/api/agents/chat", json={"agent": "procurement", "message": "ما ميزانية أقسامنا؟"}, headers=emp).json()
        assert out["trace"][0]["tool"] == "budget_status" and "ر.ع" in out["reply"]
        # تنبيهات التدقيق للمالي فقط
        assert "للمدير المالي" in c.post("/api/agents/chat", json={"agent": "audit", "message": "ما التنبيهات المفتوحة؟"}, headers=emp).json()["reply"]
        assert c.post("/api/agents/chat", json={"agent": "audit", "message": "ما التنبيهات المفتوحة؟"}, headers=fin).json()["trace"][0]["tool"] == "open_flags"
        assert c.post("/api/agents/chat", json={"agent": "nope", "message": "x"}, headers=emp).status_code == 404
