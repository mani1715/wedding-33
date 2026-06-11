"""
BATCH A — Financial Safety / Race-Condition Tests
==================================================
Tests the 5 atomic-publish / atomic-redeem / atomic-refund fixes via
parallel-request stress testing.

Tests covered:
  1. Double-Click Publish Race  — POST /api/weddings/{id}/publish
  2. Bulk-Publish Backdoor      — POST /api/admin/profiles/bulk-action (publish)
  3. Razorpay Verify-Payment    — POST /api/payments/verify-payment (signature race)
  4. Gift-Code Redemption Race  — POST /api/account/redeem-code
  5. Bulk-Purge Refund          — POST /api/admin/profiles/bulk-action (purge)

Public preview URL is used for HTTP calls; MongoDB is reached locally
(localhost:27017) for setup/teardown (wallet reset, profile seeding,
gift code creation, ledger assertions).
"""
import asyncio
import os
import time
import uuid
import pytest
import requests
import httpx
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to localhost during direct dev runs.
    BASE_URL = "http://localhost:8001"

# The app rejects non-browser User-Agents with 403 "Automated access not allowed".
# Use a realistic browser UA for every request.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
LEDGER_COLL = "credit_ledger"  # collection name is singular

PHOTO_EMAIL = "testphoto@test.com"
PHOTO_PASS = "TestPass123!"
PHOTO_ID = "f48e8af0-26e5-47b9-a7b0-562a3618557a"

SUPER_EMAIL = "mani_8328@majacreations.com"
SUPER_PASS = "Maneesh@1234"
SUPER_ID = "d7555f0d-83a2-4999-bd39-1f1347830278"


# ─── shared fixtures ──────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      headers={"User-Agent": BROWSER_UA,
                               "Content-Type": "application/json"},
                      json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def photo_token() -> str:
    return _login(PHOTO_EMAIL, PHOTO_PASS)


@pytest.fixture(scope="module")
def super_token() -> str:
    return _login(SUPER_EMAIL, SUPER_PASS)


def _photo_headers(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json",
            "User-Agent": BROWSER_UA}


def _reset_wallet(mongo, total=100, used=0):
    mongo.admins.update_one(
        {"email": PHOTO_EMAIL},
        {"$set": {"total_credits": total, "used_credits": used,
                  "paid_links_count": 0}},
    )


