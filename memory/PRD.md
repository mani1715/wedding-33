# PRD — Wedding/Celebration Invitation Platform (wedding-31 fork)

## Original Problem Statement
Clone the `mani1715/wedding-31` repository and fix a large set of architectural & logic flow mistakes documented in a 30-bug frontend audit and a 14-bug backend audit. Phased execution:
- **Batch A — Financial Safety** (CRITICAL, blocking) — race conditions and financial integrity.
- **Batch B — Data Integrity** (HIGH) — refunds on single delete, S3 cleanup, slug uniqueness, auto-purge job.
- **Batch C — Security & UX** (MEDIUM) — JWT blacklist + logout, rate limit, OG tags, CSRF.
- **Frontend 30-bug audit** — localStorage key mismatches, edit routes, missing auth guards, feature_flags persistence.

## Tech Stack
- React (CRA + Craco), TailwindCSS, Shadcn/UI
- FastAPI, Motor (async MongoDB driver), MongoDB
- Razorpay (credits purchase), AWS S3 (media), Gemini (AI translation via Emergent LLM Key)

## Architecture
```
/app/
├── backend/
│   ├── server.py (boot + index init)
│   ├── admin_dashboard_v2.py (bulk actions, quick-edit)
│   ├── wedding_lifecycle_service.py (publish atomicity)
│   ├── razorpay_credit_service.py (verify atomicity)
│   ├── gift_code_routes.py (reserve-first redemption)
│   ├── credit_service.py
│   ├── aws_service.py
│   └── tests/test_batch_a_race_safety.py
├── frontend/src/{pages, components, context}
└── memory/{PRD.md, test_credentials.md}
```

## Database Schema (key collections)
- `profiles`: { id, admin_id, slug, status, deleted_at, total_credit_cost, sections_enabled, _publish_lock }
- `admins`: { id, role, total_credits, used_credits, phone_verified }
- `payment_records`: { order_id, admin_id, status, razorpay_payment_id (unique sparse), credits_purchased }
- `gift_code_redemptions`: { id, code, admin_id, credits, ledger_id } — unique compound index (code, admin_id)
- `gift_codes`: { code, credits, per_account_limit, max_uses, status }
- `credit_ledger`: { admin_id, action_type ('used'|'add'|'refund'), amount, balance_before, balance_after, related_wedding_id }

## Test Credentials
See `/app/memory/test_credentials.md`:
- Super Admin: `mani_8328@majacreations.com` / `Maneesh@1234`
- Test Photographer: `testphoto@test.com` / `TestPass123!`

## Changelog

### 2026-02 — Batch A Financial Safety — ✅ COMPLETE & VERIFIED
- Created unique DB indexes (`payment_records.razorpay_payment_id`, `gift_code_redemptions.(code, admin_id)`).
- Closed bulk-publish "free publish" backdoor — routes through `wedding_lifecycle_service.publish_wedding`.
- Added bulk-purge refund logic + S3 cleanup (best-effort).
- Rewrote `publish_wedding` with two-tier atomic protection: `_publish_lock` claim + `used_credits` $inc guard.
- Made Razorpay verify-payment atomic via `find_one_and_update` (status: created → paid).
- Refactored gift code redemption to reserve-first pattern.
- **Stress test results (iteration_1.json): ALL 5/5 PASS** — no double-charging, no free publishes, no double-credits.

## Roadmap

### P0 — Batch B (Data Integrity) — NEXT
- Single-profile permanent delete: add refund + S3 cleanup (mirror bulk-purge).
- Slug uniqueness: exclude `deleted_at` profiles from query.
- APScheduler daily 30-day auto-purge of soft-deleted profiles.

### P1 — Frontend 30-Bug Audit
- `localStorage` key consistency: `adminToken` → `admin_token` in QR/Wishes/Greetings management.
- Celebration edit routes: append `?category=`.
- ThemeSettingsPage: fix backend URL.
- `feature_flags` state must merge into `sections_enabled` before save in `LuxuryProfileForm`.
- Add auth guards on sub-pages.

### P2 — Batch C (Security & UX)
- JWT blacklist via MongoDB TTL collection + `/api/auth/logout`.
- Rate-limit `/api/invite/{slug}` (60/IP/hour).
- Fix Open Graph meta-tags via server-side User-Agent intercept.
- CSRF: `SameSite=Strict` on user cookies + Origin check.

### Future / Backlog
- Migrate purge S3 deletion to background task.
- Seed `db.credit_packages` for full Razorpay e2e tests.
- Refactor backend into `/app/backend/{routes, models, services, tests}`.

## Open Items
- Frontend was FATAL on session start (missing `node_modules`); reinstalled via `yarn install`.
- Stale `REACT_APP_BACKEND_URL` in `frontend/.env` updated to current preview URL.
