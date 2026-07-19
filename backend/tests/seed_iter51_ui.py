"""Seed a consultation for UI testing: vendor registered + bid + CLOSED status."""
import os
import uuid
import requests
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

def _login(email, password, portal=None):
    body = {"email": email, "password": password}
    if portal: body["portal"] = portal
    r = requests.post(f"{BASE}/api/auth/login", json=body, timeout=30)
    return r.json()["access_token"]

def H(t): return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

admin = _login("admin@kdmarche-oscop.fr", "AdminKDM2025!", "admin")
vendor = _login("vendor-pro@kdmarche.fr", "Demo2026!")

cat = f"ui-iter51-{uuid.uuid4().hex[:6]}"
requests.post(f"{BASE}/api/admin/legal-matrix",
              json={"scope": "category", "category": cat, "status": "VERT",
                    "legal_reason": "TEST_UI_iter51"}, headers=H(admin), timeout=30)

# credit vendor
requests.post(f"{BASE}/api/admin/cpc/correction",
              json={"user_email": "vendor-pro@kdmarche.fr", "qty": 60,
                    "reason": "seed UI iter51", "reference": "ui51"},
              headers=H(admin), timeout=30)

opens = datetime.now(timezone.utc).isoformat()
closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
r = requests.post(f"{BASE}/api/admin/consultations",
                  json={"title": "TEST_UI_iter51 rapport",
                        "category": cat,
                        "procedure": "ENCHERE_INVERSEE",
                        "products": [{"label": "Produit UI"}],
                        "territories": ["GUADELOUPE"],
                        "opens_at": opens, "closes_at": closes},
                  headers=H(admin), timeout=30)
cid = r.json()["id"]
ref = r.json()["ref"]
print(f"CID={cid} REF={ref}")

for step in [("transition", {"to": "EN_VALIDATION"}),
             ("validate/commercial", None),
             ("publish", None),
             ("transition", {"to": "INSCRIPTIONS_OUVERTES"}),
             ("transition", {"to": "EN_COURS"})]:
    path, body = step
    r = requests.post(f"{BASE}/api/admin/consultations/{cid}/{path}",
                      json=body if body else {}, headers=H(admin), timeout=30)
    assert r.status_code == 200, f"{path} {r.text}"

r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                  json={"accept_rules": True}, headers=H(vendor), timeout=30)
assert r.status_code == 200, r.text

r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                  json={"amount_ht_cents": 8500}, headers=H(vendor), timeout=30)
assert r.status_code == 200, r.text

# Close it
r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                  json={"to": "CLOTUREE"}, headers=H(admin), timeout=30)
assert r.status_code == 200, r.text

print(f"SEEDED cid={cid} ref={ref} category={cat} CLOTUREE")
