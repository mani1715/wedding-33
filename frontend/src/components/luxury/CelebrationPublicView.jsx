/**
 * CelebrationPublicView — public viewer for NON-WEDDING invitations
 * (baby_birthday, half_saree, puberty, dhoti).
 *
 * 2026-09 — Major redesign: this view now mirrors the WEDDING invitation
 * pattern exactly (cinematic dark-luxe page, big middle banner with the
 * celebrant's name, full-page banner-design background, scroll-triggered
 * animations on every section and a "thank-you" closing footer). Only the
 * celebrant data and the design palette change per category — the layout
 * is identical to the wedding viewer so users who saw a wedding preview
 * recognise this immediately.
 *
 * Props:
 *   data         — the invitation document (slug, celebrant_info, venue, …)
 *   previewMode  — boolean. When true the page additionally renders the
 *                  watermark overlay, the demo pill, a sticky "Use this
 *                  design" CTA and the cinematic opening curtain. When
 *                  false (live public viewing) those overlays are hidden.
 *   previewExitTo — optional override for the sticky CTA target URL.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  Calendar, MapPin, Heart, Sparkles, Radio, ExternalLink,
  Image as ImageIcon, Clock, ArrowRight, X,
} from 'lucide-react';
import WishesWallSection from '@/components/luxury/WishesWallSection';
import MajaReferralCTA from '@/components/luxury/MajaReferralCTA';
import ScrollSection from '@/components/luxury/ScrollSection';
import WatermarkOverlay from '@/components/luxury/WatermarkOverlay';
import PetalConfetti from '@/components/luxury/PetalConfetti';
import '@/styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/* ── PER-CATEGORY THEME PALETTE ─────────────────────────────────────────
 * Each category mirrors the wedding viewer's dark-luxe background but
 * with category-specific accent + gradient. Pageboard stays dark; only
 * the hero gradient, the section accent and the petal-confetti colour
 * change. This is what gives the customer the impression of "different
 * design but same pattern". */
const CATEGORY_THEME = {
  baby_birthday: {
    label: 'Baby Birthday',
    label_traditional: '',
    icon: '🎂',
    eyebrow: 'A Joyful Celebration',
    primary: '#FF8FBF',            // hero accent
    accent: '#FFD27D',
    heroGradient: 'linear-gradient(135deg,#3a1727 0%,#7a3052 45%,#FFB6C1 100%)',
    sectionBg: '#0b0908',
    softBg: 'rgba(255,143,191,0.07)',
    softBorder: 'rgba(255,143,191,0.28)',
    petals: ['#FF69B4', '#FFB6C1', '#FFD27D', '#FFF8DC'],
    rsvpVerb: 'Bless the Birthday Star',
    blessingVerb: 'Send Birthday Wishes',
    storyHeading: 'A Year (or More) of Joy',
    venueHeading: 'Where the Joy Unfolds',
    closing: 'Thank you for being part of our little one\'s story.',
  },
  half_saree: {
    label: 'Half Saree Ceremony',
    label_traditional: 'Langa Voni · Pavadai Daavani',
    icon: '👗',
    eyebrow: 'A Coming-of-Age Tradition',
    primary: '#E84393',
    accent: '#FFD700',
    heroGradient: 'linear-gradient(135deg,#3a0e23 0%,#8B0A50 45%,#FFD700 100%)',
    sectionBg: '#0b0908',
    softBg: 'rgba(232,67,147,0.07)',
    softBorder: 'rgba(232,67,147,0.28)',
    petals: ['#FF1493', '#FFD700', '#FF69B4', '#FFF8DC'],
    rsvpVerb: 'Shower Your Blessings',
    blessingVerb: 'Leave a Blessing',
    storyHeading: 'A Story of Silk, Gold & Grace',
    venueHeading: 'Where Tradition Meets Today',
    closing: 'Thank you for blessing our daughter on this beautiful threshold.',
  },
  puberty: {
    label: 'Puberty Ceremony',
    label_traditional: 'Manjal Neerattu Vizha',
    icon: '🌸',
    eyebrow: 'A Sacred Threshold',
    primary: '#FF8C00',
    accent: '#FFD700',
    heroGradient: 'linear-gradient(135deg,#321906 0%,#9b5302 45%,#FFD700 100%)',
    sectionBg: '#0b0908',
    softBg: 'rgba(255,140,0,0.07)',
    softBorder: 'rgba(255,140,0,0.32)',
    petals: ['#FFD700', '#FF8C00', '#FFB347', '#FFF8DC'],
    rsvpVerb: 'Bless the Celebrant',
    blessingVerb: 'Send Blessings',
    storyHeading: 'A Sacred Coming of Age',
    venueHeading: 'Where Blessings Gather',
    closing: 'Thank you for blessing our daughter as she steps into a new chapter.',
  },
  dhoti: {
    label: 'Dhoti Ceremony',
    label_traditional: 'Vetti Kattum Vizha',
    icon: '👔',
    eyebrow: 'A Boy Becomes a Young Man',
    primary: '#9F86FF',
    accent: '#FFD700',
    heroGradient: 'linear-gradient(135deg,#1a0a3a 0%,#3a1d7a 45%,#FFD700 100%)',
    sectionBg: '#0b0908',
    softBg: 'rgba(159,134,255,0.07)',
    softBorder: 'rgba(159,134,255,0.30)',
    petals: ['#7B68EE', '#FFD700', '#9F86FF', '#FFF8DC'],
    rsvpVerb: 'Bless the Young Man',
    blessingVerb: 'Send Blessings',
    storyHeading: 'From Boyhood to Young Man',
    venueHeading: 'Where Family Pride Gathers',
    closing: 'Thank you for being part of our son\'s proud first step.',
  },
};

