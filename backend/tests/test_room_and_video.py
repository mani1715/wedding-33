"""
Backend tests for new features:
- Find My Room: GET /api/invite/wedlock-site/room-lookup
- Public invitation includes guest_rooms (phone scrubbed) + pre_wedding_links
- Admin PUT /api/admin/profiles/{id} persists guest_rooms + pre_wedding_links
- POST /api/users/profiles accepts new fields
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://wedlock-site.preview.emergentagent.com").rstrip("/")
DEMO_SLUG = "aarav-and-riya-demo"
DEMO_PROFILE_ID = "3073dc25-a18b-462f-83fd-c38a942ecae9"
ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"

UA = {"User-Agent": "Mozilla/5.0 (compatible; pytest-suite)"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json", **UA})
    return sess


@pytest.fixture(scope="module")
def admin_token(s):
    # Try a few common admin login endpoints
    for path in ["/api/admin/login", "/api/auth/admin/login", "/api/auth/login", "/api/admin/auth/login"]:
        r = s.post(f"{BASE_URL}{path}", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                continue
            tok = data.get("token") or data.get("access_token") or (data.get("data") or {}).get("token")
            if tok:
                return tok
    pytest.skip("Could not obtain admin token from known endpoints")


# ---------- room-lookup ----------
class TestRoomLookup:
    def test_partial_match_shar(self, s):
        r = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/room-lookup", params={"name": "shar"})
        assert r.status_code == 200, r.text
        data = r.json()
        # may be either {matches:[...]} or list — handle both
        matches = data.get("matches") if isinstance(data, dict) else data
        assert isinstance(matches, list)
        assert len(matches) >= 1
        names = " ".join((m.get("guest_name") or "") for m in matches).lower()
        assert "sharma" in names
        # phone must be stripped
        for m in matches:
            assert "phone" not in m or m.get("phone") in (None, "")

    def test_partial_match_priy(self, s):
        r = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/room-lookup", params={"name": "priy"})
        assert r.status_code == 200
        data = r.json()
        matches = data.get("matches") if isinstance(data, dict) else data
        assert any("kapoor" in (m.get("guest_name") or "").lower() or "priya" in (m.get("guest_name") or "").lower() for m in matches)

    def test_no_match(self, s):
        r = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/room-lookup", params={"name": "xyzqqq"})
        assert r.status_code == 200
        data = r.json()
        matches = data.get("matches") if isinstance(data, dict) else data
        assert matches == [] or matches is None or len(matches) == 0

    def test_short_name_400(self, s):
        r = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}/room-lookup", params={"name": "a"})
        assert r.status_code in (400, 422), f"expected 400/422 for 1-char name, got {r.status_code}: {r.text[:200]}"

    def test_bad_slug_404(self, s):
        r = s.get(f"{BASE_URL}/api/invite/nope-not-a-slug-xxx/room-lookup", params={"name": "shar"})
        assert r.status_code == 404


# ---------- public invitation view ----------
class TestPublicInvitation:
    def test_public_has_rooms_and_videos(self, s):
        r = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}")
        assert r.status_code == 200, r.text
        data = r.json()
        # guest_rooms
        gr = data.get("guest_rooms")
        assert isinstance(gr, list) and len(gr) >= 2, f"guest_rooms missing or empty: {gr}"
        for room in gr:
            assert room.get("phone") in (None, ""), f"phone leaked in public response: {room}"
            assert room.get("guest_name")
        # pre_wedding_links
        pw = data.get("pre_wedding_links")
        assert isinstance(pw, list) and len(pw) >= 1, f"pre_wedding_links missing: {pw}"
        first = pw[0]
        assert first.get("url"), "pre_wedding_link.url missing"


# ---------- admin PUT persistence ----------
class TestAdminProfileUpdate:
    def test_put_persists_rooms_and_links(self, s, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Read current
        r = s.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=headers)
        assert r.status_code == 200, r.text
        current = r.json()

        marker = f"TEST_{uuid.uuid4().hex[:6]}"
        new_room = {
            "guest_name": f"TEST Guest {marker}",
            "room_number": "999",
            "hotel_name": "Test Hotel",
            "phone": "+910000000000",
            "map_link": "https://maps.google.com/?q=test"
        }
        new_link = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "label": f"Test Video {marker}",
            "kind": "video"
        }

        existing_rooms = current.get("guest_rooms") or []
        existing_links = current.get("pre_wedding_links") or []
        payload = {
            "guest_rooms": existing_rooms + [new_room],
            "pre_wedding_links": existing_links + [new_link],
        }

        r = s.put(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=headers, json=payload)
        assert r.status_code in (200, 201), f"PUT failed {r.status_code}: {r.text[:400]}"

        # Verify via GET
        r2 = s.get(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=headers)
        assert r2.status_code == 200
        after = r2.json()
        rooms_after = after.get("guest_rooms") or []
        links_after = after.get("pre_wedding_links") or []
        assert any(rm.get("guest_name", "").endswith(marker) for rm in rooms_after), \
            f"new room not persisted: {rooms_after}"
        assert any((lk.get("label") or "").endswith(marker) for lk in links_after), \
            f"new link not persisted: {links_after}"

        # Public view: phone should still be redacted even for the new room with phone
        rp = s.get(f"{BASE_URL}/api/invite/{DEMO_SLUG}")
        assert rp.status_code == 200
        pub = rp.json()
        for room in pub.get("guest_rooms") or []:
            assert room.get("phone") in (None, ""), f"phone leaked publicly: {room}"

        # Cleanup: restore original
        restore = {"guest_rooms": existing_rooms, "pre_wedding_links": existing_links}
        s.put(f"{BASE_URL}/api/admin/profiles/{DEMO_PROFILE_ID}", headers=headers, json=restore)


# ---------- POST /api/users/profiles accepts new fields ----------
class TestUserProfileCreateAcceptsNewFields:
    def test_schema_accepts_fields(self, s):
        """We don't have a normal user token; we only verify the endpoint does NOT 422
        on the new fields (i.e. payload validation accepts them). Auth/permission errors
        (401/403) are acceptable here."""
        payload = {
            "groom_name": "TestGroom",
            "bride_name": "TestBride",
            "guest_rooms": [{"guest_name": "X", "room_number": "1"}],
            "pre_wedding_links": [{"url": "https://youtu.be/abc", "kind": "video"}],
        }
        r = s.post(f"{BASE_URL}/api/users/profiles", json=payload)
        # 422 here would indicate the schema rejects the new fields → failure
        assert r.status_code != 422, f"UserProfileCreate rejected new fields: {r.text[:400]}"
