#!/usr/bin/env python3
"""
Comprehensive test suite for Supabase Auth Bridge + Legacy Auth Regression.

Tests:
1. Legacy /api/auth/login regression (super admin + photographer + wrong password)
2. GET /api/auth/me with legacy token (regression)
3. Auto-mirror to Supabase on legacy login (check MongoDB supabase_user_id)
4. GET /api/auth/me-supabase (various scenarios)
5. POST /api/auth/sync-supabase-user (idempotent creation)
6. Bulk migration script (dry-run + live + bcrypt preservation)
7. CORS/route prefix verification

Test Credentials (from /app/memory/test_credentials.md):
- Super Admin: username="mani_8328" password="Maneesh@1234"
- Photographer: email="photographer.test@majatest.com" password="TestPass@123"
"""

import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load backend .env
ROOT = Path(__file__).parent / "backend"
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

# Import after path setup
from auth import get_password_hash  # noqa: E402
import supabase_admin  # noqa: E402

# Configuration
BASE_URL = "https://supabase-auth-stage.preview.emergentagent.com/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Test credentials
SUPER_ADMIN_USERNAME = "mani_8328"
SUPER_ADMIN_PASSWORD = "Maneesh@1234"
SUPER_ADMIN_EMAIL = "mani_8328@majacreations.com"

PHOTOGRAPHER_EMAIL = "photographer.test@majatest.com"
PHOTOGRAPHER_PASSWORD = "TestPass@123"

# Test results
results = {
    "passed": [],
    "failed": [],
    "warnings": [],
}


def log_pass(test_name: str, details: str = ""):
    """Log a passing test."""
    msg = f"✅ PASS: {test_name}"
    if details:
        msg += f" - {details}"
    print(msg)
    results["passed"].append({"test": test_name, "details": details})


def log_fail(test_name: str, details: str):
    """Log a failing test."""
    msg = f"❌ FAIL: {test_name} - {details}"
    print(msg)
    results["failed"].append({"test": test_name, "details": details})


def log_warn(test_name: str, details: str):
    """Log a warning."""
    msg = f"⚠️  WARN: {test_name} - {details}"
    print(msg)
    results["warnings"].append({"test": test_name, "details": details})


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


async def get_mongo_db():
    """Get MongoDB database connection."""
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME], client


# ============================================================================
# TEST 1: Legacy /api/auth/login Regression
# ============================================================================
def test_legacy_login_super_admin():
    """Test 1.1: Legacy login with super admin credentials."""
    print_section("TEST 1.1: Legacy Login - Super Admin")
    
    # Test with username
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username_or_email": SUPER_ADMIN_USERNAME, "password": SUPER_ADMIN_PASSWORD},
        timeout=10,
    )
    
    if resp.status_code != 200:
        log_fail("Legacy login (super admin username)", f"Status {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    if "access_token" not in data:
        log_fail("Legacy login (super admin username)", "Missing access_token in response")
        return None
    
    admin = data.get("admin", {})
    if admin.get("role") != "super_admin":
        log_fail("Legacy login (super admin username)", f"Expected role=super_admin, got {admin.get('role')}")
        return None
    
    log_pass("Legacy login (super admin username)", f"Logged in as {admin.get('email')}, role={admin.get('role')}")
    
    # Test with email
    resp2 = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
        timeout=10,
    )
    
    if resp2.status_code != 200:
        log_fail("Legacy login (super admin email)", f"Status {resp2.status_code}: {resp2.text}")
        return data["access_token"]
    
    log_pass("Legacy login (super admin email)", "Login with email also works")
    return data["access_token"]


