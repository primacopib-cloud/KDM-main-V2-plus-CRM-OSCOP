"""Iter 81: Restock alerts (subscribe/toggle/notify) and cart reservations (30 min)."""
import os
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
PRODUCT_ID = "61c31a9c-d072-4988-9a39-76ca46520bba"
ZONE = "GUADELOUPE"

BUYER = {"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}
ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"}


@pytest.fixture(scope="module")
def buyer_token():
    r = requests.post(f"{BASE}/api/auth/login", json=BUYER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# --- Restock alerts ---

def test_restock_alert_requires_auth():
    r = requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                      json={"product_id": PRODUCT_ID, "zone_code": ZONE})
    assert r.status_code in (401, 403)


def test_restock_alert_404_unknown_product(buyer_token):
    r = requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                      json={"product_id": "does-not-exist", "zone_code": ZONE},
                      headers=_h(buyer_token))
    assert r.status_code == 404


def test_restock_alert_toggle(buyer_token):
    # Ensure clean start: if already subscribed, unsubscribe
    mine = requests.get(f"{BASE}/api/v2/catalog/restock-alerts/mine",
                       headers=_h(buyer_token)).json().get("alerts", [])
    if any(a["product_id"] == PRODUCT_ID and a["zone_code"] == ZONE for a in mine):
        requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                      json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                      headers=_h(buyer_token))
    r1 = requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                       json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                       headers=_h(buyer_token))
    assert r1.status_code == 200
    assert r1.json()["subscribed"] is True
    r2 = requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                       json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                       headers=_h(buyer_token))
    assert r2.status_code == 200
    assert r2.json()["subscribed"] is False


def test_restock_alerts_mine_list(buyer_token):
    # subscribe again for GET test
    requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                  json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                  headers=_h(buyer_token))
    r = requests.get(f"{BASE}/api/v2/catalog/restock-alerts/mine", headers=_h(buyer_token))
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    assert any(a["product_id"] == PRODUCT_ID and a["zone_code"] == ZONE for a in alerts)


# --- Notification via admin restock ---

def test_admin_restock_triggers_notification(buyer_token, admin_token):
    # ensure buyer subscribed
    mine = requests.get(f"{BASE}/api/v2/catalog/restock-alerts/mine",
                       headers=_h(buyer_token)).json().get("alerts", [])
    if not any(a["product_id"] == PRODUCT_ID and a["zone_code"] == ZONE for a in mine):
        requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                      json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                      headers=_h(buyer_token))
    # set stock to 0
    r0 = requests.put(f"{BASE}/api/catalog/admin/stock/{PRODUCT_ID}",
                     json={"zone_code": ZONE, "quantity_available": 0},
                     headers=_h(admin_token))
    assert r0.status_code == 200, r0.text
    time.sleep(0.5)
    # restock to 30
    r30 = requests.put(f"{BASE}/api/catalog/admin/stock/{PRODUCT_ID}",
                      json={"zone_code": ZONE, "quantity_available": 30},
                      headers=_h(admin_token))
    assert r30.status_code == 200, r30.text
    body = r30.json()
    assert body.get("restock_alert_triggered") is True
    time.sleep(1)
    # buyer's mine should now be empty for this product/zone
    mine = requests.get(f"{BASE}/api/v2/catalog/restock-alerts/mine",
                       headers=_h(buyer_token)).json().get("alerts", [])
    assert not any(a["product_id"] == PRODUCT_ID and a["zone_code"] == ZONE for a in mine)


# --- Cart reservation ---

def _find_cart_item(buyer_token):
    r = requests.get(f"{BASE}/api/v2/catalog/cart?zone_code={ZONE}", headers=_h(buyer_token))
    assert r.status_code == 200, r.text
    return r.json()


def test_cart_reservation_flow(buyer_token):
    # Add 5 to cart -> reserved_until set
    r = requests.post(
        f"{BASE}/api/v2/catalog/cart/items?zone_code={ZONE}",
        json={"product_id": PRODUCT_ID, "quantity": 5},
        headers=_h(buyer_token),
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data.get("reserved_until"), f"Missing reserved_until: {data}"

    # Add 26 -> insufficient
    r2 = requests.post(
        f"{BASE}/api/v2/catalog/cart/items?zone_code={ZONE}",
        json={"product_id": PRODUCT_ID, "quantity": 26},
        headers=_h(buyer_token),
    )
    assert r2.status_code == 400
    assert "insuffisant" in r2.text.lower() or "stock" in r2.text.lower()


def test_cart_delete_releases_reservation(buyer_token):
    # find our line for the product and delete
    cart = _find_cart_item(buyer_token)
    items = cart.get("items", []) if isinstance(cart, dict) else cart
    target = next((i for i in items if i.get("product_id") == PRODUCT_ID), None)
    assert target, f"Product not in cart: {items}"
    item_id = target.get("id") or target.get("item_id")
    r = requests.delete(f"{BASE}/api/v2/catalog/cart/items/{item_id}?zone_code={ZONE}",
                       headers=_h(buyer_token))
    assert r.status_code in (200, 204), r.text


# --- RESTORATION ---

def test_zzz_restore_state(buyer_token, admin_token):
    """Restore: 15x Riz in cart, stock GP=30, no restock watcher, no reservations."""
    # Ensure stock at 30
    requests.put(f"{BASE}/api/catalog/admin/stock/{PRODUCT_ID}",
                 json={"zone_code": ZONE, "quantity_available": 30},
                 headers=_h(admin_token))
    # Remove any restock watcher for buyer
    mine = requests.get(f"{BASE}/api/v2/catalog/restock-alerts/mine",
                       headers=_h(buyer_token)).json().get("alerts", [])
    for a in mine:
        if a["product_id"] == PRODUCT_ID and a["zone_code"] == ZONE:
            requests.post(f"{BASE}/api/v2/catalog/restock-alerts",
                          json={"product_id": PRODUCT_ID, "zone_code": ZONE},
                          headers=_h(buyer_token))
    # Ensure cart contains 15x Riz. Re-add if missing.
    cart = _find_cart_item(buyer_token)
    items = cart.get("items", []) if isinstance(cart, dict) else cart
    target = next((i for i in items if i.get("product_id") == PRODUCT_ID), None)
    if not target:
        r = requests.post(
            f"{BASE}/api/v2/catalog/cart/items?zone_code={ZONE}",
            json={"product_id": PRODUCT_ID, "quantity": 15},
            headers=_h(buyer_token),
        )
        assert r.status_code in (200, 201), r.text
    else:
        # update quantity to 15 if different — use PUT if available, else remove+add
        item_id = target.get("id") or target.get("item_id")
        r = requests.put(
            f"{BASE}/api/v2/catalog/cart/items/{item_id}?zone_code={ZONE}",
            json={"quantity": 15},
            headers=_h(buyer_token),
        )
        if r.status_code >= 400:
            requests.delete(f"{BASE}/api/v2/catalog/cart/items/{item_id}?zone_code={ZONE}",
                           headers=_h(buyer_token))
            requests.post(
                f"{BASE}/api/v2/catalog/cart/items?zone_code={ZONE}",
                json={"product_id": PRODUCT_ID, "quantity": 15},
                headers=_h(buyer_token),
            )
    print("Restoration completed.")
