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
  - **Live Photo QR Code** — sample QR + 4-step "scan, tap, pick, watch" guide; QR points back at the current preview URL; "Copy invitation link" button
  - **AI Face Matching** demo — interactive "Try demo scan" button with a sweeping laser line over a sample selfie, then renders 8 matched photo thumbnails and a "Reset demo" link
  - **[Updated 10 Jun 2026 — UI parity with wedding]** Both sections rewritten to mirror the wedding `LIVE PHOTO WALL` / `FIND MY PHOTOS` panels in `DesignFullPreview.jsx` exactly: shared `Panel` (dark `#1A130B` rounded card with blur + accent border) + `Eyebrow` (◆ LIVE PHOTO WALL / ◆ AI-POWERED PHOTO SEARCH) + `SectionHeading` (Cormorant Garamond serif with "live." / "your photos" rendered in Great Vibes italic accent colour) + short muted description + accent-coloured pill `PillButton` (VIEW LIVE WALL / FIND MY PHOTOS). The demo selfie scanner and QR grid were removed in favour of the simpler wedding presentation.
  - **Cinematic closing** (`CelebrationClosing`) — in-flow reverse Ken-Burns on the design image + falling accent-colored petals + new copy "**Your presence is enough for us. Thank you.**" + celebrant signature with glow animation + date · venue strapline
  - **Footer** with celebrant signature + "Crafted with reverence · MAJA Creations"
- [10 Jun 2026] **Photo bubble centering fix** — outer absolute wrapper does the `left:50% + translateX(-50%)` math; the framer-motion child only animates scale/opacity, so transform never gets overridden. Confirmed via DOM probe: cardCenter=960, bubbleCenter=960.
- [10 Jun 2026] **Live Photo Wall + AI Face Match wired end-to-end for non-wedding invitations** (matches wedding logic 1:1)
  - **Backend** (`live_gallery_features.py`): Added 3 user-auth'd routes that mirror the admin/photographer ones, scoped to the invitation owner via JWT user_id check:
    - `POST /api/users/profiles/{profile_id}/live-gallery/upload`  (multipart, broadcasts WebSocket `photo_added`)
    - `GET  /api/users/profiles/{profile_id}/live-gallery/photos`
    - `DELETE /api/users/profiles/{profile_id}/live-gallery/{photo_id}`
  - **`UserDashboard.jsx`**: Each invitation card now has a **📸 Manage Live Photos** button below View/Copy-Link that opens the new route.
  - **`UserLiveGalleryManagement.jsx`** (new — `/user/profile/:profileId/live-gallery`): drag-and-drop dropzone (3 parallel uploads, per-file progress bar), 4 stat tiles (Photos / By you / By guests / Storage), live photo grid (hover-to-delete), and a deep link to the public invitation page.
  - **`CelebrationPublicView.jsx`** (non-wedding public invite): new `LivePhotoWallSection` near the closing:
    - Pulls `/api/public/gallery/{slug}/photos` for first paint, then subscribes to `/ws/gallery/{wedding_id}` for live `photo_added` / `photo_deleted` events — same WebSocket the wedding viewer uses.
    - Renders the last 12 photos in a grid.
    - **Two side-by-side guest CTAs**:
      - **Scan QR** → modal with QR pointing at the public invitation URL (uses `api.qrserver.com`, themed with category accent).
      - **Get my photos** → opens existing `FindMyPhotosModal` (gallery passkey → selfie upload → AI face match → 99 %+ matches with download).
    - Floating **`GuestUploadButton`** on the page so guests can also post their own shots to the wall.
  - All endpoints already category-agnostic; no schema changes needed.
- [10 Jun 2026] **Server.py:** moved `build_live_gallery_router` call to AFTER `build_user_auth_router` so `get_current_public_user` is in scope when constructing the user-side routes.

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