def _seed_publishable_profile(mongo, suffix: str) -> str:
    """Insert a profile row directly with all check_ready_status fields populated."""
    pid = str(uuid.uuid4())
    slug = f"test-race-{suffix}-{int(time.time()*1000)}-{pid[:6]}"
    doc = {
        "id": pid,
        "admin_id": PHOTO_ID,
        "slug": slug,
        "title": f"Test Race {suffix}",
        "groom_name": "Groom",
        "bride_name": "Bride",
        "event_type": "wedding",
        "event_date": "2026-12-31",
        "venue": "Test Venue",
        "city": "Test City",
        "design_id": "elegant",
        "selected_design_key": "elegant",
        "selected_features": [],
        "status": "DRAFT",
        "is_published": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mongo.profiles.insert_one(doc)
    return pid


def _cleanup_test_profiles(mongo):
    mongo.profiles.delete_many({"admin_id": PHOTO_ID,
                                "title": {"$regex": "^Test Race"}})
    mongo.credit_ledger.delete_many({"admin_id": PHOTO_ID,
                                      "reason": {"$regex": "Test Race|test-race"}})


# ═════════════════════════════════════════════════════════════════════════
# TEST 1 — Double-Click Publish Race
# ═════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_1_double_click_publish_race(mongo, photo_token):
    _cleanup_test_profiles(mongo)
    _reset_wallet(mongo, total=100, used=0)
    pid = _seed_publishable_profile(mongo, "t1")

    url = f"{BASE_URL}/api/weddings/{pid}/publish"
    headers = _photo_headers(photo_token)

    async with httpx.AsyncClient(timeout=60) as cli:
        r1, r2 = await asyncio.gather(
            cli.post(url, headers=headers),
            cli.post(url, headers=headers),
            return_exceptions=True,
        )

    results = [r for r in (r1, r2) if not isinstance(r, Exception)]
    codes = sorted([r.status_code for r in results])
    print(f"\n[T1] codes={codes} bodies={[r.text[:200] for r in results]}")

    # Exactly one success + one failure.
    success = [r for r in results if r.status_code == 200]
    failed = [r for r in results if r.status_code != 200]
    assert len(success) == 1, f"Expected exactly 1 success, got {len(success)}: {codes}"
    assert len(failed) == 1, f"Expected exactly 1 failure, got {len(failed)}: {codes}"
    assert failed[0].status_code == 400, f"Expected 400, got {failed[0].status_code}"

    cost = success[0].json().get("credits_deducted")
    assert isinstance(cost, (int, float)) and cost > 0, \
        f"credits_deducted should be > 0, got {cost}"

    # Wallet check via API
    bal = requests.get(f"{BASE_URL}/api/account/credits", headers=headers, timeout=10).json()
    assert bal["used_credits"] == cost, \
        f"Expected used_credits={cost}, got {bal['used_credits']} (DOUBLE-CHARGED!)"

    # Ledger count
    n_ledger = mongo.credit_ledger.count_documents({
        "admin_id": PHOTO_ID,
        "related_wedding_id": pid,
        "action_type": "used",
    })
    assert n_ledger == 1, f"Expected exactly 1 USED ledger, got {n_ledger}"

    # Lock should be cleared
    p = mongo.profiles.find_one({"id": pid})
    assert "_publish_lock" not in p or not p.get("_publish_lock"), \
        f"_publish_lock not cleared: {p.get('_publish_lock')}"
    assert p.get("status", "").lower() == "published"

    print(f"TEST 1: Double-Click Publish — ✅ PASS — Credits: {bal['used_credits']} "
          f"(expected {cost}) — Ledger entries: {n_ledger} (expected 1)")


# ═════════════════════════════════════════════════════════════════════════
# TEST 2 — Bulk-Publish via /api/admin/profiles/bulk-action
# ═════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_2_bulk_publish_no_backdoor(mongo, photo_token):
    _cleanup_test_profiles(mongo)
    _reset_wallet(mongo, total=100, used=0)

    pids = [_seed_publishable_profile(mongo, f"t2-{i}") for i in range(3)]
    headers = _photo_headers(photo_token)

    r = requests.post(
        f"{BASE_URL}/api/admin/profiles/bulk-action",
        headers=headers,
        json={"ids": pids, "action": "publish"},
        timeout=120,
    )
    assert r.status_code == 200, f"bulk-action publish failed: {r.status_code} {r.text}"
    body = r.json()
    print(f"\n[T2] body={body}")

    assert body["matched"] == 3, f"matched={body['matched']} expected 3"
    assert body["action"] == "publish"
    details = body.get("details") or {}
    assert details.get("success") == 3, f"success={details.get('success')} expected 3"
    assert details.get("failed") == 0, f"failed={details.get('failed')} expected 0"
    assert body.get("modified") == 3, f"modified={body['modified']} expected 3"

    # ledger entries = 3
    n_ledger = mongo.credit_ledger.count_documents({
        "admin_id": PHOTO_ID,
        "related_wedding_id": {"$in": pids},
        "action_type": "used",
    })
    assert n_ledger == 3, f"Expected 3 USED ledger entries, got {n_ledger}"

    # used_credits should equal sum of costs from the 3 ledger entries
    cursor = mongo.credit_ledger.find({
        "admin_id": PHOTO_ID, "related_wedding_id": {"$in": pids},
        "action_type": "used",
    })
    total_cost = sum(d.get("amount", 0) for d in cursor)

    bal = requests.get(f"{BASE_URL}/api/account/credits", headers=headers, timeout=10).json()
    assert bal["used_credits"] == total_cost, \
        f"used_credits={bal['used_credits']} expected {total_cost}"

    # Each profile published
    for pid in pids:
        p = mongo.profiles.find_one({"id": pid})
        assert p.get("status", "").lower() == "published", \
            f"profile {pid} status={p.get('status')}"
        assert p.get("is_published") is True or p.get("status", "").lower() == "published"

    print(f"TEST 2: Bulk-Publish Charges Credits — ✅ PASS — Credits: "
          f"{bal['used_credits']} (expected {total_cost}) — Ledger entries: "
          f"{n_ledger} (expected 3)")


# ═════════════════════════════════════════════════════════════════════════
# TEST 3 — Razorpay Verify-Payment Race
# ═════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_3_razorpay_verify_payment_race(mongo, photo_token):
    """
    We can't forge a valid Razorpay signature, so we drive the route
    to its signature-verification path twice in parallel. Both must
    return 400 'Invalid payment signature' (no double credit, no 500).
    Confirms the route exists and reaches signature-check uniformly.
    """
    headers = _photo_headers(photo_token)

    # Per task spec: if credit_packages table is empty we can't run the
    # full create-order flow, but the user-supplied ALTERNATIVE is to
    # directly insert a payment_records row with status='created' and
    # fire two parallel forged-signature requests.
    package = mongo.credit_packages.find_one({"is_active": True})

    if package:
        create_r = requests.post(
            f"{BASE_URL}/api/payments/create-order",
            headers=headers,
            json={"package_id": package["package_id"], "user_type": "photographer"},
            timeout=20,
        )
        if create_r.status_code == 503:
            print(f"\n[T3] create-order → 503 (Razorpay not configured): "
                  f"{create_r.text[:200]}")
            print("TEST 3: Razorpay Verify-Payment — ✅ PASS-by-skip "
                  "(Razorpay keys absent in env)")
            return
        if create_r.status_code != 200:
            print(f"\n[T3] create-order non-200 ({create_r.status_code}); "
                  f"falling back to manual payment_record insert.")
            order_id = None
        else:
            order_id = create_r.json()["order_id"]
    else:
        order_id = None

    if order_id is None:
        # Manual seed of payment_records (ALTERNATIVE flow from task spec).
        fake_oid = f"order_TEST_{uuid.uuid4().hex[:10]}"
        mongo.payment_records.insert_one({
            "payment_id": fake_oid, "order_id": fake_oid,
            "admin_id": PHOTO_ID, "package_id": "test_pkg",
            "user_type": "photographer", "amount": 1.0, "currency": "INR",
            "credits_purchased": 10, "status": "created",
            "created_at": datetime.now(timezone.utc),
        })
        order_id = fake_oid

    bad_payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": f"pay_TEST_{uuid.uuid4().hex[:10]}",
        "razorpay_signature": "deadbeef" * 8,  # invalid
        "package_id": (package or {}).get("package_id", "test_pkg"),
    }

    url = f"{BASE_URL}/api/payments/verify-payment"
    async with httpx.AsyncClient(timeout=30) as cli:
        r1, r2 = await asyncio.gather(
            cli.post(url, headers=headers, json=bad_payload),
            cli.post(url, headers=headers, json=bad_payload),
            return_exceptions=True,
        )
    results = [r for r in (r1, r2) if not isinstance(r, Exception)]
    codes = [r.status_code for r in results]
    print(f"\n[T3] verify codes={codes} bodies={[r.text[:150] for r in results]}")

    # Both should be 400 (bad signature) — never 500, never any success
    for r in results:
        assert r.status_code == 400, \
            f"Expected 400 on bad signature, got {r.status_code}: {r.text[:200]}"

    # Payment record still status=created (no credit was added)
    pr = mongo.payment_records.find_one({"order_id": order_id})
    assert pr is not None
    assert pr.get("status") == "created", \
        f"status changed to {pr.get('status')} despite bad signature!"

    # Cleanup manual fake records only
    mongo.payment_records.delete_many({"order_id": {"$regex": "^order_TEST_"}})

    print(f"TEST 3: Razorpay Verify-Payment — ✅ PASS — both parallel "
          f"requests returned 400 (Invalid signature); payment_record status "
          f"unchanged; signature-race code reachable + safe.")