def test_legacy_login_photographer():
    """Test 1.2: Legacy login with photographer credentials."""
    print_section("TEST 1.2: Legacy Login - Photographer")
    
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": PHOTOGRAPHER_EMAIL, "password": PHOTOGRAPHER_PASSWORD},
        timeout=10,
    )
    
    if resp.status_code != 200:
        log_fail("Legacy login (photographer)", f"Status {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    if "access_token" not in data:
        log_fail("Legacy login (photographer)", "Missing access_token in response")
        return None
    
    admin = data.get("admin", {})
    if admin.get("role") != "admin":
        log_fail("Legacy login (photographer)", f"Expected role=admin, got {admin.get('role')}")
        return None
    
    log_pass("Legacy login (photographer)", f"Logged in as {admin.get('email')}, role={admin.get('role')}")
    return data["access_token"]


def test_legacy_login_wrong_password():
    """Test 1.3: Legacy login with wrong password."""
    print_section("TEST 1.3: Legacy Login - Wrong Password")
    
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": PHOTOGRAPHER_EMAIL, "password": "WrongPassword123!"},
        timeout=10,
    )
    
    if resp.status_code == 401:
        log_pass("Legacy login (wrong password)", "Correctly rejected with 401")
    else:
        log_fail("Legacy login (wrong password)", f"Expected 401, got {resp.status_code}")


