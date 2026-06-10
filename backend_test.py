#!/usr/bin/env python3
"""
Backend API Testing Suite
Testing TWO NEW endpoints added today:
1. Music presets with celebration category support
2. AI translation endpoint (Gemini-powered, credit-gated)
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://wedding-preview-3.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@wedding.com"
ADMIN_PASSWORD = "admin123"

# Test profile slugs
CELEBRATION_SLUG = "manvith-test-bday"
WEDDING_SLUG = "anaya-rohan-test"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Common headers to bypass bot detection
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://wedding-preview-3.preview.emergentagent.com/"
}


def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Get headers with optional auth token"""
    headers = COMMON_HEADERS.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.tests.append({"name": test_name, "status": "PASS", "details": details})
        print(f"{GREEN}✅ PASS{RESET}: {test_name}")
        if details:
            print(f"   {details}")
    
    def add_fail(self, test_name: str, details: str = ""):
        self.failed += 1
        self.tests.append({"name": test_name, "status": "FAIL", "details": details})
        print(f"{RED}❌ FAIL{RESET}: {test_name}")
        if details:
            print(f"   {details}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        print(f"{'='*80}\n")
        return self.failed == 0


def get_admin_token() -> Optional[str]:
    """Login as admin and get JWT token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=COMMON_HEADERS,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"{RED}Failed to login: {response.status_code} - {response.text}{RESET}")
            return None
    except Exception as e:
        print(f"{RED}Login error: {e}{RESET}")
        return None


def get_profile_id_by_slug(slug: str, token: str) -> Optional[str]:
    """Get profile ID from slug by fetching the full invitation data"""
    try:
        response = requests.get(
            f"{BASE_URL}/invite/{slug}/full",
            headers=get_headers(token),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("id")
        return None
    except Exception as e:
        print(f"{YELLOW}Warning: Could not fetch profile ID for {slug}: {e}{RESET}")
        return None


def create_test_celebration_profile(token: str) -> Optional[str]:
    """Create a test celebration profile (baby_birthday)"""
    from datetime import datetime, timedelta
    
    event_date = (datetime.now() + timedelta(days=30)).isoformat()
    
    profile_data = {
        "groom_name": "Manvith",
        "bride_name": "Test",
        "event_type": "wedding",
        "event_date": event_date,
        "venue": "Test Venue",
        "city": "Bangalore",
        "invitation_message": "Join us in celebrating Manvith's first birthday! A day filled with joy, laughter, and precious memories.",
        "language": ["english"],
        "design_id": "baby_birthday_design_1",
        "invitation_category": "baby_birthday",
        "celebrant_info": {
            "name": "Manvith",
            "age": "1 year",
            "parents_names": "Bharath & Priya",
            "story": "Our little bundle of joy turns one! Join us as we celebrate this special milestone.",
            "subtitle": "First Birthday Celebration",
            "welcome_blessing": "May this day be filled with love and laughter"
        },
        "sections_enabled": {
            "about_couple": False,
            "events": True,
            "gallery": True,
            "rsvp": True,
            "wishes": True
        },
        "events": []
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles",
            json=profile_data,
            headers=get_headers(token),
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            profile_id = data.get("id")
            slug = data.get("slug")
            print(f"{GREEN}✓ Created celebration profile: {slug} (id: {profile_id[:8]}...){RESET}")
            return profile_id
        else:
            print(f"{RED}Failed to create celebration profile: {response.status_code} - {response.text[:200]}{RESET}")
            return None
    except Exception as e:
        print(f"{RED}Error creating celebration profile: {e}{RESET}")
        return None


def create_test_wedding_profile(token: str) -> Optional[str]:
    """Create a test wedding profile"""
    from datetime import datetime, timedelta
    
    event_date = (datetime.now() + timedelta(days=60)).isoformat()
    
    profile_data = {
        "groom_name": "Rohan",
        "bride_name": "Anaya",
        "event_type": "wedding",
        "event_date": event_date,
        "venue": "Grand Palace",
        "city": "Mumbai",
        "invitation_message": "Join us as we begin our journey together",
        "language": ["english"],
        "design_id": "royal_heritage",
        "invitation_category": "wedding",
        "sections_enabled": {
            "about_couple": True,
            "events": True,
            "gallery": True,
            "rsvp": True,
            "wishes": True
        },
        "events": []
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles",
            json=profile_data,
            headers=get_headers(token),
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            profile_id = data.get("id")
            slug = data.get("slug")
            print(f"{GREEN}✓ Created wedding profile: {slug} (id: {profile_id[:8]}...){RESET}")
            return profile_id
        else:
            print(f"{RED}Failed to create wedding profile: {response.status_code} - {response.text[:200]}{RESET}")
            return None
    except Exception as e:
        print(f"{RED}Error creating wedding profile: {e}{RESET}")
        return None


def test_music_presets_default(results: TestResults):
    """Test 1: GET /api/music/presets (default wedding library)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 1: Music Presets - Default Wedding Library{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.get(f"{BASE_URL}/music/presets", headers=COMMON_HEADERS, timeout=10)
        
        if response.status_code != 200:
            results.add_fail(
                "GET /api/music/presets",
                f"Expected 200, got {response.status_code}"
            )
            return
        
        data = response.json()
        
        # Verify JSON shape
        if "presets" not in data or "count" not in data:
            results.add_fail(
                "GET /api/music/presets - JSON shape",
                f"Missing 'presets' or 'count' keys. Got: {list(data.keys())}"
            )
            return
        
        presets = data["presets"]
        count = data["count"]
        
        # Verify count is 20 (wedding library)
        if count != 20:
            results.add_fail(
                "GET /api/music/presets - count",
                f"Expected 20 tracks, got {count}"
            )
            return
        
        if len(presets) != 20:
            results.add_fail(
                "GET /api/music/presets - presets length",
                f"Expected 20 presets, got {len(presets)}"
            )
            return
        
        # Verify first preset has required fields
        first = presets[0]
        required_fields = ["preset_id", "name", "category", "mood", "url", "duration_sec"]
        missing = [f for f in required_fields if f not in first]
        if missing:
            results.add_fail(
                "GET /api/music/presets - preset fields",
                f"Missing fields in preset: {missing}"
            )
            return
        
        results.add_pass(
            "GET /api/music/presets",
            f"Returns 20 wedding tracks with correct JSON shape"
        )
        
    except Exception as e:
        results.add_fail("GET /api/music/presets", f"Exception: {e}")


def test_music_presets_celebration(results: TestResults):
    """Test 2: GET /api/music/presets?category=celebration (new 10-track library)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 2: Music Presets - Celebration Library{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/music/presets",
            params={"category": "celebration"},
            headers=COMMON_HEADERS,
            timeout=10
        )
        
        if response.status_code != 200:
            results.add_fail(
                "GET /api/music/presets?category=celebration",
                f"Expected 200, got {response.status_code}"
            )
            return
        
        data = response.json()
        
        # Verify JSON shape
        if "presets" not in data or "count" not in data:
            results.add_fail(
                "GET /api/music/presets?category=celebration - JSON shape",
                f"Missing 'presets' or 'count' keys"
            )
            return
        
        presets = data["presets"]
        count = data["count"]
        
        # Verify count is 10 (celebration library)
        if count != 10:
            results.add_fail(
                "GET /api/music/presets?category=celebration - count",
                f"Expected 10 tracks, got {count}"
            )
            return
        
        if len(presets) != 10:
            results.add_fail(
                "GET /api/music/presets?category=celebration - presets length",
                f"Expected 10 presets, got {len(presets)}"
            )
            return
        
        # Verify preset IDs start with "cel-"
        non_cel_ids = [p["preset_id"] for p in presets if not p["preset_id"].startswith("cel-")]
        if non_cel_ids:
            results.add_fail(
                "GET /api/music/presets?category=celebration - preset IDs",
                f"Expected all IDs to start with 'cel-', but found: {non_cel_ids}"
            )
            return
        
        # Verify categories are celebration-specific
        expected_categories = ["lullaby", "joyful", "devotional", "pleasant", "cinematic"]
        categories = set(p["category"] for p in presets)
        invalid_categories = categories - set(expected_categories)
        if invalid_categories:
            results.add_fail(
                "GET /api/music/presets?category=celebration - categories",
                f"Unexpected categories: {invalid_categories}"
            )
            return
        
        results.add_pass(
            "GET /api/music/presets?category=celebration",
            f"Returns 10 celebration tracks with cel-* IDs and correct categories"
        )
        
        # Spot-check 2 audio URLs
        print(f"\n{YELLOW}Spot-checking audio URLs...{RESET}")
        urls_to_check = [presets[0]["url"], presets[5]["url"]]
        
        for i, url in enumerate(urls_to_check):
            try:
                head_response = requests.head(url, timeout=10, allow_redirects=True)
                content_type = head_response.headers.get("Content-Type", "")
                
                if head_response.status_code == 200 and "audio" in content_type.lower():
                    results.add_pass(
                        f"Audio URL check #{i+1}",
                        f"URL: {url} - Status: 200, Content-Type: {content_type}"
                    )
                else:
                    results.add_fail(
                        f"Audio URL check #{i+1}",
                        f"URL: {url} - Status: {head_response.status_code}, Content-Type: {content_type}"
                    )
            except Exception as e:
                results.add_fail(f"Audio URL check #{i+1}", f"URL: {url} - Error: {e}")
        
    except Exception as e:
        results.add_fail("GET /api/music/presets?category=celebration", f"Exception: {e}")


def test_translation_no_auth(results: TestResults, profile_id: str):
    """Test 3: POST /api/admin/profiles/{id}/translate without auth (expect 401)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 3: AI Translation - No Auth (expect 401){RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{profile_id}/translate",
            json={"language": "tamil"},
            timeout=10
        )
        
        if response.status_code == 401:
            results.add_pass(
                "POST /api/admin/profiles/{id}/translate - no auth",
                "Correctly returns 401 Unauthorized"
            )
        else:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - no auth",
                f"Expected 401, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - no auth", f"Exception: {e}")


def test_translation_invalid_language(results: TestResults, profile_id: str, token: str):
    """Test 4: POST /api/admin/profiles/{id}/translate with invalid language (expect 400)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 4: AI Translation - Invalid Language (expect 400){RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    # Test 4a: English (source language, should be rejected)
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{profile_id}/translate",
            json={"language": "english"},
            headers=get_headers(token),
            timeout=10
        )
        
        if response.status_code == 400:
            results.add_pass(
                "POST /api/admin/profiles/{id}/translate - language=english",
                "Correctly rejects English as target language (400)"
            )
        else:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - language=english",
                f"Expected 400, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - language=english", f"Exception: {e}")
    
    # Test 4b: Unknown language (e.g., french)
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{profile_id}/translate",
            json={"language": "french"},
            headers=get_headers(token),
            timeout=10
        )
        
        if response.status_code == 400:
            results.add_pass(
                "POST /api/admin/profiles/{id}/translate - language=french",
                "Correctly rejects unknown language (400)"
            )
        else:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - language=french",
                f"Expected 400, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - language=french", f"Exception: {e}")


def test_translation_not_found(results: TestResults, token: str):
    """Test 5: POST /api/admin/profiles/{id}/translate with non-existent profile (expect 404)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 5: AI Translation - Profile Not Found (expect 404){RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    fake_profile_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{fake_profile_id}/translate",
            json={"language": "tamil"},
            headers=get_headers(token),
            timeout=10
        )
        
        if response.status_code == 404:
            results.add_pass(
                "POST /api/admin/profiles/{id}/translate - non-existent profile",
                "Correctly returns 404 Not Found"
            )
        else:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - non-existent profile",
                f"Expected 404, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - non-existent profile", f"Exception: {e}")


