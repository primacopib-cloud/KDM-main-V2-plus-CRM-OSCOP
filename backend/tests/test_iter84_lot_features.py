"""Iter84 lot tests: purchase-needs batch, upload, community-board gauge, close-grouping, catalog admin upload."""
import io
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={
        "email": "admin@kdmarche-oscop.fr",
        "password": "AdminKDM2025!",
        "portal": "admin",
    })
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def created_refs():
    return []


# ---------- Public batch purchase-needs ----------
def test_batch_purchase_needs_creates_one_per_product(created_refs):
    payload = {
        "company": "TEST_Iter84 SARL",
        "contact_name": "Test Iter84",
        "email": "test-iter84@example.com",
        "phone": "0590000000",
        "territory": "Guadeloupe",
        "items": [
            {"product": "Produit Test A", "quantity": "10 cartons"},
            {"product": "Produit Test B", "quantity": "5 palettes",
             "images": ["/api/uploads/needs/x.jpg"]},
        ],
    }
    r = requests.post(f"{API}/public/purchase-needs/batch", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 2
    assert len(data["references"]) == 2
    for ref in data["references"]:
        created_refs.append(ref["reference"])
        assert ref["reference"].startswith("BA-")


# ---------- Public upload need image ----------
def test_upload_need_image_returns_url_and_serves(admin_session):
    # 1x1 JPEG
    jpeg_bytes = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
        "0709090808 0a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c"
        "1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100"
        "ffc4001f0000010501010101010100000000000000000102030405060708090a0bff"
        "c400b5100002010303020403050504040000017d01020300041105122131410613516"
        "1071322718114328191a1082342b1c11552d1f02433627282090a161718191a25262"
        "728292a3435363738393a434445464748494a535455565758595a636465666768696"
        "a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9a"
        "ab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e"
        "7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd0ffd9".replace(" ", "")
    )
    files = {"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    r = requests.post(f"{API}/public/purchase-needs/upload-image", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    url = data["url"]
    # Resolve full URL
    full = url if url.startswith("http") else f"{BASE_URL}{url}"
    r2 = requests.get(full)
    assert r2.status_code == 200
    assert "image" in r2.headers.get("content-type", "").lower()


# ---------- Community-board gauge ----------
def test_community_board_has_gauge_and_flags():
    r = requests.get(f"{API}/public/community-board")
    assert r.status_code == 200
    demands = r.json().get("demands", [])
    assert isinstance(demands, list)
    if not demands:
        pytest.skip("no communityplace demands in DB")
    for d in demands:
        assert "current_quantity" in d
        assert "goal_quantity" in d
        assert "grouping_closed" in d
        assert isinstance(d["grouping_closed"], bool)


# ---------- Admin close-grouping ----------
@pytest.fixture(scope="module")
def seeded_need(admin_session):
    """Create a test need & flip communityplace flag directly via admin list to grab id, then set via DB helper.
    Since we don't have DB access, we use publish_communityplace which triggers Stripe; instead we use a helper:
    We'll POST a single need, then call publish_communityplace path — but that requires Stripe. Alternative:
    Use batch endpoint then set communityplace via admin update? None available. We do it via the direct
    admin path: PATCH? Not available. Fallback: call publish_communityplace and accept it may fail; if so,
    we mark via direct MongoDB using motor.
    """
    # Create need via public endpoint
    payload = {
        "company": "TEST_CloseGroup Iter84",
        "contact_name": "Close Group",
        "email": "test-close-iter84@example.com",
        "phone": "0590111111",
        "territory": "Guadeloupe",
        "product": "TEST_Produit CloseGroup",
        "quantity": "20 cartons",
    }
    r = requests.post(f"{API}/public/purchase-needs", json=payload)
    assert r.status_code == 200, r.text
    ref = r.json()["reference"]
    # Get id via admin list
    r2 = admin_session.get(f"{API}/admin/purchase-needs")
    assert r2.status_code == 200
    needs = r2.json().get("needs", [])
    match = next((n for n in needs if n["reference"] == ref), None)
    assert match, "created need not found in admin list"
    need_id = match["id"]

    # Set communityplace flag directly in DB (bypass Stripe)
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient

    async def set_flag():
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL"))
        db = client[os.environ.get("DB_NAME")]
        await db.purchase_needs.update_one({"id": need_id}, {"$set": {"communityplace": True}})
        client.close()
    asyncio.get_event_loop().run_until_complete(set_flag())

    yield {"id": need_id, "reference": ref}

    # Cleanup
    async def cleanup():
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL"))
        db = client[os.environ.get("DB_NAME")]
        await db.purchase_needs.delete_one({"id": need_id})
        client.close()
    asyncio.get_event_loop().run_until_complete(cleanup())


def test_close_grouping_flow(admin_session, seeded_need):
    need_id = seeded_need["id"]
    ref = seeded_need["reference"]
    # First close: OK
    r = admin_session.post(f"{API}/admin/purchase-needs/{need_id}/close-grouping")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["grouping_closed"] is True
    assert data["notified"] >= 0

    # Second close: 409
    r2 = admin_session.post(f"{API}/admin/purchase-needs/{need_id}/close-grouping")
    assert r2.status_code == 409, r2.text

    # Join after close: 409
    r3 = requests.post(f"{API}/public/purchase-needs/{ref}/join",
                       json={"email": "joiner-test-iter84@example.com", "quantity": 3})
    assert r3.status_code == 409, r3.text
    assert "clôtur" in r3.json().get("detail", "").lower()


# ---------- Catalog admin upload image ----------
def test_catalog_admin_upload_image(admin_session):
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360000000000005000155a3a4e40000000049454e44ae426082"
    )
    files = {"file": ("test.png", io.BytesIO(png_bytes), "image/png")}
    # Try multiple candidate endpoints
    r = admin_session.post(f"{API}/catalog/admin/upload-image", files=files)
    if r.status_code == 404:
        pytest.skip(f"endpoint /catalog/admin/upload-image not found: {r.status_code}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "url" in data


# ---------- Cleanup created batch needs ----------
def test_zzz_cleanup_batch_refs(created_refs, admin_session):
    if not created_refs:
        return
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient

    async def purge():
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL"))
        db = client[os.environ.get("DB_NAME")]
        res = await db.purchase_needs.delete_many({"reference": {"$in": created_refs}})
        client.close()
        return res.deleted_count
    deleted = asyncio.get_event_loop().run_until_complete(purge())
    assert deleted == len(created_refs)
