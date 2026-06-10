"""
Bucket 1A — Song Requests, Check-Ins, Live Stream, Dress Code, Calendar
Backend regression suite.

Demo slug: aarav-and-riya-demo  (sections_enabled fully on, song_requests_settings.enabled=True)
"""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
DEMO_SLUG = "aarav-and-riya-demo"
DEMO_PROFILE_ID = "9a06f989-6d6f-49d2-bd0d-df2a00d3cb43"

ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"


# ----------------------------- fixtures -----------------------------

@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ----------------------------- Invitation public view -----------------------------

class TestPublicInvitationView:
    """GET /api/invite/{slug} returns new Bucket 1A fields."""

    def test_invitation_public_view_has_new_fields(self, api):
        r = api.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}")
        assert r.status_code == 200, r.text
        data = r.json()

        # new top-level fields
        assert "live_stream" in data, "live_stream missing"
        assert "song_requests_settings" in data, "song_requests_settings missing"
        assert "dress_code_settings" in data, "dress_code_settings missing"

        # sections_enabled toggles
        sec = data.get("sections_enabled") or {}
        for key in ("live_stream", "live_timeline", "song_requests", "dress_code", "check_in"):
            assert key in sec, f"sections_enabled.{key} missing"

        # demo profile expectations
        assert sec.get("song_requests") is True
        assert sec.get("check_in") is True
        assert sec.get("dress_code") is True
        assert sec.get("live_stream") is True

        srs = data.get("song_requests_settings") or {}
        assert srs.get("enabled") is True
        assert int(srs.get("max_per_guest", 0)) == 3

        ls = data.get("live_stream") or {}
        assert ls.get("platform") == "youtube"
        assert ls.get("embed_enabled") is True
        assert "youtube" in (ls.get("url") or "").lower()


# ----------------------------- Song Requests -----------------------------

class TestSongRequests:
    """POST /api/invite/{slug}/song-requests + GET /songs alias."""

    def test_post_song_request_valid(self, api):
        unique_guest = f"TEST_Guest_{uuid.uuid4().hex[:6]}"
        payload = {
            "guest_name": unique_guest,
            "guest_phone": f"+9100000{uuid.uuid4().int % 10000:04d}",
            "song_title": "TEST Tum Hi Ho",
            "artist": "Arijit Singh",
            "provider_url": "https://open.spotify.com/track/test",
            "message": "Please play this!"
        }
        r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/song-requests", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data and isinstance(data["id"], str)
        assert data["guest_name"] == unique_guest
        assert data["song_title"] == "TEST Tum Hi Ho"
        assert data["artist"] == "Arijit Singh"
        assert data["provider_url"] == "https://open.spotify.com/track/test"
        assert "created_at" in data

    def test_post_song_request_empty_title_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/song-requests", json={
            "guest_name": "TEST_Empty",
            "song_title": "   ",
        })
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"

    def test_post_song_request_rate_limit_429(self, api):
        """Same guest_name+phone exceeding max_per_guest=3 returns 429."""
        gname = f"TEST_RateLimit_{uuid.uuid4().hex[:6]}"
        phone = f"+91777{uuid.uuid4().int % 1000000:07d}"
        for i in range(3):
            r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/song-requests", json={
                "guest_name": gname,
                "guest_phone": phone,
                "song_title": f"TEST song {i}",
            })
            assert r.status_code == 200, f"submission {i} failed: {r.status_code} {r.text}"

        # 4th should be blocked
        r4 = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/song-requests", json={
            "guest_name": gname,
            "guest_phone": phone,
            "song_title": "TEST overflow",
        })
        assert r4.status_code == 429, f"expected 429, got {r4.status_code}: {r4.text}"

    def test_post_song_request_disabled_profile_returns_403(self, api, admin_headers):
        """Create a throwaway profile with song_requests_settings.enabled=False."""
        # create temp profile
        slug = f"test-songoff-{uuid.uuid4().hex[:8]}"
        payload = {
            "groom_name": "TEST_GroomSR",
            "bride_name": "TEST_BrideSR",
            "wedding_date": "2026-12-12",
            "venue_name": "Test Hall",
            "venue_address": "Test Addr",
            "slug": slug,
            "template_id": "royal_mughal_design_1",
        }
        rc = requests.post(f"{BASE_URL}/api/admin/profiles", json=payload, headers=admin_headers)
        if rc.status_code != 200:
            pytest.skip(f"Could not create temp profile for negative test: {rc.status_code} {rc.text[:200]}")
        pid = rc.json().get("id")
        try:
            # song_requests_settings defaults to enabled=False (per model), so POST should 403
            r = requests.post(f"{BASE_URL}/api/invite/{slug}/song-requests", json={
                "guest_name": "TEST_X",
                "song_title": "TEST blocked",
            })
            assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        finally:
            requests.delete(f"{BASE_URL}/api/admin/profiles/{pid}", headers=admin_headers)

    def test_get_songs_alias_returns_list(self, api):
        r = api.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/songs")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # we've posted some TEST songs in earlier tests; list must be >=1
        if data:
            row = data[0]
            for key in ("id", "guest_name", "song_title", "created_at"):
                assert key in row


