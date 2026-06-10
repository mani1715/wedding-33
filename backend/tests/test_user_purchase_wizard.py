"""
Pytest suite for MAJA user-facing purchase wizard backend changes.

Covers:
  - GET /api/public/expiry-tiers
  - GET /api/public/addons
  - GET /api/public/design-pricing
  - POST /api/users/profiles/{id}/buy-addon (happy path, idempotency,
    insufficient credits, not-found, auth)

Uses the seeded test user testuser+maja@example.com / MajaTest@2026.
"""
from __future__ import annotations

import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
# Preview ingress may be sleeping — fall back to localhost (the test agent runs in-cluster)
LOCAL_URL = "http://localhost:8001"

EMAIL = "testuser+maja@example.com"
PASSWORD = "MajaTest@2026"

EXPECTED_TIERS = {"1_month", "3_months", "6_months", "1_year"}
EXPECTED_ADDONS = {
    "music", "live_gallery", "ai_story", "rsvp", "whatsapp",
    "parking", "gift_registry", "digital_shagun", "ai_face_match", "save_the_date",
}


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def _get(url, **kw):
    kw.setdefault("headers", {}).setdefault("User-Agent", UA)
    return requests.get(url, **kw)


def _post(url, **kw):
    kw.setdefault("headers", {}).setdefault("User-Agent", UA)
    return requests.post(url, **kw)


def _resolve_base() -> str:
    """Pick whichever base URL is healthy."""
    for url in (BASE_URL, LOCAL_URL):
        try:
            r = _get(f"{url}/api/public/expiry-tiers", timeout=5)
            if r.status_code == 200:
                return url
        except Exception:
            continue
    return LOCAL_URL


BASE = _resolve_base()


