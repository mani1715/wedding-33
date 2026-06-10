# PRD — MAJA Creations (Wedding Invitation Platform)

## Original Problem Statement
> https://github.com/mani1715/wedding-28
> Clone the repo and develop the full web. After seeing the full preview, the user will request changes.

## Goal (Current Session)
- Clone the GitHub repo into /app
- Install backend (Python/FastAPI) + frontend (React/CRACO) deps
- Bring the site up on the preview URL so the user can review it
- No new features, integrations, or design changes (per user instructions)

## Tech Stack (from repo)
- Backend: FastAPI, MongoDB (motor), JWT/passlib/bcrypt, Razorpay, Twilio, AWS S3, Gemini, emergentintegrations
- Frontend: React 19, CRACO, Tailwind, Radix UI, framer-motion, three.js, react-router-dom v7
- Domain: Multi-event invitation SaaS (weddings, baby birthdays, half saree, puberty, dhoti ceremonies) with photographer/credit/pricing/admin modules.

## What's Been Implemented (this session)
- [10 Jun 2026] Cloned `mani1715/wedding-28` into /app
- [10 Jun 2026] Installed Python deps from backend/requirements.txt (bleach, twilio, razorpay, etc. resolved)
- [10 Jun 2026] Installed frontend deps via yarn
- [10 Jun 2026] Updated `frontend/.env` REACT_APP_BACKEND_URL to the current container preview URL
- [10 Jun 2026] supervisor restarted: backend + frontend RUNNING
- [10 Jun 2026] Verified landing page loads: "MAJA Creations — Cinematic invitations for every celebration"
- [10 Jun 2026] **Full preview redesign — matches wedding layout exactly** — Rewrote `/app/frontend/src/pages/CelebrationInvitationPreview.jsx`:
  - Full-bleed blurred design image as fixed page background (SoftDesignBackdrop pattern, copied from `DesignFullPreview.jsx`)
  - Centered "poster" invitation card with eyebrow + circular celebrant photo bubble + bottom cream/tinted panel containing family line + big serif celebrant name + nickname + date + venue + parents — visually identical pattern to wedding's `UniversalDesignRenderer` hero
  - Top bar: ← Designs · "PREVIEW · {Category}" · USE THIS DESIGN
  - Below hero: Our Story section, Cherished Photos gallery (3 sample photos per category), Closing Blessing section, sticky bottom CTA
  - Verified visually for baby_birthday, half_saree, puberty, dhoti
- [10 Jun 2026] **Feature parity with wedding live invitation** — added the full guest experience:
  - **Opening animation** (`CelebrationOpening`) — full-screen 2.5 s cinematic zoom-in over the design backdrop with eyebrow + celebrant name + nickname + date; plays once per session per category (sessionStorage key `celeb_open_seen_*`)
  - **Live countdown** (D / H / M / S) until the celebration date, ticking via `useSyncExternalStore` (React-19 strict-purity-safe)
  - **Event details** card pair (Date + Time, Venue with Google Maps deep link)
  - **RSVP form** (name, guest count, attending toggle, optional note, animated confirmation — preview mode, no API write)
  - **Blessings & Wishes Wall** with 3 sample wishes + "add yours" form (in-memory in preview)
  - **Cinematic closing** (`CelebrationClosing`) — in-flow reverse Ken-Burns on the design image + falling accent-colored petals + "WITH ALL OUR LOVE · Thank you for visiting. · — Celebrant —" overlay
  - **Footer** with celebrant signature + "Crafted with reverence · MAJA Creations"

## Known Things to Be Aware Of
- Backend has `security_middleware` that blocks bot user-agents (curl etc.) on `/api/` root. Browser/frontend access works fine.
- Pricing/credit/admin seeders run on backend startup (idempotent inserts logged).
- Auth/Admin credentials: NOT created by us; whatever the repo's own seed scripts (init_admin / init_super_admin) generate is in effect.

## Next Action Items (await user direction)
- User will preview the live site and tell us which changes they want.

## Backlog (deferred / unknown until user decides)
- Any UX/visual changes
- Any new features or integrations
- Content (couple names, dates, venue, photos)
- Auth seeding / admin credential reset