def test_translation_success_tamil(results: TestResults, profile_id: str, token: str) -> Optional[Dict]:
    """Test 6: POST /api/admin/profiles/{id}/translate with Tamil (expect 200)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 6: AI Translation - Tamil (expect 200){RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        # Get admin credit balance before
        credit_response = requests.get(
            f"{BASE_URL}/admin/credits",
            headers=get_headers(token),
            timeout=10
        )
        credits_before = None
        if credit_response.status_code == 200:
            credits_before = credit_response.json().get("available_credits")
            print(f"   Credits before: {credits_before}")
        
        # Make translation request
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{profile_id}/translate",
            json={"language": "tamil"},
            headers=get_headers(token),
            timeout=45  # Gemini can take time
        )
        
        if response.status_code != 200:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - tamil",
                f"Expected 200, got {response.status_code} - {response.text}"
            )
            return None
        
        data = response.json()
        
        # Verify response shape
        required_fields = ["language", "translation", "credits_remaining"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - tamil response shape",
                f"Missing fields: {missing}"
            )
            return None
        
        if data["language"] != "tamil":
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - tamil language field",
                f"Expected 'tamil', got '{data['language']}'"
            )
            return None
        
        translation = data["translation"]
        if not isinstance(translation, dict):
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - tamil translation type",
                f"Expected dict, got {type(translation)}"
            )
            return None
        
        # Verify translation has expected keys (at least some of them)
        expected_keys = ["invitation_message", "story", "closing_message", "subtitle", "welcome_blessing"]
        found_keys = [k for k in expected_keys if k in translation]
        if not found_keys:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - tamil translation keys",
                f"Expected at least one of {expected_keys}, got {list(translation.keys())}"
            )
            return None
        
        # Verify credit deduction
        credits_after = data.get("credits_remaining")
        if credits_before is not None and credits_after is not None:
            if credits_after == credits_before - 1:
                print(f"   Credits after: {credits_after} (deducted 1 credit)")
            else:
                results.add_fail(
                    "POST /api/admin/profiles/{id}/translate - tamil credit deduction",
                    f"Expected {credits_before - 1} credits, got {credits_after}"
                )
                return None
        
        results.add_pass(
            "POST /api/admin/profiles/{id}/translate - tamil",
            f"Successfully translated to Tamil, deducted 1 credit"
        )
        
        print(f"\n{YELLOW}Tamil Translation Sample:{RESET}")
        for key, value in list(translation.items())[:3]:
            print(f"   {key}: {value[:100]}..." if len(str(value)) > 100 else f"   {key}: {value}")
        
        return translation
        
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - tamil", f"Exception: {e}")
        return None


def test_translation_success_telugu(results: TestResults, profile_id: str, token: str) -> Optional[Dict]:
    """Test 7: POST /api/admin/profiles/{id}/translate with Telugu (expect 200)"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 7: AI Translation - Telugu (expect 200){RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/profiles/{profile_id}/translate",
            json={"language": "telugu"},
            headers=get_headers(token),
            timeout=45
        )
        
        if response.status_code != 200:
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - telugu",
                f"Expected 200, got {response.status_code} - {response.text}"
            )
            return None
        
        data = response.json()
        
        if data["language"] != "telugu":
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - telugu language field",
                f"Expected 'telugu', got '{data['language']}'"
            )
            return None
        
        translation = data["translation"]
        if not isinstance(translation, dict):
            results.add_fail(
                "POST /api/admin/profiles/{id}/translate - telugu translation type",
                f"Expected dict, got {type(translation)}"
            )
            return None
        
        results.add_pass(
            "POST /api/admin/profiles/{id}/translate - telugu",
            f"Successfully translated to Telugu"
        )
        
        print(f"\n{YELLOW}Telugu Translation Sample:{RESET}")
        for key, value in list(translation.items())[:3]:
            print(f"   {key}: {value[:100]}..." if len(str(value)) > 100 else f"   {key}: {value}")
        
        return translation
        
    except Exception as e:
        results.add_fail("POST /api/admin/profiles/{id}/translate - telugu", f"Exception: {e}")
        return None


