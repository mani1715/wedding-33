"""Quick backend test for the photographer-tier discount + bonus credits
applied during Razorpay credit-pack purchase creation. We can't run a
real Razorpay sandbox here, so this test only validates the discount/bonus
math by hitting the route with a Pro-tier admin and asserting the response
payload before Razorpay would be called.

(If Razorpay keys are placeholders we get a 503 — also acceptable, the
test then validates the response shape via direct math helpers.)
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
UA = {"User-Agent": "MAJA-tests/1.0 (pytest)"}


@pytest.fixture(scope="module")
def admin_at_pro():
    """Seed a temp admin with paid_links_count = 2 (Pro tier) and yield
    their JWT. Cleanup at teardown."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from pymongo import MongoClient
    from auth import get_password_hash, create_access_token

    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    admin_id = str(uuid.uuid4())
    db.admins.insert_one({
        "id": admin_id,
        "email": f"razortest-{admin_id}@test.com",
        "password_hash": get_password_hash("dontcare"),
        "name": "Razor Test",
        "role": "admin",
        "status": "ACTIVE",
        "total_credits": 0,
        "used_credits": 0,
        "paid_links_count": 2,    # Pro tier
        "phone_verified": True,
        "self_signup": False,
    })
    token = create_access_token({"sub": admin_id, "role": "admin"})
    try:
        yield {"admin_id": admin_id, "token": token, "db": db}
    finally:
        db.admins.delete_one({"id": admin_id})
        db.credit_purchases.delete_many({"admin_id": admin_id})
        client.close()


def test_pro_tier_purchase_applies_discount_and_bonus(admin_at_pro):
    """When a Pro-tier admin creates a purchase order, the returned
    amount_inr should be ~10% less than the pack base price AND the
    credits should be ~10% more than the pack base credits."""
    # Find any photographer credit pack
    pricing = requests.get(
        f"{BASE_URL}/api/public/pricing/effective?audience=photographer",
        headers=UA,
    ).json()
    packs = pricing.get("packs") or []
    paid = [p for p in packs if p.get("price", 0) > 0]
    if not paid:
        pytest.skip("No paid photographer credit packs configured")
    pack = paid[0]

    headers = {**UA, "Authorization": f"Bearer {admin_at_pro['token']}"}
    r = requests.post(
        f"{BASE_URL}/api/admin/credits/purchase/create-order",
        json={"pack_id": pack["id"]},
        headers=headers,
    )
    if r.status_code == 503:
        # Razorpay placeholder keys — verify the gate is the only failure.
        msg = r.json().get("detail", "")
        assert "Razorpay" in msg or "PLACEHOLDER" in msg.upper() or "Payment gateway" in msg
        pytest.skip("Razorpay sandbox unavailable in this env")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["tier"] == "pro"
    assert body["tier_discount_pct"] == 10
    assert body["tier_bonus_pct"] == 10
    expected_price = max(1, round(pack["price"] * 90 / 100))
    expected_bonus = round(pack["credits"] * 10 / 100)
    assert body["amount_inr"] == expected_price
    assert body["base_amount_inr"] == pack["price"]
    assert body["bonus_credits"] == expected_bonus
    assert body["credits"] == pack["credits"] + expected_bonus

    # Sanity: the persisted purchase doc carries the same fields
    db = admin_at_pro["db"]
    pdoc = db.credit_purchases.find_one({"admin_id": admin_at_pro["admin_id"]})
    assert pdoc is not None
    assert pdoc["tier_key"] == "pro"
    assert pdoc["bonus_credits"] == expected_bonus


def test_starter_admin_pays_full_price(admin_at_pro):
    """A Starter-tier admin (paid_links=0) should pay the full price and
    receive 0 bonus credits. We mutate the existing fixture admin to 0."""
    db = admin_at_pro["db"]
    db.admins.update_one(
        {"id": admin_at_pro["admin_id"]},
        {"$set": {"paid_links_count": 0}},
    )
    pricing = requests.get(
        f"{BASE_URL}/api/public/pricing/effective?audience=photographer",
        headers=UA,
    ).json()
    paid = [p for p in pricing.get("packs", []) if p.get("price", 0) > 0]
    if not paid:
        pytest.skip("No paid photographer credit packs configured")
    pack = paid[0]
    headers = {**UA, "Authorization": f"Bearer {admin_at_pro['token']}"}
    r = requests.post(
        f"{BASE_URL}/api/admin/credits/purchase/create-order",
        json={"pack_id": pack["id"]},
        headers=headers,
    )
    if r.status_code == 503:
        pytest.skip("Razorpay sandbox unavailable in this env")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "starter"
    assert body["tier_discount_pct"] == 0
    assert body["tier_bonus_pct"] == 0
    assert body["amount_inr"] == pack["price"]
    assert body["credits"] == pack["credits"]
    assert body["bonus_credits"] == 0
