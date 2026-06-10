/**
 * Step definitions for the floating "How to create your wedding link" tour.
 *
 * Two presets:
 *   - HOMEPAGE_USER_STEPS — for couples landing on the public site (`/`)
 *   - PHOTOGRAPHER_STEPS  — for photographers inside the admin dashboard
 *
 * `target` is a CSS selector resolved at runtime. When a step has no
 * target (or the element isn't found) the card centers on screen and the
 * spotlight is suppressed.
 */

export const HOMEPAGE_USER_STEPS = [
  {
    title: 'Pick a theme',
    body: 'Start by scrolling to the 10 cinematic themes below. Each is a complete look — palette, fonts, animations — built for one Indian wedding culture.',
    target: '[data-testid="themes-grid"]',
    badge: 'Browse',
  },
  {
    title: 'Buy your theme',
    body: 'Tap "Buy theme" on the card you love. Themes are paid in credits — top up later from your wallet.',
    target: '[data-testid^="theme-buy-btn-"]',
    badge: 'Purchase',
  },
  {
    title: 'Choose an event',
    body: 'After purchase you\'ll pick which event this link is for — Marriage, Reception, Engagement and more. One link per event.',
    badge: 'Event',
  },
  {
    title: 'Choose your favourite design',
    body: 'Every theme ships with 3 photo-designs per event. Click any design card to open the full rich preview with photos, story, RSVP and more.',
    badge: 'Design',
  },
  {
    title: 'Fill in your details',
    body: 'Add your names, dates, venue, photos and event info. Drafts are free — credits are only spent when you publish.',
    badge: 'Edit',
  },
  {
    title: 'Pick a link expiry',
    body: 'Decide how long the public link stays alive — 6 months, 1 year, even lifetime. Each tier costs different credits.',
    badge: 'Expiry',
  },
  {
    title: 'Publish & share',
    body: 'One tap to publish. Share the link on WhatsApp, Instagram and SMS. Guests can RSVP, send shagun, request songs and check-in.',
    badge: 'Live',
  },
];

export const PHOTOGRAPHER_STEPS = [
  {
    title: 'Step 1 — Top up your credits',
    body: 'Click the "Credits" pill at the top-right to buy a pack. Drafts cost nothing — credits are only spent when you publish a paid link. As you climb the loyalty ladder (Pro / Elite / Partner) packs auto-discount and you earn bonus credits.',
    target: '[data-testid="dashboard-credits-pill"]',
    badge: '1 · Wallet',
  },
  {
    title: 'Step 2 — Create a new wedding',
    body: 'Click "Create Wedding" to open the luxury wizard. Don\'t worry — nothing is charged until you publish.',
    target: '[data-testid="dashboard-create-wedding"]',
    badge: '2 · Create',
  },
  {
    title: 'Step 3 — Pick the ceremony',
    body: 'Inside the wizard the first card is "Event" — pick Marriage, Reception, Sangeet, Haldi, Mehendi or Engagement. Each event tunes the photo slots and design defaults.',
    badge: '3 · Event',
  },
  {
    title: 'Step 4 — Fill couple details + photos',
    body: 'Add the bride/groom names, wedding date, venue and upload couple/bride/groom photos. The green ✓ next to each photo slot means it will appear on the public invitation.',
    badge: '4 · Couple',
  },
  {
    title: 'Step 5 — Choose theme & design',
    body: 'Open the "Theme" step. You\'ll first see all 10 cultural themes — pick one, then 3 designs unlock for that theme. Click "Preview" to open the full invitation in a NEW TAB (your draft stays safe).',
    badge: '5 · Theme',
  },
  {
    title: 'Step 6 — Tune the features',
    body: 'Toggle premium add-ons (RSVP, gallery, AI story, multi-language). Every toggle updates the live credit total at the bottom of the Publish step in real-time.',
    badge: '6 · Features',
  },
  {
    title: 'Step 7 — Publish & share',
    body: 'On the Publish step you\'ll see the auto-calculated total ("Publish Now · 7 credits"). Tap it — credits deduct atomically, your paid-links count goes up, and a public share link is generated. Copy and send it to your couple.',
    target: '[data-testid="publish-btn"]',
    badge: '7 · Publish',
  },
];
