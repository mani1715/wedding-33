"""Backend regression tests for:
- GET /api/invite/{slug}/full batched payload (venues / travel / shagun / referral_code)
- POST /api/admin/profiles/{profile_id}/upload-photo (multi-size WebP pipeline)
- convert_to_webp_responsive helper (EXIF + aspect-ratio preserved)
"""
import os
import io
import sys
import pytest
import requests
from pathlib import Path
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://joy-optimized.preview.emergentagent.com").rstrip("/")
SLUG = "aarav-and-riya-demo"
PROFILE_ID = "5b14dafa-c26c-446d-82d9-32f5d23d0bdf"
UPLOADS_DIR = Path("/app/uploads/photos")

# Make backend importable for direct unit tests of helper
sys.path.insert(0, "/app/backend")


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@wedding.com", "password": "admin123"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------- /full payload tests ----------

class TestInviteFullPayload:
    """Batched public invite endpoint."""

    def test_full_returns_200_and_all_top_level_keys(self, api):
        r = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["invite", "wishes", "gifts", "blessings", "gallery_info",
                  "shagun_enabled", "shagun", "venues", "travel", "referral_code"]:
            assert k in data, f"missing top-level key {k}"

    def test_blessings_has_legacy_and_new_keys(self, api):
        d = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20).json()
        b = d["blessings"]
        # legacy
        for k in ("blessing_count", "blessing_total_amount", "wishes_count", "recent_blessings"):
            assert k in b, f"legacy key missing: {k}"
        # new
        for k in ("total_count", "recent"):
            assert k in b, f"new key missing: {k}"
        # values consistent
        assert b["total_count"] == b["blessing_count"]
        assert isinstance(b["recent"], list)
        assert isinstance(b["recent_blessings"], list)

    def test_venues_main_venue_has_links(self, api):
        d = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20).json()
        mv = d["venues"]["main_venue"]
        assert mv["name"]
        links = mv["links"]
        assert links["google_maps"].startswith("http")
        assert links["apple_maps"].startswith("http")
        assert "uber.com" in links["uber"]
        assert "olacabs.com" in links["ola"]
        assert links["whatsapp_share"].startswith("https://wa.me/")

    def test_travel_links(self, api):
        d = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20).json()
        links = d["travel"]["links"]
        for k in ("google_maps", "ola", "uber", "rapido"):
            assert k in links and links[k].startswith("http"), f"travel link missing/invalid: {k}"

    def test_shagun_enabled_and_upi_links(self, api):
        d = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20).json()
        sh = d["shagun"]
        assert sh["enabled"] is True
        assert d["shagun_enabled"] is True
        assert len(sh["suggested"]) >= 1
        for entry in sh["suggested"]:
            assert entry["link"].startswith("upi://pay?"), entry["link"]

    def test_referral_code_populated(self, api):
        d = api.get(f"{BASE_URL}/api/invite/{SLUG}/full", timeout=20).json()
        assert d["referral_code"] == "MAJA-TEST-001"


# ---------- WebP responsive helper (direct unit test) ----------

class TestConvertToWebpResponsive:
    """Unit test of the helper using an in-memory UploadFile-like object."""

    @pytest.mark.asyncio
    async def test_helper_preserves_aspect_ratio_and_widths(self, tmp_path):
        from server import convert_to_webp_responsive  # noqa
        from fastapi import UploadFile
        # 2400x1600 RGB test image
        im = Image.new("RGB", (2400, 1600), color=(120, 80, 40))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        upload = UploadFile(filename="test.png", file=buf)
        variants = await convert_to_webp_responsive(upload, tmp_path, "unit_test_img")

        # All variant files exist with non-zero size
        for label in ("small", "medium", "large", "original"):
            assert label in variants
        # Originals capped at 1920 -> width=1920, height=1280
        assert variants["width"] == 1920
        assert variants["height"] == 1280
        # Check files on disk
        for label, target_w in [("small", 320), ("medium", 640), ("large", 1280)]:
            fp = tmp_path / f"unit_test_img_{label}.webp"
            assert fp.exists(), f"missing variant file {fp}"
            assert fp.stat().st_size > 0
            with Image.open(fp) as v:
                assert v.width == target_w
                # aspect ratio of capped original = 1920:1280 = 3:2 => h = w*2/3
                expected_h = int(target_w * 1280 / 1920)
                assert abs(v.height - expected_h) <= 1, (label, v.size, expected_h)
        orig_fp = tmp_path / "unit_test_img.webp"
        assert orig_fp.exists() and orig_fp.stat().st_size > 0


# ---------- Upload endpoint integration test ----------

class TestUploadPhotoPipeline:
    """POST /api/admin/profiles/{id}/upload-photo end-to-end."""

    def test_upload_returns_media_variants_and_files_on_disk(self, api, admin_token):
        im = Image.new("RGB", (2400, 1600), color=(40, 80, 120))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=92)
        buf.seek(0)

        headers = {"Authorization": f"Bearer {admin_token}"}
        files = {"file": ("test_upload.jpg", buf, "image/jpeg")}
        data = {"caption": "TEST_pytest_upload"}

        r = api.post(
            f"{BASE_URL}/api/admin/profiles/{PROFILE_ID}/upload-photo",
            headers=headers, files=files, data=data, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()

        mv = body.get("media_variants")
        assert mv is not None, "media_variants missing in response"
        for k in ("small", "medium", "large", "original", "width", "height", "size"):
            assert k in mv, f"variant key missing: {k}"

        # media_url should == variants.original
        assert body["media_url"] == mv["original"]

        # Files on disk under /app/uploads/photos
        for label in ("small", "medium", "large", "original"):
            url = mv[label]
            # URL is /uploads/photos/<base>{_label}.webp or /uploads/photos/<base>.webp
            assert url.startswith("/uploads/photos/")
            fs_path = Path("/app") / url.lstrip("/")
            assert fs_path.exists(), f"variant file does not exist: {fs_path}"
            assert fs_path.stat().st_size > 0

        # width/height sane (cap at 1920)
        assert mv["width"] <= 1920
        assert mv["height"] <= 1920

        # NOTE: /uploads/* is only routed internally (k8s ingress routes /api/* to
        # backend); we don't assert public HTTP reachability of the static asset.

        # Cleanup: remove media record so the gallery doesn't grow indefinitely
        media_id = body.get("id")
        if media_id:
            api.delete(f"{BASE_URL}/api/admin/media/{media_id}",
                       headers=headers, timeout=20)
