"""Pytest coverage for the photographer loyalty tier system (Feb 2026).

Covers:
  - GET  /api/super-admin/pricing/photographer-tiers
  - PUT  /api/super-admin/pricing/photographer-tiers (admin auth, validation)
  - GET  /api/photographer/me/tier (resolves tier from paid_links_count)
  - GET  /api/public/pricing/effective?audience=photographer (embedded config)

Uses live HTTP via REACT_APP_BACKEND_URL — same pattern as the existing
backend test suite.
"""
import os
import uuid
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set in /app/backend/.env"

UA = {"User-Agent": "MAJA-tests/1.0 (pytest)"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def super_admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "mani_8328@majacreations.com", "password": "Maneesh@1234"},
        headers=UA,
    )
    if r.status_code != 200:
        pytest.skip(f"Super-admin login failed: {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, r.text
    return tok


@pytest.fixture(scope="module")
def auth_headers(super_admin_token):
    return {**UA, "Authorization": f"Bearer {super_admin_token}", "Content-Type": "application/json"}


# ---------- public endpoint ----------
def test_public_pricing_photographer_includes_tiers():
    r = requests.get(
        f"{BASE_URL}/api/public/pricing/effective",
        params={"audience": "photographer"}, headers=UA,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "photographer_tiers" in data
    pt = data["photographer_tiers"]
    assert pt and pt["enabled"] is True
    assert [t["key"] for t in pt["tiers"]] == ["starter", "pro", "elite", "partner"]
    # Default discount ladder
    by_key = {t["key"]: t for t in pt["tiers"]}
    assert by_key["starter"]["min_paid_links"] == 0
    assert by_key["pro"]["discount_pct"] >= 0
    assert by_key["partner"]["discount_pct"] >= 0


def test_public_pricing_normal_user_excludes_tiers():
    r = requests.get(
        f"{BASE_URL}/api/public/pricing/effective",
        params={"audience": "normal_user"}, headers=UA,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("photographer_tiers") is None


# ---------- admin tier CRUD ----------
def test_admin_can_read_tier_config(auth_headers):
    r = requests.get(f"{BASE_URL}/api/super-admin/pricing/photographer-tiers", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enabled"] is True
    assert len(data["tiers"]) == 4


def test_admin_can_update_tier_config(auth_headers):
    # Read current
    r = requests.get(f"{BASE_URL}/api/super-admin/pricing/photographer-tiers", headers=auth_headers)
    original = r.json()
    try:
        # Mutate partner discount to 99%
        mutated = {
            "enabled": original["enabled"],
            "tiers": [
                {**t, "discount_pct": 99 if t["key"] == "partner" else t["discount_pct"]}
                for t in original["tiers"]
            ],
        }
        r = requests.put(
            f"{BASE_URL}/api/super-admin/pricing/photographer-tiers",
            json=mutated, headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        saved = r.json()
        partner = next(t for t in saved["tiers"] if t["key"] == "partner")
        assert partner["discount_pct"] == 99
        # Public endpoint reflects change
        r = requests.get(f"{BASE_URL}/api/public/pricing/effective?audience=photographer", headers=UA)
        partner_pub = next(t for t in r.json()["photographer_tiers"]["tiers"] if t["key"] == "partner")
        assert partner_pub["discount_pct"] == 99
    finally:
        # Restore
        requests.put(
            f"{BASE_URL}/api/super-admin/pricing/photographer-tiers",
            json=original, headers=auth_headers,
        )


def test_put_rejects_invalid_tier_keys(auth_headers):
    bad = {"enabled": True, "tiers": [
        {"key": "starter", "label": "Starter", "min_paid_links": 0, "discount_pct": 0, "bonus_pct": 0},
        {"key": "pro",     "label": "Pro",     "min_paid_links": 2, "discount_pct": 10, "bonus_pct": 10},
    ]}
    r = requests.put(
        f"{BASE_URL}/api/super-admin/pricing/photographer-tiers",
        json=bad, headers=auth_headers,
    )
    assert r.status_code == 400, r.text


def test_put_requires_super_admin_auth():
    r = requests.put(
        f"{BASE_URL}/api/super-admin/pricing/photographer-tiers",
        json={"enabled": True, "tiers": []},
        headers={**UA, "Content-Type": "application/json"},
    )
    assert r.status_code in (401, 403)


# ---------- /me/tier resolution ----------
@pytest.mark.parametrize("paid,expected_key", [
    (0,  "starter"),
    (1,  "starter"),
    (2,  "pro"),
    (4,  "pro"),
    (5,  "elite"),
    (9,  "elite"),
    (10, "partner"),
    (50, "partner"),
])
def test_me_tier_resolves_correctly(paid, expected_key):
    """Inject a temp admin via Mongo with paid_links_count=N, then call
    /me/tier using a freshly-minted JWT. Cleans up after itself."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from pymongo import MongoClient
    from auth import get_password_hash, create_access_token

    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    admin_id = str(uuid.uuid4())
    db.admins.insert_one({
        "id": admin_id,
        "email": f"tier-{admin_id}@test.com",
        "password_hash": get_password_hash("dontcare"),
        "name": "Tier Test",
        "role": "admin",
        "status": "ACTIVE",
        "total_credits": 100,
        "used_credits": 0,
        "paid_links_count": paid,
        "phone_verified": True,
        "self_signup": False,
    })
    try:
        token = create_access_token({"sub": admin_id, "role": "admin"})
        r = requests.get(
            f"{BASE_URL}/api/photographer/me/tier",
            headers={**UA, "Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["paid_links_count"] == paid
        assert body["tier"]["key"] == expected_key
        if expected_key == "partner":
            assert body["next_tier"] is None
            assert body["links_to_next"] == 0
        else:
            assert body["next_tier"] is not None
    finally:
        db.admins.delete_one({"id": admin_id})
        client.close()