def test_translation_persistence(results: TestResults, profile_id: str, token: str):
    """Test 8: Verify translations persisted in MongoDB"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 8: Translation Persistence in MongoDB{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        # Fetch profile data
        response = requests.get(
            f"{BASE_URL}/admin/profiles/{profile_id}",
            headers=get_headers(token),
            timeout=10
        )
        
        if response.status_code != 200:
            results.add_fail(
                "Translation persistence check",
                f"Could not fetch profile: {response.status_code}"
            )
            return
        
        profile = response.json()
        translations = profile.get("translations", {})
        
        # Check for tamil and telugu
        if "tamil" not in translations:
            results.add_fail(
                "Translation persistence - tamil",
                "Tamil translation not found in profile.translations"
            )
        else:
            results.add_pass(
                "Translation persistence - tamil",
                "Tamil translation persisted in profile.translations"
            )
        
        if "telugu" not in translations:
            results.add_fail(
                "Translation persistence - telugu",
                "Telugu translation not found in profile.translations"
            )
        else:
            results.add_pass(
                "Translation persistence - telugu",
                "Telugu translation persisted in profile.translations"
            )
        
    except Exception as e:
        results.add_fail("Translation persistence check", f"Exception: {e}")


def test_regression_celebration_invite(results: TestResults):
    """Test 9: Regression - GET /api/invite/manvith-test-bday"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 9: Regression - Celebration Invite{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.get(f"{BASE_URL}/invite/{CELEBRATION_SLUG}", headers=COMMON_HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Verify it's a celebration profile
            if data.get("invitation_category") == "baby_birthday":
                results.add_pass(
                    "GET /api/invite/manvith-test-bday",
                    "Returns 200 with celebration design data"
                )
            else:
                results.add_fail(
                    "GET /api/invite/manvith-test-bday",
                    f"Expected invitation_category='baby_birthday', got '{data.get('invitation_category')}'"
                )
        else:
            results.add_fail(
                "GET /api/invite/manvith-test-bday",
                f"Expected 200, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("GET /api/invite/manvith-test-bday", f"Exception: {e}")


def test_regression_wedding_invite(results: TestResults):
    """Test 10: Regression - GET /api/invite/anaya-rohan-test"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST 10: Regression - Wedding Invite{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    
    try:
        response = requests.get(f"{BASE_URL}/invite/{WEDDING_SLUG}", headers=COMMON_HEADERS, timeout=10)
        
        if response.status_code == 200:
            results.add_pass(
                "GET /api/invite/anaya-rohan-test",
                "Returns 200 (wedding regression sanity check)"
            )
        else:
            results.add_fail(
                "GET /api/invite/anaya-rohan-test",
                f"Expected 200, got {response.status_code}"
            )
    except Exception as e:
        results.add_fail("GET /api/invite/anaya-rohan-test", f"Exception: {e}")


def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}BACKEND API TEST SUITE - TWO NEW ENDPOINTS{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Celebration Profile: {CELEBRATION_SLUG}")
    print(f"Wedding Profile: {WEDDING_SLUG}")
    
    results = TestResults()
    
    # Get admin token
    print(f"\n{YELLOW}Authenticating as admin...{RESET}")
    token = get_admin_token()
    if not token:
        print(f"{RED}FATAL: Could not authenticate. Aborting tests.{RESET}")
        sys.exit(1)
    print(f"{GREEN}✓ Authenticated successfully{RESET}")
    
    # Get or create celebration profile
    print(f"\n{YELLOW}Checking for celebration profile...{RESET}")
    profile_id = get_profile_id_by_slug(CELEBRATION_SLUG, token)
    
    if not profile_id:
        print(f"{YELLOW}Celebration profile not found. Creating test profile...{RESET}")
        profile_id = create_test_celebration_profile(token)
        
        if not profile_id:
            print(f"{RED}FATAL: Could not create celebration profile. Aborting translation tests.{RESET}")
            profile_id = "UNKNOWN"
        else:
            # Re-fetch to get the actual slug
            print(f"{YELLOW}Fetching created profile details...{RESET}")
            response = requests.get(
                f"{BASE_URL}/admin/profiles/{profile_id}",
                headers=get_headers(token),
                timeout=10
            )
            if response.status_code == 200:
                actual_slug = response.json().get("slug")
                print(f"{GREEN}✓ Profile created with slug: {actual_slug}{RESET}")
                print(f"{GREEN}✓ Profile ID: {profile_id}{RESET}")
    else:
        print(f"{GREEN}✓ Found existing profile{RESET}")
        print(f"{GREEN}✓ Profile ID: {profile_id}{RESET}")
    
    # Run tests
    test_music_presets_default(results)
    test_music_presets_celebration(results)
    
    if profile_id != "UNKNOWN":
        test_translation_no_auth(results, profile_id)
        test_translation_invalid_language(results, profile_id, token)
        test_translation_not_found(results, token)
        test_translation_success_tamil(results, profile_id, token)
        test_translation_success_telugu(results, profile_id, token)
        test_translation_persistence(results, profile_id, token)
    else:
        print(f"\n{YELLOW}Skipping translation tests (no profile ID){RESET}")
    
    test_regression_celebration_invite(results)
    test_regression_wedding_invite(results)
    
    # Print summary
    success = results.summary()
    
    # Print detailed results for failed tests
    if results.failed > 0:
        print(f"\n{RED}FAILED TESTS:{RESET}")
        for test in results.tests:
            if test["status"] == "FAIL":
                print(f"  • {test['name']}")
                if test["details"]:
                    print(f"    {test['details']}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
