# Iteration 7 - new per-photo enable/disable toggles round-trip tests
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"
DEMO_PROFILE_ID = "c3a95fbd-950e-43a5-90d3-39308a10bd60"
DEMO_SLUG = "aarav-and-riya-demo"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token in login response: {r.json()}"
    return token


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestShowPhotoToggles:
    """Round-trip the 3 new boolean flags through admin PUT + admin GET + public GET."""

    def test_initial_profile_has_show_flags(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # all three flags must be present and boolean
        for k in ("show_couple_photo", "show_bride_photo", "show_groom_photo"):
            assert k in body, f"missing field {k} in admin profile response"
            assert isinstance(body[k], bool), f"{k} should be bool, got {type(body[k])}"

    def test_put_show_groom_photo_false_then_revert(self, auth_headers):
        # 1) PUT show_groom_photo=false
        put_r = requests.put(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}",
            headers=auth_headers,
            json={"show_groom_photo": False},
            timeout=15,
        )
        assert put_r.status_code == 200, put_r.text
        assert put_r.json().get("show_groom_photo") is False

        # 2) GET admin returns false
        get_r = requests.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=auth_headers, timeout=15)
        assert get_r.status_code == 200
        assert get_r.json().get("show_groom_photo") is False

        # 3) Public invite returns false
        pub_r = requests.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}", timeout=15)
        assert pub_r.status_code == 200, pub_r.text
        pub = pub_r.json()
        assert "show_groom_photo" in pub, f"public view missing show_groom_photo. keys={list(pub.keys())}"
        assert pub["show_groom_photo"] is False

        # 4) Revert
        revert_r = requests.put(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}",
            headers=auth_headers,
            json={"show_groom_photo": True},
            timeout=15,
        )
        assert revert_r.status_code == 200
        assert revert_r.json().get("show_groom_photo") is True

        # 5) Verify revert
        pub_r2 = requests.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}", timeout=15)
        assert pub_r2.json().get("show_groom_photo") is True

    def test_public_invite_emits_all_three_flags(self):
        r = requests.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}", timeout=15)
        assert r.status_code == 200
        body = r.json()
        for k in ("show_couple_photo", "show_bride_photo", "show_groom_photo"):
            assert k in body, f"public InvitationPublicView missing {k}"
            assert isinstance(body[k], bool)
