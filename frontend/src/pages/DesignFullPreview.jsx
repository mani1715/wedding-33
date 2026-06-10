/**
 * DesignFullPreview — Unified Stage layout.
 *
 * One single design-themed look for the ENTIRE page:
 *   • Page background = the design's natural parchment / cream / palette
 *     colour (from `design.bg`), PLUS a soft, low-opacity copy of the
 *     same design image fixed in the background — so the design extends
 *     everywhere (not just at the top).
 *   • Hero card: the design photo shown smaller (max-width 620 px),
 *     centered, sharp, with a soft drop-shadow. Empty space on the
 *     sides shares the same design-themed background, with subtle
 *     ornamental floating motifs.
 *   • All sub-sections (Our Story, Ceremonies, Names, Map, Comments,
 *     etc.) sit on top of the same background with a translucent
 *     parchment-tinted panel — so the design pattern is always visible.
 *
 * Structure (extensible):
 *   <PageStage>
 *     <SoftDesignBackdrop />          fixed, low-opacity design image
 *     <SideOrnaments />               subtle theme accent shapes
 *     <main>
 *       <HeroCard />                  the invitation
 *       <StorySection />
 *       <CeremoniesSection />
 *       <NamesSection (placeholder) />
 *       <MapSection (placeholder) />
 *       <CommentsSection (placeholder) />
 *       <VariantSwitcher />
 *     </main>
 *   </PageStage>
 *
 * Adding a new section later is just: drop a <Panel> child in <main>.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, Check, Edit3, Image as ImageIcon, Link as LinkIcon, MapPin, MessageSquare, Save, Share2, Upload, Users, X } from 'lucide-react';
import { ALL_DESIGNS, useThemeDesigns } from '@/themes/allDesigns';
import { KERALA_COLORS } from '@/themes/kerala_backwaters/kerala.colors';
import { getThemeById } from '@/themes/masterThemes';
import { normaliseEvent, resolveDesign, pageBgForDesign } from '@/themes/themeDesignResolver';
import { AnimationProvider } from '@/components/animations';
import UniversalDesignRenderer from '@/themes/UniversalDesignRenderer';
import { isLight as isLightColor } from '@/themes/textContrast';
import { getThemeSampleData } from '@/themes/sampleData';
import { OpeningOrchestrator, ClosingOrchestrator } from '@/themes/shared/ThemeAnimationOrchestrator';
import ThemeAnimatedBackground from '@/components/ThemeAnimatedBackground';
import DesignImage from '@/components/DesignImage';
import { Heart, Send, Sparkles, Gift, Plane, Hotel, Building2, Camera, Search } from 'lucide-react';
import { eventPhoto, DEFAULT_COUPLE_PHOTO, DEFAULT_BRIDE_PHOTO, DEFAULT_GROOM_PHOTO } from '@/themes/samplePhotos';

const LS_KEY = 'wedding3.designSelections.v1';
const readSelections = () => { try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}'); } catch { return {}; } };
const writeSelections = (d) => { try { localStorage.setItem(LS_KEY, JSON.stringify(d)); } catch (e) { /* ignore */ } };

const DEFAULT_PHOTO = 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=400&fit=crop&q=85';

// Build per-theme defaults from THEME_SAMPLE_DATA so each theme preview has
// its own culturally resonant placeholder couple (Lakshmi & Karthik for South
// Indian, Simran & Arjun for Punjabi, etc.).
// `event` (e.g. "haldi", "mehndi") drives the hero photo — Haldi/Mehndi show
// the freshly-generated single-person portraits, every other event shows the
// couple shot.
const buildDefaultText = (themeId, event) => {
  const s = getThemeSampleData(themeId) || {};
  return {
    bride: s.bride || 'Anaya',
    groom: s.groom || 'Vihaan',
    date:  s.weddingDate || '14 February 2026',
    venue: `${s.venue || 'Falaknuma Palace'}${s.city ? ' · ' + s.city.split(',')[0] : ''}`,
    story: s.story || 'Two souls. One promise. A wedding to remember.',
    photo: eventPhoto(event) || DEFAULT_PHOTO,
    bride_about:  s.bride_about  || '',
    groom_about:  s.groom_about  || '',
    couple_about: s.couple_about || s.story || '',
    nakshatram:   s.nakshatram   || '',
    muhurtam:     s.muhurtam     || '',
    wedding_time: s.wedding_time || '11:00 AM',
  };
};

const DEFAULT_CEREMONIES = [
  { key: 'Engagement', date: '10 February 2026', venue: 'Garden Pavilion', time: '6:30 PM' },
  { key: 'Marriage',   date: '14 February 2026', venue: 'The Mandap',       time: '11:00 AM' },
  { key: 'Reception',  date: '15 February 2026', venue: 'Falaknuma Palace', time: '7:00 PM' },
];

const DEFAULT_FAMILY = [
  { side: 'Bride', members: ['Rajesh & Meena Kapoor (Parents)', 'Aarav Kapoor (Brother)'] },
  { side: 'Groom', members: ['Suresh & Lata Mehta (Parents)', 'Riya Mehta (Sister)'] },
];

