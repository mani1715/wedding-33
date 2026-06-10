"""Iteration 10 regression tests — covers the specific endpoints mentioned in
the review request for the wedding-23 UI refactor (photographer stats,
photographer tiers, login flows, and public room-lookup)."""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://love-story-125.preview.emergentagent.com").rstrip("/")

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json", **UA})
    return sess


# --- Public photographer stats ----------------------------------------------
class TestPhotographerStats:
    def test_public_photographer_stats(self, s):
        r = s.get(f"{BASE_URL}/api/public/photographer-stats", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("published_total", "photographers_total", "bonus_credits_granted"):
            assert k in data, f"missing {k}"
            assert isinstance(data[k], int), f"{k} not int: {type(data[k])}"
        # non-negative sanity
        assert data["published_total"] >= 0
        assert data["photographers_total"] >= 0
        assert data["bonus_credits_granted"] >= 0


# --- Photographer pricing tiers ---------------------------------------------
class TestPhotographerTiers:
    def test_pricing_effective_photographer(self, s):
        r = s.get(f"{BASE_URL}/api/public/pricing/effective", params={"audience": "photographer"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        ptiers = data.get("photographer_tiers")
        assert ptiers is not None, "photographer_tiers missing"
        tiers = ptiers.get("tiers")
        assert isinstance(tiers, list) and len(tiers) >= 4, "expected >=4 tiers"
        keys = {t["key"] for t in tiers}
        for expected in ("starter", "pro", "elite", "partner"):
            assert expected in keys, f"missing tier {expected}"
        for t in tiers:
            for fld in ("label", "min_paid_links", "discount_pct", "bonus_pct"):
                assert fld in t, f"tier {t.get('key')} missing field {fld}"


# --- Photographer admin login ------------------------------------------------
class TestPhotographerLogin:
    def test_admin_login_returns_token(self, s):
        r = s.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "photographer.test@majatest.com", "password": "TestPass@123"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body, f"no access_token in body keys={list(body.keys())}"
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 10
        # admin payload (sometimes under 'admin' or top-level fields)
        assert ("admin" in body) or ("email" in body) or ("role" in body), f"no admin payload: {body}"


# --- Normal user login (cookie based, requires Mozilla UA) -------------------
class TestUserLogin:
    def test_user_login_sets_cookie(self):
        sess = requests.Session()
        sess.headers.update({"Content-Type": "application/json", **UA})
        r = sess.post(
            f"{BASE_URL}/api/users/login",
            json={"email": "user.test@majatest.com", "password": "TestPass@123"},
            timeout=15,
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        body = r.json()
        assert "user_id" in body or "user" in body, f"no user_id payload: {body}"
        # Cookie can be Set-Cookie OR HttpOnly via session
        cookie_names = {c.name for c in sess.cookies}
        assert "user_session_token" in cookie_names or "Set-Cookie" in r.headers, (
            f"user_session_token cookie not set; cookies={cookie_names}, headers={dict(r.headers)}"
        )


# --- Public room-lookup regression ------------------------------------------
class TestRoomLookup:
    def test_room_lookup_nonexistent_slug(self, s):
        r = s.get(
            f"{BASE_URL}/api/invite/nonexistent-slug-xyz-123/room-lookup",
            params={"name": "test"},
            timeout=15,
        )
        # Acceptable per spec: 200 with matches:[] OR 404
        assert r.status_code in (200, 404), f"unexpected {r.status_code}: {r.text[:200]}"
        if r.status_code == 200:
            data = r.json()
            assert "matches" in data, f"missing matches key: {data}"
            assert isinstance(data["matches"], list)

    def test_room_lookup_short_name_validation(self, s):
        # name with <2 chars should be rejected (422 or 400) OR ignored gracefully
        r = s.get(
            f"{BASE_URL}/api/invite/nonexistent-slug-xyz-123/room-lookup",
            params={"name": "a"},
            timeout=15,
        )
        assert r.status_code in (200, 400, 404, 422), f"unexpected {r.status_code}"
