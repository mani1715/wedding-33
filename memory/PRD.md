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