const ordinal = (n) => {
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

const resolveUrl = (u) => {
  if (!u) return '';
  if (u.startsWith('data:') || u.startsWith('blob:')) return u;
  if (u.startsWith('http')) {
    return u.replace(/(https?:\/\/[^/]+)\/uploads\//i, `$1/api/uploads/`);
  }
  const path = u.startsWith('/uploads/') ? `/api${u}` : u;
  return `${API_URL}${path}`;
};

/* ── Countdown ─────────────────────────────────────────────────────── */
const CountdownTile = ({ v, l, accent }) => (
  <div className="flex flex-col items-center px-3 sm:px-4 py-2 rounded-2xl backdrop-blur"
    style={{
      background: 'rgba(255,248,220,0.08)',
      border: '1px solid rgba(255,248,220,0.18)',
      minWidth: 60,
    }}>
    <span className="text-2xl sm:text-3xl font-semibold" style={{ color: accent }}>
      {String(v).padStart(2, '0')}
    </span>
    <span className="text-[10px] sm:text-xs uppercase tracking-[0.18em]"
      style={{ color: 'rgba(255,248,220,0.7)' }}>{l}</span>
  </div>
);

const Countdown = ({ targetDate, accent }) => {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!targetDate) return null;
  const t = new Date(targetDate).getTime();
  const diff = t - now;
  if (Number.isNaN(t)) return null;
  if (diff <= 0) {
    return (
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur"
        style={{
          background: 'rgba(255,248,220,0.08)',
          border: '1px solid rgba(255,248,220,0.18)',
          color: accent,
        }}
        data-testid="celebration-countdown-done">
        <Sparkles className="w-4 h-4" /> The day has arrived.
      </div>
    );
  }
  const days = Math.floor(diff / 86_400_000);
  const hours = Math.floor((diff % 86_400_000) / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  const secs = Math.floor((diff % 60_000) / 1000);
  return (
    <div className="flex gap-2 sm:gap-3" data-testid="celebration-countdown">
      <CountdownTile v={days} l="Days" accent={accent} />
      <CountdownTile v={hours} l="Hrs" accent={accent} />
      <CountdownTile v={mins} l="Mins" accent={accent} />
      <CountdownTile v={secs} l="Secs" accent={accent} />
    </div>
  );
};

/* ── Opening curtain — mirrors wedding's cinematic intro ──────────── */
const OpeningCurtain = ({ name, subtitle, accent, gradient, onDone }) => {
  useEffect(() => {
    const id = setTimeout(onDone, 1900);
    return () => clearTimeout(id);
  }, [onDone]);

  return (
    <motion.div
      key="curtain"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.6 } }}
      transition={{ duration: 0.4 }}
      className="fixed inset-0 z-[300] grid place-items-center"
      style={{
        background: 'radial-gradient(ellipse at center,#1f1612 0%,#0b0908 70%, #000 100%)',
      }}
      data-testid="celebration-opening-curtain"
    >
      <div className="absolute inset-0 opacity-30" style={{ background: gradient }} />
      <div className="relative text-center px-6">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="text-[10px] sm:text-xs tracking-[0.42em] uppercase mb-5"
          style={{ color: accent }}
        >
          ✦  Sample Invitation Preview  ✦
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, scale: 0.7, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-5xl sm:text-7xl md:text-8xl leading-none"
          style={{ color: '#FFF8DC', letterSpacing: '-0.01em' }}
          data-testid="celebration-opening-name"
        >
          {name}
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.7 }}
          className="text-base sm:text-xl uppercase tracking-[0.32em] mt-4"
          style={{ color: 'rgba(255,248,220,0.85)' }}
        >
          {subtitle}
        </motion.p>
      </div>
    </motion.div>
  );
};