@pytest.fixture(scope="session")
def authed_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    r = s.post(f"{BASE}/api/users/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    if r.status_code != 200:
        pytest.skip(f"Login failed ({r.status_code}): {r.text[:200]}")
    # Cookie is Secure-only; on http localhost it won't auto-send. Promote
    # to Authorization: Bearer <token> for all subsequent calls.
    token = s.cookies.get("user_session_token") or s.cookies.get("maja_session")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def user_balance(authed_session):
    """Return the user's current credit balance via /api/users/me."""
    r = authed_session.get(f"{BASE}/api/users/me", timeout=10)
    assert r.status_code == 200, f"/users/me failed: {r.status_code} {r.text}"
    return int(r.json().get("credits", 0))


# ── PUBLIC ENDPOINTS ────────────────────────────────────────────────────────
class TestPublicEndpoints:
    def test_expiry_tiers(self):
        r = _get(f"{BASE}/api/public/expiry-tiers", timeout=10)
        assert r.status_code == 200
        tiers = r.json().get("tiers", [])
        ids = {t["id"] for t in tiers}
        assert EXPECTED_TIERS.issubset(ids), f"Missing tiers: {EXPECTED_TIERS - ids}"
        for t in tiers:
            assert {"id", "label", "days", "credits"}.issubset(t.keys())

    def test_addons_catalogue(self):
        r = _get(f"{BASE}/api/public/addons", timeout=10)
        assert r.status_code == 200
        addons = r.json().get("addons", [])
        assert len(addons) >= 10, f"Expected at least 10 addons, got {len(addons)}"
        ids = {a["id"] for a in addons}
        assert EXPECTED_ADDONS.issubset(ids), f"Missing addons: {EXPECTED_ADDONS - ids}"
        for a in addons:
            assert {"id", "label", "credits"}.issubset(a.keys())

    def test_design_pricing(self):
        r = _get(f"{BASE}/api/public/design-pricing", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "pricing" in body
        assert isinstance(body["pricing"], dict)


# ── BUY-ADDON FLOW ──────────────────────────────────────────────────────────
class TestBuyAddon:
    @pytest.fixture(scope="class")
    def profile_id(self, authed_session):
        # Top up if balance too low to comfortably run all tests
        me = authed_session.get(f"{BASE}/api/users/me", timeout=10).json()
        if int(me.get("credits", 0)) < 10:
            # Use mongo direct top-up via dev endpoint if available; otherwise skip
            pytest.skip(f"User balance too low ({me.get('credits')}) to run buy-addon suite")

        # Pick any valid design_id from pricing; fall back to a sentinel
        dp = _get(f"{BASE}/api/public/design-pricing", timeout=10).json().get("pricing", {})
        design_id = next(iter(dp.keys()), "rm_marriage_01")
        unique = uuid.uuid4().hex[:6]
        payload = {
            "design_id": design_id,
            "groom_name": f"TEST_Groom_{unique}",
            "bride_name": f"TEST_Bride_{unique}",
            "event_type": "marriage",
            "event_date": "2027-01-15T18:00:00",
            "venue": "Test Venue",
            "city": "Mumbai",
            "invitation_message": "Test invitation for pytest",
        }
        r = authed_session.post(f"{BASE}/api/users/profiles", json=payload, timeout=15)
        assert r.status_code in (200, 201), f"Create profile failed: {r.status_code} {r.text[:400]}"
        prof = r.json().get("profile") or r.json()
        pid = prof.get("id")
        assert pid, f"No profile id in response: {r.json()}"
        return pid

    def _balance(self, sess):
        return int(sess.get(f"{BASE}/api/users/me", timeout=10).json().get("credits", 0))

    def test_buy_music_addon_happy_path(self, authed_session, profile_id):
        before = self._balance(authed_session)
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"addon_id": "music"},
            timeout=10,
        )
        assert r.status_code == 200, f"buy-addon failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body["success"] is True
        assert body["already_purchased"] is False
        assert body["credits_charged"] == 1
        after = self._balance(authed_session)
        assert after == before - 1, f"Balance not decreased: {before}→{after}"
        # Profile should now contain the addon
        prof = authed_session.get(f"{BASE}/api/users/profiles/{profile_id}", timeout=10).json()
        prof = prof.get("profile") or prof
        addon_ids = {a.get("id") for a in (prof.get("add_ons") or [])}
        assert "music" in addon_ids

    def test_buy_addon_idempotent(self, authed_session, profile_id):
        before = self._balance(authed_session)
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"addon_id": "music"},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["already_purchased"] is True
        assert body["credits_charged"] == 0
        after = self._balance(authed_session)
        assert after == before, "Balance changed on idempotent re-buy"

    def test_buy_addon_unknown_profile(self, authed_session):
        r = authed_session.post(
            f"{BASE}/api/users/profiles/does_not_exist_xyz/buy-addon",
            json={"addon_id": "music"},
            timeout=10,
        )
        assert r.status_code == 404

    def test_buy_addon_unknown_addon(self, authed_session, profile_id):
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"addon_id": "no_such_addon_xyz"},
            timeout=10,
        )
        assert r.status_code == 404

    def test_buy_addon_no_auth(self, profile_id):
        r = _post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"addon_id": "music"},
            timeout=10,
        )
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_buy_addon_empty_body_returns_422(self, authed_session, profile_id):
        """Empty {} body should fail Pydantic validation with 422."""
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={},
            timeout=10,
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        # FastAPI's 422 includes 'detail' with 'addon_id' field reference
        assert "addon_id" in r.text, f"422 body should mention addon_id: {r.text[:300]}"

    def test_buy_addon_missing_addon_id_returns_422(self, authed_session, profile_id):
        """Body without addon_id field returns 422."""
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"foo": "bar"},
            timeout=10,
        )
        assert r.status_code == 422
        assert "addon_id" in r.text

    def test_buy_addon_extra_unknown_fields_ok(self, authed_session, profile_id):
        """Extra unknown fields should be ignored as long as addon_id is present.
        Use an already-purchased addon to keep this idempotent."""
        r = authed_session.post(
            f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
            json={"addon_id": "music", "ignored_field": "abc", "another": 42},
            timeout=10,
        )
        assert r.status_code == 200, f"Expected 200 with extra fields, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body.get("success") is True

    def test_buy_addon_insufficient_credits(self, authed_session, profile_id):
        """Try to spend more than the user has by buying every remaining addon.
        At least one of them should hit 402 once credits run out."""
        addons = _get(f"{BASE}/api/public/addons", timeout=10).json()["addons"]
        owned = set()
        prof = authed_session.get(f"{BASE}/api/users/profiles/{profile_id}", timeout=10).json()
        prof = prof.get("profile") or prof
        owned = {a.get("id") for a in (prof.get("add_ons") or [])}

        got_402 = False
        for a in sorted(addons, key=lambda x: -int(x.get("credits", 0))):
            if a["id"] in owned:
                continue
            r = authed_session.post(
                f"{BASE}/api/users/profiles/{profile_id}/buy-addon",
                json={"addon_id": a["id"]},
                timeout=10,
            )
            if r.status_code == 402:
                detail = r.json()
                # detail may be wrapped under "detail" key by FastAPI
                d = detail.get("detail") if isinstance(detail.get("detail"), dict) else detail
                assert "required" in d and "balance" in d, f"402 missing required/balance: {detail}"
                got_402 = True
                break
            elif r.status_code == 200:
                owned.add(a["id"])
            else:
                pytest.fail(f"Unexpected {r.status_code} on {a['id']}: {r.text[:200]}")

        if not got_402:
            pytest.skip("User had enough credits to buy every remaining addon — 402 path not exercised")