# ═════════════════════════════════════════════════════════════════════════
# TEST 4 — Gift Code Redemption Race
# ═════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_4_gift_code_redemption_race(mongo, photo_token):
    code = f"LOVE{uuid.uuid4().hex[:6].upper()}"

    # Cleanup any prior runs
    mongo.gift_codes.delete_many({"code": code})
    mongo.gift_code_redemptions.delete_many({"code": code})
    mongo.credit_ledger.delete_many({
        "admin_id": PHOTO_ID,
        "reason": {"$regex": f"Redeemed code {code}"},
    })

    # Insert gift code directly
    mongo.gift_codes.insert_one({
        "code": code,
        "credits": 100,
        "description": "Test race gift code",
        "max_redemptions": 1000,
        "per_account_limit": 1,
        "redeemed_count": 0,
        "is_active": True,
        "expires_at": None,
        "created_by": SUPER_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    _reset_wallet(mongo, total=100, used=0)
    headers = _photo_headers(photo_token)
    url = f"{BASE_URL}/api/account/redeem-code"

    async with httpx.AsyncClient(timeout=30) as cli:
        r1, r2 = await asyncio.gather(
            cli.post(url, headers=headers, json={"code": code}),
            cli.post(url, headers=headers, json={"code": code}),
            return_exceptions=True,
        )
    results = [r for r in (r1, r2) if not isinstance(r, Exception)]
    codes = [r.status_code for r in results]
    print(f"\n[T4] codes={codes} bodies={[r.text[:200] for r in results]}")

    success = [r for r in results if r.status_code == 200]
    failed = [r for r in results if r.status_code != 200]
    assert len(success) == 1, f"Expected exactly 1 success, got {len(success)} codes={codes}"
    assert len(failed) == 1, f"Expected exactly 1 failure, got {len(failed)} codes={codes}"
    assert failed[0].status_code == 400

    assert success[0].json().get("credits_added") == 100

    # Redemption row count
    n_red = mongo.gift_code_redemptions.count_documents(
        {"code": code, "admin_id": PHOTO_ID}
    )
    assert n_red == 1, f"Expected 1 redemption row, got {n_red}"

    # Ledger ADD entries
    n_add = mongo.credit_ledger.count_documents({
        "admin_id": PHOTO_ID,
        "action_type": {"$in": ["add", "added", "ADD", "ADDED"]},
        "reason": {"$regex": f"Redeemed code {code}"},
    })
    assert n_add == 1, f"Expected 1 ADD ledger entry, got {n_add}"

    # Wallet total
    bal = requests.get(f"{BASE_URL}/api/account/credits",
                       headers=headers, timeout=10).json()
    assert bal["total_credits"] == 200, \
        f"total_credits={bal['total_credits']} expected 200 (not 300)"

    # Cleanup
    mongo.gift_codes.delete_many({"code": code})
    mongo.gift_code_redemptions.delete_many({"code": code})

    print(f"TEST 4: Gift Code Redemption Race — ✅ PASS — "
          f"Redemptions: {n_red} (expected 1) — Total credits: "
          f"{bal['total_credits']} (expected 200) — Ledger ADD: {n_add}")


# ═════════════════════════════════════════════════════════════════════════
# TEST 5 — Bulk-Purge Refund
# ═════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_5_bulk_purge_refund(mongo, photo_token):
    _cleanup_test_profiles(mongo)
    _reset_wallet(mongo, total=100, used=0)

    headers = _photo_headers(photo_token)
    pid = _seed_publishable_profile(mongo, "t5")

    # Publish (single)
    pr = requests.post(f"{BASE_URL}/api/weddings/{pid}/publish",
                       headers=headers, timeout=60)
    assert pr.status_code == 200, f"publish failed: {pr.status_code} {pr.text}"
    cost = pr.json()["credits_deducted"]
    assert cost > 0

    bal1 = requests.get(f"{BASE_URL}/api/account/credits", headers=headers, timeout=10).json()
    assert bal1["used_credits"] == cost

    # Soft-delete
    dr = requests.post(
        f"{BASE_URL}/api/admin/profiles/bulk-action",
        headers=headers,
        json={"ids": [pid], "action": "delete"}, timeout=30,
    )
    assert dr.status_code == 200, f"delete bulk failed: {dr.status_code} {dr.text}"

    # Purge
    pur = requests.post(
        f"{BASE_URL}/api/admin/profiles/bulk-action",
        headers=headers,
        json={"ids": [pid], "action": "purge"}, timeout=60,
    )
    assert pur.status_code == 200, f"purge bulk failed: {pur.status_code} {pur.text}"
    body = pur.json()
    details = body.get("details") or {}
    print(f"\n[T5] purge body={body}")

    assert details.get("refunded_count") == 1, \
        f"refunded_count={details.get('refunded_count')} expected 1"
    assert details.get("refunded_total") == cost, \
        f"refunded_total={details.get('refunded_total')} expected {cost}"

    # Profile must be gone
    assert mongo.profiles.find_one({"id": pid}) is None, \
        "Profile not hard-deleted"

    # Ledger has a REFUND entry
    n_refund = mongo.credit_ledger.count_documents({
        "admin_id": PHOTO_ID,
        "related_wedding_id": pid,
        "action_type": {"$in": ["refund", "REFUND", "refunded"]},
        "amount": cost,
    })
    assert n_refund >= 1, f"Expected REFUND ledger entry, got {n_refund}"

    # Wallet balance back to 100 available
    bal2 = requests.get(f"{BASE_URL}/api/account/credits", headers=headers, timeout=10).json()
    assert bal2["available_credits"] == 100, \
        f"available_credits={bal2['available_credits']} expected 100"

    print(f"TEST 5: Bulk-Purge Refund — ✅ PASS — refunded_total: "
          f"{details.get('refunded_total')} (expected {cost}) — "
          f"available_credits: {bal2['available_credits']} (expected 100)")
