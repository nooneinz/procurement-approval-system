"""تعبئة بيانات تجريبية محلية: أقسام وميزانيات ومستخدمون بأدوار مختلفة وموردون.

للتجربة المحلية فقط — يرفض العمل على سيرفر غير محلي إلا مع --allow-remote.
الاستخدام (والخادم يعمل):  python scripts/seed_demo.py
يقرأ حساب المشرف من backend/.env (ADMIN_EMAIL / ADMIN_PASSWORD) أو من متغيرات البيئة.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DEMO_PASSWORD = "Demo@2026"


def load_env() -> dict:
    env = dict(os.environ)
    f = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--allow-remote", action="store_true")
    a = ap.parse_args()
    if urlparse(a.base).hostname not in ("127.0.0.1", "localhost") and not a.allow_remote:
        sys.exit("رفض التنفيذ: هذا السكربت للتجربة المحلية فقط. استخدم --allow-remote إن كنت متأكداً.")
    env = load_env()
    if not env.get("ADMIN_PASSWORD"):
        sys.exit("اضبط ADMIN_PASSWORD في backend/.env ثم شغّل الخادم أولاً.")

    def call(path, body=None, token=None):
        req = urllib.request.Request(a.base + "/api" + path, method="POST" if body is not None else "GET",
                                     data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json; charset=utf-8", **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                return None  # موجود مسبقاً
            raise SystemExit(f"{path}: {e.code} {e.read().decode()[:200]}")

    tok = call("/auth/login", {"email": env.get("ADMIN_EMAIL", "admin@company.local"), "password": env["ADMIN_PASSWORD"]})["token"]
    depts = {d["name"]: d["id"] for d in call("/departments", token=tok)}
    for name, budget in [("تقنية المعلومات", 40000), ("الموارد البشرية", 15000), ("المالية", 12000), ("العمليات والمشتريات", 60000), ("التسويق", 25000)]:
        if name not in depts:
            depts[name] = call("/departments", {"name": name, "annual_budget": budget}, tok)["id"]
    users = [
        ("أحمد البلوشي", "ahmed.balushi@company.om", "employee", "تقنية المعلومات"),
        ("نورة الحارثية", "noora.harthi@company.om", "dept_manager", "تقنية المعلومات"),
        ("سالم الراشدي", "salim.rashdi@company.om", "employee", "العمليات والمشتريات"),
        ("هند الشكيلية", "hind.shukaili@company.om", "dept_manager", "العمليات والمشتريات"),
        ("فهد المعولي", "fahad.maawali@company.om", "finance_manager", None),
        ("ليلى الريامية", "laila.riyami@company.om", "general_manager", None),
    ]
    for name, email, role, dept in users:
        body = {"name": name, "email": email, "password": DEMO_PASSWORD, "role": role}
        if dept:
            body["department_id"] = depts[dept]
        call("/users", body, tok)
    for v in ["شركة مسقط لتقنية المعلومات", "مؤسسة صحار للتجهيزات المكتبية", "شركة صلالة للحلول التقنية", "مؤسسة نزوى للتوريدات"]:
        call("/vendors", {"name": v}, tok)
    print("تمت التعبئة. حسابات التجربة (كلمة المرور لكلٍّ منها):", DEMO_PASSWORD)
    for name, email, role, _ in users:
        print(f"  {email:34} {role:16} {name}")


if __name__ == "__main__":
    main()