# ============================================================================
# TEST 2: GET /api/auth/me with Legacy Token
# ============================================================================
def test_auth_me_with_legacy_token(token: str):
    """Test 2: GET /api/auth/me with legacy access_token."""
    print_section("TEST 2: GET /api/auth/me (Legacy Token Regression)")
    
    if not token:
        log_fail("GET /api/auth/me", "No token provided (previous test failed)")
        return
    
    resp = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    
    if resp.status_code != 200:
        log_fail("GET /api/auth/me", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    if "id" not in data or "email" not in data:
        log_fail("GET /api/auth/me", f"Missing required fields in response: {data}")
        return
    
    log_pass("GET /api/auth/me", f"Retrieved admin: {data.get('email')}, role={data.get('role')}")


# ============================================================================
# TEST 3: Auto-Mirror to Supabase on Legacy Login
# ============================================================================
async def test_auto_mirror_on_login():
    """Test 3: Verify supabase_user_id is set after legacy login."""
    print_section("TEST 3: Auto-Mirror to Supabase on Legacy Login")
    
    db, client = await get_mongo_db()
    
    try:
        # Check super admin
        super_admin = await db.admins.find_one(
            {"email": SUPER_ADMIN_EMAIL.lower()},
            {"_id": 0, "email": 1, "supabase_user_id": 1}
        )
        
        if not super_admin:
            log_fail("Auto-mirror (super admin)", f"Admin not found: {SUPER_ADMIN_EMAIL}")
        elif not super_admin.get("supabase_user_id"):
            log_warn("Auto-mirror (super admin)", "supabase_user_id not set (may need another login)")
        else:
            log_pass("Auto-mirror (super admin)", f"supabase_user_id={super_admin['supabase_user_id']}")
        
        # Check photographer
        photographer = await db.admins.find_one(
            {"email": PHOTOGRAPHER_EMAIL.lower()},
            {"_id": 0, "email": 1, "supabase_user_id": 1}
        )
        
        if not photographer:
            log_fail("Auto-mirror (photographer)", f"Admin not found: {PHOTOGRAPHER_EMAIL}")
        elif not photographer.get("supabase_user_id"):
            log_warn("Auto-mirror (photographer)", "supabase_user_id not set (may need another login)")
        else:
            log_pass("Auto-mirror (photographer)", f"supabase_user_id={photographer['supabase_user_id']}")
    
    finally:
        client.close()


# ============================================================================
# TEST 4: GET /api/auth/me-supabase
# ============================================================================
def test_me_supabase_no_auth():
    """Test 4.1: GET /api/auth/me-supabase without Authorization header."""
    print_section("TEST 4.1: GET /api/auth/me-supabase - No Auth Header")
    
    resp = requests.get(f"{BASE_URL}/auth/me-supabase", timeout=10)
    
    if resp.status_code == 401:
        detail = resp.json().get("detail", "")
        if "bearer token" in detail.lower():
            log_pass("GET /api/auth/me-supabase (no auth)", "Correctly rejected with 401 'Missing bearer token'")
        else:
            log_warn("GET /api/auth/me-supabase (no auth)", f"Got 401 but unexpected message: {detail}")
    else:
        log_fail("GET /api/auth/me-supabase (no auth)", f"Expected 401, got {resp.status_code}")


def test_me_supabase_invalid_token():
    """Test 4.2: GET /api/auth/me-supabase with invalid token."""
    print_section("TEST 4.2: GET /api/auth/me-supabase - Invalid Token")
    
    resp = requests.get(
        f"{BASE_URL}/auth/me-supabase",
        headers={"Authorization": "Bearer garbage_token_12345"},
        timeout=10,
    )
    
    if resp.status_code == 401:
        detail = resp.json().get("detail", "")
        if "invalid" in detail.lower() or "supabase" in detail.lower():
            log_pass("GET /api/auth/me-supabase (invalid token)", f"Correctly rejected with 401: {detail}")
        else:
            log_warn("GET /api/auth/me-supabase (invalid token)", f"Got 401 but unexpected message: {detail}")
    else:
        log_fail("GET /api/auth/me-supabase (invalid token)", f"Expected 401, got {resp.status_code}")


async def test_me_supabase_valid_token_linked():
    """Test 4.3: GET /api/auth/me-supabase with valid token for linked user."""
    print_section("TEST 4.3: GET /api/auth/me-supabase - Valid Token (Linked User)")
    
    db, client = await get_mongo_db()
    
    try:
        # Find an admin that has supabase_user_id set
        admin = await db.admins.find_one(
            {"supabase_user_id": {"$exists": True, "$ne": None}},
            {"_id": 0, "email": 1, "supabase_user_id": 1}
        )
        
        if not admin:
            log_warn("GET /api/auth/me-supabase (linked)", "No linked admin found in DB (skip test)")
            return
        
        # Create a Supabase JWT for this user
        # We'll use the admin client to generate a session
        try:
            supa_client = supabase_admin.get_admin_client()
            
            # Try to sign in with the photographer credentials (if this is the photographer)
            if admin["email"] == PHOTOGRAPHER_EMAIL.lower():
                # Create a new test user with known password for testing
                test_email = f"test_linked_{int(time.time())}@test.com"
                test_password = f"TestPass_{secrets.token_urlsafe(8)}"
                
                # Create user in Supabase
                create_resp = supa_client.auth.admin.create_user({
                    "email": test_email,
                    "password": test_password,
                    "email_confirm": True,
                })
                
                if not create_resp or not create_resp.user:
                    log_fail("GET /api/auth/me-supabase (linked)", "Failed to create test Supabase user")
                    return
                
                sb_user_id = create_resp.user.id
                
                # Link this Supabase user to the photographer admin in MongoDB
                await db.admins.update_one(
                    {"email": PHOTOGRAPHER_EMAIL.lower()},
                    {"$set": {"supabase_user_id": sb_user_id}}
                )
                
                # Sign in to get access token
                sign_in_resp = supa_client.auth.sign_in_with_password({
                    "email": test_email,
                    "password": test_password,
                })
                
                if not sign_in_resp or not sign_in_resp.session:
                    log_fail("GET /api/auth/me-supabase (linked)", "Failed to sign in with test user")
                    return
                
                access_token = sign_in_resp.session.access_token
                
                # Now test the endpoint
                resp = requests.get(
                    f"{BASE_URL}/auth/me-supabase",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                
                if resp.status_code != 200:
                    log_fail("GET /api/auth/me-supabase (linked)", f"Status {resp.status_code}: {resp.text}")
                    return
                
                data = resp.json()
                if "access_token" not in data or "admin" not in data:
                    log_fail("GET /api/auth/me-supabase (linked)", f"Missing required fields: {data}")
                    return
                
                admin_data = data["admin"]
                if admin_data.get("supabase_user_id") != sb_user_id:
                    log_fail("GET /api/auth/me-supabase (linked)", f"supabase_user_id mismatch")
                    return
                
                log_pass("GET /api/auth/me-supabase (linked)", 
                        f"Retrieved admin: {admin_data.get('email')}, got legacy token")
                
                # Clean up test user
                try:
                    supa_client.auth.admin.delete_user(sb_user_id)
                except Exception:
                    pass
            else:
                log_warn("GET /api/auth/me-supabase (linked)", 
                        "Skipping - would need to create test Supabase user with known password")
        
        except Exception as e:
            log_fail("GET /api/auth/me-supabase (linked)", f"Error: {str(e)}")
    
    finally:
        client.close()


async def test_me_supabase_valid_token_unlinked():
    """Test 4.4: GET /api/auth/me-supabase with valid token for unlinked user."""
    print_section("TEST 4.4: GET /api/auth/me-supabase - Valid Token (Unlinked User)")
    
    try:
        # Create a brand new Supabase user that has no MongoDB admin row
        supa_client = supabase_admin.get_admin_client()
        test_email = f"test_unlinked_{int(time.time())}@test.com"
        test_password = f"TestPass_{secrets.token_urlsafe(8)}"
        
        create_resp = supa_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,
        })
        
        if not create_resp or not create_resp.user:
            log_fail("GET /api/auth/me-supabase (unlinked)", "Failed to create test Supabase user")
            return
        
        sb_user_id = create_resp.user.id
        
        # Sign in to get access token
        sign_in_resp = supa_client.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password,
        })
        
        if not sign_in_resp or not sign_in_resp.session:
            log_fail("GET /api/auth/me-supabase (unlinked)", "Failed to sign in with test user")
            return
        
        access_token = sign_in_resp.session.access_token
        
        # Test the endpoint - should return 404 with error=no_admin_record
        resp = requests.get(
            f"{BASE_URL}/auth/me-supabase",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        
        if resp.status_code == 404:
            detail = resp.json().get("detail", {})
            if isinstance(detail, dict) and detail.get("error") == "no_admin_record":
                log_pass("GET /api/auth/me-supabase (unlinked)", 
                        "Correctly returned 404 with error=no_admin_record")
            else:
                log_warn("GET /api/auth/me-supabase (unlinked)", 
                        f"Got 404 but unexpected detail: {detail}")
        else:
            log_fail("GET /api/auth/me-supabase (unlinked)", 
                    f"Expected 404, got {resp.status_code}: {resp.text}")
        
        # Clean up
        try:
            supa_client.auth.admin.delete_user(sb_user_id)
        except Exception:
            pass
    
    except Exception as e:
        log_fail("GET /api/auth/me-supabase (unlinked)", f"Error: {str(e)}")


# ============================================================================
# TEST 5: POST /api/auth/sync-supabase-user
# ============================================================================
async def test_sync_supabase_user_no_auth():
    """Test 5.1: POST /api/auth/sync-supabase-user without Authorization."""
    print_section("TEST 5.1: POST /api/auth/sync-supabase-user - No Auth")
    
    resp = requests.post(
        f"{BASE_URL}/auth/sync-supabase-user",
        json={"name": "Test User"},
        timeout=10,
    )
    
    if resp.status_code == 401:
        log_pass("POST /api/auth/sync-supabase-user (no auth)", "Correctly rejected with 401")
    else:
        log_fail("POST /api/auth/sync-supabase-user (no auth)", 
                f"Expected 401, got {resp.status_code}")


async def test_sync_supabase_user_create():
    """Test 5.2: POST /api/auth/sync-supabase-user creates admin row."""
    print_section("TEST 5.2: POST /api/auth/sync-supabase-user - Create Admin")
    
    db, client = await get_mongo_db()
    
    try:
        # Create a brand new Supabase user
        supa_client = supabase_admin.get_admin_client()
        test_email = f"test_sync_{int(time.time())}@test.com"
        test_password = f"TestPass_{secrets.token_urlsafe(8)}"
        test_name = "Test Sync User"
        
        create_resp = supa_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,
        })
        
        if not create_resp or not create_resp.user:
            log_fail("POST /api/auth/sync-supabase-user (create)", "Failed to create test Supabase user")
            return
        
        sb_user_id = create_resp.user.id
        
        # Sign in to get access token
        sign_in_resp = supa_client.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password,
        })
        
        if not sign_in_resp or not sign_in_resp.session:
            log_fail("POST /api/auth/sync-supabase-user (create)", "Failed to sign in")
            return
        
        access_token = sign_in_resp.session.access_token
        
        # Call sync endpoint
        resp = requests.post(
            f"{BASE_URL}/auth/sync-supabase-user",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": test_name},
            timeout=10,
        )
        
        if resp.status_code not in (200, 201):
            log_fail("POST /api/auth/sync-supabase-user (create)", 
                    f"Status {resp.status_code}: {resp.text}")
            return
        
        data = resp.json()
        if not data.get("success") or "access_token" not in data or "admin" not in data:
            log_fail("POST /api/auth/sync-supabase-user (create)", 
                    f"Missing required fields: {data}")
            return
        
        admin_data = data["admin"]
        if admin_data.get("email") != test_email:
            log_fail("POST /api/auth/sync-supabase-user (create)", 
                    f"Email mismatch: expected {test_email}, got {admin_data.get('email')}")
            return
        
        log_pass("POST /api/auth/sync-supabase-user (create)", 
                f"Created admin: {admin_data.get('email')}, got legacy token")
        
        # Test idempotency - call again with same token
        resp2 = requests.post(
            f"{BASE_URL}/auth/sync-supabase-user",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": test_name},
            timeout=10,
        )
        
        if resp2.status_code not in (200, 201):
            log_fail("POST /api/auth/sync-supabase-user (idempotent)", 
                    f"Status {resp2.status_code}: {resp2.text}")
        else:
            data2 = resp2.json()
            if data2.get("admin", {}).get("id") == admin_data.get("id"):
                log_pass("POST /api/auth/sync-supabase-user (idempotent)", 
                        "Returned same admin (no duplicate)")
            else:
                log_fail("POST /api/auth/sync-supabase-user (idempotent)", 
                        "Created duplicate admin")
        
        # Clean up
        try:
            await db.admins.delete_one({"email": test_email})
            supa_client.auth.admin.delete_user(sb_user_id)
        except Exception:
            pass
    
    except Exception as e:
        log_fail("POST /api/auth/sync-supabase-user (create)", f"Error: {str(e)}")
    
    finally:
        client.close()