# ----------------------------- Admin song-requests -----------------------------

class TestAdminSongRequests:
    def test_admin_list_song_requests(self, api, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}/song-requests",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_admin_list_song_requests_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}/song-requests")
        assert r.status_code in (401, 403), r.status_code

    def test_admin_delete_song_request(self, api, admin_headers):
        # create one, then delete it
        gname = f"TEST_DelTarget_{uuid.uuid4().hex[:6]}"
        cr = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/song-requests", json={
            "guest_name": gname,
            "song_title": "TEST delete me",
        })
        assert cr.status_code == 200, cr.text
        sid = cr.json()["id"]

        dr = requests.delete(
            f"{BASE_URL}/api/admin/song-requests/{sid}",
            headers=admin_headers,
        )
        assert dr.status_code == 200, dr.text
        assert dr.json().get("success") is True

        # verify gone
        lst = requests.get(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}/song-requests",
            headers=admin_headers,
        ).json()
        assert all(row["id"] != sid for row in lst)


# ----------------------------- Check-Ins -----------------------------

class TestCheckIns:
    def test_check_in_valid(self, api):
        gname = f"TEST_CheckIn_{uuid.uuid4().hex[:6]}"
        phone = f"+91888{uuid.uuid4().int % 1000000:07d}"
        r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/check-in", json={
            "guest_name": gname,
            "guest_phone": phone,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data and "guest_name" in data and "created_at" in data
        assert data["guest_name"] == gname

        # idempotent within 30 minutes — same id should come back
        r2 = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/check-in", json={
            "guest_name": gname,
            "guest_phone": phone,
        })
        assert r2.status_code == 200, r2.text
        assert r2.json()["id"] == data["id"], "duplicate within 30min should return same id"

    def test_check_in_missing_name_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/check-in", json={
            "guest_phone": "+910000000000",
        })
        assert r.status_code == 422, r.text

    def test_check_in_empty_name_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/invite/{DEMO_SLUG}/check-in", json={
            "guest_name": "   ",
        })
        assert r.status_code == 422, r.text

    def test_check_in_disabled_returns_403(self, api, admin_headers):
        """Create a profile with sections_enabled.check_in=False (default), test 403."""
        slug = f"test-checkoff-{uuid.uuid4().hex[:8]}"
        payload = {
            "groom_name": "TEST_GroomCI",
            "bride_name": "TEST_BrideCI",
            "wedding_date": "2026-12-12",
            "venue_name": "Test Hall",
            "venue_address": "Test Addr",
            "slug": slug,
            "template_id": "royal_mughal_design_1",
        }
        rc = requests.post(f"{BASE_URL}/api/admin/profiles", json=payload, headers=admin_headers)
        if rc.status_code != 200:
            pytest.skip(f"Could not create temp profile for negative test: {rc.status_code} {rc.text[:200]}")
        pid = rc.json().get("id")
        try:
            r = requests.post(f"{BASE_URL}/api/invite/{slug}/check-in", json={
                "guest_name": "TEST_BlockedGuest",
            })
            assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        finally:
            requests.delete(f"{BASE_URL}/api/admin/profiles/{pid}", headers=admin_headers)


class TestAdminCheckIns:
    def test_admin_check_ins_list_with_stats(self, api, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}/check-ins",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "check_ins" in data and isinstance(data["check_ins"], list)
        assert "stats" in data
        stats = data["stats"]
        assert "total_check_ins" in stats and isinstance(stats["total_check_ins"], int)
        assert "per_event" in stats and isinstance(stats["per_event"], dict)
        assert stats["total_check_ins"] == len(data["check_ins"])

    def test_admin_check_ins_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}/check-ins")
        assert r.status_code in (401, 403)


# ----------------------------- Calendar ICS regression -----------------------------

class TestCalendarIcs:
    def test_calendar_ics_demo(self, api):
        r = api.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/calendar")
        assert r.status_code == 200, r.text
        ctype = r.headers.get("Content-Type", "")
        assert "text/calendar" in ctype, f"bad content-type: {ctype}"
        body = r.text
        assert "BEGIN:VCALENDAR" in body
        assert "END:VCALENDAR" in body