const DesignFullPreview = () => {
  const { themeId, event: rawEvent, designIndex } = useParams();
  const navigate = useNavigate();
  const themeMeta = useMemo(() => getThemeById(themeId), [themeId]);
  const event = useMemo(() => normaliseEvent(rawEvent), [rawEvent]);
  const idx = Math.max(0, Math.min(2, parseInt(designIndex || '0', 10)));
  // PHASE 8: lazy-load this specific theme's design config (also keeps cache hot).
  const themeDesigns = useThemeDesigns(themeId);

  const resolved = useMemo(() => resolveDesign(themeId, event, idx), [themeId, event, idx, themeDesigns]);
  const sampleData = useMemo(() => getThemeSampleData(themeId) || {}, [themeId]);
  const tokens = resolved?.theme?.tokens || (themeId === 'kerala_backwaters'
    ? { background: KERALA_COLORS.water, text: KERALA_COLORS.text, accent: KERALA_COLORS.secondary }
    : (themeDesigns?.tokens || ALL_DESIGNS[themeId]?.tokens || { background: '#0a0a0a', text: '#F5ECD7', accent: '#D4AF37' }));

  const [text, setText] = useState(() => {
    const stored = readSelections();
    return { ...buildDefaultText(themeId, event), ...(stored.text || {}) };
  });
  const [saved, setSaved] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [coverText, setCoverText] = useState(() => {
    const stored = readSelections();
    return stored.coverText ?? false;
  });

  /* When the event changes (user switches between Haldi/Mehndi/Marriage etc.)
     swap the hero photo to the matching default UNLESS the user has uploaded
     a custom photo (data: URL or non-default URL). */
  useEffect(() => {
    const defaults = buildDefaultText(themeId, event);
    setText((prev) => {
      const isDefault =
        !prev.photo ||
        prev.photo === DEFAULT_PHOTO ||
        prev.photo === DEFAULT_COUPLE_PHOTO ||
        prev.photo === DEFAULT_BRIDE_PHOTO ||
        prev.photo === DEFAULT_GROOM_PHOTO ||
        prev.photo.includes('/uploads/themes/');
      return isDefault ? { ...prev, photo: defaults.photo } : prev;
    });
  }, [themeId, event]);

  /* Per-theme cinematic opening — plays every time the user lands on a
     design preview (no sessionStorage gating).  The user complained that
     once-per-session caching meant the opening "didn't come" when they
     navigated between designs, so every entry replays the full cinematic. */
  const [openingDone, setOpeningDone] = useState(false);
  const markOpeningDone = useCallback(() => { setOpeningDone(true); }, []);
  // Replay the opening every time the user switches to a different design
  // (themeId / event / idx change) so each pick gets its own cinematic intro.
  useEffect(() => { setOpeningDone(false); }, [themeId, event, idx]);

  // SAFETY: never trap users on a blank screen if the opening orchestrator
  // chunk is slow or never reports completion.
  useEffect(() => {
    if (openingDone) return;
    const id = setTimeout(() => setOpeningDone(true), 6000);
    return () => clearTimeout(id);
  }, [openingDone, themeId, event, idx]);
  const footerRef = useRef(null);

  // Use design's own bg colour as the unified page colour
  const pageBg = pageBgForDesign(resolved?.design, { tokens });
  // Pick a readable text colour against the parchment background
  const textOnBg = isLightColor(pageBg) ? '#1A0F08' : '#FFF8DC';
  const mutedText = isLightColor(pageBg) ? 'rgba(40,26,16,0.78)' : 'rgba(255,248,220,0.85)';

  // User-requested change (2026-06-06):
  //   The previous backdrop layered a heavy `pageBg` tint + animated particles
  //   over the design artwork, dulling beautiful pieces like the Kerala
  //   backwaters illustration. Keep the page wrapper TRANSPARENT so the
  //   `SoftDesignBackdrop` image (now displayed crisply) is the actual page
  //   background. A readable text colour is still computed against the
  //   original tokens.background palette so headings stay legible.
  useEffect(() => {
    // Remove dark overlays and set LIGHT background
    document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
    document.body.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)';
    return () => { document.body.style.background = ''; };
  }, [pageBg]);

  if (!themeMeta || !resolved) {
    return (
      <div className="min-h-screen grid place-items-center px-6" style={{ background: 'linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)', color: '#2F2F2F' }}>
        <div className="text-center">
          <h2 className="font-display text-3xl mb-3">Design not available.</h2>
          <button onClick={() => navigate(`/themes/${themeId}/events`)} className="lux-btn lux-btn-ghost">
            Back to ceremonies
          </button>
        </div>
      </div>
    );
  }

  const accent = tokens.accentGold || tokens.accent;
  const imgUrl = resolved.design.image;
  const headingFont = tokens.heading || '"Cormorant Garamond", serif';

  const handleSave = () => {
    const data = readSelections();
    data.text = text;
    data.coverText = coverText;
    data[`${themeId}__${event}`] = { themeId, event, designIndex: idx, designId: resolved.design.id };
    data.lastPick = { themeId, event, designIndex: idx, designId: resolved.design.id, savedAt: new Date().toISOString() };
    writeSelections(data);
    setSaved(true);
    setTimeout(() => setSaved(false), 2200);
  };

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try { await navigator.share({ title: `${themeMeta.name} · ${event}`, url }); return; } catch { /* user cancelled */ }
    }
    try { await navigator.clipboard.writeText(url); setSaved(true); setTimeout(() => setSaved(false), 1800); } catch { /* ignore */ }
  };

  return (
    <AnimationProvider>
      {/* Petal burst on scroll/touch — luxury micro-interaction.
          Pointer-events: none, never blocks UI. */}
      {openingDone && <PetalBurstOverlay accent={accent} />}

      {/* Per-theme cinematic opening — fires once per session per theme.
          Until the opening is done the rest of the page stays hidden. */}
      {!openingDone && (
        <OpeningOrchestrator
          themeId={themeId}
          event={event}
          image={resolved?.design?.image}
          bride={text.bride}
          groom={text.groom}
          date={text.date}
          monogram={`${(text.bride || '?')[0]} & ${(text.groom || '?')[0]}`}
          onComplete={markOpeningDone}
        />
      )}
      <div
        className="relative"
        style={{
          // TRANSPARENT wrapper — the design image (via SoftDesignBackdrop)
          // is now the page background. Previously this was `background: pageBg`
          // which painted a solid dark colour over the artwork.
          background: 'transparent',
          color: textOnBg, minHeight: '100vh',
          opacity: openingDone ? 1 : 0,
          pointerEvents: openingDone ? 'auto' : 'none',
          transition: 'opacity 0.55s ease',
        }}
        data-testid={`design-full-preview-${themeId}-${event.toLowerCase()}-${idx}`}
      >
        {/* ── DESIGN IMAGE PAGE BACKGROUND (fixed, edge-to-edge, visible) ─── */}
        <SoftDesignBackdrop image={imgUrl} accent={accent} pageBg={pageBg} />

        {/* ── Top controls ── */}
        <div
          className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 md:px-10 py-4"
          style={{
            background: `linear-gradient(180deg, ${pageBg}DD 0%, ${pageBg}00 100%)`,
            backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
          }}
        >
          <button
            onClick={() => navigate(`/themes/${themeId}/events/${event}`)}
            className="inline-flex items-center gap-2 text-xs tracking-[0.3em] uppercase px-3 py-2 rounded-md"
            style={{ color: textOnBg, background: `${pageBg}CC`, border: `1px solid ${accent}55` }}
            data-testid="back-to-designs"
          >
            <ArrowLeft className="w-4 h-4" /> Designs
          </button>
          <div className="flex items-center gap-2">
            <button onClick={() => setEditMode(v => !v)}
              className="inline-flex items-center gap-2 text-[11px] tracking-[0.25em] uppercase px-3 py-2 rounded-md"
              style={{
                color: editMode ? pageBg : textOnBg,
                background: editMode ? accent : `${pageBg}CC`,
                border: `1px solid ${accent}77`,
              }}
              data-testid="toggle-edit-mode">
              <Edit3 className="w-3.5 h-3.5" /> {editMode ? 'Done editing' : 'Edit text'}
            </button>
            <button onClick={handleSave}
              className="inline-flex items-center gap-2 text-[11px] tracking-[0.25em] uppercase px-3 py-2 rounded-md"
              style={{ color: pageBg, background: accent, border: `1px solid ${accent}` }}
              data-testid="save-selection">
              {saved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
              {saved ? 'Saved' : 'Save pick'}
            </button>
            <button onClick={handleShare}
              className="hidden sm:inline-flex items-center gap-2 text-[11px] tracking-[0.25em] uppercase px-3 py-2 rounded-md"
              style={{ color: textOnBg, background: `${pageBg}CC`, border: `1px solid ${accent}77` }}
              data-testid="share-design">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
          </div>
        </div>

        {/* ── PAGE CONTENT ── */}
        <main className="relative z-10" style={{ paddingTop: 70 }}>

          {/* HERO — invitation rendered through UniversalDesignRenderer
               so the photographer's clean text card always sits on top of
               (and covers) the poster's baked-in text. */}
          <Panel pageBg={pageBg} accent={accent} variant="hero">
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 1.0, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
              className="relative mx-auto"
              style={{
                maxWidth: 'min(560px, 92vw)',
                width: '100%',
                willChange: 'transform',
                animation: 'card-float 6s ease-in-out infinite',
                filter: 'drop-shadow(0 30px 60px rgba(0,0,0,0.30)) drop-shadow(0 10px 24px rgba(0,0,0,0.18))',
              }}
              data-testid="card-text-overlay"
            >
              <UniversalDesignRenderer
                design={resolved.design}
                theme={resolved.theme}
                bride={text.bride}
                groom={text.groom}
                date={text.date}
                venue={text.venue}
                photo={text.photo}
                coverText={coverText}
                testId={`hero-${resolved.design.id}`}
              />
            </motion.div>

            <div className="mt-6 flex items-center justify-center">
              <button
                onClick={() => setCoverText((v) => !v)}
                className="inline-flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase px-3 py-2 rounded-md"
                style={{
                  color: coverText ? pageBg : textOnBg,
                  background: coverText ? accent : `${accent}22`,
                  border: `1px solid ${accent}66`,
                }}
                data-testid="toggle-cover-text"
                title="Hide any baked-in text on the template"
              >
                {coverText ? '✓ Clean canvas (hides design)' : 'Hide template baked-in text'}
              </button>
            </div>

            <div
              aria-hidden
              className="text-[10px] tracking-[0.5em] uppercase mt-6 text-center"
              style={{ color: accent, opacity: 0.85 }}
            >
              ▾ Scroll for details
            </div>
          </Panel>

          {/* OUR STORY */}
          <Panel pageBg={pageBg} accent={accent} testId="info-section">
            <Eyebrow accent={accent}>◆ Our Story</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Two souls. <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>One promise.</em>
            </SectionHeading>
            <p className="text-[1.05rem] leading-relaxed" style={{ color: mutedText }}>{text.story}</p>
          </Panel>

          {/* COUNTDOWN — live ticker until the wedding moment */}
          <CountdownSection
            pageBg={pageBg}
            accent={accent}
            textOnBg={textOnBg}
            mutedText={mutedText}
            headingFont={headingFont}
            weddingDate={text.date}
          />

          {/* SEQUENTIAL PHOTO REVEAL — Groom (left) → Bride (right) →
              Couple → Wedding details. NOT side-by-side. */}
          <SequentialPhotoReveal
            pageBg={pageBg}
            accent={accent}
            textOnBg={textOnBg}
            mutedText={mutedText}
            headingFont={headingFont}
            bride={text.bride}
            groom={text.groom}
            heroPhoto={text.photo}
            brideBio={text.bride_about}
            groomBio={text.groom_about}
            coupleStory={text.couple_about || text.story}
            weddingDate={text.date}
            weddingTime={text.wedding_time}
            venue={text.venue}
            nakshatram={text.nakshatram}
            muhurtam={text.muhurtam}
          />

          {/* PHOTO GALLERY — smooth horizontal scroll powered by CSS transform
              + will-change so it scrolls 60fps even on mid-range phones. */}
          <PhotoGallerySection
            pageBg={pageBg}
            accent={accent}
            textOnBg={textOnBg}
            mutedText={mutedText}
            headingFont={headingFont}
            heroPhoto={text.photo}
          />

          {/* Events/Ceremonies panel removed per requirement */}

          {/* NAMES — Bride & Groom side family (placeholder, ready to wire) */}
          <Panel pageBg={pageBg} accent={accent} testId="names-section">
            <Eyebrow accent={accent}><Users className="w-3 h-3 inline-block mr-2 -mt-0.5" /> Family</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              With blessings <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>from both sides.</em>
            </SectionHeading>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
              {DEFAULT_FAMILY.map((f) => (
                <div key={f.side} className="px-5 py-4 rounded-md" style={{ background: `${accent}10`, border: `1px solid ${accent}33` }}>
                  <div className="text-[11px] tracking-[0.3em] uppercase mb-2" style={{ color: accent }}>{f.side}'s side</div>
                  <ul className="space-y-1 text-sm" style={{ color: mutedText }}>
                    {f.members.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </Panel>

          {/* MAP — venue location (placeholder, ready to wire to Google Maps later) */}
          <Panel pageBg={pageBg} accent={accent} testId="map-section">
            <Eyebrow accent={accent}><MapPin className="w-3 h-3 inline-block mr-2 -mt-0.5" /> Venue</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Find <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>your way.</em>
            </SectionHeading>
            <div
              className="mt-5 rounded-md flex items-center justify-center text-sm"
              style={{
                background: `${accent}10`, border: `1px solid ${accent}33`,
                color: mutedText, minHeight: 220,
                backgroundImage: 'linear-gradient(135deg, rgba(0,0,0,0.04) 25%, transparent 25%, transparent 50%, rgba(0,0,0,0.04) 50%, rgba(0,0,0,0.04) 75%, transparent 75%, transparent)',
                backgroundSize: '20px 20px',
              }}
            >
              <div className="text-center">
                <MapPin className="w-7 h-7 mx-auto mb-2" style={{ color: accent }} />
                <div className="font-display text-lg" style={{ fontFamily: headingFont, color: textOnBg }}>{text.venue}</div>
                <div className="text-[11px] tracking-[0.3em] uppercase mt-1" style={{ color: accent }}>Map coming soon</div>
              </div>
            </div>
          </Panel>

          {/* COMMENTS / WISHES — guest book placeholder */}
          {/* WISHES */}
          <Panel pageBg={pageBg} accent={accent} testId="comments-section">
            <Eyebrow accent={accent}><MessageSquare className="w-3 h-3 inline-block mr-2 -mt-0.5" /> Wishes</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Leave a <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>blessing.</em>
            </SectionHeading>
            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
              {(sampleData?.wishes || []).slice(0, 4).map((w, i) => (
                <div key={i} className="px-4 py-3 rounded-md"
                  style={{ background: `${accent}10`, border: `1px solid ${accent}33` }}
                  data-testid={`dfp-wish-${i}`}>
                  <Heart className="w-3.5 h-3.5 mb-2" style={{ color: accent }} />
                  <p className="text-sm italic" style={{ color: textOnBg }}>"{w.text}"</p>
                  <div className="text-[10px] tracking-[0.25em] uppercase mt-2" style={{ color: mutedText }}>— {w.from}</div>
                </div>
              ))}
            </div>
            <div className="mt-5 text-center">
              <button className="text-[11px] tracking-[0.25em] uppercase px-4 py-2 rounded-md"
                style={{ color: textOnBg, background: `${accent}15`, border: `1px solid ${accent}66` }}
                data-testid="dfp-wish-cta">
                <MessageSquare className="w-3.5 h-3.5 inline-block mr-2 -mt-0.5" />
                Send your wish
              </button>
            </div>
          </Panel>

          {/* RSVP */}
          <Panel pageBg={pageBg} accent={accent} testId="rsvp-section">
            <Eyebrow accent={accent}>◆ Will you be there?</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Kindly <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>respond.</em>
            </SectionHeading>
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input placeholder="Your name" data-testid="dfp-rsvp-name"
                className="px-3 py-2.5 rounded-md text-sm outline-none"
                style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}55` }} />
              <input placeholder="Phone (+91)" data-testid="dfp-rsvp-phone"
                className="px-3 py-2.5 rounded-md text-sm outline-none"
                style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}55` }} />
              <select data-testid="dfp-rsvp-attending"
                className="px-3 py-2.5 rounded-md text-sm outline-none"
                style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}55` }}>
                <option>Yes, with joy</option>
                <option>Regretfully no</option>
                <option>Trying my best</option>
              </select>
              <input type="number" min={1} max={10} defaultValue={1} placeholder="Guests" data-testid="dfp-rsvp-guests"
                className="px-3 py-2.5 rounded-md text-sm outline-none"
                style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}55` }} />
            </div>
            <textarea rows={2} placeholder="A message for the couple (optional)"
              className="mt-3 w-full px-3 py-2.5 rounded-md text-sm outline-none"
              style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}55`, resize: 'vertical' }}
              data-testid="dfp-rsvp-message" />
            <div className="mt-4 text-right">
              <button className="text-[11px] tracking-[0.3em] uppercase px-5 py-2.5 rounded-md inline-flex items-center gap-2"
                style={{ color: pageBg, background: accent }}
                data-testid="dfp-rsvp-submit">
                Send RSVP <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </Panel>

          {/* LIVE PHOTO WALL teaser */}
          <Panel pageBg={pageBg} accent={accent} testId="live-photo-wall-section">
            <Eyebrow accent={accent}>◆ Live Photo Wall</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Photos appear <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>live.</em>
            </SectionHeading>
            <p className="mt-3 text-sm" style={{ color: mutedText }}>
              The photographer's hand-picked moments stream here as the wedding unfolds.
            </p>
            <div className="mt-4">
              <button className="text-[11px] tracking-[0.3em] uppercase px-5 py-2.5 rounded-md inline-flex items-center gap-2"
                style={{ color: pageBg, background: accent }}
                data-testid="dfp-live-wall-cta">
                <Camera className="w-3.5 h-3.5" /> View live wall
              </button>
            </div>
          </Panel>

          {/* FIND MY PHOTOS */}
          <Panel pageBg={pageBg} accent={accent} testId="find-photos-section">
            <Eyebrow accent={accent}>◆ AI-powered photo search</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Find <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>your photos</em> from the wedding.
            </SectionHeading>
            <p className="mt-3 text-sm" style={{ color: mutedText }}>
              Upload one selfie. Our AI will surface every photo of you from the day.
            </p>
            <div className="mt-4">
              <button className="text-[11px] tracking-[0.3em] uppercase px-5 py-2.5 rounded-md inline-flex items-center gap-2"
                style={{ color: pageBg, background: accent }}
                data-testid="dfp-find-photos-cta">
                <Search className="w-3.5 h-3.5" /> Find My Photos
              </button>
            </div>
          </Panel>

          {/* TRAVEL & STAY */}
          {Array.isArray(sampleData?.travel) && sampleData.travel.length > 0 && (
            <Panel pageBg={pageBg} accent={accent} testId="travel-section">
              <Eyebrow accent={accent}>◆ Travel &amp; Stay</Eyebrow>
              <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
                How to <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>reach us.</em>
              </SectionHeading>
              <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
                {sampleData.travel.map((v, i) => {
                  const Icon = (v.type || '').toLowerCase().includes('airport') ? Plane
                    : (v.type || '').toLowerCase().includes('stay') ? Hotel
                    : Building2;
                  return (
                    <div key={i} className="px-4 py-3 rounded-md flex items-start gap-3"
                      style={{ background: `${accent}10`, border: `1px solid ${accent}33` }}
                      data-testid={`dfp-travel-${i}`}>
                      <div className="w-9 h-9 rounded-full grid place-items-center flex-shrink-0"
                        style={{ background: `${accent}25`, color: accent }}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: mutedText }}>{v.type}</div>
                        <div className="text-base font-semibold" style={{ color: textOnBg, fontFamily: headingFont }}>{v.name}</div>
                        <div className="text-sm" style={{ color: mutedText }}>{v.note}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}

          {/* GIFT REGISTRY */}
          {sampleData?.gifts && (
            <Panel pageBg={pageBg} accent={accent} testId="gifts-section">
              <Eyebrow accent={accent}><Gift className="w-3 h-3 inline-block mr-2 -mt-0.5" /> Gifts</Eyebrow>
              <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
                {sampleData.gifts.headline}
              </SectionHeading>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: mutedText }}>
                {sampleData.gifts.message}
              </p>
            </Panel>
          )}

          {/* DIGITAL SHAGUN */}
          {sampleData?.shagun && (
            <Panel pageBg={pageBg} accent={accent} testId="shagun-section">
              <Eyebrow accent={accent}>◆ Digital Shagun</Eyebrow>
              <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
                Send your <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>blessings.</em>
              </SectionHeading>
              <p className="mt-3 text-sm" style={{ color: mutedText }}>{sampleData.shagun.msg}</p>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="px-4 py-3 rounded-md" style={{ background: `${accent}10`, border: `1px solid ${accent}33` }}>
                  <div className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: mutedText }}>UPI ID</div>
                  <div className="font-mono text-sm" style={{ color: textOnBg }}>{sampleData.shagun.upi}</div>
                </div>
                <div className="px-4 py-3 rounded-md" style={{ background: `${accent}10`, border: `1px solid ${accent}33` }}>
                  <div className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: mutedText }}>Payee</div>
                  <div className="text-sm" style={{ color: textOnBg }}>{sampleData.shagun.payee || `${text.bride} & ${text.groom}`}</div>
                </div>
              </div>
            </Panel>
          )}

          {/* MAJA REFERRAL */}
          <Panel pageBg={pageBg} accent={accent} testId="referral-section">
            <Eyebrow accent={accent}><Sparkles className="w-3 h-3 inline-block mr-2 -mt-0.5" /> Loved this invitation?</Eyebrow>
            <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
              Crafted by <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>MAJA Creations.</em>
            </SectionHeading>
            <p className="mt-3 text-sm" style={{ color: mutedText }}>
              Want one for your own wedding? Refer your photographer to MAJA and unlock cinematic invitations for any culture.
            </p>
          </Panel>

          {/* VARIANT SWITCHER */}
          <Panel pageBg={pageBg} accent={accent} compact>
            <div className="flex items-baseline justify-between flex-wrap gap-4">
              <div>
                <div className="text-[10px] tracking-[0.5em] uppercase mb-2" style={{ color: accent }}>
                  ◈ {themeMeta.name} · {event} · Design {idx + 1}
                </div>
                <div className="text-xl md:text-2xl" style={{ fontFamily: headingFont, color: textOnBg }}>
                  {resolved.design.title}
                </div>
                <p className="text-sm max-w-xl mt-1.5" style={{ color: mutedText }}>{resolved.design.description}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {[0, 1, 2].map((i) => (
                  <button key={i}
                    onClick={() => navigate(`/themes/${themeId}/events/${event}/design/${i}`)}
                    className="text-[11px] tracking-[0.25em] uppercase px-3 py-2 rounded-md"
                    style={{
                      color: i === idx ? pageBg : textOnBg,
                      background: i === idx ? accent : `${accent}15`,
                      border: `1px solid ${accent}66`,
                    }}
                    data-testid={`switch-design-${i}`}>
                    Design {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </Panel>
        </main>

        {/* Edit panel */}
        {editMode && (
          <motion.div
            initial={{ y: 60, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 60, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="fixed bottom-0 left-0 right-0 z-50 px-5 md:px-10 pb-6 pt-5"
            style={{
              background: `linear-gradient(0deg, ${pageBg}F4 0%, ${pageBg}AA 70%, ${pageBg}00 100%)`,
              backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
            }}
            data-testid="edit-text-panel"
          >
            <div className="max-w-5xl mx-auto space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <EditField label="Bride" value={text.bride} onChange={(v) => setText(s => ({ ...s, bride: v }))} testId="edit-bride" accent={accent} textOnBg={textOnBg} pageBg={pageBg} />
                <EditField label="Groom" value={text.groom} onChange={(v) => setText(s => ({ ...s, groom: v }))} testId="edit-groom" accent={accent} textOnBg={textOnBg} pageBg={pageBg} />
                <EditField label="Date"  value={text.date}  onChange={(v) => setText(s => ({ ...s, date: v }))}  testId="edit-date"  accent={accent} textOnBg={textOnBg} pageBg={pageBg} />
                <EditField label="Venue" value={text.venue} onChange={(v) => setText(s => ({ ...s, venue: v }))} testId="edit-venue" accent={accent} textOnBg={textOnBg} pageBg={pageBg} />
              </div>
              <PhotoEditor
                value={text.photo}
                onChange={(v) => setText((s) => ({ ...s, photo: v }))}
                accent={accent} textOnBg={textOnBg} pageBg={pageBg}
              />
            </div>
          </motion.div>
        )}

        {/* page-level keyframes */}
        <style>{`
          @keyframes card-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
          @keyframes side-orb-drift {
            0%   { transform: translate(0,0)   rotate(0deg); }
            50%  { transform: translate(8px,-12px) rotate(8deg); }
            100% { transform: translate(0,0)   rotate(0deg); }
          }
        `}</style>

        {/* Closing-animation sentinel — when the photographer/customer
            scrolls to this element the per-theme closing fires. */}
        <div ref={footerRef} data-testid="dfp-closing-sentinel" style={{ height: 60 }} />

        {/* Footer with the couple photo as full-bleed background — last
            thing the guest sees before the closing animation. */}
        <PreviewFooter
          couplePhoto={text.photo}
          bride={text.bride}
          groom={text.groom}
          accent={accent}
          headingFont={headingFont}
        />
        {openingDone && (
          <ClosingOrchestrator
            themeId={themeId}
            eventType={event}
            image={resolved?.design?.image}
            bride={text.bride}
            groom={text.groom}
            date={text.date}
          />
        )}
      </div>
    </AnimationProvider>
  );
};

/* ────────────────────────────────────────────────────────────────────
   SoftDesignBackdrop — Renders the SAME design image as a soft, blurred
   full-viewport backdrop so the design extends edge-to-edge of the page
   (instead of just sitting inside a centered card on a flat shade). The
   center hero card still pops because it uses the crisp, un-blurred
   variant via UniversalDesignRenderer + a strong drop-shadow.
   ──────────────────────────────────────────────────────────────────── */
const SoftDesignBackdrop = ({ image, accent, pageBg = '#1A130B' }) => {
  if (!image) {
    // Pure-CSS fallback when no image URL (kept GPU-cheap)
    return (
      <div
        aria-hidden
        style={{
          position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
          background: `
            radial-gradient(ellipse at top left, ${accent}1F 0%, transparent 55%),
            radial-gradient(ellipse at bottom right, ${accent}14 0%, transparent 60%),
            ${pageBg}
          `,
        }}
      />
    );
  }
  return (
    <>
      {/* The design image is the page background — full-bleed, crisp, no
          heavy blur or dark tint. User explicitly asked (2026-06-06) for
          the artwork itself (e.g. Kerala palms / brass lamps) to be the
          visible background instead of a teal / black overlay. */}
      <img
        aria-hidden
        src={image}
        alt=""
        draggable={false}
        loading="eager"
        decoding="async"
        style={{
          position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
          width: '100%', height: '100%', objectFit: 'cover',
          // Very mild softening to avoid hard crop edges on ultra-wide
          // screens. Crisp enough that the artwork stays recognisable.
          filter: 'blur(4px) saturate(1.05)',
          transform: 'scale(1.04)',
          transformOrigin: 'center center',
          opacity: 1,
          willChange: 'transform',
        }}
        data-testid="design-page-background"
      />
      {/* Soft accent orbs — kept from previous design for cinematic feel.
          Heavy `pageBg` tinting wash was REMOVED so the artwork shows. */}
      <div
        aria-hidden
        style={{
          position: 'fixed', left: '4vw', top: '40vh',
          width: 220, height: 220, zIndex: 1, pointerEvents: 'none',
          background: `radial-gradient(circle, ${accent}33 0%, transparent 70%)`,
          filter: 'blur(20px)',
          animation: 'side-orb-drift 18s ease-in-out infinite',
        }}
      />
      <div
        aria-hidden
        style={{
          position: 'fixed', right: '4vw', top: '60vh',
          width: 260, height: 260, zIndex: 1, pointerEvents: 'none',
          background: `radial-gradient(circle, ${accent}28 0%, transparent 70%)`,
          filter: 'blur(22px)',
          animation: 'side-orb-drift 22s ease-in-out infinite reverse',
        }}
      />
    </>
  );
};

/* ────────────────────────────────────────────────────────────────────
   Panel — a translucent parchment-tinted container used by every
   section so the design backdrop is always visible underneath.
   ──────────────────────────────────────────────────────────────────── */
const Panel = ({ pageBg, accent, children, variant, compact, testId }) => {
  const isHero = variant === 'hero';
  return (
    <section
      data-testid={testId}
      className="relative px-6 md:px-16"
      style={{
        paddingTop:    isHero ? '3rem' : (compact ? '2.6rem' : '4.5rem'),
        paddingBottom: isHero ? '4rem' : (compact ? '2.6rem' : '4.5rem'),
      }}
    >
      <div
        className="max-w-3xl mx-auto rounded-2xl px-6 md:px-10 py-8 md:py-10"
        style={{
          background: isHero ? 'transparent' : `${pageBg}CC`,
          backdropFilter: isHero ? 'none' : 'blur(8px)',
          WebkitBackdropFilter: isHero ? 'none' : 'blur(8px)',
          border: isHero ? 'none' : `1px solid ${accent}44`,
          boxShadow: isHero ? 'none' : '0 16px 50px rgba(0,0,0,0.10)',
        }}
      >
        {children}
      </div>
    </section>
  );
};

const Eyebrow = ({ accent, children }) => (
  <div className="text-[10px] tracking-[0.4em] uppercase mb-3" style={{ color: accent }}>{children}</div>
);

const SectionHeading = ({ children, font, color }) => (
  <h2
    className="leading-tight"
    style={{ fontFamily: font, color, fontSize: 'clamp(1.6rem, 3.2vw, 2.5rem)' }}
  >
    {children}
  </h2>
);

const EditField = ({ label, value, onChange, testId, accent, textOnBg, pageBg }) => (
  <label className="block">
    <span
      className="text-[10px] tracking-[0.3em] uppercase block mb-1.5 font-semibold"
      style={{ color: textOnBg, opacity: 0.85 }}
    >
      {label}
    </span>
    <input value={value} onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2.5 rounded-md text-[15px] outline-none"
      style={{ background: `${pageBg}EE`, color: textOnBg, border: `1px solid ${accent}77`, fontFamily: '"Cormorant Garamond", serif' }}
      data-testid={testId} />
  </label>
);

/* ────────────────────────────────────────────────────────────────────
   PhotoEditor — drag-and-drop file upload + click to upload + URL paste
   ──────────────────────────────────────────────────────────────────── */
const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // 5 MB

const PhotoEditor = ({ value, onChange, accent, textOnBg, pageBg }) => {
  const [dragOver, setDragOver] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const ingestFile = useCallback((file) => {
    setError('');
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please drop an image file (jpg / png / webp).');
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setError('Image is larger than 5 MB. Pick a smaller photo.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => onChange(e.target.result);
    reader.onerror = () => setError('Could not read the file.');
    reader.readAsDataURL(file);
  }, [onChange]);

  const onDrop = (e) => {
    e.preventDefault(); e.stopPropagation();
    setDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) ingestFile(file);
  };
  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = (e) => { e.preventDefault(); setDragOver(false); };
  const onFilePick = (e) => { const f = e.target.files?.[0]; if (f) ingestFile(f); };
  const onUrlApply = () => {
    if (!urlInput.trim()) return;
    setError('');
    onChange(urlInput.trim());
    setUrlInput('');
  };

  return (
    <div className="rounded-md p-3" style={{ background: `${pageBg}EE`, border: `1px solid ${accent}55` }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] tracking-[0.3em] uppercase" style={{ color: accent }}>Couple Photo</span>
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="text-[10px] tracking-[0.2em] uppercase inline-flex items-center gap-1 opacity-75 hover:opacity-100"
            style={{ color: textOnBg }}
            data-testid="clear-photo"
          >
            <X className="w-3 h-3" /> Remove
          </button>
        )}
      </div>

      <div className="flex flex-col md:flex-row items-stretch gap-3">
        {/* Drop / upload zone */}
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => fileRef.current?.click()}
          className="flex-1 rounded-md cursor-pointer transition-colors"
          style={{
            border: `2px dashed ${dragOver ? accent : accent + '66'}`,
            background: dragOver ? `${accent}18` : 'transparent',
            padding: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
          data-testid="photo-dropzone"
        >
          {value ? (
            <img
              src={value}
              alt="Couple"
              style={{ width: 56, height: 56, borderRadius: '50%', objectFit: 'cover', border: `2px solid ${accent}`, flexShrink: 0 }}
            />
          ) : (
            <div style={{ width: 56, height: 56, borderRadius: '50%', display: 'grid', placeItems: 'center', background: `${accent}18`, flexShrink: 0 }}>
              <ImageIcon className="w-6 h-6" style={{ color: accent }} />
            </div>
          )}
          <div className="text-left">
            <div className="text-[12px] font-medium inline-flex items-center gap-1.5" style={{ color: textOnBg }}>
              <Upload className="w-3.5 h-3.5" /> Drag &amp; drop or click to upload
            </div>
            <div className="text-[10px] mt-0.5 opacity-75" style={{ color: textOnBg }}>
              JPG / PNG / WEBP, up to 5&nbsp;MB
            </div>
          </div>
          <input ref={fileRef} type="file" accept="image/*" onChange={onFilePick} className="hidden" data-testid="photo-file-input" />
        </div>

        {/* URL input */}
        <div className="flex-1 rounded-md flex items-stretch gap-2" style={{ border: `1px solid ${accent}55`, padding: 6 }}>
          <span className="grid place-items-center px-2" style={{ color: accent }}><LinkIcon className="w-4 h-4" /></span>
          <input
            type="url"
            value={urlInput}
            placeholder="…or paste an image URL"
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onUrlApply(); } }}
            className="flex-1 px-2 py-2 rounded-md text-[13px] outline-none"
            style={{ background: 'transparent', color: textOnBg, border: 'none' }}
            data-testid="photo-url-input"
          />
          <button
            type="button"
            onClick={onUrlApply}
            className="px-3 text-[10px] tracking-[0.25em] uppercase rounded-md"
            style={{ background: accent, color: pageBg, border: `1px solid ${accent}` }}
            data-testid="photo-url-apply"
          >
            Use
          </button>
        </div>
      </div>

      {error && (
        <div className="text-[11px] mt-2" style={{ color: '#B83A2C' }} data-testid="photo-error">{error}</div>
      )}
    </div>
  );
};

/* Quick brightness check on a #RRGGBB string — true if light (need dark text) */
function isLightHex(hex) {
  return isLightColor(hex);
}

/* ────────────────────────────────────────────────────────────────────
   PhotoGallerySection — buttery-smooth horizontal photo carousel.

   The user complained that the previous scroller was laggy. Fixes:
   - Wrap each tile in a fixed-size flex item so the browser doesn't
     reflow on every frame.
   - Force GPU compositing via `transform: translate3d(0,0,0)` and
     `will-change: transform` so scrolling animates on the GPU.
   - Use native `overflow-x: auto` + `scroll-snap` + `overscroll-behavior`
     so iOS/Android momentum scroll is preserved.
   - Lazy-load tiles + `decoding="async"` to keep paint cost low.
   - Custom prev/next chips that nudge by one tile via `scrollBy`.
   ──────────────────────────────────────────────────────────────────── */
const GALLERY_PHOTOS = [
  'https://images.unsplash.com/photo-1604017011826-d3b4c23f8914?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1601471075416-8c19a6a565c5?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1519741497674-611481863552?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1606800052052-a08af7148866?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1591604466107-ec97de577aff?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=1200&q=82&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1529636798458-92182e662485?w=1200&q=82&auto=format&fit=crop',
];

const PhotoGallerySection = ({ pageBg, accent, textOnBg, mutedText, headingFont, heroPhoto }) => {
  const scrollerRef = React.useRef(null);
  const photos = React.useMemo(() => {
    const list = heroPhoto ? [heroPhoto, ...GALLERY_PHOTOS] : GALLERY_PHOTOS;
    // dedupe while preserving order
    return Array.from(new Set(list));
  }, [heroPhoto]);

  const nudge = (dir) => {
    const el = scrollerRef.current;
    if (!el) return;
    const card = el.querySelector('[data-gallery-tile]');
    const step = (card?.getBoundingClientRect().width || 280) + 16; // gap
    el.scrollBy({ left: dir * step, behavior: 'smooth' });
  };

  return (
    <section
      className="relative"
      data-testid="gallery-section"
      style={{ paddingTop: '4.5rem', paddingBottom: '4.5rem' }}
    >
      <div className="max-w-5xl mx-auto px-6 md:px-16 mb-5 flex items-end justify-between gap-4">
        <div>
          <Eyebrow accent={accent}>◆ Memories</Eyebrow>
          <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
            A few <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>frozen frames.</em>
          </SectionHeading>
          <p className="mt-2 text-sm" style={{ color: mutedText }}>
            Swipe through. Your wedding gallery will live here.
          </p>
        </div>
        <div className="hidden md:flex gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={() => nudge(-1)}
            aria-label="Previous photos"
            className="w-10 h-10 rounded-full grid place-items-center transition-transform active:scale-95"
            style={{ background: `${accent}22`, color: textOnBg, border: `1px solid ${accent}66` }}
            data-testid="gallery-prev"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => nudge(1)}
            aria-label="Next photos"
            className="w-10 h-10 rounded-full grid place-items-center transition-transform active:scale-95"
            style={{ background: accent, color: pageBg, border: `1px solid ${accent}` }}
            data-testid="gallery-next"
          >
            <ArrowLeft className="w-4 h-4 rotate-180" />
          </button>
        </div>
      </div>

      <div
        ref={scrollerRef}
        className="gallery-scroller flex gap-4 px-6 md:px-16 pb-4"
        style={{
          overflowX: 'auto',
          overflowY: 'hidden',
          scrollSnapType: 'x mandatory',
          overscrollBehaviorX: 'contain',
          WebkitOverflowScrolling: 'touch',
          scrollBehavior: 'smooth',
          willChange: 'scroll-position',
          // GPU compositing — keeps animation off the main thread
          transform: 'translate3d(0,0,0)',
        }}
        data-testid="gallery-scroller"
      >
        {photos.map((src, i) => (
          <figure
            key={`${src}-${i}`}
            data-gallery-tile
            className="relative flex-shrink-0 rounded-xl overflow-hidden"
            style={{
              width: 'min(72vw, 320px)',
              aspectRatio: '4 / 5',
              scrollSnapAlign: 'start',
              background: `${accent}18`,
              border: `1px solid ${accent}44`,
              boxShadow: '0 14px 30px rgba(0,0,0,0.18)',
              transform: 'translate3d(0,0,0)',
            }}
            data-testid={`gallery-tile-${i}`}
          >
            <img
              src={src}
              alt={`Memory ${i + 1}`}
              loading="lazy"
              decoding="async"
              draggable={false}
              className="w-full h-full object-cover"
              style={{ willChange: 'transform', transform: 'translate3d(0,0,0)' }}
            />
          </figure>
        ))}
      </div>

      <style>{`
        /* Slim, themed scrollbar (WebKit + Firefox) */
        .gallery-scroller::-webkit-scrollbar { height: 6px; }
        .gallery-scroller::-webkit-scrollbar-track { background: transparent; }
        .gallery-scroller::-webkit-scrollbar-thumb {
          background: rgba(212,175,55,0.4);
          border-radius: 999px;
        }
        .gallery-scroller { scrollbar-color: rgba(212,175,55,0.5) transparent; scrollbar-width: thin; }
      `}</style>
    </section>
  );
};

/* ────────────────────────────────────────────────────────────────────
   CountdownSection — live D-H-M-S ticker until the wedding moment.
   Parses `weddingDate` flexibly ("14 February 2026", ISO, etc.). When
   the date is in the past or unparseable, the section renders a
   graceful "Just married" badge instead.
   ──────────────────────────────────────────────────────────────────── */
const parseWeddingDate = (s) => {
  if (!s) return null;
  const t = Date.parse(s);
  if (!Number.isNaN(t)) return new Date(t);
  // "14 February 2026" style
  const m = String(s).match(/(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (m) {
    const months = ['january','february','march','april','may','june','july','august','september','october','november','december'];
    const mi = months.indexOf(m[2].toLowerCase());
    if (mi >= 0) return new Date(Number(m[3]), mi, Number(m[1]));
  }
  return null;
};

const CountdownSection = ({ pageBg, accent, textOnBg, mutedText, headingFont, weddingDate }) => {
  const target = React.useMemo(() => parseWeddingDate(weddingDate), [weddingDate]);
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!target) return null;
  const diff = target.getTime() - now;
  const past = diff <= 0;
  const total = Math.max(0, diff);
  const days = Math.floor(total / 86_400_000);
  const hours = Math.floor((total % 86_400_000) / 3_600_000);
  const mins = Math.floor((total % 3_600_000) / 60_000);
  const secs = Math.floor((total % 60_000) / 1_000);
  const cells = [
    { v: days,  k: 'Days'    },
    { v: hours, k: 'Hours'   },
    { v: mins,  k: 'Minutes' },
    { v: secs,  k: 'Seconds' },
  ];
  return (
    <section
      className="relative"
      data-testid="countdown-section"
      style={{ paddingTop: '4rem', paddingBottom: '4rem' }}
    >
      <div className="max-w-3xl mx-auto px-6 md:px-16 text-center">
        <Eyebrow accent={accent}>◆ Countdown</Eyebrow>
        <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
          {past ? (
            <>Just <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>married.</em></>
          ) : (
            <>Until <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>we say I do.</em></>
          )}
        </SectionHeading>
        {!past && (
          <div className="mt-6 grid grid-cols-4 gap-3 md:gap-5">
            {cells.map((c) => (
              <div
                key={c.k}
                className="rounded-xl py-4 md:py-5 px-1 transition-transform"
                style={{
                  background: `${accent}14`,
                  border: `1px solid ${accent}44`,
                  color: textOnBg,
                  boxShadow: `0 8px 26px rgba(0,0,0,0.25), inset 0 0 0 1px ${accent}22`,
                }}
                data-testid={`countdown-${c.k.toLowerCase()}`}
              >
                <div className="font-display text-3xl md:text-5xl" style={{ color: accent }}>
                  {String(c.v).padStart(2, '0')}
                </div>
                <div className="mt-1 text-[10px] tracking-[0.3em] uppercase" style={{ color: mutedText }}>
                  {c.k}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};


/* ────────────────────────────────────────────────────────────────────
   SequentialPhotoReveal — NEW FLOW (Feb 2026 user spec):
     • Slide 1: Groom photo enters from the LEFT, bio text on the RIGHT
     • Slide 2: Bride photo enters from the RIGHT, bio text on the LEFT
     • Slide 3: Couple photo centered with couple-story text below
     • Slide 4: "Wedding Details" panel — date, time, nakshatram, muhurtam, venue

   Each slide animates in via IntersectionObserver as the user scrolls.
   The couple shot is also rendered as a soft blurred background behind
   slide 3 so the moment of "Together" feels cinematic.
   ──────────────────────────────────────────────────────────────────── */
const REVEAL_SHOTS = {
  groom: 'https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=1200&q=82&auto=format&fit=crop',
  bride: 'https://images.unsplash.com/photo-1591604466107-ec97de577aff?w=1200&q=82&auto=format&fit=crop',
};

const SideRevealSlide = ({
  side,           // 'left' | 'right'  — which side the PHOTO enters from
  label,
  name,
  bio,
  photo,
  accent,
  textOnBg,
  mutedText,
  headingFont,
  testid,
}) => {
  const ref = React.useRef(null);
  const [visible, setVisible] = React.useState(false);
  React.useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.25 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const photoEnter  = visible ? 'translateX(0)' : (side === 'left' ? 'translateX(-80px)' : 'translateX(80px)');
  const textEnter   = visible ? 'translateX(0)' : (side === 'left' ? 'translateX(60px)'  : 'translateX(-60px)');
  return (
    <div
      ref={ref}
      className={`relative grid grid-cols-1 md:grid-cols-2 items-center gap-6 md:gap-12 px-6 md:px-16 py-14 ${
        side === 'right' ? 'md:[direction:rtl]' : ''
      }`}
      data-testid={testid}
    >
      {/* Photo column */}
      <div
        className="relative rounded-2xl overflow-hidden transition-all duration-[1100ms] ease-out md:[direction:ltr]"
        style={{
          width: '100%',
          maxWidth: 460,
          aspectRatio: '4/5',
          background: `${accent}18`,
          border: `1px solid ${accent}55`,
          boxShadow: '0 30px 60px rgba(0,0,0,0.4)',
          opacity: visible ? 1 : 0,
          transform: photoEnter,
          justifySelf: side === 'right' ? 'end' : 'start',
        }}
      >
        <img
          src={photo}
          alt={`${label} portrait`}
          loading="lazy"
          decoding="async"
          className="w-full h-full object-cover"
          style={{ transform: 'translate3d(0,0,0)' }}
        />
        <div
          className="absolute inset-0 flex flex-col justify-end p-5 md:[direction:ltr]"
          style={{ background: 'linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.7) 100%)' }}
        >
          <div className="text-[10px] tracking-[0.4em] uppercase" style={{ color: '#FFF8DC' }}>{label}</div>
          <div className="font-display text-2xl mt-1" style={{ color: '#FFF8DC', fontFamily: `${headingFont}, serif` }}>{name}</div>
        </div>
      </div>

      {/* Text column */}
      <div
        className="md:[direction:ltr] transition-all duration-[1100ms] ease-out"
        style={{
          opacity: visible ? 1 : 0,
          transform: textEnter,
          transitionDelay: '180ms',
        }}
      >
        <div className="text-[10px] tracking-[0.4em] uppercase mb-2" style={{ color: accent }}>{label}</div>
        <div className="font-display text-3xl md:text-4xl mb-3" style={{ color: textOnBg, fontFamily: `${headingFont}, serif` }}>
          {name}
        </div>
        <p className="text-[15px] leading-relaxed" style={{ color: mutedText }}>
          {bio || `A short story about ${name} will appear here once the photographer fills in the bio inside the Couple step.`}
        </p>
      </div>
    </div>
  );
};

const CoupleTogetherSlide = ({ bride, groom, photo, story, accent, textOnBg, mutedText, headingFont }) => {
  const ref = React.useRef(null);
  const [visible, setVisible] = React.useState(false);
  React.useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className="relative grid place-items-center min-h-[90vh] py-16"
      data-testid="reveal-slide-couple"
    >
      {photo && (
        <div aria-hidden className="absolute inset-0 overflow-hidden pointer-events-none" style={{ opacity: 0.2 }}>
          <img src={photo} alt="" className="w-full h-full object-cover blur-lg scale-110" />
        </div>
      )}
      <div
        className="relative text-center max-w-2xl px-6 md:px-16 transition-all duration-[1200ms] ease-out"
        style={{
          opacity: visible ? 1 : 0,
          transform: visible ? 'scale(1) translateY(0)' : 'scale(0.95) translateY(40px)',
        }}
      >
        <div
          className="relative mx-auto mb-6 rounded-2xl overflow-hidden"
          style={{
            width: 'min(72vw, 380px)',
            aspectRatio: '4/5',
            background: `${accent}18`,
            border: `1px solid ${accent}55`,
            boxShadow: '0 35px 70px rgba(0,0,0,0.55)',
          }}
        >
          <img src={photo} alt="Couple" loading="lazy" decoding="async" className="w-full h-full object-cover" />
        </div>
        <div className="text-[10px] tracking-[0.4em] uppercase mb-2" style={{ color: accent }}>Together</div>
        <div
          className="font-display text-4xl md:text-5xl mb-3"
          style={{ color: textOnBg, fontFamily: `${headingFont}, serif` }}
        >
          {groom} <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>&amp;</em> {bride}
        </div>
        <p className="text-[15px] leading-relaxed" style={{ color: mutedText }}>
          {story || `Their story will be filled in by the photographer in the Couple step — the joint paragraph of how they met, fell in love, and decided to spend forever together.`}
        </p>
      </div>
    </div>
  );
};

const WeddingDetailsSlide = ({ date, time, nakshatram, muhurtam, venue, accent, textOnBg, mutedText, headingFont }) => {
  const rows = [
    { label: 'Date',       value: date,       testid: 'detail-date' },
    { label: 'Time',       value: time,       testid: 'detail-time' },
    { label: 'Muhurtam',   value: muhurtam,   testid: 'detail-muhurtam' },
    { label: 'Nakshatram', value: nakshatram, testid: 'detail-nakshatram' },
    { label: 'Venue',      value: venue,      testid: 'detail-venue' },
  ].filter((r) => r.value);
  if (rows.length === 0) return null;
  return (
    <section
      className="relative max-w-3xl mx-auto px-6 md:px-16 py-16"
      data-testid="wedding-details-panel"
    >
      <Eyebrow accent={accent}>◆ Wedding details</Eyebrow>
      <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
        Save the <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>moment.</em>
      </SectionHeading>
      <dl
        className="mt-6 rounded-2xl divide-y"
        style={{
          background: `${accent}10`,
          border: `1px solid ${accent}33`,
        }}
      >
        {rows.map((r) => (
          <div
            key={r.testid}
            className="flex items-baseline justify-between gap-6 py-3 px-5"
            style={{ borderColor: `${accent}22` }}
            data-testid={r.testid}
          >
            <dt className="text-[11px] tracking-[0.3em] uppercase" style={{ color: mutedText }}>{r.label}</dt>
            <dd className="font-display text-lg text-right" style={{ color: textOnBg }}>{r.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
};

const SequentialPhotoReveal = ({
  pageBg, accent, textOnBg, mutedText, headingFont,
  bride, groom, heroPhoto,
  brideBio, groomBio, coupleStory,
  weddingDate, weddingTime, venue, nakshatram, muhurtam,
}) => (
  <section
    className="relative"
    data-testid="sequential-photo-reveal"
    style={{ paddingTop: '2rem', paddingBottom: '2rem', background: pageBg }}
  >
    <div className="max-w-3xl mx-auto px-6 md:px-16 text-center mb-6">
      <Eyebrow accent={accent}>◆ Meet the couple</Eyebrow>
      <SectionHeading font={headingFont} color={textOnBg} accent={accent}>
        Two stories <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>one love.</em>
      </SectionHeading>
      <p className="mt-2 text-sm" style={{ color: mutedText }}>
        Scroll to meet {groom}, then {bride}, then the two of them together.
      </p>
    </div>

    <SideRevealSlide
      side="left"
      label="The Groom"
      name={groom}
      bio={groomBio}
      photo={REVEAL_SHOTS.groom}
      accent={accent}
      textOnBg={textOnBg}
      mutedText={mutedText}
      headingFont={headingFont}
      testid="reveal-slide-groom"
    />
    <SideRevealSlide
      side="right"
      label="The Bride"
      name={bride}
      bio={brideBio}
      photo={REVEAL_SHOTS.bride}
      accent={accent}
      textOnBg={textOnBg}
      mutedText={mutedText}
      headingFont={headingFont}
      testid="reveal-slide-bride"
    />
    <CoupleTogetherSlide
      bride={bride}
      groom={groom}
      photo={heroPhoto}
      story={coupleStory}
      accent={accent}
      textOnBg={textOnBg}
      mutedText={mutedText}
      headingFont={headingFont}
    />
    <WeddingDetailsSlide
      date={weddingDate}
      time={weddingTime}
      venue={venue}
      nakshatram={nakshatram}
      muhurtam={muhurtam}
      accent={accent}
      textOnBg={textOnBg}
      mutedText={mutedText}
      headingFont={headingFont}
    />
  </section>
);


/* ────────────────────────────────────────────────────────────────────
   PetalBurstOverlay — petal-shower bursts on scroll / touch.
   Listens to wheel + touchmove and emits a short-lived cluster of
   animated petals from the cursor / touch point. Uses requestAnimationFrame
   for 60fps, and removes finished petals via a state cleanup so we never
   leak DOM nodes.
   ──────────────────────────────────────────────────────────────────── */
const PetalBurstOverlay = ({ accent = '#D4AF37' }) => {
  const [petals, setPetals] = React.useState([]);
  const lastEmit = React.useRef(0);

  React.useEffect(() => {
    const emit = (x, y) => {
      const now = Date.now();
      if (now - lastEmit.current < 150) return; // throttle
      lastEmit.current = now;
      const burst = Array.from({ length: 5 }).map((_, i) => ({
        id: `${now}-${i}`,
        x: x + (Math.random() - 0.5) * 40,
        y: y + (Math.random() - 0.5) * 20,
        dx: (Math.random() - 0.5) * 140,
        dy: 120 + Math.random() * 200,
        rot: (Math.random() - 0.5) * 540,
        size: 10 + Math.random() * 14,
        hue: ['#F5C2D6', '#FCE0A6', accent, '#FFB0C5', '#FFD8A8'][Math.floor(Math.random() * 5)],
        born: now,
      }));
      setPetals((p) => [...p, ...burst].slice(-80));
    };

    const onWheel = (e) => emit(e.clientX || window.innerWidth / 2, e.clientY || 120);
    const onTouchMove = (e) => {
      const t = e.touches?.[0];
      if (t) emit(t.clientX, t.clientY);
    };
    let lastPointerEmit = 0;
    const onPointerMove = (e) => {
      // Pointer-move can fire 100+ times/sec — throttle stricter than scroll.
      const now = Date.now();
      if (now - lastPointerEmit < 250) return;
      lastPointerEmit = now;
      emit(e.clientX, e.clientY);
    };
    window.addEventListener('wheel',       onWheel,       { passive: true });
    window.addEventListener('touchmove',   onTouchMove,   { passive: true });
    window.addEventListener('pointermove', onPointerMove, { passive: true });

    const sweep = setInterval(() => {
      const cutoff = Date.now() - 2200;
      setPetals((p) => p.filter((x) => x.born > cutoff));
    }, 600);

    return () => {
      window.removeEventListener('wheel', onWheel);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('pointermove', onPointerMove);
      clearInterval(sweep);
    };
  }, [accent]);

  return (
    <div
      aria-hidden
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 30,
        overflow: 'hidden',
      }}
      data-testid="petal-burst-overlay"
    >
      {petals.map((p) => (
        <span
          key={p.id}
          style={{
            position: 'absolute',
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size * 1.4,
            borderRadius: '40% 60% 60% 40% / 60% 30% 70% 40%',
            background: `linear-gradient(180deg, ${p.hue}cc, ${p.hue}99)`,
            boxShadow: `0 0 12px ${p.hue}66`,
            transform: 'translate3d(0,0,0)',
            animation: 'maja-petal-fall 2.1s ease-out forwards',
            '--dx': `${p.dx}px`,
            '--dy': `${p.dy}px`,
            '--rot': `${p.rot}deg`,
          }}
        />
      ))}
      <style>{`
        @keyframes maja-petal-fall {
          0%   { opacity: 0;  transform: translate3d(0, -10px, 0) rotate(0deg); }
          15%  { opacity: 1; }
          100% { opacity: 0;  transform: translate3d(var(--dx, 0), var(--dy, 100px), 0) rotate(var(--rot, 180deg)); }
        }
      `}</style>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────
   PreviewFooter — the very last thing the guest scrolls into.
   Renders the couple photo as a full-bleed background (zoomed slow),
   with the bride+groom names overlaid in a glassy card. Caps the rich
   preview with a "matched bookend" to the opening banner.
   ──────────────────────────────────────────────────────────────────── */
const PreviewFooter = ({ couplePhoto, bride, groom, accent, headingFont }) => {
  const ref = React.useRef(null);
  const [visible, setVisible] = React.useState(false);
  React.useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.2 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <section
      ref={ref}
      className="relative overflow-hidden"
      style={{ minHeight: '70vh' }}
      data-testid="preview-footer"
    >
      {/* Couple-photo bg — zoomed and slow-panned via CSS keyframes */}
      <div aria-hidden className="absolute inset-0 pointer-events-none">
        {couplePhoto && (
          <img
            src={couplePhoto}
            alt=""
            className="w-full h-full object-cover"
            style={{
              transform: visible ? 'scale(1.05)' : 'scale(1.15)',
              transition: 'transform 6s ease-out',
              opacity: 0.45,
            }}
          />
        )}
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(180deg, rgba(8,5,3,0.4) 0%, rgba(8,5,3,0.85) 100%)',
          }}
        />
      </div>

      <div
        className="relative grid place-items-center text-center px-6 md:px-16"
        style={{ minHeight: '70vh' }}
      >
        <div
          className="rounded-2xl px-8 py-10 max-w-xl"
          style={{
            background: 'rgba(8,5,3,0.4)',
            border: `1px solid ${accent}55`,
            backdropFilter: 'blur(8px)',
            opacity: visible ? 1 : 0,
            transform: visible ? 'translateY(0)' : 'translateY(40px)',
            transition: 'opacity 1.2s ease-out, transform 1.2s ease-out',
          }}
          data-testid="preview-footer-card"
        >
          <div className="text-[10px] tracking-[0.4em] uppercase mb-3" style={{ color: accent }}>
            ◆ With love
          </div>
          <div
            className="font-display text-4xl md:text-5xl mb-3"
            style={{ color: '#FFF8DC', fontFamily: `${headingFont}, serif` }}
          >
            {groom} <em style={{ color: accent, fontFamily: '"Great Vibes", cursive', fontStyle: 'italic' }}>&amp;</em> {bride}
          </div>
          <div className="text-sm tracking-[0.2em] uppercase" style={{ color: 'rgba(255,248,220,0.7)' }}>
            Thank you for being part of our forever
          </div>
        </div>
      </div>
    </section>
  );
};

export default DesignFullPreview;
