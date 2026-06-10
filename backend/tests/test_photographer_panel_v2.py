"""
Tests for photographer panel changes (Iteration covering):
- /api/admin/upload-image (admin pre-save upload)
- /api/music/presets (60 presets)
- /api/admin/expiry-tiers (admin GET)
- /api/admin/ai/story (Gemini-2.5-flash via Emergent LLM Key)
"""
import io
import os
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://vows-design-2.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


@pytest.fixture(scope="session")
def admin_token(api_client):
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text}"
    data = r.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "User-Agent": UA}


def _make_png_bytes():
    """Create a tiny valid 2x2 PNG."""
    # IHDR
    def chunk(t, data):
        crc = zlib.crc32(t + data) & 0xffffffff
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
    raw = b"\x00" + b"\xff\x00\x00" * 2 + b"\x00" + b"\x00\xff\x00" * 2
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# --- Music Presets ---
class TestMusicPresets:
    def test_music_presets_returns_60(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/music/presets")
        assert r.status_code == 200, f"unexpected {r.status_code}: {r.text[:200]}"
        body = r.json()
        # support either list or {presets:[...]}
        presets = body if isinstance(body, list) else body.get("presets", [])
        assert len(presets) == 60, f"expected 60 presets, got {len(presets)}"
        p0 = presets[0]
        for k in ("id", "title", "mood", "url"):
            assert k in p0, f"missing key {k} in preset: {p0}"


# --- Expiry Tiers (admin) ---
class TestExpiryTiers:
    def test_get_expiry_tiers_returns_4(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/admin/expiry-tiers", headers=auth_headers)
        assert r.status_code == 200, f"unexpected {r.status_code}: {r.text[:300]}"
        body = r.json()
        tiers = body if isinstance(body, list) else body.get("tiers", body.get("expiry_tiers", []))
        assert len(tiers) == 4, f"expected 4 tiers, got {len(tiers)}: {tiers}"
        ids = set()
        for t in tiers:
            tid = t.get("id") or t.get("key") or t.get("tier")
            ids.add(tid)
        expected = {"1_month", "3_months", "6_months", "1_year"}
        assert expected.issubset(ids), f"missing expected tier ids; got {ids}"

    def test_expiry_tiers_requires_auth(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/admin/expiry-tiers")
        assert r.status_code in (401, 403), f"should require auth, got {r.status_code}"


# --- Admin Upload Image ---
class TestAdminUploadImage:
    def test_upload_png_success(self, api_client, auth_headers):
        png = _make_png_bytes()
        files = {"file": ("test.png", io.BytesIO(png), "image/png")}
        data = {"slot": "bride"}
        # multipart -> don't set content-type
        h = {k: v for k, v in auth_headers.items() if k.lower() != "content-type"}
        r = api_client.post(
            f"{BASE_URL}/api/admin/upload-image",
            headers=h,
            files=files,
            data=data,
        )
        assert r.status_code == 200, f"upload failed {r.status_code}: {r.text[:400]}"
        body = r.json()
        url = body.get("url") or body.get("path") or body.get("image_url")
        assert url, f"no url in response: {body}"
        assert "/uploads/" in url, f"expected /uploads/ prefix, got {url}"

    def test_upload_requires_auth(self, api_client):
        png = _make_png_bytes()
        files = {"file": ("test.png", io.BytesIO(png), "image/png")}
        r = api_client.post(
            f"{BASE_URL}/api/admin/upload-image",
            files=files,
            data={"slot": "bride"},
        )
        assert r.status_code in (401, 403), f"should require auth, got {r.status_code}"


# --- AI Story (Gemini via Emergent LLM Key) ---
class TestAIStory:
    def test_ai_story_returns_non_empty(self, api_client, auth_headers):
        payload = {
            "bride": "Aisha",
            "groom": "Rohan",
            "theme": "cinematic_royal",
            "tone": "cinematic_royal",
            "kind": "invitation",
            "language": "English",
            "notes": "Met at a Mumbai coffee shop during a monsoon evening.",
        }
        r = api_client.post(
            f"{BASE_URL}/api/admin/ai/story",
            json=payload,
            headers={**auth_headers, "Content-Type": "application/json"},
            timeout=60,
        )
        assert r.status_code == 200, f"ai story failed {r.status_code}: {r.text[:400]}"
        body = r.json()
        story = body.get("story") or body.get("text") or body.get("content") or ""
        assert isinstance(story, str) and len(story.strip()) > 50, (
            f"empty/short story returned: {body}"
        )