/* ── Demo pill (preview-only) ─────────────────────────────────────── */
const DemoPill = ({ accent, label }) => (
  <div className="fixed top-3 left-1/2 -translate-x-1/2 z-40 inline-flex items-center gap-2 px-3 py-1.5 rounded-full backdrop-blur shadow-lg"
    style={{
      background: 'rgba(11,9,8,0.78)',
      border: `1px solid ${accent}66`,
      color: '#FFF8DC',
    }}
    data-testid="celebration-demo-pill">
    <Sparkles className="w-3 h-3" style={{ color: accent }} />
    <span className="text-[10px] tracking-[0.32em] uppercase">{label}</span>
  </div>
);

/* ── Sticky "Use this design" CTA at bottom (preview-only) ────────── */
const UseThisDesignCTA = ({ accent, targetUrl }) => (
  <div
    className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 inline-flex items-center gap-2 px-4 py-2.5 rounded-full shadow-xl backdrop-blur"
    style={{
      background: 'rgba(11,9,8,0.92)',
      border: `1px solid ${accent}66`,
      color: '#FFF8DC',
    }}
    data-testid="celebration-use-design-cta"
  >
    <Sparkles className="w-3.5 h-3.5" style={{ color: accent }} />
    <span className="text-[11px] tracking-[0.28em] uppercase">Sample preview</span>
    <span className="w-px h-3" style={{ background: 'rgba(255,248,220,0.2)' }} />
    {targetUrl
      ? (
        <Link
          to={targetUrl}
          className="inline-flex items-center gap-1 text-[11px] tracking-[0.22em] uppercase hover:opacity-80 transition-opacity"
          style={{ color: accent }}
          data-testid="celebration-use-design-link"
        >
          Use this design <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      )
      : (
        <button
          type="button"
          onClick={() => window.history.length > 1 ? window.history.back() : (window.location.href = '/')}
          className="inline-flex items-center gap-1 text-[11px] tracking-[0.22em] uppercase hover:opacity-80 transition-opacity"
          style={{ color: accent }}
          data-testid="celebration-use-design-link"
        >
          Back to designs <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    <Link
      to="/"
      className="ml-1 w-6 h-6 rounded-full grid place-items-center hover:bg-white/10 transition-colors"
      aria-label="Close preview"
      data-testid="celebration-close-preview"
    >
      <X className="w-3 h-3" />
    </Link>
  </div>
);

/* ── RSVP form ─────────────────────────────────────────────────────
 * In preview mode the submission is mocked (no backend hit) so testers
 * can play with the form without polluting the DB. In live mode it
 * POSTs to /api/rsvp?slug=... like before. */
const RSVPInline = ({ slug, accent, verb, previewMode }) => {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [guests, setGuests] = useState(1);
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('yes');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { setErr('Please enter your name'); return; }
    if (!previewMode && !/^\+[1-9]\d{1,14}$/.test(phone.trim())) {
      setErr('Phone must be in E.164 format (e.g. +919876543210)');
      return;
    }
    setSubmitting(true); setErr('');
    try {
      if (previewMode) {
        // Demo mode — just simulate a 600 ms delay
        await new Promise((r) => setTimeout(r, 600));
        setDone(true);
        return;
      }
      await axios.post(`${API_URL}/api/rsvp?slug=${slug}`, {
        guest_name: name.trim(),
        guest_phone: phone.trim(),
        status,
        guest_count: Math.max(1, Math.min(10, Number(guests) || 1)),
        message: message.trim() || null,
      });
      setDone(true);
    } catch (e2) {
      const d = e2.response?.data?.detail;
      setErr(typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x.msg).join('; ') : 'Could not submit RSVP. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="text-center py-8" data-testid="rsvp-success">
        <Sparkles className="w-10 h-10 mx-auto mb-2" style={{ color: accent }} />
        <p className="text-lg font-medium" style={{ color: '#FFF8DC' }}>
          Thank you! Your blessing has been received.
        </p>
      </div>
    );
  }

  const inputStyle = {
    background: 'rgba(255,248,220,0.05)',
    border: '1px solid rgba(255,248,220,0.18)',
    color: '#FFF8DC',
  };

  return (
    <form onSubmit={submit} className="space-y-3.5" data-testid="rsvp-form">
      <input
        type="text"
        placeholder="Your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full px-4 py-3 rounded-xl focus:outline-none placeholder:opacity-50"
        style={inputStyle}
        data-testid="rsvp-name"
      />
      <input
        type="tel"
        placeholder={previewMode ? 'Phone (any format for demo)' : 'Phone (e.g. +919876543210)'}
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        className="w-full px-4 py-3 rounded-xl focus:outline-none placeholder:opacity-50"
        style={inputStyle}
        data-testid="rsvp-phone"
      />
      <div className="grid grid-cols-2 gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="px-4 py-3 rounded-xl focus:outline-none"
          style={inputStyle}
          data-testid="rsvp-status"
        >
          <option value="yes">I will attend</option>
          <option value="maybe">Maybe</option>
          <option value="no">Cannot make it</option>
        </select>
        <input
          type="number"
          min="1"
          max="10"
          placeholder="Guests"
          value={guests}
          onChange={(e) => setGuests(e.target.value)}
          className="px-4 py-3 rounded-xl focus:outline-none placeholder:opacity-50"
          style={inputStyle}
          data-testid="rsvp-guests"
        />
      </div>
      <textarea
        rows={3}
        placeholder="Leave a message (optional)"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="w-full px-4 py-3 rounded-xl focus:outline-none resize-none placeholder:opacity-50"
        style={inputStyle}
        data-testid="rsvp-message"
      />
      {err && <p className="text-sm" style={{ color: '#ff8788' }} data-testid="rsvp-error">{err}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-full py-3 rounded-xl font-medium disabled:opacity-60 transition-transform hover:scale-[1.01]"
        style={{ background: accent, color: '#1c1410' }}
        data-testid="rsvp-submit"
      >
        {submitting ? 'Sending…' : `${verb} →`}
      </button>
    </form>
  );
};

/* ── PHOTO GALLERY ────────────────────────────────────────────────── */
const PhotoGallery = ({ photos, accent, title }) => {
  if (!photos || photos.length === 0) return null;
  return (
    <section className="px-6 md:px-12 py-16" data-testid="celebration-gallery">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <span className="text-xs tracking-[0.32em] uppercase"
            style={{ color: accent }}>
            Moments to remember
          </span>
          <h2 className="font-display text-3xl sm:text-5xl mt-2"
            style={{ color: '#FFF8DC' }}>
            {title || 'Cherished Photos'}
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4">
          {photos.map((url, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.94, y: 20 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.6, delay: idx * 0.05 }}
              className="aspect-square rounded-2xl overflow-hidden shadow-2xl"
              style={{
                background: 'rgba(255,248,220,0.05)',
                border: '1px solid rgba(255,248,220,0.1)',
              }}
              data-testid={`celebration-photo-${idx}`}
            >
              <img
                src={resolveUrl(url)}
                alt={`Memory ${idx + 1}`}
                loading="lazy"
                className="w-full h-full object-cover hover:scale-110 transition-transform duration-700"
              />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

/* ── MAIN VIEWER ──────────────────────────────────────────────────── */
const CelebrationPublicView = ({ data, previewMode = false, previewExitTo = null }) => {
  const cat = data?.invitation_category || 'baby_birthday';
  const theme = CATEGORY_THEME[cat] || CATEGORY_THEME.baby_birthday;
  const ci = data?.celebrant_info || {};

  // Apply the SAME dark-luxe body as wedding so the page background extends
  // edge-to-edge and feels cinematic. Cleans up on unmount so navigating
  // elsewhere doesn't leave the luxe class behind.
  useEffect(() => {
    const prevBg = document.body.style.background;
    document.body.classList.add('luxe');
    document.body.style.background = theme.sectionBg;
    return () => {
      document.body.classList.remove('luxe');
      document.body.style.background = prevBg;
    };
  }, [theme.sectionBg]);

  const [opening, setOpening] = useState(!!previewMode);
  // Safety net — never leave a user on a black curtain
  useEffect(() => {
    if (!opening) return;
    const id = setTimeout(() => setOpening(false), 4500);
    return () => clearTimeout(id);
  }, [opening]);

  const celebrantName = ci.celebrant_name || data?.groom_name || 'Our Star';
  const firstName = celebrantName.split(' ')[0];
  const nickname = ci.nickname_visible ? ci.nickname : null;
  const father = ci.father_name || '';
  const mother = ci.mother_name || '';
  const parents = [father, mother].filter(Boolean).join(' & ');
  const story = ci.story || data?.love_story || '';
  const extras = Array.isArray(ci.extra_photos) ? ci.extra_photos.filter(Boolean) : [];
  const coverPhoto = data?.couple_photo_url || data?.bride_photo_url || data?.groom_photo_url || '';
  const allPhotos = [coverPhoto, ...extras].filter(Boolean);
  const eventDate = data?.event_date ? new Date(data.event_date) : null;
  const formattedDate = eventDate
    ? eventDate.toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
    : 'TBA';
  const formattedTime = eventDate
    ? eventDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    : '';
  const venue = data?.venue || '';
  const city = data?.city || '';
  const mapLink = data?.map_settings?.map_link || '';
  const videoLink = ci.video_link || '';
  const liveLink = ci.live_link || '';
  const closingMsg = ci.closing_message || theme.closing;

  const subtitle = useMemo(() => {
    if (cat === 'baby_birthday' && ci.age_turning) {
      return `Turning ${ordinal(Number(ci.age_turning))}`;
    }
    return theme.eyebrow;
  }, [cat, ci.age_turning, theme.eyebrow]);

  /* ── RENDER ─────────────────────────────────────────────────────── */
  return (
    <div className="luxe-page min-h-screen relative"
      data-testid="celebration-public-view"
      data-category={cat}
      style={{ background: theme.sectionBg, color: '#FFF8DC' }}
    >
      {/* Preview-only celebratory confetti drifting in the background */}
      {previewMode && (
        <PetalConfetti
          colors={theme.petals}
          count={28}
          className="pointer-events-none fixed inset-0 z-[1]"
        />
      )}

      {/* Preview-only watermark + demo pill */}
      {previewMode && <WatermarkOverlay text={`${theme.label} · MAJA Demo`} />}
      {previewMode && <DemoPill accent={theme.accent} label={`Preview · ${theme.label}`} />}

      {/* ── OPENING CURTAIN (preview only) ─────────────────────────── */}
      <AnimatePresence>
        {previewMode && opening && (
          <OpeningCurtain
            name={firstName}
            subtitle={subtitle}
            accent={theme.accent}
            gradient={theme.heroGradient}
            onDone={() => setOpening(false)}
          />
        )}
      </AnimatePresence>

      {/* ── HERO — middle banner with celebrant name ────────────────── */}
      <motion.section
        className="relative overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: previewMode && opening ? 0 : 1 }}
        transition={{ duration: 0.8 }}
        data-testid="celebration-hero"
      >
        {/* Full-banner design background — gradient + cover photo + dark
            legibility overlay. Same recipe as wedding HeroCover. */}
        <div className="absolute inset-0" style={{ background: theme.heroGradient }} />
        {coverPhoto && (
          <div className="absolute inset-0 overflow-hidden">
            <motion.img
              src={resolveUrl(coverPhoto)}
              alt={celebrantName}
              initial={{ scale: 1.12 }}
              animate={{ scale: 1 }}
              transition={{ duration: 8, ease: 'easeOut' }}
              className="w-full h-full object-cover"
              style={{ opacity: 0.5 }}
            />
          </div>
        )}
        <div className="absolute inset-0" style={{
          background: 'linear-gradient(180deg, rgba(11,9,8,0.25) 0%, rgba(11,9,8,0.85) 100%)',
        }} />

        {/* monogram corners — purely decorative, gives the wedding-grade feel */}
        <div className="absolute top-6 left-6 sm:top-10 sm:left-10 text-2xl sm:text-4xl opacity-80"
          style={{ color: theme.accent }}>✦</div>
        <div className="absolute top-6 right-6 sm:top-10 sm:right-10 text-2xl sm:text-4xl opacity-80"
          style={{ color: theme.accent }}>✦</div>
        <div className="absolute bottom-6 left-6 sm:bottom-10 sm:left-10 text-2xl sm:text-4xl opacity-80"
          style={{ color: theme.accent }}>✦</div>
        <div className="absolute bottom-6 right-6 sm:bottom-10 sm:right-10 text-2xl sm:text-4xl opacity-80"
          style={{ color: theme.accent }}>✦</div>

        <div className="relative z-10 px-6 sm:px-12 py-24 sm:py-36 max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: previewMode && opening ? 0 : 1, y: 0 }}
            transition={{ duration: 1.1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-6 backdrop-blur"
              style={{
                background: 'rgba(11,9,8,0.45)',
                border: `1px solid ${theme.accent}66`,
                color: theme.accent,
              }}
              data-testid="hero-category-pill">
              <span className="text-lg">{theme.icon}</span>
              <span className="text-xs uppercase tracking-[0.32em] font-medium">
                {theme.label}
              </span>
            </div>

            {theme.label_traditional && (
              <p className="text-xs sm:text-sm tracking-[0.32em] uppercase mb-3"
                style={{ color: theme.accent, opacity: 0.85 }}>
                {theme.label_traditional}
              </p>
            )}

            <p className="text-sm sm:text-base uppercase tracking-[0.28em] mb-5"
              style={{ color: '#FFF8DC', opacity: 0.85, textShadow: '0 2px 12px rgba(0,0,0,0.45)' }}
              data-testid="hero-subtitle">
              {subtitle}
            </p>

            <h1 className="font-display text-6xl sm:text-8xl md:text-9xl mb-3 leading-[0.95] tracking-tight"
              style={{
                color: '#FFF8DC',
                textShadow: '0 8px 38px rgba(0,0,0,0.45)',
                letterSpacing: '-0.01em',
              }}
              data-testid="hero-celebrant-name">
              {celebrantName}
            </h1>

            {nickname && (
              <p className="text-lg sm:text-2xl italic mb-4 opacity-95"
                style={{ color: theme.accent, fontFamily: 'cursive' }}
                data-testid="hero-nickname">
                {`"${nickname}"`}
              </p>
            )}

            {parents && (
              <p className="text-sm sm:text-base mb-6 opacity-90"
                style={{ color: '#FFF8DC', textShadow: '0 2px 10px rgba(0,0,0,0.4)' }}
                data-testid="hero-parents">
                Beloved child of <span className="font-medium">{parents}</span>
              </p>
            )}

            {eventDate && (
              <div className="flex flex-col items-center gap-5 mt-8">
                <div className="flex items-center gap-3 px-4 py-2 rounded-full backdrop-blur"
                  style={{
                    background: 'rgba(11,9,8,0.55)',
                    border: '1px solid rgba(255,248,220,0.18)',
                    color: '#FFF8DC',
                  }}
                  data-testid="hero-date">
                  <Calendar className="w-5 h-5" style={{ color: theme.accent }} />
                  <span className="text-base sm:text-lg font-medium">{formattedDate}</span>
                  {formattedTime && <>
                    <span className="opacity-70">·</span>
                    <Clock className="w-5 h-5" style={{ color: theme.accent }} />
                    <span>{formattedTime}</span>
                  </>}
                </div>
                <Countdown targetDate={data?.event_date} accent={theme.accent} />
              </div>
            )}
          </motion.div>
        </div>
      </motion.section>

      {/* ── CELEBRANT PHOTO SHOWCASE (3 large cards) ─────────────── */}
      {allPhotos.length > 0 && (
        <ScrollSection
          as="section"
          className="px-6 md:px-12 py-20 relative"
          testid="celebration-showcase"
        >
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{ background: theme.heroGradient }}
          />
          <div className="max-w-5xl mx-auto relative">
            <div className="text-center mb-10">
              <span className="text-xs tracking-[0.32em] uppercase"
                style={{ color: theme.accent }}>
                {cat === 'baby_birthday' ? 'Our Little One' : 'The Celebrant'}
              </span>
              <h2 className="font-display text-3xl sm:text-5xl mt-2" style={{ color: '#FFF8DC' }}>
                {firstName}
              </h2>
            </div>
            <div className={`grid gap-5 ${allPhotos.length === 1 ? 'grid-cols-1 max-w-sm mx-auto' : allPhotos.length === 2 ? 'grid-cols-1 sm:grid-cols-2 max-w-2xl mx-auto' : 'grid-cols-1 sm:grid-cols-3'}`}>
              {allPhotos.slice(0, 3).map((url, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 24, scale: 0.95 }}
                  whileInView={{ opacity: 1, y: 0, scale: 1 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.8, delay: idx * 0.1, ease: [0.22, 1, 0.36, 1] }}
                  className={`aspect-[3/4] rounded-3xl overflow-hidden shadow-2xl ${idx === 1 ? 'sm:-mt-6' : ''}`}
                  style={{
                    background: 'rgba(255,248,220,0.05)',
                    border: '1px solid rgba(255,248,220,0.1)',
                  }}
                >
                  <img
                    src={resolveUrl(url)}
                    alt={`${celebrantName} ${idx + 1}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-700"
                  />
                </motion.div>
              ))}
            </div>
          </div>
        </ScrollSection>
      )}

      {/* ── STORY ─────────────────────────────────────────────────── */}
      {story && (
        <ScrollSection
          as="section"
          className="px-6 md:px-12 py-20"
          testid="celebration-story"
        >
          <div className="max-w-3xl mx-auto text-center">
            <span className="text-xs tracking-[0.32em] uppercase"
              style={{ color: theme.accent }}>
              Our Story
            </span>
            <h2 className="font-display text-3xl sm:text-5xl mt-2 mb-3"
              style={{ color: '#FFF8DC' }}>
              {theme.storyHeading}
            </h2>
            <div
              className="w-16 h-px mx-auto my-6"
              style={{ background: `linear-gradient(90deg, transparent, ${theme.accent}, transparent)` }}
            />
            <div className="text-base sm:text-lg leading-relaxed whitespace-pre-line"
              style={{ color: 'rgba(255,248,220,0.85)' }}
              dangerouslySetInnerHTML={{ __html: story }} />
          </div>
        </ScrollSection>
      )}

      {/* ── PHOTO GALLERY (full) ──────────────────────────────────── */}
      {allPhotos.length > 1 && (
        <ScrollSection className="" testid="celebration-gallery-scroll">
          <PhotoGallery photos={allPhotos} accent={theme.accent} title="Cherished Photos" />
        </ScrollSection>
      )}

      {/* ── VENUE + MAP ────────────────────────────────────────────── */}
      {(venue || city || mapLink) && (
        <ScrollSection
          as="section"
          className="px-6 md:px-12 py-20"
          testid="celebration-venue"
        >
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <span className="text-xs tracking-[0.32em] uppercase"
                style={{ color: theme.accent }}>
                {theme.venueHeading}
              </span>
              <h2 className="font-display text-3xl sm:text-5xl mt-2"
                style={{ color: '#FFF8DC' }}>Venue</h2>
            </div>
            <div className="rounded-3xl overflow-hidden shadow-2xl"
              style={{
                background: theme.softBg,
                border: `1px solid ${theme.softBorder}`,
                backdropFilter: 'blur(6px)',
              }}>
              <div className="p-8 text-center">
                <MapPin className="w-8 h-8 mx-auto mb-3" style={{ color: theme.accent }} />
                {venue && <p className="text-xl font-medium mb-1"
                  style={{ color: '#FFF8DC' }}>{venue}</p>}
                {city && <p className="text-base opacity-75 mb-4"
                  style={{ color: 'rgba(255,248,220,0.7)' }}>{city}</p>}
                {mapLink && (
                  <a
                    href={mapLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-transform hover:scale-[1.03]"
                    style={{ background: theme.accent, color: '#1c1410' }}
                    data-testid="celebration-map-link"
                  >
                    Open in Maps <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
              {mapLink && mapLink.includes('google.com/maps') && (
                <iframe
                  title="Venue map"
                  src={mapLink.replace('/maps/', '/maps/embed?pb=&q=')}
                  className="w-full"
                  style={{ height: 320, border: 0 }}
                  loading="lazy"
                />
              )}
            </div>
          </div>
        </ScrollSection>
      )}

      {/* ── VIDEO / LIVE LINKS ────────────────────────────────────── */}
      {(videoLink || liveLink) && (
        <ScrollSection
          as="section"
          className="px-6 md:px-12 py-12"
          testid="celebration-media-links"
        >
          <div className="max-w-4xl mx-auto grid sm:grid-cols-2 gap-4">
            {videoLink && (
              <a
                href={videoLink}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-2xl p-6 flex items-center gap-4 hover:shadow-2xl transition-all hover:scale-[1.02]"
                style={{
                  background: theme.softBg,
                  border: `1px solid ${theme.softBorder}`,
                  color: '#FFF8DC',
                }}
                data-testid="celebration-video-link"
              >
                <div className="w-12 h-12 rounded-full grid place-items-center"
                  style={{ background: theme.accent }}>
                  <ImageIcon className="w-6 h-6" style={{ color: '#1c1410' }} />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.22em] opacity-70">Watch the Story</div>
                  <div className="font-medium">Open Video</div>
                </div>
              </a>
            )}
            {liveLink && (
              <a
                href={liveLink}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-2xl p-6 flex items-center gap-4 hover:shadow-2xl transition-all hover:scale-[1.02]"
                style={{
                  background: theme.softBg,
                  border: `1px solid ${theme.softBorder}`,
                  color: '#FFF8DC',
                }}
                data-testid="celebration-live-link"
              >
                <div className="w-12 h-12 rounded-full grid place-items-center"
                  style={{ background: theme.accent }}>
                  <Radio className="w-6 h-6" style={{ color: '#1c1410' }} />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.22em] opacity-70">Live Stream</div>
                  <div className="font-medium">Join Live</div>
                </div>
              </a>
            )}
          </div>
        </ScrollSection>
      )}

      {/* ── RSVP ──────────────────────────────────────────────────── */}
      <ScrollSection
        as="section"
        className="px-6 md:px-12 py-20"
        testid="celebration-rsvp"
      >
        <div className="max-w-xl mx-auto">
          <div className="text-center mb-8">
            <span className="text-xs tracking-[0.32em] uppercase"
              style={{ color: theme.accent }}>
              Your Presence is a Gift
            </span>
            <h2 className="font-display text-3xl sm:text-5xl mt-2"
              style={{ color: '#FFF8DC' }}>RSVP</h2>
          </div>
          <div className="rounded-3xl p-6 sm:p-8 shadow-2xl"
            style={{
              background: theme.softBg,
              border: `1px solid ${theme.softBorder}`,
              backdropFilter: 'blur(8px)',
            }}>
            <RSVPInline
              slug={data?.slug}
              accent={theme.accent}
              verb={theme.rsvpVerb}
              previewMode={previewMode}
            />
          </div>
        </div>
      </ScrollSection>

      {/* ── BLESSINGS / WISHES WALL ───────────────────────────────── */}
      <ScrollSection
        as="section"
        className="px-6 md:px-12 py-20"
        testid="celebration-blessings"
      >
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-10">
            <Heart className="w-8 h-8 mx-auto mb-2" style={{ color: theme.accent }} />
            <span className="text-xs tracking-[0.32em] uppercase"
              style={{ color: theme.accent }}>
              {theme.blessingVerb}
            </span>
            <h2 className="font-display text-3xl sm:text-5xl mt-2"
              style={{ color: '#FFF8DC' }}>Blessings Wall</h2>
          </div>
          {previewMode ? (
            /* Demo wishes — wedding viewer uses the same approach */
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                { name: 'Anita Aunty', message: `Many wishes to dear ${firstName}! May happiness be your forever companion.` },
                { name: 'Vikram Uncle', message: `Such a beautiful moment. Sending love and blessings.` },
                { name: 'Priya', message: `So happy for ${firstName}! Wishing health, joy and laughter.` },
                { name: 'Cousin Tara', message: `Can't wait to celebrate this special day with the family!` },
              ].map((w, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.6, delay: idx * 0.06 }}
                  className="rounded-2xl p-4"
                  style={{
                    background: theme.softBg,
                    border: `1px solid ${theme.softBorder}`,
                  }}
                  data-testid={`celebration-demo-wish-${idx}`}
                >
                  <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,248,220,0.92)' }}>
                    “{w.message}”
                  </p>
                  <p className="text-xs mt-3 tracking-[0.18em] uppercase"
                    style={{ color: theme.accent }}>
                    — {w.name}
                  </p>
                </motion.div>
              ))}
            </div>
          ) : (
            <WishesWallSection slug={data?.slug} />
          )}
        </div>
      </ScrollSection>

      {/* ── THANK-YOU / CLOSING ──────────────────────────────────── */}
      <ScrollSection
        as="section"
        className="relative px-6 md:px-12 py-24 text-center overflow-hidden"
        testid="celebration-closing"
      >
        <div className="absolute inset-0 opacity-20" style={{ background: theme.heroGradient }} />
        <div className="relative max-w-2xl mx-auto">
          <Sparkles className="w-10 h-10 mx-auto mb-5" style={{ color: theme.accent }} />
          <span className="text-xs tracking-[0.42em] uppercase block mb-3"
            style={{ color: theme.accent }}>
            With Heartfelt Gratitude
          </span>
          <h2 className="font-display text-4xl sm:text-6xl mb-6"
            style={{ color: '#FFF8DC', letterSpacing: '-0.01em' }}>
            Thank You
          </h2>
          <div
            className="w-16 h-px mx-auto mb-6"
            style={{ background: `linear-gradient(90deg, transparent, ${theme.accent}, transparent)` }}
          />
          <p className="font-display text-xl sm:text-2xl italic leading-relaxed"
            style={{ color: 'rgba(255,248,220,0.92)' }}
            data-testid="celebration-closing-message">
            {closingMsg}
          </p>
          <p className="text-sm mt-6 tracking-[0.32em] uppercase"
            style={{ color: theme.accent }}>
            — The {parents ? parents.split(' & ').slice(-1)[0] : firstName} Family
          </p>
        </div>
      </ScrollSection>

      {/* ── MAJA FOOTER ──────────────────────────────────────────── */}
      <div className="px-6 md:px-12 pb-10">
        <MajaReferralCTA />
      </div>

      {/* ── FOOTER (celebrant name + brand) ──────────────────────── */}
      <footer className="relative px-6 md:px-12 pt-10 pb-16 text-center"
        style={{ borderTop: `1px solid ${theme.softBorder}` }}
        data-testid="celebration-footer">
        <p className="font-display text-3xl sm:text-4xl"
          style={{ color: '#FFF8DC' }}>
          {celebrantName}
        </p>
        <p className="text-xs tracking-[0.32em] uppercase mt-3"
          style={{ color: theme.accent, opacity: 0.85 }}>
          Crafted with reverence · MAJA Creations
        </p>
      </footer>

      {/* ── Sticky CTA (preview only) ────────────────────────────── */}
      {previewMode && (
        <UseThisDesignCTA
          accent={theme.accent}
          targetUrl={previewExitTo}
        />
      )}
    </div>
  );
};

export default CelebrationPublicView;
