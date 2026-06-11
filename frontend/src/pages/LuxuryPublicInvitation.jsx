import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import axios from 'axios';
import { Calendar, MapPin, Send, Heart, MessageCircle, Clock, Sparkles, Lock } from 'lucide-react';
import WaxSealOpening from '@/components/luxury/WaxSealOpening';
import { OpeningOrchestrator, ClosingOrchestrator } from '@/themes/shared/ThemeAnimationOrchestrator';
import PetalConfetti from '@/components/luxury/PetalConfetti';
import AmbientMusicPlayer from '@/components/luxury/AmbientMusicPlayer';
import WatermarkOverlay from '@/components/luxury/WatermarkOverlay';
import MandalaLoader from '@/components/luxury/MandalaLoader';
import ScrollSection from '@/components/luxury/ScrollSection';
import DigitalShagunSection from '@/components/luxury/DigitalShagunSection';
import TravelLinksSection from '@/components/luxury/TravelLinksSection';
import VenuesSection from '@/components/luxury/VenuesSection';
import GiftRegistrySection from '@/components/luxury/GiftRegistrySection';
import LivePhotoWallTeaser from '@/components/luxury/LivePhotoWallTeaser';
import GuestUploadButton from '@/components/luxury/GuestUploadButton';
import WishesWallSection from '@/components/luxury/WishesWallSection';
import FindMyPhotosModal from '@/components/luxury/FindMyPhotosModal';
import FindMyRoomSection from '@/components/luxury/FindMyRoomSection';
import PreWeddingSection from '@/components/luxury/PreWeddingSection';
import MajaReferralCTA from '@/components/luxury/MajaReferralCTA';
import PersonalizedWelcome from '@/components/luxury/PersonalizedWelcome';
import HoneymoonFundSection from '@/components/luxury/HoneymoonFundSection';
import AddToCalendarButton from '@/components/luxury/AddToCalendarButton';
import LiveStreamSection from '@/components/luxury/LiveStreamSection';
import LiveTimelineSection from '@/components/luxury/LiveTimelineSection';
import SongRequestSection from '@/components/luxury/SongRequestSection';
import CheckInSection from '@/components/luxury/CheckInSection';
import DressCodeSection from '@/components/luxury/DressCodeSection';
import { getThemeById } from '@/themes/masterThemes';
import { resolveDesign, resolveHeroDesign, findDesignById, normaliseEvent, pageBgForDesign } from '@/themes/themeDesignResolver';
import UniversalDesignRenderer from '@/themes/UniversalDesignRenderer';
import SmartImage from '@/components/perf/SmartImage';
import ThemeAnimatedBackground from '@/components/ThemeAnimatedBackground';
import { InvitePrefetchContext } from '@/context/InvitePrefetchContext';
import CelebrationPublicView from '@/components/luxury/CelebrationPublicView';
import '@/styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const LuxuryPublicInvitation = () => {
  // BUG H FIX: the per-event share link is /invite/:slug/:eventType (the QR
  // codes on event invitation cards point here). Previously the component
  // ignored `eventType` entirely, so scanning a Reception-specific QR opened
  // the full wedding invitation with no acknowledgement of the event. We now
  // read the param and, after the invitation finishes loading, scroll the
  // matching event section into view so the guest lands on the right
  // ceremony details. The other sections remain accessible by scrolling so
  // we don't break the full-invitation reading experience.
  const { slug, eventType } = useParams();
  const [searchParams] = useSearchParams();
  const guestToken = searchParams.get('g');
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [passcode, setPasscode] = useState('');
  const [requirePasscode, setRequirePasscode] = useState(false);
  const [rsvpDone, setRsvpDone] = useState(false);
  const [wishDone, setWishDone] = useState(false);
  const [galleryInfo, setGalleryInfo] = useState(null);
  const [prefetch, setPrefetch] = useState(null); // batched side-data
  const [findOpen, setFindOpen] = useState(false);
  const [selectedLang, setSelectedLang] = useState('');
  const footerRef = useRef(null);

  useEffect(() => {
    // Apply light theme for invitation pages - remove dark overlays
    document.body.classList.add('luxe');
    document.body.classList.remove('luxe-grain', 'luxe-vignette');
    // Add light background
    document.body.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)';
    return () => {
      document.body.classList.remove('luxe');
      document.body.style.background = '';
    };
  }, []);

  useEffect(() => { fetchInvite(); /* eslint-disable-next-line */ }, [slug]);

  // NOTE: galleryInfo is now populated by the batched /full endpoint below.
  // We keep this as a fallback in case /full failed (e.g. older backend deploy).
  useEffect(() => {
    if (!slug) return;
    if (galleryInfo !== null) return; // already loaded via /full
    if (prefetch?.slug === slug) return;
    const t = setTimeout(() => {
      axios.get(`${API_URL}/api/public/gallery/${slug}/info`)
        .then((r) => setGalleryInfo(r.data))
        .catch(() => setGalleryInfo(null));
    }, 800); // delay so /full has time to land first
    return () => clearTimeout(t);
  }, [slug, galleryInfo, prefetch]);

  const fetchInvite = async (code = null) => {
    setLoading(true); setError('');
    try {
      // Mobile-perf: prefer the batched /full endpoint — one round trip instead
      // of 8+. Falls back to the legacy /invite/{slug} if /full is unavailable
      // (e.g. older backend deploy, passcode-protected invitation, etc.).
      if (!code) {
        try {
          const full = await axios.get(`${API_URL}/api/invite/${slug}/full`);
          const fd = full.data || {};
          if (fd.invite) {
            setData(fd.invite);
            setGalleryInfo(fd.gallery_info || null);
            setPrefetch({
              slug,
              wishes:        fd.wishes        || [],
              gifts:         fd.gifts         || null,
              blessings:     fd.blessings     || { total_count: 0, recent: [] },
              gallery_info:  fd.gallery_info  || null,
              shagun_enabled: !!fd.shagun_enabled,
              shagun:        fd.shagun        || null,
              venues:        fd.venues        || null,
              travel:        fd.travel        || null,
              referral_code: fd.referral_code || null,
            });
            setRequirePasscode(false);
            return;
          }
        } catch (eFull) {
          if (eFull.response?.status === 401 || eFull.response?.status === 403) {
            setRequirePasscode(true);
            return;
          }
          if (eFull.response?.status === 404) {
            setError('This invitation could not be found.');
            return;
          }
          if (eFull.response?.status === 410) {
            setError('This invitation has expired.');
            return;
          }
          // soft-fail → fall through to legacy single endpoint
        }
      }
      const url = `${API_URL}/api/invite/${slug}${code ? `?passcode=${encodeURIComponent(code)}` : ''}`;
      const res = await axios.get(url);
      setData(res.data);
      setRequirePasscode(false);
    } catch (e) {
      if (e.response?.status === 401 || e.response?.status === 403) {
        setRequirePasscode(true);
      } else if (e.response?.status === 404) {
        setError('This invitation could not be found.');
      } else if (e.response?.status === 410) {
        setError('This invitation has expired.');
      } else {
        setError(e.response?.data?.detail || 'Failed to load invitation.');
      }
    } finally { setLoading(false); }
  };

  // BUG H FIX: when the URL includes /:eventType (per-event QR scan),
  // scroll the matching event card into view a beat after the invitation
  // finishes loading. We look for a section / element marked with either
  // `data-event-type` or the standard `testid="section-event-{type}"`
  // pattern. Fail silently if no match exists (the invitation may not have
  // events that match a stale QR).
  useEffect(() => {
    if (!eventType || !data || loading) return;
    const norm = String(eventType).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const target = setTimeout(() => {
      const el =
        document.querySelector(`[data-event-type="${norm}"]`) ||
        document.querySelector(`[data-testid="section-event-${norm}"]`) ||
        document.querySelector(`[data-testid="event-${norm}"]`) ||
        document.getElementById(`event-${norm}`);
      if (el && typeof el.scrollIntoView === 'function') {
        try { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_e) {}
      }
    }, 900); // wait for hero / opening to settle
    return () => clearTimeout(target);
  }, [eventType, data, loading]);

  // Prompt 02 — Cinematic opening hooks (must be called unconditionally)
  // Opening animation is automatically skipped on:
  //   1. ?skip_intro=1 query string (dev/testing)
  //   2. ANY mobile/tablet viewport (<1024 px) — the cinematic Three.js
  //      opening was the #1 cause of "page freezes after open" on phones
  //   3. Users with `prefers-reduced-motion: reduce`
  // On desktop it still plays in full.
  const [openingDone, setOpeningDone] = useState(() => {
    if (typeof window === 'undefined') return false;
    if (searchParams.get('skip_intro') === '1') return true;
    const isMobileLike = window.matchMedia('(max-width: 1023px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return isMobileLike || reduced;
  });

  // SAFETY: tighter safety net so guests on slow networks aren't trapped
  // behind a frozen splash. Was 6 s — dropped to 3 s.
  useEffect(() => {
    if (openingDone) return;
    const id = setTimeout(() => setOpeningDone(true), 3000);
    return () => clearTimeout(id);
  }, [openingDone]);
  const formattedDate = React.useMemo(() => {
    if (!data?.event_date) return '';
    try {
      return new Date(data.event_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    } catch (_) { return ''; }
  }, [data?.event_date]);

  if (loading) {
    return <div className="luxe min-h-screen grid place-items-center"><MandalaLoader label="Opening invitation" /></div>;
  }

  if (requirePasscode) {
    return (
      <div className="luxe min-h-screen grid place-items-center px-6">
        <form onSubmit={(e) => { e.preventDefault(); fetchInvite(passcode); }}
          className="lux-glass p-10 max-w-md w-full text-center" data-testid="passcode-form">
          <div className="w-14 h-14 rounded-full grid place-items-center mx-auto mb-5"
            style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}>
            <Lock className="w-5 h-5" style={{ color: '#16110C' }} />
          </div>
          <span className="lux-eyebrow block mb-3">◆ Private Invitation</span>
          <h2 className="font-display text-3xl mb-2" style={{ color: '#FFF8DC' }}>Passcode required</h2>
          <p className="text-sm mb-5" style={{ color: 'rgba(255,248,220,0.6)' }}>This invitation is locked. Please enter the passcode shared with you.</p>
          <input type="text" value={passcode} onChange={(e) => setPasscode(e.target.value)} required
            placeholder="••••••" className="w-full px-4 py-3 rounded-lg bg-transparent text-center tracking-[0.4em] outline-none mb-4"
            style={{ color: '#FFF8DC', border: '1px solid var(--lux-border)' }} data-testid="passcode-input" />
          <button type="submit" className="lux-btn w-full justify-center" data-testid="passcode-submit">Unlock</button>
        </form>
      </div>
    );
  }

  if (error) {
    return (
      <div className="luxe min-h-screen grid place-items-center px-6">
        <div className="lux-glass p-10 max-w-md text-center" data-testid="invite-error">
          <h2 className="font-display text-3xl mb-3" style={{ color: '#FFF8DC' }}>Oh dear.</h2>
          <p className="text-sm mb-6" style={{ color: 'rgba(255,248,220,0.65)' }}>{error}</p>
          <button onClick={() => navigate('/')} className="lux-btn lux-btn-ghost">Back to studio</button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ── 2026 — Universal Invitations: route non-wedding categories to a
  // dedicated, category-aware viewer. The wedding flow below is preserved
  // 100% intact.
  if (data.invitation_category && data.invitation_category !== 'wedding') {
    return (
      <InvitePrefetchContext.Provider value={prefetch}>
        <CelebrationPublicView data={data} />
      </InvitePrefetchContext.Provider>
    );
  }

  // Backend returns FLAT InvitationPublicView (not wrapped in `profile`)
  const themeId = data.design_id || data.design_theme || 'royal_mughal';
  const theme = getThemeById(themeId);
  const bride = data.bride_name || 'Bride';
  const groom = data.groom_name || 'Groom';
  const monogram = `${(bride[0] || 'A').toUpperCase()} & ${(groom[0] || 'B').toUpperCase()}`;
  const weddingDate = data.event_date ? new Date(data.event_date) : null;
  // Merge backend-validated events with the form's extended events (which
  // carry the per-event visibility flag, hero photo, etc., persisted under
  // custom_text._maja). Filter out any ceremony explicitly disabled by the
  // photographer so guests never see ceremonies marked off.
  let events = data.events || [];
  try {
    const majaRaw = data.custom_text?._maja?.events_extended;
    if (majaRaw) {
      const ext = typeof majaRaw === 'string' ? JSON.parse(majaRaw) : majaRaw;
      if (Array.isArray(ext) && ext.length > 0) events = ext;
    }
  } catch (_) { /* ignore parse errors, keep backend events */ }
  events = events.filter((e) => e?.visible !== false);
  const greetings = (data.greetings || []).slice(0, 8);
  const planType = data.plan_type || 'FREE';
  const watermark = planType === 'FREE';
  const musicUrl = data.background_music?.file_url || data.background_music?.url || '';

  // ── Multi-language: pull translations + render language picker.
  // `data.translations` is { language_code: { field: translatedText } }.
  // We default to the data's primary language (or the first available
  // translation) and let the user toggle.  Each translated text falls
  // back to the original (English) value when missing.
  const availableLangs = Object.keys(data.translations || {});
  const baseLang = (data.language && data.language[0]) || 'english';
  const allLangs = Array.from(new Set([baseLang, ...availableLangs]));
  const activeLang = selectedLang || baseLang;
  const tr = (fieldName, fallback) => {
    if (activeLang === baseLang) return fallback;
    const t = data.translations?.[activeLang]?.[fieldName];
    return t || fallback;
  };

  const venueText = tr('venue', data.venue || '');
  const venueAddress = tr('city', data.city || '');
  const story = tr('love_story', data.love_story || data.story || '');
  const brideAbout = tr('bride_about', data.bride_about || '');
  const groomAbout = tr('groom_about', data.groom_about || '');
  const guestRooms = Array.isArray(data.guest_rooms) ? data.guest_rooms : [];
  const preWeddingLinks = Array.isArray(data.pre_wedding_links) ? data.pre_wedding_links : [];
  const resolveUrl = (u) => {
    if (!u) return '';
    if (u.startsWith('data:')) return u;
    // Use the universal media-url helper so /uploads/... gets rewritten to
    // /api/uploads/... — without that, the K8s ingress sends the request
    // to the React SPA instead of the FastAPI service and the browser
    // gets back index.html (broken image icon).
    if (u.startsWith('http')) {
      return u.replace(/(https?:\/\/[^/]+)\/uploads\//i, `$1/api/uploads/`);
    }
    const path = u.startsWith('/uploads/') ? `/api${u}` : u;
    return `${API_URL}${path}`;
  };
  // Per-photo enable/disable toggles (Feb 2026). Default true for legacy
  // profiles. When false, the photo isn't rendered even if a URL exists —
  // toggling back on restores the saved URL without a re-upload.
  const showBride  = data.show_bride_photo  !== false;
  const showGroom  = data.show_groom_photo  !== false;
  const showCouple = data.show_couple_photo !== false;
  const bridePhoto  = showBride  ? resolveUrl(data.bride_photo_url || '') : '';
  const groomPhoto  = showGroom  ? resolveUrl(data.groom_photo_url || '') : '';
  const couplePhoto = showCouple ? resolveUrl(
    data.couple_photo_url
      || (data.cover_photo_id ? `/api/media/${data.cover_photo_id}` : '')
      || ''
  ) : '';

  // Resolve the marquee invitation design + per-event designs from the catalogue.
  // design_selections (optional, populated by photographer in profile form) is a
  // map of event → designId (P0 Task 2 will expose this picker in the form).
  const designSelections = data.design_selections || {};
  const heroResolved = resolveHeroDesign(themeId, designSelections);
  const resolvedPerEvent = (events || []).map((evt) => {
    const evtKey = normaliseEvent(evt.event_type || evt.type);
    const sel = designSelections[evtKey];
    if (sel) {
      const found = findDesignById(themeId, sel);
      if (found) return { evt, ...found };
    }
    const r = resolveDesign(themeId, evtKey, 0);
    return r ? { evt, ...r } : { evt, theme: null, design: null, event: evtKey };
  });

  /* Resolve the opening (link-open) background photo with sensible fallbacks.
   * Priority:
   *   1. opening_photo_url (custom upload OR resolved bride/groom/couple URL)
   *   2. couple_photo_url
   *   3. cover photo
   *   4. hero design image (last resort)
   */
  const openingBgUrl = resolveUrl(
    data.opening_photo_url
      || data.couple_photo_url
      || (data.cover_photo_id ? `/api/media/${data.cover_photo_id}` : '')
      || ''
  );

  // Determine primary event type for opening/closing animations
  // (the main public invitation defaults to the wedding "marriage" event;
  // per-event invitation routes can override via ?event= in future)
  const primaryEventType = (() => {
    if (data.primary_event_type) return data.primary_event_type;
    const marriageEvt = (events || []).find((e) => normaliseEvent(e.event_type || e.type) === 'marriage');
    if (marriageEvt) return 'marriage';
    if (events && events[0]) return normaliseEvent(events[0].event_type || events[0].type);
    return 'marriage';
  })();

  return (
    <InvitePrefetchContext.Provider value={prefetch}>
      <>
      {/* 3D Theme-Based Animated Background - ONLY for invitation pages */}
      <ThemeAnimatedBackground theme={themeId || 'temple'} />
      
      {/* Universal opening (Feb 2026) — single 2.5 s zoom-in over the
          couple's chosen opening photo with bride & groom names. Replaces
          all previous per-theme 3D openings. */}
      {!openingDone && (
        <OpeningOrchestrator
          themeId={themeId}
          eventType={primaryEventType}
          image={heroResolved?.design?.image}
          openingImage={openingBgUrl}
          couplePhoto={couplePhoto}
          bride={bride}
          groom={groom}
          date={formattedDate}
          monogram={monogram}
          onComplete={() => setOpeningDone(true)}
        />
      )}

      <div className="luxe min-h-screen relative" data-testid="public-invitation"
        style={{
          opacity: openingDone ? 1 : 0,
          transition: 'opacity 0.55s ease',
          pointerEvents: openingDone ? 'auto' : 'none',
          background: 'transparent',
        }}>
        {/* 2026 — Universal Invitation Category banner.
            Surfaces the invitation type (Baby Birthday / Half Saree / Puberty / Dhoti)
            to guests so they immediately recognise the ceremony. Wedding is the
            default and intentionally hides this banner. */}
        {data.invitation_category && data.invitation_category !== 'wedding' && (() => {
          const ICONS = { baby_birthday: '🎂', half_saree: '👗', puberty: '🌸', dhoti: '👔' };
          const LABELS = {
            baby_birthday: 'Baby Birthday',
            half_saree:    'Half Saree Ceremony',
            puberty:       'Puberty Ceremony',
            dhoti:         'Dhoti Ceremony',
          };
          const ci = data.celebrant_info || {};
          const ordinal = (n) => {
            const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
            return n + (s[(v - 20) % 10] || s[v] || s[0]);
          };
          const subtitle = (() => {
            if (data.invitation_category === 'baby_birthday' && ci.age_turning) {
              return `${ci.celebrant_name || data.groom_name}'s ${ordinal(ci.age_turning)} Birthday`;
            }
            return `Celebrating ${ci.celebrant_name || data.groom_name}`;
          })();
          return (
            <div className="relative z-30 pointer-events-none w-full px-4 pt-3 sm:pt-5">
              <div className="max-w-3xl mx-auto pointer-events-auto rounded-full flex items-center justify-center gap-2 px-4 py-2"
                style={{ background: 'rgba(11,9,8,0.62)', backdropFilter: 'blur(10px)', border: '1px solid rgba(212,175,55,0.35)' }}
                data-testid="invitation-category-banner">
                <span className="text-lg">{ICONS[data.invitation_category] || '✦'}</span>
                <span className="text-[10px] sm:text-xs tracking-[0.3em] uppercase"
                  style={{ color: '#D4AF37' }}>
                  {LABELS[data.invitation_category] || 'Celebration'}
                </span>
                <span className="hidden sm:inline opacity-50" style={{ color: '#FFF8DC' }}>·</span>
                <span className="hidden sm:inline text-xs" style={{ color: 'rgba(255,248,220,0.85)' }}>
                  {subtitle}
                </span>
              </div>
            </div>
          );
        })()}
        {/* Phase 3A — couple-photo page backdrop.
            iOS Safari note: `background-attachment: fixed` and large CSS
            `filter: blur()` BOTH freeze scroll on iPhone. We use a normal
            absolutely-positioned <img> with `object-cover` instead — same
            premium look, zero scroll cost. The image sits on its own
            compositor layer (`translateZ(0)`) so it never repaints on scroll. */}
        {(() => {
          const bgPhoto = data?.couple_photo_url || data?.bride_photo_url || data?.groom_photo_url;
          if (!bgPhoto) return null;
          return (
            <div
              aria-hidden
              className="absolute inset-0 overflow-hidden"
              style={{ zIndex: 0, pointerEvents: 'none' }}
              data-testid="page-bg-photo"
            >
              <img
                src={bgPhoto}
                alt=""
                loading="eager"
                decoding="async"
                className="w-full h-full object-cover"
                style={{
                  transform: 'translateZ(0)',  // own GPU layer, no repaints on scroll
                  opacity: 0.55,
                  filter: 'saturate(0.85)',    // tiny, color-only filter — cheap
                }}
              />
              {/* Readability scrim — flat gradient, no blur */}
              <div
                aria-hidden
                className="absolute inset-0"
                style={{
                  background:
                    'linear-gradient(180deg, rgba(10,8,5,0.72) 0%, rgba(10,8,5,0.55) 30%, rgba(10,8,5,0.65) 70%, rgba(10,8,5,0.86) 100%)',
                }}
              />
            </div>
          );
        })()}
        {/* All real content sits above the backdrop */}
        <div className="relative" style={{ zIndex: 1 }}>
        {/* Feb 2026 — Persistent ambient petal shower for the entire scroll
            experience. Sits below the main content (zIndex: 0 inside the
            absolute container) but above the photo backdrop. */}
        {openingDone && <PetalShower count={18} />}
        {/* Prompt 14 — Personalized welcome (only if ?g=token in URL) */}
        {guestToken && openingDone && <PersonalizedWelcome slug={slug} token={guestToken} />}

        {watermark && <WatermarkOverlay />}

        {/* Language switcher — shown only when the couple uploaded multi-language
            translations to `profile.translations`.  We always include the base
            language so the user can switch back to the original. */}
        {allLangs.length > 1 && (
          <div
            className="fixed z-40 flex items-center gap-1 px-2 py-1.5 rounded-full"
            style={{
              top: 12, right: 12,
              background: 'rgba(14,10,6,0.78)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(212,175,55,0.35)',
            }}
            data-testid="lang-switcher"
          >
            {allLangs.map((lng) => {
              const active = activeLang === lng;
              return (
                <button
                  key={lng}
                  type="button"
                  onClick={() => setSelectedLang(lng)}
                  className="text-[10px] tracking-[0.18em] uppercase px-2 py-1 rounded-full"
                  style={{
                    background: active ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'transparent',
                    color: active ? '#16110C' : 'rgba(255,248,220,0.7)',
                  }}
                  data-testid={`lang-pick-${lng}`}
                >
                  {lng}
                </button>
              );
            })}
          </div>
        )}

        {/* Hero */}
        <HeroCover bride={bride} groom={groom} date={weddingDate} theme={theme} />

        {/* Featured invitation design — uses the user's selected theme to render
            an animated 3D-overlay design from the master 180-design catalogue. */}
        {heroResolved && (
          <ScrollSection className="px-6 md:px-16 py-16 max-w-3xl mx-auto" testid="section-featured-design">
            <span className="lux-eyebrow block mb-4 text-center">◆ The Invitation</span>
            <h2 className="font-display text-[2rem] md:text-[2.8rem] leading-[1.05] mb-8 text-center" style={{ color: '#FFF8DC' }}>
              Our <span className="text-gold italic font-script">card.</span>
            </h2>
            <UniversalDesignRenderer
              design={heroResolved.design}
              theme={heroResolved.theme}
              bride={bride}
              groom={groom}
              date={weddingDate ? weddingDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }) : ''}
              venue={venueText}
              testId="featured-design"
              style={{ maxWidth: 540, margin: '0 auto' }}
            />
          </ScrollSection>
        )}

        {/* Bride / Groom / Couple showcase — photo + bio, asymmetric layout */}
        <BrideGroomCoupleShowcase
          bride={bride}
          groom={groom}
          bridePhoto={bridePhoto}
          groomPhoto={groomPhoto}
          couplePhoto={couplePhoto}
          brideAbout={brideAbout}
          groomAbout={groomAbout}
          loveStory={story}
          eventType={primaryEventType}
          showBride={showBride}
          showGroom={showGroom}
          showCouple={showCouple}
        />

        {/* July 2026 — Families & blessings section. Only shown if the
            photographer entered at least one parent's name in the wizard.
            All four slots are independent; partial info renders gracefully. */}
        {(() => {
          const maja = data.custom_text?._maja || {};
          const bf = maja.bride_father || '';
          const bm = maja.bride_mother || '';
          const gf = maja.groom_father || '';
          const gm = maja.groom_mother || '';
          if (!bf && !bm && !gf && !gm) return null;
          return (
            <ScrollSection className="px-6 md:px-16 py-20 max-w-4xl mx-auto" testid="section-families">
              <span className="lux-eyebrow block mb-5">◆ With the blessings of</span>
              <h2 className="font-display text-[2.2rem] md:text-[2.8rem] leading-[1.05] mb-10" style={{ color: '#FFF8DC' }}>
                Our <span className="text-gold italic font-script">families.</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {(bf || bm) && (
                  <div className="lux-glass p-6 text-center">
                    <div className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: '#D4AF37' }}>
                      Bride's parents
                    </div>
                    {bf && <p className="font-display text-xl mb-1" style={{ color: '#FFF8DC' }}>{bf}</p>}
                    {(bf && bm) && <p className="text-xs my-1.5" style={{ color: 'rgba(255,248,220,0.5)' }}>&amp;</p>}
                    {bm && <p className="font-display text-xl" style={{ color: '#FFF8DC' }}>{bm}</p>}
                  </div>
                )}
                {(gf || gm) && (
                  <div className="lux-glass p-6 text-center">
                    <div className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: '#D4AF37' }}>
                      Groom's parents
                    </div>
                    {gf && <p className="font-display text-xl mb-1" style={{ color: '#FFF8DC' }}>{gf}</p>}
                    {(gf && gm) && <p className="text-xs my-1.5" style={{ color: 'rgba(255,248,220,0.5)' }}>&amp;</p>}
                    {gm && <p className="font-display text-xl" style={{ color: '#FFF8DC' }}>{gm}</p>}
                  </div>
                )}
              </div>
            </ScrollSection>
          );
        })()}

        {/* July 2026 — Additional couple-photo carousel.  Renders only
            when the photographer added extras via the wizard's MultiPhoto
            uploader. The primary couple photo is already shown in the
            BrideGroomCoupleShowcase above. */}
        {(() => {
          const maja = data.custom_text?._maja || {};
          const extras = Array.isArray(maja.couple_photos) ? maja.couple_photos.filter(Boolean) : [];
          if (extras.length === 0) return null;
          // BUG F FIX: respect sections_enabled.photos toggle — default
          // "show" (existing invitations without the field continue to
          // display their gallery).
          if (data?.sections_enabled?.photos === false) return null;
          return (
            <ScrollSection className="px-6 md:px-16 py-16 max-w-5xl mx-auto" testid="section-couple-extra-photos">
              <span className="lux-eyebrow block mb-4 text-center">◆ Moments</span>
              <h2 className="font-display text-[2rem] md:text-[2.6rem] leading-[1.05] mb-8 text-center" style={{ color: '#FFF8DC' }}>
                A few more <span className="text-gold italic font-script">memories.</span>
              </h2>
              <div className="flex gap-3 overflow-x-auto pb-4 snap-x snap-mandatory" style={{ scrollbarWidth: 'thin' }}>
                {extras.map((url, i) => (
                  <div
                    key={i}
                    className="snap-center rounded-xl overflow-hidden flex-shrink-0"
                    style={{ width: 280, height: 360, border: '1px solid rgba(212,175,55,0.3)', background: 'rgba(8,5,3,0.6)' }}
                  >
                    <img
                      src={resolveUrl(url)}
                      alt={`Couple memory ${i + 1}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                ))}
              </div>
            </ScrollSection>
          );
        })()}

        {/* Story */}
        {story && (
          <ScrollSection className="px-6 md:px-16 py-24 max-w-4xl mx-auto" testid="section-story">
            <span className="lux-eyebrow block mb-5">◆ Our Story</span>
            <h2 className="font-display text-[2.4rem] md:text-[3.4rem] leading-[1.05] mb-8" style={{ color: '#FFF8DC' }}>
              How <span className="text-gold italic font-script">we</span> met
            </h2>
            <p className="font-heading text-[1.1rem] md:text-[1.25rem] leading-[1.85] whitespace-pre-wrap"
              style={{ color: 'rgba(255,248,220,0.78)' }}>
              {story}
            </p>
          </ScrollSection>
        )}

        {/* Events section removed per requirement — Haldi/Mehendi/Sangeet/Engagement etc. no longer shown */}

        {/* Bucket 1A — Live event timeline (Now / Next / Done) */}
        {(data?.sections_enabled?.live_timeline ?? false) && (
          <LiveTimelineSection events={events} slug={slug} />
        )}

        {/* Bucket 1A — Dress Code carousel */}
        <DressCodeSection settings={data.dress_code_settings} />

        {/* Bucket 1A — Live Stream link / embed. July 2026: also accept
            the simpler `youtube_live_url` field saved by the photographer
            wizard's Stay & Video step. */}
        <LiveStreamSection
          liveStream={
            (data.live_stream && data.live_stream.enabled)
              ? data.live_stream
              : (data.custom_text?._maja?.youtube_live_url
                  ? { enabled: true, url: data.custom_text._maja.youtube_live_url, embed_enabled: true, message: 'Watch our wedding live from anywhere.' }
                  : null)
          }
        />

        {/* Bucket 1A — Add to Calendar prominent CTA strip */}
        <ScrollSection className="px-6 md:px-16 py-10" testid="section-add-to-calendar">
          <div className="max-w-3xl mx-auto text-center">
            <span className="lux-eyebrow inline-block mb-4">◆ Save the dates</span>
            <h3 className="font-display text-[1.6rem] md:text-[2rem] mb-5" style={{ color: '#FFF8DC' }}>
              One tap. <span className="text-gold italic font-script">All events.</span>
            </h3>
            <AddToCalendarButton slug={slug} />
          </div>
        </ScrollSection>

        {/* Venue / map */}
        {venueText && (
          <ScrollSection className="px-6 md:px-16 py-24 max-w-4xl mx-auto" testid="section-venue">
            <span className="lux-eyebrow block mb-5">◆ Venue</span>
            <h2 className="font-display text-[2.4rem] md:text-[3.4rem] leading-[1.05] mb-6" style={{ color: '#FFF8DC' }}>
              The <span className="text-gold italic font-script">where.</span>
            </h2>
            <p className="text-[1.05rem] leading-relaxed mb-2" style={{ color: 'rgba(255,248,220,0.8)' }}>{venueText}</p>
            {venueAddress && <p className="text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,248,220,0.6)' }}>{venueAddress}</p>}
            <a target="_blank" rel="noreferrer" href={`https://www.google.com/maps/search/${encodeURIComponent([venueText, venueAddress].filter(Boolean).join(', '))}`} className="lux-btn lux-btn-ghost">
              Open in Maps <MapPin className="w-3.5 h-3.5" />
            </a>
          </ScrollSection>
        )}

        {/* Parking — rendered only when the couple has enabled it.
            `profile.parking.enabled === true` toggles this section.  We
            show the parking note + an optional Maps deep-link. */}
        {data.parking?.enabled && (
          <ScrollSection className="px-6 md:px-16 py-20 max-w-4xl mx-auto" testid="section-parking">
            <span className="lux-eyebrow block mb-5">◆ Parking &amp; Travel</span>
            <h2 className="font-display text-[2rem] md:text-[2.6rem] leading-[1.05] mb-6" style={{ color: '#FFF8DC' }}>
              How to <span className="text-gold italic font-script">park.</span>
            </h2>
            {data.parking?.note && (
              <p className="text-[1rem] leading-relaxed mb-3" style={{ color: 'rgba(255,248,220,0.8)' }} data-testid="parking-note">
                {tr('parking_note', data.parking.note)}
              </p>
            )}
            {data.parking?.address && (
              <p className="text-sm mb-4" style={{ color: 'rgba(255,248,220,0.6)' }} data-testid="parking-address">
                {data.parking.address}
              </p>
            )}
            {(data.parking?.map_link || data.parking?.address || data.parking?.note) && (
              <a
                target="_blank"
                rel="noreferrer"
                href={
                  data.parking?.map_link
                    || `https://www.google.com/maps/search/${encodeURIComponent([data.parking?.address || '', venueText].filter(Boolean).join(', '))}`
                }
                className="lux-btn lux-btn-ghost"
                data-testid="parking-map-link"
              >
                Open parking map <MapPin className="w-3.5 h-3.5" />
              </a>
            )}
          </ScrollSection>
        )}

        {/* Countdown */}
        {/* BUG B FIX: honour sections_enabled.countdown — default "show". */}
        {weddingDate && (data?.sections_enabled?.countdown !== false) && <Countdown date={weddingDate} />}

        {/* Pre-wedding shoot (Google Drive / YouTube / Vimeo embed) */}
        <PreWeddingSection preWeddingLinks={preWeddingLinks} />

        {/* Find My Room — guest accommodation lookup (popup-style trigger) */}
        <FindMyRoomSection slug={slug} hasRooms={guestRooms.length > 0} variant="popup" />

        {/* RSVP */}
        {/* BUG 27 FIX: respect the sections_enabled.rsvp toggle. Default to
            "shown" when the field is missing (existing invitations created
            before the toggle existed must keep working). */}
        {(data?.sections_enabled?.rsvp !== false) && (
          <ScrollSection className="px-6 md:px-16 py-24" testid="section-rsvp">
            <div className="max-w-2xl mx-auto">
              <span className="lux-eyebrow block mb-5">◆ Will you be there?</span>
              <h2 className="font-display text-[2.4rem] md:text-[3.4rem] leading-[1.05] mb-8" style={{ color: '#FFF8DC' }}>
                Kindly <span className="text-gold italic font-script">respond.</span>
              </h2>
              <RSVPForm slug={slug} rsvpSettings={data.rsvp_settings} onSuccess={() => setRsvpDone(true)} />
            </div>
          </ScrollSection>
        )}

        {/* Phase 1H — Honeymoon Fund (UPI / QR) — shown only when couple has enabled it */}
        <HoneymoonFundSection fund={data.honeymoon_fund} couple={`${bride} & ${groom}`} />

        {/* Bucket 1A — Guest Check-In */}
        <CheckInSection
          slug={slug}
          enabled={data?.sections_enabled?.check_in ?? false}
          events={events}
        />

        {/* Bucket 1A — Song Requests (build the playlist) */}
        <SongRequestSection slug={slug} settings={data.song_requests_settings} />

        {/* Wishes — Prompt 07: moderated wishes wall with featured spotlight */}
        {/* BUG D FIX: honour sections_enabled.greetings — default "show". */}
        {(data?.sections_enabled?.greetings !== false) && <WishesWallSection slug={slug} />}

        {/* Phase 38 — Live Photo Wall teaser */}
        <LivePhotoWallTeaser slug={slug} />

        {/* Sprint 10 — Find My Photos CTA (AI face match) */}
        {galleryInfo?.enabled && (
          <section className="px-6 md:px-12 py-12 md:py-16 text-center" data-testid="find-photos-cta">
            <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.7 }} className="max-w-2xl mx-auto">
              <span className="lux-eyebrow inline-block mb-3">◆ AI-powered photo search</span>
              <h2 className="font-display text-[1.9rem] md:text-[2.6rem] mb-3" style={{ color: '#FFF8DC' }}>
                Find <span className="font-script italic text-gold">your photos</span> from the wedding
              </h2>
              <p className="text-sm md:text-base mb-6" style={{ color: 'rgba(255,248,220,0.7)' }}>
                Upload one selfie. Our AI will instantly find every photo of you from the {galleryInfo.total_photos || ''} captured at the wedding.
              </p>
              <button onClick={() => setFindOpen(true)} className="lux-btn inline-flex items-center gap-2"
                data-testid="open-find-photos">
                <Sparkles className="w-4 h-4" /> Find My Photos
              </button>
            </motion.div>
          </section>
        )}

        {/* Sprint 8 — Multi-venue travel section */}
        <VenuesSection slug={slug} />

        {/* Sprint 9 — Optional gift registry / "no gifts please" note */}
        <GiftRegistrySection slug={slug} />

        {/* Digital Shagun (UPI live blessing counter) */}
        <DigitalShagunSection slug={slug} couple={`${bride} & ${groom}`} />

        {/* Viral photographer-referral CTA */}
        <MajaReferralCTA slug={slug} />

        {/* Inline thematic closing motif — sits above the footer */}
        {openingDone && (
          <ClosingOrchestrator
            themeId={themeId}
            eventType={primaryEventType}
            image={heroResolved?.design?.image}
            bride={bride}
            groom={groom}
            date={formattedDate}
          />
        )}

        {/* Footer */}
        <footer ref={footerRef} className="px-6 md:px-16 py-14 text-center border-t" style={{ borderColor: 'var(--lux-border)' }} data-testid="invitation-footer">
          <div className="font-script text-3xl text-gold mb-2 italic">{bride} & {groom}</div>
          <div className="text-xs tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
            Crafted with reverence · MAJA Creations
          </div>
        </footer>

        {/* BUG E FIX: respect background_music.enabled (and the legacy
            sections_enabled.music alias) — photographers who disabled music
            in the Features panel were still getting it played to guests. */}
        {musicUrl && (data?.background_music?.enabled !== false) && (data?.sections_enabled?.music !== false) && (
          <AmbientMusicPlayer src={musicUrl} defaultVolume={0.35} />
        )}
        <PetalConfetti trigger={rsvpDone ? Date.now() : false} count={42} duration={5200} />
        <PetalConfetti trigger={wishDone ? Date.now() : false} count={26} duration={4200} />
        <FindMyPhotosModal slug={slug} open={findOpen} onClose={() => setFindOpen(false)} />

        {/* Prompt 13 — Floating guest upload button (after cinematic opening) */}
        {openingDone && <GuestUploadButton slug={slug} />}
        </div>{/* /relative content wrapper (Phase 3A) */}
      </div>
      </>
    </InvitePrefetchContext.Provider>
  );
};

const PortraitPanel = ({ photo, fallbackInitial, accentSide = 'left', direction = 'left' }) => {
  // Feb 2026 — Strong 3D entrance (12° tilt + 200 px slide + depth fade, 800 ms)
  // Photo enters from `direction` side with perspective rotateY so it feels
  // like the page is physically tilting toward the viewer. Reduced-motion users
  // still get a clean fade.
  const reduce = useReducedMotion();
  const xDelta = direction === 'right' ? 200 : -200;
  const rotY   = direction === 'right' ? -12 : 12;
  return (
    <motion.div
      initial={reduce ? { opacity: 0 } : { opacity: 0, x: xDelta, rotateY: rotY, scale: 0.92, filter: 'blur(8px)' }}
      whileInView={reduce ? { opacity: 1 } : { opacity: 1, x: 0, rotateY: 0, scale: 1, filter: 'blur(0px)' }}
      viewport={{ once: true, margin: '-10%', amount: 0.15 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="relative w-full"
      style={{ maxWidth: 460, aspectRatio: '4 / 5', perspective: 1200, transformStyle: 'preserve-3d' }}
      data-testid={`portrait-panel-${direction}`}
    >
      <div
        className="absolute inset-0 rounded-[3px]"
        style={{
          background: 'linear-gradient(135deg, rgba(212,175,55,0.45) 0%, rgba(212,175,55,0.08) 60%, transparent 100%)',
          padding: 2,
          boxShadow: '0 30px 80px rgba(0,0,0,0.55), 0 12px 30px rgba(0,0,0,0.35)',
        }}
      >
        <div className="w-full h-full overflow-hidden rounded-[2px]" style={{ background: '#1A130B' }}>
          {photo ? (
            <img
              src={photo} alt="" loading="lazy"
              className="w-full h-full object-cover"
              style={{ filter: 'saturate(1.05) contrast(1.04)' }}
            />
          ) : (
            <div
              className="w-full h-full grid place-items-center font-script"
              style={{
                background: 'radial-gradient(circle at 30% 25%, rgba(212,175,55,0.22), transparent 65%)',
                color: '#D4AF37',
                fontSize: 'clamp(7rem, 18vw, 14rem)',
                lineHeight: 1, fontStyle: 'italic',
              }}
            >
              {(fallbackInitial || '?').toUpperCase()}
            </div>
          )}
        </div>
      </div>
      <div
        aria-hidden className="absolute pointer-events-none"
        style={{
          [accentSide]: -14, top: -14, width: 56, height: 56,
          borderTop: '1px solid rgba(212,175,55,0.55)',
          [`border${accentSide === 'left' ? 'Left' : 'Right'}`]: '1px solid rgba(212,175,55,0.55)',
        }}
      />
      <div
        aria-hidden className="absolute pointer-events-none"
        style={{
          [accentSide === 'left' ? 'right' : 'left']: -14, bottom: -14, width: 56, height: 56,
          borderBottom: '1px solid rgba(212,175,55,0.55)',
          [`border${accentSide === 'left' ? 'Right' : 'Left'}`]: '1px solid rgba(212,175,55,0.55)',
        }}
      />
    </motion.div>
  );
};

const BridePanelText = ({ name, about, eyebrow, side }) => {
  // Feb 2026 — Words feel like they're flying in from "somewhere" with a
  // strong 3D word-reveal (per-line stagger + small perspective rotateX).
  const reduce = useReducedMotion();
  const xDelta = side === 'right' ? 200 : -200;
  return (
  <motion.div
    initial={reduce ? { opacity: 0 } : { opacity: 0, x: xDelta, rotateY: side === 'right' ? -12 : 12, filter: 'blur(6px)' }}
    whileInView={reduce ? { opacity: 1 } : { opacity: 1, x: 0, rotateY: 0, filter: 'blur(0px)' }}
    viewport={{ once: true, margin: '-10%', amount: 0.15 }}
    transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
    className="w-full"
    style={{ perspective: 1200 }}
  >
    <motion.span
      initial={{ opacity: 0, rotateX: -25, y: 14 }}
      whileInView={{ opacity: 1, rotateX: 0, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: 0.45 }}
      className="lux-eyebrow block mb-4">◆ {eyebrow}</motion.span>
    <motion.h3
      initial={{ opacity: 0, rotateX: -25, y: 18 }}
      whileInView={{ opacity: 1, rotateX: 0, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.7, delay: 0.55 }}
      className="font-display leading-[1.05] mb-5"
      style={{ color: '#FFF8DC', fontSize: 'clamp(2.4rem, 5vw, 4.2rem)' }}>
      {name}
    </motion.h3>
    <div className="h-px w-16 mb-5"
         style={{ background: 'linear-gradient(90deg, #D4AF37 0%, transparent 100%)' }} />
    {about ? (
      <p className="font-heading whitespace-pre-wrap"
         style={{ color: 'rgba(255,248,220,0.78)', fontSize: 'clamp(1rem, 1.3vw, 1.15rem)', lineHeight: 1.85 }}>
        {about}
      </p>
    ) : (
      <p className="text-sm italic" style={{ color: 'rgba(255,248,220,0.45)' }}>
        A short bio will appear here.
      </p>
    )}
  </motion.div>
  );
};

export const BrideGroomCoupleShowcase = ({
  bride, groom,
  bridePhoto, groomPhoto, couplePhoto,
  brideAbout, groomAbout, loveStory,
  eventType,           // Feb 2026 — for single-photo events (haldi/mehendi)
  // Feb 2026 — per-slot enable flags. When false, the slot is fully hidden
  // (section + divider removed from the DOM, not just the photo blanked).
  // Defaults preserve old behavior for callers that don't pass them.
  showBride = true, showGroom = true, showCouple = true,
}) => {
  // Effective slot visibility = (toggle ON) AND (something to show)
  const brideSlot  = showBride  && (bridePhoto  || brideAbout);
  const groomSlot  = showGroom  && (groomPhoto  || groomAbout);
  const coupleSlot = showCouple && (couplePhoto || loveStory);
  const hasAny = brideSlot || groomSlot || coupleSlot;
  if (!hasAny) return null;

  // Feb 2026 — Haldi & Mehendi feature only ONE person (typically the bride).
  // Skip the bride+groom split layout for those events; show the single photo
  // as a centered cinematic hero so the page stays balanced.
  const evt = (eventType || '').toLowerCase();
  const isSinglePhoto = evt === 'haldi' || evt === 'mehendi' || evt === 'mehndi';

  if (isSinglePhoto) {
    const featuredPhoto = bridePhoto || groomPhoto || couplePhoto;
    const featuredName  = bridePhoto ? bride : (groomPhoto ? groom : `${bride} & ${groom}`);
    const featuredAbout = bridePhoto ? brideAbout : (groomPhoto ? groomAbout : loveStory);
    const eyebrow = evt === 'haldi' ? 'Haldi Ceremony' : 'Mehendi Ceremony';
    return (
      <section className="relative py-20 md:py-28 overflow-hidden" data-testid={`section-single-${evt}`}>
        <PetalShower testId="petal-shower-section" />
        <ScrollSection className="px-6 md:px-16 max-w-4xl mx-auto" testid={`section-single-${evt}-inner`}>
          <div className="text-center mb-10">
            <span className="lux-eyebrow block mb-4">◆ {eyebrow}</span>
            <h3 className="font-display leading-[1.05]"
                style={{ color: '#FFF8DC', fontSize: 'clamp(2.4rem, 5vw, 4.2rem)' }}>
              {featuredName}
            </h3>
          </div>
          <div className="flex justify-center">
            <PortraitPanel photo={featuredPhoto} fallbackInitial={(featuredName || '?')[0]} accentSide="left" direction="left" />
          </div>
          {featuredAbout && (
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.9, delay: 0.2 }}
              className="font-heading text-center mt-10 max-w-2xl mx-auto whitespace-pre-wrap italic"
              style={{ color: 'rgba(255,248,220,0.78)', fontSize: 'clamp(1rem, 1.3vw, 1.18rem)', lineHeight: 1.85 }}
            >
              {featuredAbout}
            </motion.p>
          )}
        </ScrollSection>
      </section>
    );
  }

  return (
    <section className="relative py-20 md:py-28 overflow-hidden" data-testid="section-bride-groom-couple">
      {/* Feb 2026 — Petal shower decoration throughout (option a) */}
      <PetalShower testId="petal-shower-section" />
      {brideSlot && (
        <ScrollSection className="px-6 md:px-16 max-w-6xl mx-auto" testid="section-bride">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
            <PortraitPanel photo={bridePhoto} fallbackInitial={bride[0]} accentSide="left" direction="left" />
            <BridePanelText name={bride} about={brideAbout} eyebrow="The Bride" side="right" />
          </div>
        </ScrollSection>
      )}
      {brideSlot && groomSlot && (
        <div className="flex justify-center my-16 md:my-24" aria-hidden>
          <div className="flex items-center gap-4" style={{ color: '#D4AF37' }}>
            <div style={{ width: 64, height: 1, background: 'linear-gradient(90deg, transparent, #D4AF37)' }} />
            <Sparkles className="w-4 h-4" />
            <div style={{ width: 64, height: 1, background: 'linear-gradient(90deg, #D4AF37, transparent)' }} />
          </div>
        </div>
      )}
      {groomSlot && (
        <ScrollSection className="px-6 md:px-16 max-w-6xl mx-auto" testid="section-groom">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
            <BridePanelText name={groom} about={groomAbout} eyebrow="The Groom" side="left" />
            <div className="md:order-last flex justify-end">
              <PortraitPanel photo={groomPhoto} fallbackInitial={groom[0]} accentSide="right" direction="right" />
            </div>
          </div>
        </ScrollSection>
      )}
      {coupleSlot && (
        <ScrollSection className="px-6 md:px-16 max-w-4xl mx-auto mt-16 md:mt-24" testid="section-couple-meet">
          <div className="text-center mb-8">
            <span className="lux-eyebrow block mb-4">◆ Together</span>
            <h3 className="font-display leading-[1.05]"
                style={{ color: '#FFF8DC', fontSize: 'clamp(2.2rem, 4.8vw, 3.8rem)' }}>
              {bride} <span className="text-gold italic font-script">&amp;</span> {groom}
            </h3>
          </div>
          {couplePhoto && (
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: '-15%', amount: 0.1 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
              className="relative mx-auto w-full overflow-hidden"
              style={{
                maxWidth: 720, aspectRatio: '3 / 2', borderRadius: 4,
                border: '1px solid rgba(212,175,55,0.35)',
                boxShadow: '0 24px 60px rgba(0,0,0,0.4), 0 8px 20px rgba(0,0,0,0.25)',
              }}
            >
              <SmartImage
                src={couplePhoto}
                alt=""
                priority={true}
                className="w-full h-full"
                style={{ width: '100%', height: '100%' }}
              />
            </motion.div>
          )}
          {loveStory && (
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.9, delay: 0.2 }}
              className="font-heading text-center mt-8 max-w-2xl mx-auto whitespace-pre-wrap italic"
              style={{ color: 'rgba(255,248,220,0.78)', fontSize: 'clamp(1rem, 1.3vw, 1.18rem)', lineHeight: 1.85 }}
            >
              {loveStory}
            </motion.p>
          )}
        </ScrollSection>
      )}
    </section>
  );
};

