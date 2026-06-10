"""
Tests for:
  - Public pricing endpoint /api/public/pricing/effective (audience-aware)
  - Profile opening_* fields (opening_photo_url, opening_bg_source,
    use_couple_photo_as_opening_bg) round-trip via admin PUT
  - InvitationPublicView /api/invite/{slug} includes the new opening_* fields
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"
DEMO_SLUG = "aarav-and-riya-demo"
DEMO_PROFILE_ID = "c3a95fbd-950e-43a5-90d3-39308a10bd60"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api):
    r = api.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if r.status_code != 200:
        pytest.skip(f"Admin auth failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_client(api, admin_token):
    api.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api


# ---------- /api/public/pricing/effective ----------
class TestPublicPricing:
    """Audience-aware effective-pricing endpoint"""

    def test_pricing_photographer_shape(self, api):
        r = requests.get(
            f"{BASE_URL}/api/public/pricing/effective",
            params={"audience": "photographer"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Mandatory keys
        for k in ("themes", "designs", "options", "packs", "plans", "post_sub"):
            assert k in data, f"missing key {k}"
        assert isinstance(data["themes"], dict)
        assert isinstance(data["designs"], dict)
        assert isinstance(data["options"], dict)
        assert isinstance(data["packs"], list)
        assert isinstance(data["plans"], list)
        # post_sub can be null or dict
        assert data["post_sub"] is None or isinstance(data["post_sub"], dict)
        # Plans must be the monthly subscription plans w/ price + credits_per_month
        for p in data["plans"]:
            assert "price" in p
            assert "credits_per_month" in p
        # Options have credits + is_free
        for k, v in data["options"].items():
            assert "credits" in v, f"option {k} missing credits"
            assert "is_free" in v, f"option {k} missing is_free"

    def test_pricing_normal_user_has_no_plans(self, api):
        r = requests.get(
            f"{BASE_URL}/api/public/pricing/effective",
            params={"audience": "normal_user"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["plans"] == [], "normal_user should have empty plans"
        assert data["post_sub"] is None, "normal_user should have no post_sub"
        assert isinstance(data["themes"], dict)
        assert isinstance(data["options"], dict)
        assert isinstance(data["packs"], list)


# ---------- Profile opening_* fields ----------
class TestProfileOpeningFields:
    """Round-trip opening_photo_url / opening_bg_source / use_couple_photo_as_opening_bg"""

    def test_admin_get_profile_returns_opening_fields(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}")
        assert r.status_code == 200, r.text
        data = r.json()
        for k in (
            "opening_photo_url",
            "opening_bg_source",
            "use_couple_photo_as_opening_bg",
        ):
            assert k in data, f"profile missing {k} (got keys: {list(data.keys())[:30]})"

    def test_admin_put_profile_updates_opening_fields(self, admin_client):
        # Snapshot original
        orig = admin_client.get(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}"
        ).json()
        original_payload = {
            "opening_photo_url": orig.get("opening_photo_url"),
            "opening_bg_source": orig.get("opening_bg_source") or "couple",
            "use_couple_photo_as_opening_bg": orig.get(
                "use_couple_photo_as_opening_bg", True
            ),
        }

        try:
            new_url = "https://example.com/test-opening.jpg"
            put_body = {
                "opening_photo_url": new_url,
                "opening_bg_source": "custom",
                "use_couple_photo_as_opening_bg": False,
            }
            r = admin_client.put(
                f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}",
                json=put_body,
            )
            assert r.status_code == 200, r.text

            # GET to verify persistence
            r2 = admin_client.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}")
            assert r2.status_code == 200
            d = r2.json()
            assert d["opening_photo_url"] == new_url
            assert d["opening_bg_source"] == "custom"
            assert d["use_couple_photo_as_opening_bg"] is False
        finally:
            # Restore
            admin_client.put(
                f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}",
                json=original_payload,
            )


# ---------- Public invite payload exposes opening_* ----------
class TestInvitePublicViewOpening:
    def test_public_invite_contains_opening_fields(self):
        r = requests.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}")
        assert r.status_code == 200, r.text
        data = r.json()
        for k in (
            "opening_photo_url",
            "opening_bg_source",
            "use_couple_photo_as_opening_bg",
        ):
            assert k in data, f"public invite missing {k}"
        # types
        assert isinstance(data["use_couple_photo_as_opening_bg"], bool)
        assert data["opening_bg_source"] in (
            "couple",
            "bride",
            "groom",
            "custom",
            None,
        )