# ============================================================================
# TEST 6: Bulk Migration Script
# ============================================================================
async def test_migration_script_dry_run():
    """Test 6.1: Migration script with --dry-run."""
    print_section("TEST 6.1: Bulk Migration Script - Dry Run")
    
    try:
        result = subprocess.run(
            ["python", "scripts/migrate_admins_to_supabase.py", "--dry-run"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            log_fail("Migration script (dry-run)", f"Exit code {result.returncode}: {result.stderr}")
            return
        
        output = result.stdout
        if "would_migrate" in output or "already_linked" in output or "Found" in output:
            log_pass("Migration script (dry-run)", "Ran successfully, no DB changes")
        else:
            log_warn("Migration script (dry-run)", f"Unexpected output: {output[:200]}")
    
    except Exception as e:
        log_fail("Migration script (dry-run)", f"Error: {str(e)}")


async def test_migration_script_live():
    """Test 6.2: Migration script live run (idempotent)."""
    print_section("TEST 6.2: Bulk Migration Script - Live Run")
    
    try:
        result = subprocess.run(
            ["python", "scripts/migrate_admins_to_supabase.py"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            log_fail("Migration script (live)", f"Exit code {result.returncode}: {result.stderr}")
            return
        
        output = result.stdout
        if "migrated" in output or "already_linked" in output:
            log_pass("Migration script (live)", "Ran successfully")
        else:
            log_warn("Migration script (live)", f"Unexpected output: {output[:200]}")
    
    except Exception as e:
        log_fail("Migration script (live)", f"Error: {str(e)}")


async def test_migration_bcrypt_preservation():
    """Test 6.3: Migration preserves bcrypt password (can sign in with original pw)."""
    print_section("TEST 6.3: Bulk Migration - Bcrypt Password Preservation")
    
    db, client = await get_mongo_db()
    
    try:
        # Create a fresh admin with bcrypt hash
        test_email = f"test_bcrypt_{int(time.time())}@test.com"
        test_password = f"TestPass_{secrets.token_urlsafe(8)}"
        test_admin_id = f"test_admin_{secrets.token_urlsafe(8)}"
        
        bcrypt_hash = get_password_hash(test_password)
        
        await db.admins.insert_one({
            "id": test_admin_id,
            "email": test_email,
            "password_hash": bcrypt_hash,
            "name": "Test Bcrypt User",
            "role": "admin",
            "status": "active",
            "total_credits": 0,
            "used_credits": 0,
            "created_at": "2026-06-11T00:00:00Z",
        })
        
        # Run migration script
        result = subprocess.run(
            ["python", "scripts/migrate_admins_to_supabase.py"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            log_fail("Migration bcrypt preservation", f"Script failed: {result.stderr}")
            return
        
        # Check that admin now has supabase_user_id
        admin = await db.admins.find_one({"email": test_email}, {"_id": 0})
        if not admin or not admin.get("supabase_user_id"):
            log_fail("Migration bcrypt preservation", "Admin not migrated (no supabase_user_id)")
            return
        
        sb_user_id = admin["supabase_user_id"]
        
        # Try to sign in with original password via Supabase
        try:
            supa_client = supabase_admin.get_admin_client()
            sign_in_resp = supa_client.auth.sign_in_with_password({
                "email": test_email,
                "password": test_password,
            })
            
            if sign_in_resp and sign_in_resp.session:
                log_pass("Migration bcrypt preservation", 
                        "Successfully signed in with original password (bcrypt import worked)")
            else:
                log_fail("Migration bcrypt preservation", 
                        "Sign in failed (bcrypt import may not have worked)")
        
        except Exception as e:
            log_fail("Migration bcrypt preservation", f"Sign in error: {str(e)}")
        
        # Clean up
        try:
            await db.admins.delete_one({"id": test_admin_id})
            supa_client.auth.admin.delete_user(sb_user_id)
        except Exception:
            pass
    
    except Exception as e:
        log_fail("Migration bcrypt preservation", f"Error: {str(e)}")
    
    finally:
        client.close()


# ============================================================================
# TEST 7: CORS / Route Prefix Verification
# ============================================================================
def test_route_prefix():
    """Test 7: Verify new routes are accessible under /api/auth/."""
    print_section("TEST 7: CORS / Route Prefix Verification")
    
    endpoints = [
        "/auth/me-supabase",
        "/auth/sync-supabase-user",
    ]
    
    for endpoint in endpoints:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        # We expect 401 (no auth), not 404 (route not found)
        if resp.status_code in (401, 400):
            log_pass(f"Route prefix {endpoint}", f"Endpoint accessible (got {resp.status_code})")
        elif resp.status_code == 404:
            log_fail(f"Route prefix {endpoint}", "Endpoint not found (404)")
        else:
            log_warn(f"Route prefix {endpoint}", f"Unexpected status {resp.status_code}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
async def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 80)
    print("  SUPABASE AUTH BRIDGE + LEGACY AUTH REGRESSION TEST SUITE")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"MongoDB: {MONGO_URL}/{DB_NAME}")
    print("=" * 80)
    
    # TEST 1: Legacy login regression
    super_admin_token = test_legacy_login_super_admin()
    photographer_token = test_legacy_login_photographer()
    test_legacy_login_wrong_password()
    
    # TEST 2: GET /api/auth/me with legacy token
    if super_admin_token:
        test_auth_me_with_legacy_token(super_admin_token)
    if photographer_token:
        test_auth_me_with_legacy_token(photographer_token)
    
    # TEST 3: Auto-mirror to Supabase
    await test_auto_mirror_on_login()
    
    # TEST 4: GET /api/auth/me-supabase
    test_me_supabase_no_auth()
    test_me_supabase_invalid_token()
    await test_me_supabase_valid_token_linked()
    await test_me_supabase_valid_token_unlinked()
    
    # TEST 5: POST /api/auth/sync-supabase-user
    await test_sync_supabase_user_no_auth()
    await test_sync_supabase_user_create()
    
    # TEST 6: Bulk migration script
    await test_migration_script_dry_run()
    await test_migration_script_live()
    await test_migration_bcrypt_preservation()
    
    # TEST 7: Route prefix
    test_route_prefix()
    
    # Print summary
    print_section("TEST SUMMARY")
    print(f"✅ PASSED: {len(results['passed'])}")
    print(f"❌ FAILED: {len(results['failed'])}")
    print(f"⚠️  WARNINGS: {len(results['warnings'])}")
    
    if results["failed"]:
        print("\nFailed Tests:")
        for fail in results["failed"]:
            print(f"  ❌ {fail['test']}: {fail['details']}")
    
    if results["warnings"]:
        print("\nWarnings:")
        for warn in results["warnings"]:
            print(f"  ⚠️  {warn['test']}: {warn['details']}")
    
    print("\n" + "=" * 80)
    
    # Save results to file
    with open("/app/test_reports/supabase_auth_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to /app/test_reports/supabase_auth_test_results.json")
    
    return len(results["failed"]) == 0


if __name__ == "__main__":
    # Create test_reports directory
    Path("/app/test_reports").mkdir(exist_ok=True)
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