export const HeroCover = ({ bride, groom, date, theme }) => {
  // Bucket 2 — Bride slides in from LEFT, Groom from RIGHT.
  // Mobile devices respect `useReducedMotion` so users with motion-reduction
  // preferences still get a clean fade.
  const reduce = useReducedMotion();
  const slideX = (dir) => reduce
    ? { initial: { opacity: 0 }, animate: { opacity: 1 } }
    : {
        initial: { opacity: 0, x: dir === 'left' ? -80 : 80, filter: 'blur(8px)' },
        animate: { opacity: 1, x: 0, filter: 'blur(0px)' },
      };

  return (
    <section className="relative min-h-screen flex items-center justify-center px-6 md:px-16 overflow-hidden" data-testid="section-hero">
      <div className="lux-orbit" style={{ width: 760, height: 760, top: -180, right: -180 }} />
      <div className="lux-orbit" style={{ width: 1100, height: 1100, top: -360, right: -360, opacity: 0.5 }} />

      {/* Floating mandala decorations — pure CSS, decorative, no scroll cost */}
      {!reduce && (
        <>
          <FloatingMandala size={140} top="12%" left="6%" duration={14} delay={0} opacity={0.35} />
          <FloatingMandala size={170} top="22%" right="8%" duration={18} delay={2} opacity={0.28} flip />
          <FloatingMandala size={110} bottom="14%" left="12%" duration={16} delay={3.5} opacity={0.32} />
          <FloatingMandala size={130} bottom="22%" right="14%" duration={20} delay={5} opacity={0.26} flip />
        </>
      )}

      <motion.div className="text-center relative z-10 max-w-4xl"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.span initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 1 }}
          className="lux-eyebrow block mb-6">◆ {theme.culture} · {theme.name}</motion.span>
        <h1 className="font-display text-[3.2rem] md:text-[7rem] leading-[0.95] tracking-tight" style={{ color: '#FFF8DC' }}>
          <motion.span
            {...slideX('left')}
            transition={{ delay: 0.45, duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
            whileTap={{ scale: 0.97 }}
            className="inline-block"
            data-testid="hero-bride"
          >
            {bride}
          </motion.span>
          <motion.span
            initial={{ opacity: 0, scale: 0.6, rotate: -15 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            transition={{ delay: 0.75, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
            className="block text-gold italic font-script font-light my-2 md:my-4 text-[2.2rem] md:text-[4.5rem]"
          >
            &amp;
          </motion.span>
          <motion.span
            {...slideX('right')}
            transition={{ delay: 0.95, duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
            whileTap={{ scale: 0.97 }}
            className="inline-block"
            data-testid="hero-groom"
          >
            {groom}
          </motion.span>
        </h1>
        {date && (
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.4, duration: 1 }}
            className="mt-10 inline-flex items-center gap-4 text-sm tracking-[0.3em] uppercase"
            style={{ color: 'rgba(255,248,220,0.7)' }}>
            <Calendar className="w-4 h-4" style={{ color: '#D4AF37' }} />
            <span>{date.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' })}</span>
          </motion.div>
        )}
      </motion.div>
    </section>
  );
};

/* Feb 2026 — PetalShower: ambient marigold-petal decoration that drifts down
   the section. Pure CSS-keyframe driven, no scroll listeners, zero JS cost.
   Twelve petals at varied speeds + horizontal offsets so the motion never
   feels mechanical. Pointer-events disabled. */
const PetalShower = ({ count = 12, testId = 'petal-shower' }) => {
  const reduce = useReducedMotion();
  if (reduce) return null;
  const petals = Array.from({ length: count }, (_, i) => i);
  return (
    <div
      aria-hidden
      data-testid={testId}
      style={{
        position: 'absolute', inset: 0, overflow: 'hidden',
        pointerEvents: 'none', zIndex: 0,
      }}
    >
      {petals.map((i) => {
        const left = ((i * 8.3) % 100);
        const dur  = 14 + ((i * 1.7) % 10);     // 14–24 s
        const dly  = (i * 0.9) % 12;
        const size = 14 + ((i * 3) % 14);       // 14–28 px
        const sway = 30 + ((i * 7) % 50);
        const hue  = i % 2 === 0 ? '#E8A87C' : '#D4AF37'; // marigold / gold
        return (
          <span
            key={i}
            style={{
              position: 'absolute',
              top: '-32px',
              left: `${left}%`,
              width: size, height: size,
              borderRadius: '50% 0 50% 0',
              background: `radial-gradient(circle at 30% 30%, ${hue}, transparent 70%)`,
              opacity: 0.55,
              animation: `petal-fall ${dur}s linear ${dly}s infinite, petal-sway ${dur / 2}s ease-in-out ${dly}s infinite alternate`,
              ['--sway']: `${sway}px`,
              transform: `rotate(${i * 23}deg)`,
            }}
          />
        );
      })}
      <style>{`
        @keyframes petal-fall { 0%{transform:translateY(-8vh) rotate(0)} 100%{transform:translateY(110vh) rotate(720deg)} }
        @keyframes petal-sway { 0%{margin-left:0} 100%{margin-left:var(--sway)} }
      `}</style>
    </div>
  );
};


/* Floating mandala — pure CSS animation, no scroll listeners, near-zero cost.
   Used by HeroCover to add gentle ambient decoration around the names. */
const FloatingMandala = ({ size = 120, top, left, right, bottom, duration = 16, delay = 0, opacity = 0.3, flip = false }) => (
  <div
    aria-hidden
    style={{
      position: 'absolute',
      top, left, right, bottom,
      width: size, height: size,
      opacity,
      pointerEvents: 'none',
      transform: flip ? 'scaleX(-1)' : undefined,
      animation: `float-mandala ${duration}s ease-in-out ${delay}s infinite`,
      zIndex: 1,
    }}
  >
    <style>{`@keyframes float-mandala {
      0%,100% { transform: translateY(0) rotate(0deg) ${flip ? 'scaleX(-1)' : ''}; }
      50%     { transform: translateY(-16px) rotate(8deg) ${flip ? 'scaleX(-1)' : ''}; }
    }`}</style>
    <svg viewBox="0 0 100 100" width={size} height={size}>
      {[...Array(12)].map((_, i) => (
        <ellipse
          key={i}
          cx="50" cy="22" rx="3.5" ry="14"
          fill="#D4AF37"
          opacity={0.5 - (i % 3) * 0.1}
          transform={`rotate(${i * 30} 50 50)`}
        />
      ))}
      <circle cx="50" cy="50" r="3.5" fill="#E8C766" />
      <circle cx="50" cy="50" r="18" fill="none" stroke="#D4AF37" strokeWidth="0.5" opacity="0.6" />
      <circle cx="50" cy="50" r="32" fill="none" stroke="#D4AF37" strokeWidth="0.3" opacity="0.4" strokeDasharray="2 3" />
    </svg>
  </div>
);

export const Countdown = ({ date }) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const diff = Math.max(date.getTime() - now, 0);
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return (
    <ScrollSection className="px-6 md:px-16 py-20 max-w-4xl mx-auto" testid="section-countdown">
      <span className="lux-eyebrow block mb-5 text-center">◆ Until the moment</span>
      <div className="grid grid-cols-4 gap-3 md:gap-6">
        {[{ v: d, l: 'Days' }, { v: h, l: 'Hours' }, { v: m, l: 'Min' }, { v: s, l: 'Sec' }].map((u) => (
          <div key={u.l} className="lux-glass p-5 text-center">
            <div className="font-display text-4xl md:text-6xl text-gold leading-none">{String(u.v).padStart(2, '0')}</div>
            <div className="mt-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.6)' }}>{u.l}</div>
          </div>
        ))}
      </div>
    </ScrollSection>
  );
};

const RSVPForm = ({ slug, rsvpSettings, onSuccess }) => {
  const settings = rsvpSettings || {};
  const [form, setForm] = useState({
    guest_name: '',
    email: '',
    guest_phone: '+91',
    status: 'yes',
    guest_count: 1,
    message: '',
    dietary_preference: '',
    allergies: '',
    plus_one: false,
    kids_count: 0,
  });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [done, setDone] = useState(false);

  const dietaryOptions = [
    { v: 'veg',     label: 'Vegetarian',    show: settings.dietary_show_veg !== false },
    { v: 'nonveg',  label: 'Non-Vegetarian', show: settings.dietary_show_nonveg !== false },
    { v: 'vegan',   label: 'Vegan',         show: settings.dietary_show_vegan !== false },
    { v: 'jain',    label: 'Jain',          show: settings.dietary_show_jain !== false },
  ].filter((o) => o.show);

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      // Only send fields the couple has actually enabled
      const payload = {
        guest_name:  form.guest_name,
        guest_phone: form.guest_phone,
        status:      form.status,
        guest_count: parseInt(form.guest_count, 10) || 1,
        message:     form.message || undefined,
      };
      if (settings.dietary_enabled && form.dietary_preference) payload.dietary_preference = form.dietary_preference;
      if (settings.allergies_enabled && form.allergies)        payload.allergies = form.allergies;
      if (settings.plus_one_enabled)                            payload.plus_one  = !!form.plus_one;
      if (settings.kids_enabled)                                payload.kids_count = parseInt(form.kids_count, 10) || 0;

      await axios.post(
        `${API_URL}/api/rsvp?slug=${encodeURIComponent(slug)}`,
        payload
      );
      setDone(true); onSuccess?.();
    } catch (e) {
      const d = e.response?.data?.detail;
      const msg = Array.isArray(d) ? d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join(' · ') : (d || 'RSVP failed.');
      setErr(msg);
    }
    finally { setBusy(false); }
  };

  if (done) return (
    <div className="lux-glass p-8 text-center" data-testid="rsvp-success">
      <Sparkles className="w-5 h-5 mx-auto mb-3" style={{ color: '#D4AF37' }} />
      <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>Thank you.</h3>
      <p className="text-sm" style={{ color: 'rgba(255,248,220,0.7)' }}>Your response has been received with love.</p>
    </div>
  );

  return (
    <form onSubmit={submit} className="lux-glass p-7 space-y-4" data-testid="rsvp-form">
      <Row>
        <LField label="Your Name"><input required type="text" value={form.guest_name} onChange={(e) => setForm({ ...form, guest_name: e.target.value })} style={lInput} data-testid="rsvp-name" /></LField>
        <LField label="Phone (with +91)"><input required type="tel" value={form.guest_phone} onChange={(e) => setForm({ ...form, guest_phone: e.target.value })} placeholder="+919876543210" style={lInput} data-testid="rsvp-phone" /></LField>
      </Row>
      <Row>
        <LField label="Attending"><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} style={{ ...lInput, cursor: 'pointer', appearance: 'none' }} data-testid="rsvp-attending">
          <option value="yes" style={{ background: '#1A130B' }}>Yes, with joy</option>
          <option value="no" style={{ background: '#1A130B' }}>Regretfully no</option>
          <option value="maybe" style={{ background: '#1A130B' }}>Trying my best</option>
        </select></LField>
        <LField label="Guests"><input type="number" min={1} max={10} value={form.guest_count} onChange={(e) => setForm({ ...form, guest_count: e.target.value })} style={lInput} data-testid="rsvp-guests" /></LField>
      </Row>

      {/* Phase 1C — Dietary preference (only when couple enabled it) */}
      {settings.dietary_enabled && dietaryOptions.length > 0 && (
        <LField label="Dietary preference">
          <select
            value={form.dietary_preference}
            onChange={(e) => setForm({ ...form, dietary_preference: e.target.value })}
            style={{ ...lInput, cursor: 'pointer', appearance: 'none' }}
            data-testid="rsvp-dietary"
          >
            <option value="" style={{ background: '#1A130B' }}>— Select —</option>
            {dietaryOptions.map((o) => (
              <option key={o.v} value={o.v} style={{ background: '#1A130B' }}>{o.label}</option>
            ))}
          </select>
        </LField>
      )}

      {/* Phase 1C — Allergies note */}
      {settings.allergies_enabled && (
        <LField label="Allergies (optional, max 250 chars)">
          <textarea
            rows={2}
            maxLength={250}
            value={form.allergies}
            onChange={(e) => setForm({ ...form, allergies: e.target.value })}
            placeholder="e.g. peanuts, dairy, gluten…"
            style={{ ...lInput, resize: 'vertical' }}
            data-testid="rsvp-allergies"
          />
        </LField>
      )}

      {/* Phase 1C — Plus-one + Kids */}
      {(settings.plus_one_enabled || settings.kids_enabled) && (
        <Row>
          {settings.plus_one_enabled && (
            <LField label="Bringing a plus-one?">
              <label className="flex items-center gap-3 py-2 cursor-pointer" data-testid="rsvp-plusone-wrap">
                <input
                  type="checkbox"
                  checked={!!form.plus_one}
                  onChange={(e) => setForm({ ...form, plus_one: e.target.checked })}
                  style={{ width: 18, height: 18, accentColor: '#D4AF37' }}
                  data-testid="rsvp-plusone"
                />
                <span className="text-sm" style={{ color: '#FFF8DC' }}>Yes, with my partner</span>
              </label>
            </LField>
          )}
          {settings.kids_enabled && (
            <LField label="Kids attending">
              <input
                type="number"
                min={0}
                max={20}
                value={form.kids_count}
                onChange={(e) => setForm({ ...form, kids_count: e.target.value })}
                style={lInput}
                data-testid="rsvp-kids"
              />
            </LField>
          )}
        </Row>
      )}

      <LField label="Message (optional)"><textarea rows={2} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} style={{ ...lInput, resize: 'vertical' }} data-testid="rsvp-message" /></LField>
      {err && <div className="text-sm px-3 py-2 rounded-md" style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9' }}>{err}</div>}
      <button type="submit" disabled={busy} className="lux-btn w-full justify-center" data-testid="rsvp-submit">
        {busy ? 'Sending…' : 'Send RSVP'} <Send className="w-3.5 h-3.5" />
      </button>
    </form>
  );
};

const WishForm = ({ slug, onSuccess }) => {
  const [form, setForm] = useState({ guest_name: '', message: '' });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      await axios.post(`${API_URL}/api/invite/${slug}/greetings`, {
        guest_name: form.guest_name,
        message: form.message,
      });
      setDone(true); setForm({ guest_name: '', message: '' }); onSuccess?.();
    } catch (e) {
      const d = e.response?.data?.detail;
      const msg = Array.isArray(d) ? d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join(' · ') : (d || 'Could not send wish.');
      setErr(msg);
    }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="lux-glass p-7 space-y-4" data-testid="wish-form">
      <Row>
        <LField label="Your Name"><input required type="text" value={form.guest_name} onChange={(e) => setForm({ ...form, guest_name: e.target.value })} style={lInput} data-testid="wish-name" /></LField>
      </Row>
      <LField label="Your Wish (250 chars max)"><textarea required maxLength={250} rows={3} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="A blessing for the couple…" style={{ ...lInput, resize: 'vertical' }} data-testid="wish-message" /></LField>
      {done && <div className="text-sm px-3 py-2 rounded-md" style={{ background: 'rgba(212,175,55,0.12)', color: '#E8C766' }}>Wish recorded. Thank you.</div>}
      {err && <div className="text-sm px-3 py-2 rounded-md" style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9' }}>{err}</div>}
      <button type="submit" disabled={busy} className="lux-btn lux-btn-ghost" data-testid="wish-submit">
        {busy ? 'Sending…' : 'Send Wish'} <MessageCircle className="w-3.5 h-3.5" />
      </button>
    </form>
  );
};

const lInput = {
  width: '100%', padding: '0.85rem 1rem', background: 'transparent', color: '#FFF8DC',
  border: '1px solid var(--lux-border)', borderRadius: '0.5rem', outline: 'none',
  fontFamily: 'Manrope, sans-serif', fontSize: '0.92rem', caretColor: '#D4AF37',
};

const Row = ({ children }) => <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>;

const LField = ({ label, children }) => (
  <label className="block">
    <span className="block text-[10px] tracking-[0.3em] uppercase mb-2" style={{ color: 'rgba(255,248,220,0.55)' }}>{label}</span>
    {children}
  </label>
);

export default React.memo(LuxuryPublicInvitation);
