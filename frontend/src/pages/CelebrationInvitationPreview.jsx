/**
 * CelebrationInvitationPreview
 * -----------------------------------------------------------------------------
 * Full live-invitation preview for non-wedding categories (baby_birthday,
 * half_saree, puberty, dhoti).
 *
 * Layout mirrors the wedding DesignFullPreview:
 *   • Full-bleed blurred design image as page background (SoftDesignBackdrop)
 *   • Centered hero "invitation card" rendered like the homepage card
 *     (eyebrow + circular photo bubble + bottom cream panel with celebrant
 *     name, date and venue) — but at a larger, poster size.
 *   • A scroll-down indicator + an "Our Story" / Cherished Photos /
 *     Blessings section below.
 *   • Sticky bottom CTA: "Use this design" → buy flow.
 *
 * Route: /preview/celebration/:category   or
 *        /preview/celebration/:category/:designId
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Sparkles, Heart, MapPin, Calendar, Send, MessageSquare, QrCode, Camera, Share2,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const inOneMonth = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  d.setHours(17, 30, 0, 0);
  return d;
};

const fmtDate = (d) => d.toLocaleDateString('en-IN', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
});

/* ─────────────────────────────────────────────────────────────────────
   Per-category presentation tokens — palette + sample text.
   Mirrors NonWeddingDesignCard so the live preview is visually
   consistent with the homepage card the user clicks from.
   ───────────────────────────────────────────────────────────────────── */
const CATEGORY_TOKENS = {
  baby_birthday: {
    label: 'Baby Birthday',
    eyebrow: 'First Birthday',
    familyLine: 'With Blessings From Our Family',
    accent: '#FF69B4',
    panelTint: 'rgba(255,235,243,0.94)',
    panelText: '#3B1E2B',
    celebrant: 'Manvi Sharma',
    nickname: 'Mini',
    parents: 'Aakash Sharma & Priya Sharma',
    date: inOneMonth(),
    venue: 'The Royal Banquet · Hyderabad',
    photo: 'https://images.unsplash.com/photo-1519689680058-324335c77eba?w=400&q=80&fit=crop',
    story:
      'A year ago, our world was transformed by a tiny pair of footsteps and the brightest of smiles. ' +
      'Manvi has grown into our little sunshine — from her first giggle, to her first tooth, to her first ' +
      'wobbly step. Come help us celebrate one full year of joy, laughter and unconditional love.',
    extraPhotos: [
      'https://images.unsplash.com/photo-1519689680058-324335c77eba?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1492725764893-90b379c2b6e7?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1544027993-37dbfe43562a?w=600&q=80&fit=crop',
    ],
    closing: "Your blessings are her greatest gift. We can't wait to celebrate with you.",
  },
  half_saree: {
    label: 'Half Saree Ceremony',
    eyebrow: 'Half Saree Ceremony',
    familyLine: 'Together With Our Family',
    accent: '#C71585',
    panelTint: 'rgba(255,232,243,0.94)',
    panelText: '#3B0F2B',
    celebrant: 'Meera Karthik',
    nickname: '',
    parents: 'Karthik Iyer & Lakshmi Iyer',
    date: inOneMonth(),
    venue: 'Sri Krishna Kalyana Mandapam · Chennai',
    photo: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&q=80&fit=crop',
    story:
      'Today our little girl steps into a new chapter — draped in her first half-saree, blessed by ' +
      'family, music and tradition. From plaits of jasmine to silk and gold, every detail tells a story ' +
      'of love. We invite you to share this sacred moment with us.',
    extraPhotos: [
      'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1583394293214-28ded15ee548?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1492288991661-058aa541ff43?w=600&q=80&fit=crop',
    ],
    closing: 'Bless our Meera with your love, presence and prayers.',
  },
  puberty: {
    label: 'Puberty Ceremony',
    eyebrow: 'Manjal Neerattu',
    familyLine: 'With Blessings From Our Family',
    accent: '#FF8C00',
    panelTint: 'rgba(255,240,224,0.94)',
    panelText: '#3B1F0F',
    celebrant: 'Anika Sundar',
    nickname: '',
    parents: 'Sundar Murali & Priya Sundar',
    date: inOneMonth(),
    venue: 'Sri Meenakshi Mandapam · Coimbatore',
    photo: 'https://images.unsplash.com/photo-1631049551717-1a2d5c52ca7d?w=400&q=80&fit=crop',
    story:
      'Our daughter has reached a sacred milestone. Surrounded by turmeric, blessings and family, ' +
      'we mark this beautiful coming-of-age — a threshold between childhood and grace. Join us in ' +
      'showering Anika with your warmest wishes.',
    extraPhotos: [
      'https://images.unsplash.com/photo-1631049551717-1a2d5c52ca7d?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1583394293214-28ded15ee548?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&q=80&fit=crop',
    ],
    closing: 'Your blessings light the path ahead.',
  },
  dhoti: {
    label: 'Dhoti Ceremony',
    eyebrow: 'Vetti Kattum Vizha',
    familyLine: 'Together With Our Family',
    accent: '#7B68EE',
    panelTint: 'rgba(232,232,255,0.94)',
    panelText: '#1A1A3B',
    celebrant: 'Arjun Vasanth',
    nickname: '',
    parents: 'Vasanth Krishnan & Geetha Vasanth',
    date: inOneMonth(),
    venue: 'Anjaneyar Temple Mandapam · Madurai',
    photo: 'https://images.unsplash.com/photo-1543342384-1f1350e27861?w=400&q=80&fit=crop',
    story:
      'Today our young man dons the dhoti for the first time — a proud moment of tradition, family ' +
      "and growing up. From childhood's small steps to standing tall in our heritage, we celebrate " +
      "every chapter of Arjun's journey. Be with us as he begins this new one.",
    extraPhotos: [
      'https://images.unsplash.com/photo-1543342384-1f1350e27861?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1576675784201-0e142b423952?w=600&q=80&fit=crop',
      'https://images.unsplash.com/photo-1607113256158-56a934936ef1?w=600&q=80&fit=crop',
    ],
    closing: 'Your presence is our pride.',
  },
};

const resolveImg = (u) => {
  if (!u) return '';
  if (u.startsWith('http') || u.startsWith('data:') || u.startsWith('blob:')) return u;
  return `${API_URL}${u.startsWith('/') ? '' : '/'}${u}`;
};

/* SoftDesignBackdrop — the SAME design image extended to a soft, blurred
   full-viewport background. Lifted from DesignFullPreview so the look
   matches wedding previews exactly. */
const SoftDesignBackdrop = ({ image, accent }) => {
  if (!image) {
    return (
      <div aria-hidden style={{
        position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
        background: `radial-gradient(ellipse at top left, ${accent}1F 0%, transparent 55%),
                     radial-gradient(ellipse at bottom right, ${accent}14 0%, transparent 60%),
                     #1A130B`,
      }} />
    );
  }
  return (
    <>
      <img aria-hidden src={image} alt="" draggable={false} loading="eager" decoding="async"
        style={{
          position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
          width: '100%', height: '100%', objectFit: 'cover',
          filter: 'blur(18px) saturate(1.1)',
          transform: 'scale(1.1)',
          opacity: 0.85,
          willChange: 'transform',
        }}
        data-testid="celebration-preview-backdrop"
      />
      <div aria-hidden style={{
        position: 'fixed', inset: 0, zIndex: 1, pointerEvents: 'none',
        background: 'linear-gradient(180deg, rgba(11,9,8,0.25) 0%, rgba(11,9,8,0.55) 100%)',
      }} />
      <div aria-hidden style={{
        position: 'fixed', left: '4vw', top: '40vh',
        width: 240, height: 240, zIndex: 1, pointerEvents: 'none',
        background: `radial-gradient(circle, ${accent}40 0%, transparent 70%)`,
        filter: 'blur(24px)',
      }} />
      <div aria-hidden style={{
        position: 'fixed', right: '4vw', top: '55vh',
        width: 280, height: 280, zIndex: 1, pointerEvents: 'none',
        background: `radial-gradient(circle, ${accent}33 0%, transparent 70%)`,
        filter: 'blur(26px)',
      }} />
    </>
  );
};

/* HeroInvitationCard — the centered "poster" with design as card background,
   eyebrow at top, circular celebrant photo bubble, and bottom cream/tinted
   panel with family line, big serif celebrant name, date and venue.
   Visually matches NonWeddingDesignCard but at poster scale. */

/* ─────────────────────────────────────────────────────────────────────
   CelebrationOpening — full-screen 2.5 s cinematic intro that mirrors
   the wedding `ZoomInOpening`, but for a single celebrant.

   Background  = the design image (so you immediately recognize the
                 design before the invitation appears).
   Foreground  = eyebrow (e.g. "FIRST BIRTHDAY") + the celebrant name
                 in luxe serif + the date underneath.
   ───────────────────────────────────────────────────────────────────── */
const CelebrationOpening = ({ image, token, onComplete }) => {
  useEffect(() => {
    if (!onComplete) return undefined;
    const t = setTimeout(() => onComplete(), 2500);
    return () => clearTimeout(t);
  }, [onComplete]);

  return (
    <motion.div
      role="presentation"
      data-testid="celebration-opening"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999, overflow: 'hidden',
        background: '#0A0707',
      }}
    >
      {/* Zooming design background */}
      <motion.div
        initial={{ scale: 1.18 }} animate={{ scale: 1.0 }}
        transition={{ duration: 2.5, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: 'absolute', inset: 0,
          backgroundImage: `url("${image || token.photo}")`,
          backgroundSize: 'cover', backgroundPosition: 'center',
        }}
      />
      <div style={{
        position: 'absolute', inset: 0,
        background:
          'radial-gradient(ellipse at center, rgba(8,5,11,0.18) 0%, rgba(8,5,11,0.6) 55%, rgba(8,5,11,0.9) 100%)',
      }} />
      <div style={{
        position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
        textAlign: 'center', padding: '0 24px',
      }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.88, y: 18 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        >
          <div style={{
            fontFamily: 'Cinzel, "Cormorant Garamond", serif',
            fontSize: 'clamp(12px, 1.6vw, 14px)',
            letterSpacing: '0.55em', textTransform: 'uppercase',
            color: token.accent,
            textShadow: '0 1px 8px rgba(0,0,0,0.55)',
            marginBottom: 14,
          }}>
            ◇ {token.eyebrow} ◇
          </div>
          <div style={{
            fontFamily: 'Cinzel, "Cormorant Garamond", serif', fontWeight: 500,
            fontSize: 'clamp(34px, 7vw, 80px)', lineHeight: 1.05,
            letterSpacing: '0.04em', color: '#FFF8DC',
            textShadow: `0 2px 18px rgba(0,0,0,0.6), 0 0 60px ${token.accent}33`,
          }}>
            {token.celebrant}
          </div>
          {token.nickname && (
            <div style={{
              fontFamily: '"Great Vibes", "Pinyon Script", cursive',
              fontSize: 'clamp(24px, 4.5vw, 48px)', color: token.accent,
              margin: '6px 0 2px', textShadow: '0 2px 18px rgba(0,0,0,0.5)',
            }}>
              “{token.nickname}”
            </div>
          )}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ delay: 1.1, duration: 1.0 }}
            style={{
              marginTop: 22, fontFamily: 'Cinzel, serif',
              fontSize: 'clamp(11px, 1.6vw, 14px)',
              letterSpacing: '0.4em', textTransform: 'uppercase',
              color: 'rgba(255,248,220,0.85)',
            }}
          >
            {fmtDate(token.date)}
          </motion.div>
        </motion.div>
      </div>
    </motion.div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   Countdown — live D/H/M/S until the celebration date.
   Uses useSyncExternalStore so the strict React-19 purity lint stays
   happy while the cells still tick every second.
   ───────────────────────────────────────────────────────────────────── */
const tickStore = (() => {
  const listeners = new Set();
  let timer = null;
  const ensureTimer = () => {
    if (timer || listeners.size === 0) return;
    timer = setInterval(() => listeners.forEach((l) => l()), 1000);
  };
  return {
    subscribe(listener) {
      listeners.add(listener);
      ensureTimer();
      return () => {
        listeners.delete(listener);
        if (listeners.size === 0 && timer) { clearInterval(timer); timer = null; }
      };
    },
    getSnapshot() { return Date.now(); },
  };
})();

const useCountdown = (target) => {
  const now = React.useSyncExternalStore(tickStore.subscribe, tickStore.getSnapshot, tickStore.getSnapshot);
  const diff = Math.max(0, target.getTime() - now);
  return {
    d: Math.floor(diff / 86400000),
    h: Math.floor((diff % 86400000) / 3600000),
    m: Math.floor((diff % 3600000) / 60000),
    s: Math.floor((diff % 60000) / 1000),
  };
};

const CountdownBlock = ({ token, accent }) => {
  const { d, h, m, s } = useCountdown(token.date);
  const cell = (label, value) => (
    <div className="text-center px-3 md:px-5 py-3 rounded-xl min-w-[68px] md:min-w-[88px]"
      style={{ background: 'rgba(11,9,8,0.7)', border: `1px solid ${accent}55` }}>
      <div className="font-display text-2xl md:text-4xl"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        {String(value).padStart(2, '0')}
      </div>
      <div className="text-[9px] md:text-[10px] tracking-[0.3em] uppercase mt-1"
        style={{ color: `${accent}` }}>
        {label}
      </div>
    </div>
  );
  return (
    <div className="max-w-3xl mx-auto text-center" data-testid="celebration-preview-countdown">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3" style={{ color: accent }}>
        ◆ Counting down to the day
      </span>
      <h3 className="font-display text-3xl md:text-4xl leading-tight mb-7"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        Save the date.
      </h3>
      <div className="flex items-center justify-center gap-2 md:gap-4">
        {cell('Days', d)}
        {cell('Hours', h)}
        {cell('Minutes', m)}
        {cell('Seconds', s)}
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   EventDetails — date/time/venue block with a Google-Maps deep link.
   ───────────────────────────────────────────────────────────────────── */
const EventDetails = ({ token, accent }) => {
  const mapsHref = `https://www.google.com/maps/search/${encodeURIComponent(token.venue)}`;
  return (
    <div className="max-w-3xl mx-auto" data-testid="celebration-preview-event-details">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
        style={{ color: accent }}>
        ◆ When &amp; Where
      </span>
      <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-8"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        We would love to have you with us.
      </h3>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="rounded-xl px-5 py-6"
          style={{ background: 'rgba(11,9,8,0.78)', border: `1px solid ${accent}44` }}>
          <Calendar className="w-5 h-5 mb-2" style={{ color: accent }} />
          <div className="text-[10px] tracking-[0.3em] uppercase opacity-75 mb-1">Date</div>
          <div className="text-lg" style={{ color: '#FFF8DC' }}>{fmtDate(token.date)}</div>
          <div className="text-sm mt-1" style={{ color: 'rgba(255,248,220,0.7)' }}>
            {token.date.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true })}
          </div>
        </div>
        <div className="rounded-xl px-5 py-6"
          style={{ background: 'rgba(11,9,8,0.78)', border: `1px solid ${accent}44` }}>
          <MapPin className="w-5 h-5 mb-2" style={{ color: accent }} />
          <div className="text-[10px] tracking-[0.3em] uppercase opacity-75 mb-1">Venue</div>
          <div className="text-lg" style={{ color: '#FFF8DC' }}>{token.venue}</div>
          <a href={mapsHref} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 text-[11px] tracking-[0.25em] uppercase mt-3"
            style={{ color: accent }} data-testid="celebration-preview-map-link">
            Open in Google Maps →
          </a>
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   RSVPDemo — visual demo of the RSVP form. In real invitations this
   posts to /api/invitations/{slug}/rsvp, but on the preview page we
   just show a confirmation toast so couples can experience the flow.
   ───────────────────────────────────────────────────────────────────── */
const RSVPDemo = ({ token, accent }) => {
  const [form, setForm] = useState({ name: '', count: 1, attending: 'yes', message: '' });
  const [sent, setSent] = useState(false);
  const onSubmit = (e) => {
    e.preventDefault();
    setSent(true);
    setTimeout(() => setSent(false), 4500);
  };
  return (
    <div className="max-w-xl mx-auto" data-testid="celebration-preview-rsvp">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
        style={{ color: accent }}>
        ◆ Will you be there?
      </span>
      <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-7"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        Kindly <span style={{ color: accent, fontStyle: 'italic' }}>respond.</span>
      </h3>
      <form onSubmit={onSubmit} className="rounded-2xl px-6 py-7 space-y-4"
        style={{ background: 'rgba(11,9,8,0.82)', border: `1px solid ${accent}44`, backdropFilter: 'blur(8px)' }}>
        <label className="block">
          <span className="text-[10px] tracking-[0.3em] uppercase opacity-80">Your name</span>
          <input type="text" required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full mt-1.5 px-3 py-2.5 rounded-md text-[15px] outline-none"
            style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC',
              border: `1px solid ${accent}55`, fontFamily: '"Cormorant Garamond", serif' }}
            data-testid="rsvp-name" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[10px] tracking-[0.3em] uppercase opacity-80">Guests</span>
            <input type="number" min={1} max={20} value={form.count}
              onChange={(e) => setForm({ ...form, count: e.target.value })}
              className="w-full mt-1.5 px-3 py-2.5 rounded-md text-[15px] outline-none"
              style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC',
                border: `1px solid ${accent}55` }}
              data-testid="rsvp-count" />
          </label>
          <label className="block">
            <span className="text-[10px] tracking-[0.3em] uppercase opacity-80">Attending</span>
            <select value={form.attending}
              onChange={(e) => setForm({ ...form, attending: e.target.value })}
              className="w-full mt-1.5 px-3 py-2.5 rounded-md text-[15px] outline-none"
              style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC',
                border: `1px solid ${accent}55` }}
              data-testid="rsvp-attending">
              <option value="yes" style={{ background: '#0b0908' }}>Joyfully accepts</option>
              <option value="no" style={{ background: '#0b0908' }}>Regretfully declines</option>
              <option value="maybe" style={{ background: '#0b0908' }}>Trying my best</option>
            </select>
          </label>
        </div>
        <label className="block">
          <span className="text-[10px] tracking-[0.3em] uppercase opacity-80">A note (optional)</span>
          <textarea rows={3} value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
            className="w-full mt-1.5 px-3 py-2.5 rounded-md text-[15px] outline-none resize-none"
            style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC',
              border: `1px solid ${accent}55`, fontFamily: '"Cormorant Garamond", serif' }}
            placeholder={`A blessing for ${token.celebrant.split(' ')[0]}…`}
            data-testid="rsvp-message" />
        </label>
        <button type="submit"
          className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-md text-[11px] tracking-[0.3em] uppercase font-medium"
          style={{ background: accent, color: '#16110C', border: `1px solid ${accent}` }}
          data-testid="rsvp-send">
          Send RSVP <Send className="w-3.5 h-3.5" />
        </button>
        <AnimatePresence>
          {sent && (
            <motion.div
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="text-center text-[11px] tracking-[0.25em] uppercase"
              style={{ color: accent }} data-testid="rsvp-confirmation">
              ✓ Thank you — your RSVP has been received (preview mode).
            </motion.div>
          )}
        </AnimatePresence>
      </form>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   BlessingsWall — sample wishes feed + add-your-own form (preview mode
   only stores in local component state).
   ───────────────────────────────────────────────────────────────────── */
const SAMPLE_BLESSINGS_FOR = (celebrantFirst) => [
  { name: 'Vinitha Aunty', text: `Many many happy wishes to little ${celebrantFirst}! May this year bring health, laughter and a lifetime of beautiful memories. 💕` },
  { name: 'Karthik Mama',  text: `Bless you, ${celebrantFirst}. Always remember that the whole family is rooting for you — today and every day after.` },
  { name: 'Anu',           text: `So so so excited for ${celebrantFirst}! See you at the celebration ✨` },
];

const BlessingsWall = ({ token, accent }) => {
  const initial = useMemo(() => SAMPLE_BLESSINGS_FOR(token.celebrant.split(' ')[0]), [token.celebrant]);
  const [wishes, setWishes] = useState(initial);
  const [draft, setDraft] = useState({ name: '', text: '' });

  const addWish = (e) => {
    e.preventDefault();
    if (!draft.name.trim() || !draft.text.trim()) return;
    setWishes((w) => [{ name: draft.name.trim(), text: draft.text.trim() }, ...w]);
    setDraft({ name: '', text: '' });
  };

  return (
    <div className="max-w-3xl mx-auto" data-testid="celebration-preview-blessings">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
        style={{ color: accent }}>
        ◆ Blessings &amp; Wishes
      </span>
      <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-7"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        A wall of love.
      </h3>

      <form onSubmit={addWish} className="rounded-2xl px-5 py-5 mb-6 grid sm:grid-cols-[1fr_2fr_auto] gap-2"
        style={{ background: 'rgba(11,9,8,0.78)', border: `1px solid ${accent}44` }}>
        <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          placeholder="Your name"
          className="px-3 py-2.5 rounded-md text-[14px] outline-none"
          style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC', border: `1px solid ${accent}55` }}
          data-testid="wish-name" />
        <input value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })}
          placeholder={`Share a wish for ${token.celebrant.split(' ')[0]}…`}
          className="px-3 py-2.5 rounded-md text-[14px] outline-none"
          style={{ background: 'rgba(255,255,255,0.04)', color: '#FFF8DC', border: `1px solid ${accent}55` }}
          data-testid="wish-text" />
        <button type="submit"
          className="px-4 py-2.5 rounded-md text-[11px] tracking-[0.25em] uppercase font-medium inline-flex items-center justify-center gap-1.5"
          style={{ background: accent, color: '#16110C', border: `1px solid ${accent}` }}
          data-testid="wish-add">
          <MessageSquare className="w-3.5 h-3.5" /> Send
        </button>
      </form>

      <div className="space-y-3">
        {wishes.map((w, i) => (
          <motion.div key={`${w.name}-${i}`}
            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.55, delay: 0.04 * i }}
            className="rounded-xl px-5 py-4"
            style={{ background: 'rgba(11,9,8,0.72)', border: `1px solid ${accent}33` }}>
            <div className="text-[10px] tracking-[0.3em] uppercase mb-1"
              style={{ color: accent }}>{w.name}</div>
            <p className="text-[14px] leading-relaxed" style={{ color: 'rgba(255,248,220,0.88)' }}>
              {w.text}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   LivePhotoQR — a sample QR code panel. In real invitations this QR
   points guests at `/i/{slug}/live-photos` where they can upload to a
   shared live gallery. Here we render a sample QR that resolves to the
   preview URL itself so couples can visualise the feature.
   ───────────────────────────────────────────────────────────────────── */
const LivePhotoQR = ({ token, accent, link }) => {
  const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=2&color=${
    accent.replace('#', '')}&bgcolor=FFF8DC&data=${encodeURIComponent(link)}`;
  return (
    <div className="max-w-3xl mx-auto" data-testid="celebration-preview-qr">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
        style={{ color: accent }}>
        ◆ Live Photo Wall
      </span>
      <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-3"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        Scan &amp; share your moment.
      </h3>
      <p className="text-center text-sm md:text-base mb-7"
        style={{ color: 'rgba(255,248,220,0.7)' }}>
        Every guest can capture a photo on their phone and watch it appear instantly on the live wall
        at the venue. Print this QR on the printed invite — or guests can scan it directly from their
        digital copy.
      </p>
      <div className="grid sm:grid-cols-[auto_1fr] gap-6 items-center rounded-2xl px-6 py-7"
        style={{ background: 'rgba(11,9,8,0.78)', border: `1px solid ${accent}44` }}>
        <div className="mx-auto sm:mx-0 p-3 rounded-xl"
          style={{ background: '#FFF8DC', boxShadow: `0 12px 28px ${accent}33` }}>
          <img src={qrSrc} alt="Live photo wall QR" width={180} height={180}
            style={{ display: 'block' }} data-testid="celebration-preview-qr-image" />
        </div>
        <ol className="space-y-2.5 text-sm md:text-base"
          style={{ color: 'rgba(255,248,220,0.85)' }}>
          <li className="flex gap-3"><span style={{ color: accent }}>①</span>
            Open the camera app on your phone and scan the QR.</li>
          <li className="flex gap-3"><span style={{ color: accent }}>②</span>
            Tap the link — no app needed.</li>
          <li className="flex gap-3"><span style={{ color: accent }}>③</span>
            Pick up to <strong style={{ color: '#FFF8DC' }}>5 photos</strong> from your roll.</li>
          <li className="flex gap-3"><span style={{ color: accent }}>④</span>
            Watch them appear on the projector wall at the venue ✨
          </li>
        </ol>
      </div>
      <div className="text-center mt-4">
        <button type="button"
          onClick={() => { try { navigator.clipboard?.writeText(link); } catch (_) { /* ignore */ } }}
          className="inline-flex items-center gap-2 text-[11px] tracking-[0.3em] uppercase px-4 py-2 rounded-md"
          style={{ color: accent, border: `1px solid ${accent}55`, background: 'rgba(11,9,8,0.6)' }}
          data-testid="celebration-preview-qr-copy">
          <Share2 className="w-3.5 h-3.5" /> Copy invitation link
        </button>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   AIFaceMatch — sample of the AI face matching add-on. The real flow
   (in LuxuryPublicInvitation) uses /api/ai/face-match to surface
   moments where the guest appears in the wedding's photo library.
   Here we render a static visual demo so couples can preview the look.
   ───────────────────────────────────────────────────────────────────── */
const AIFaceMatch = ({ token, accent }) => {
  const [step, setStep] = useState('idle');
  const onTryDemo = () => {
    setStep('scanning');
    setTimeout(() => setStep('matched'), 2200);
  };
  return (
    <div className="max-w-3xl mx-auto" data-testid="celebration-preview-face-match">
      <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
        style={{ color: accent }}>
        ◆ AI Face Matching
      </span>
      <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-3"
        style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
        Find <span style={{ color: accent, fontStyle: 'italic' }}>your photos</span> after the event.
      </h3>
      <p className="text-center text-sm md:text-base mb-7"
        style={{ color: 'rgba(255,248,220,0.7)' }}>
        Take a single selfie — our AI will surface every photo from the celebration
        that <strong style={{ color: '#FFF8DC' }}>you appear in</strong>. No scrolling through
        thousands of photos. Just yours.
      </p>
      <div className="rounded-2xl px-6 py-7 grid sm:grid-cols-[auto_1fr] gap-6 items-center"
        style={{ background: 'rgba(11,9,8,0.78)', border: `1px solid ${accent}44` }}>
        <div className="relative mx-auto sm:mx-0">
          <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-full overflow-hidden"
            style={{ border: `3px solid ${accent}`,
              boxShadow: '0 8px 28px rgba(0,0,0,0.45)' }}>
            <img src={token.photo} alt="Sample selfie"
              className="w-full h-full"
              style={{ objectFit: 'cover', objectPosition: 'center top' }} />
          </div>
          {step === 'scanning' && (
            <motion.div
              initial={{ y: -10, opacity: 0.7 }} animate={{ y: 70, opacity: 0.7 }}
              transition={{ duration: 1.4, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
              className="absolute left-0 right-0 mx-auto h-[3px] rounded-full"
              style={{ width: '90%', background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
                top: 10, boxShadow: `0 0 14px ${accent}` }}
            />
          )}
        </div>
        <div>
          {step === 'idle' && (
            <>
              <p className="text-sm md:text-base mb-3" style={{ color: 'rgba(255,248,220,0.85)' }}>
                Tap below to see how the AI scans a guest&apos;s face and matches it against the
                event&apos;s photo library in seconds.
              </p>
              <button type="button" onClick={onTryDemo}
                className="inline-flex items-center gap-2 text-[11px] tracking-[0.3em] uppercase px-4 py-2.5 rounded-md font-medium"
                style={{ background: accent, color: '#16110C', border: `1px solid ${accent}` }}
                data-testid="celebration-preview-face-demo">
                <Camera className="w-4 h-4" /> Try demo scan
              </button>
            </>
          )}
          {step === 'scanning' && (
            <p className="text-sm tracking-[0.2em] uppercase" style={{ color: accent }}>
              ✦ Scanning library… matching face features…
            </p>
          )}
          {step === 'matched' && (
            <>
              <p className="text-[11px] tracking-[0.3em] uppercase mb-3"
                style={{ color: accent }}>
                ✓ 27 photos matched
              </p>
              <div className="grid grid-cols-4 gap-2">
                {token.extraPhotos.concat(token.extraPhotos).slice(0, 8).map((p, i) => (
                  <motion.div key={i}
                    initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.45, delay: 0.06 * i }}
                    className="aspect-square rounded-md overflow-hidden"
                    style={{ border: `1px solid ${accent}55` }}>
                    <img src={p} alt={`Match ${i + 1}`} className="w-full h-full object-cover" loading="lazy" />
                  </motion.div>
                ))}
              </div>
              <button type="button" onClick={() => setStep('idle')}
                className="mt-3 text-[10px] tracking-[0.3em] uppercase"
                style={{ color: 'rgba(255,248,220,0.6)' }}
                data-testid="celebration-preview-face-reset">
                Reset demo
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────
   CelebrationClosing — in-flow "Thank you for visiting" cinematic outro.
   Sits above the footer. Trigger on intersection so it plays once the
   guest has scrolled all the way through.
   ───────────────────────────────────────────────────────────────────── */
const CelebrationClosing = ({ image, token, accent }) => {
  const ref = useRef(null);
  const [played, setPlayed] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) setPlayed(true); });
    }, { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <section ref={ref} className="relative overflow-hidden"
      style={{ minHeight: '80vh' }} data-testid="celebration-closing">
      {/* Slow reverse Ken-Burns over the design image */}
      <motion.div
        initial={{ scale: 1.06, opacity: 0 }}
        animate={played ? { scale: 1.18, opacity: 0.55 } : { scale: 1.06, opacity: 0 }}
        transition={{ duration: 6, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: 'absolute', inset: 0,
          backgroundImage: `url("${image || token.photo}")`,
          backgroundSize: 'cover', backgroundPosition: 'center',
          filter: 'saturate(0.9)',
        }}
      />
      {/* Vignette */}
      <div style={{
        position: 'absolute', inset: 0,
        background:
          'radial-gradient(ellipse at center, rgba(8,5,11,0.35) 0%, rgba(8,5,11,0.78) 60%, rgba(8,5,11,0.96) 100%)',
      }} />
      {/* Petal-like drifting dots */}
      {played && Array.from({ length: 18 }).map((_, i) => (
        <motion.span key={i}
          initial={{ y: -20, x: 0, opacity: 0 }}
          animate={{
            y: '90vh',
            x: (i % 2 ? 1 : -1) * (30 + (i % 4) * 25),
            opacity: [0, 0.9, 0.9, 0],
            rotate: 360,
          }}
          transition={{ duration: 5.5 + (i % 3) * 0.7, delay: i * 0.18, ease: 'linear' }}
          style={{
            position: 'absolute', left: `${6 + i * 5}%`, top: 0,
            width: 12, height: 9,
            borderRadius: '70% 30% 70% 30%',
            background: accent,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            opacity: 0.85,
          }}
        />
      ))}
      <div className="relative grid place-items-center text-center px-6"
        style={{ minHeight: '80vh', zIndex: 5 }}>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={played ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
          transition={{ duration: 1.4, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <div style={{
            fontFamily: 'Cinzel, serif',
            fontSize: 'clamp(11px, 1.6vw, 14px)',
            letterSpacing: '0.5em', textTransform: 'uppercase',
            color: accent, marginBottom: 18,
          }}>
            With all our love
          </div>
          <div style={{
            fontFamily: '"Cormorant Garamond", serif', fontWeight: 600,
            fontSize: 'clamp(28px, 5.4vw, 64px)', lineHeight: 1.12,
            color: '#FFF8DC',
            textShadow: '0 2px 18px rgba(0,0,0,0.55)',
            maxWidth: '20ch',
            margin: '0 auto',
          }}>
            Your presence is enough for us. Thank you.
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={played ? {
              opacity: [0, 1, 1],
              scale: [0.85, 1.08, 1.0],
              textShadow: [
                '0 0 0px rgba(255,248,220,0)',
                `0 0 36px ${accent}AA`,
                `0 0 18px ${accent}88`,
              ],
            } : { opacity: 0, scale: 0.85 }}
            transition={{ duration: 2.2, delay: 1.4, ease: [0.22, 1, 0.36, 1] }}
            style={{
              fontFamily: '"Great Vibes", "Pinyon Script", cursive',
              fontSize: 'clamp(34px, 6.5vw, 72px)', color: accent,
              marginTop: 22, letterSpacing: '0.01em',
            }}
            data-testid="closing-celebrant-signature"
          >
            — {token.celebrant} —
          </motion.div>
          <div style={{
            marginTop: 22, fontFamily: 'Cinzel, serif',
            fontSize: 'clamp(11px, 1.5vw, 13px)',
            letterSpacing: '0.42em', textTransform: 'uppercase',
            color: 'rgba(255,248,220,0.8)',
          }}>
            {fmtDate(token.date)} · {token.venue}
          </div>
        </motion.div>
      </div>
    </section>
  );
};

/* HeroInvitationCard — the centered "poster" with design as card background,
   eyebrow at top, circular celebrant photo bubble, and bottom cream/tinted
   panel with family line, big serif celebrant name, date and venue.
   Visually matches NonWeddingDesignCard but at poster scale. */
const HeroInvitationCard = ({ design, token }) => {
  const baseImg = resolveImg(design?.preview_image || design?.thumbnail);
  return (
    <div className="relative mx-auto overflow-hidden rounded-2xl"
      style={{
        width: 'min(560px, 92vw)',
        aspectRatio: '3 / 4',
        background: '#161210',
        boxShadow: '0 40px 80px rgba(0,0,0,0.45), 0 12px 28px rgba(0,0,0,0.25)',
        border: '1px solid rgba(212,175,55,0.18)',
      }}
      data-testid="celebration-preview-hero-card"
    >
      {/* Base design art */}
      {baseImg && (
        <img src={baseImg} alt={design?.name || token.label}
          className="absolute inset-0 w-full h-full object-cover" />
      )}

      {/* Soft top wash so the eyebrow stays readable */}
      <div aria-hidden className="absolute top-0 inset-x-0 h-28 pointer-events-none"
        style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 100%)' }} />

      {/* Eyebrow */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
        className="absolute top-6 inset-x-0 text-center px-4 z-10"
      >
        <span className="font-display text-xs sm:text-sm tracking-[0.42em] uppercase"
          style={{ color: token.panelText, textShadow: '0 1px 6px rgba(255,255,255,0.5)' }}>
          ◇ {token.eyebrow} ◇
        </span>
      </motion.div>

      {/* Photo bubble — outer wrapper does the absolute centering so that
          framer-motion's animated transform (scale) doesn't clobber the
          translateX(-50%) used for horizontal centering. */}
      <div className="absolute z-10"
        style={{
          top: '20%',
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
          className="relative"
        >
          <div className="rounded-full overflow-hidden"
            style={{
              width: 'min(40vw, 156px)',
              height: 'min(40vw, 156px)',
              border: `4px solid ${token.accent}`,
              boxShadow: '0 8px 28px rgba(0,0,0,0.45), inset 0 0 0 4px rgba(255,255,255,0.95)',
              background: '#fff',
            }}>
            <img src={token.photo} alt={token.celebrant}
              className="w-full h-full"
              style={{ objectFit: 'cover', objectPosition: 'center top', display: 'block' }} />
          </div>
          <div aria-hidden className="absolute -inset-2 rounded-full pointer-events-none"
            style={{ border: `1.5px dashed ${token.accent}80` }} />
        </motion.div>
      </div>

      {/* Bottom cream / tinted invitation panel */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.95, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
        className="absolute bottom-0 inset-x-0 px-5 pt-16 pb-8 text-center"
        style={{
          background: `linear-gradient(180deg, rgba(255,255,255,0) 0%, ${token.panelTint} 38%, ${token.panelTint} 100%)`,
        }}
      >
        <span className="block text-[10px] sm:text-xs tracking-[0.32em] uppercase mb-2"
          style={{ color: `${token.panelText}AA` }}>
          {token.familyLine}
        </span>
        <h2 className="font-display leading-tight"
          style={{
            color: token.panelText,
            fontFamily: '"Cormorant Garamond", serif',
            fontSize: 'clamp(2rem, 5vw, 3.2rem)',
            fontWeight: 600,
            letterSpacing: '-0.01em',
          }}>
          {token.celebrant}
        </h2>
        {token.nickname && (
          <p className="italic mt-1" style={{ color: token.panelText, opacity: 0.7,
            fontFamily: '"Cormorant Garamond", serif', fontSize: 'clamp(0.95rem, 1.6vw, 1.15rem)' }}>
            “{token.nickname}”
          </p>
        )}
        <span className="block text-[11px] sm:text-xs tracking-[0.28em] uppercase mt-3"
          style={{ color: token.panelText }}>
          {fmtDate(token.date)}
        </span>
        <span className="block text-[10px] sm:text-[11px] tracking-[0.22em] uppercase mt-1.5"
          style={{ color: `${token.panelText}AA` }}>
          {token.venue}
        </span>
        <span className="block text-[9px] sm:text-[10px] tracking-[0.32em] uppercase mt-3"
          style={{ color: `${token.panelText}77` }}>
          Beloved child of {token.parents}
        </span>
      </motion.div>
    </div>
  );
};

/* Module-level cache so the design fetch is shared across mounts and
   the effect below doesn't need to call setState from an async path. */
const designCache = new Map(); // key: category → designs[]
const fetchPromises = new Map();

const loadDesignsForCategory = (category) => {
  if (designCache.has(category)) return Promise.resolve(designCache.get(category));
  if (fetchPromises.has(category)) return fetchPromises.get(category);
  const p = axios
    .get(`${API_URL}/api/event-categories/${category}/designs`)
    .then((res) => {
      const designs = res?.data?.designs || [];
      designCache.set(category, designs);
      return designs;
    })
    .catch(() => {
      designCache.set(category, []);
      return [];
    })
    .finally(() => { fetchPromises.delete(category); });
  fetchPromises.set(category, p);
  return p;
};

const CelebrationInvitationPreview = () => {
  const { category, designId } = useParams();
  const navigate = useNavigate();

  const token = CATEGORY_TOKENS[category] || CATEGORY_TOKENS.baby_birthday;
  const accent = token.accent;

  // Opening animation: plays once on first mount per session-per-category.
  // Stored in sessionStorage so navigating between designs in the same
  // category doesn't replay the intro, but a fresh tab will see it.
  const sessionKey = `celeb_open_seen_${category || 'x'}`;
  const alreadySeen = typeof window !== 'undefined' && window.sessionStorage?.getItem(sessionKey) === '1';
  const [openingDone, setOpeningDone] = useState(alreadySeen);
  const finishOpening = () => {
    try { window.sessionStorage.setItem(sessionKey, '1'); } catch (_) { /* ignore */ }
    setOpeningDone(true);
  };

  // Trigger a load if needed; the actual state update happens via the
  // resolved-promise callback below, which is NOT inside an effect.
  const cached = category ? designCache.get(category) : [];
  const [designs, setDesigns] = useState(cached);

  if (category && !designCache.has(category) && !fetchPromises.has(category)) {
    loadDesignsForCategory(category).then(setDesigns);
  } else if (category && !cached && fetchPromises.has(category)) {
    fetchPromises.get(category).then(setDesigns);
  }

  const designMeta = useMemo(() => {
    if (!designs || designs.length === 0) return null;
    if (designId) return designs.find((d) => d.design_id === designId) || designs[0];
    return designs[0];
  }, [designs, designId]);

  const loading = !designs;

  const backdropImg = useMemo(
    () => resolveImg(designMeta?.preview_image || designMeta?.thumbnail),
    [designMeta],
  );

  const goBack = () => {
    if (window.history.length > 1) window.history.back();
    else navigate('/');
  };

  const goBuy = () => {
    const id = designMeta?.design_id || designId;
    if (!id) { navigate('/'); return; }
    navigate(`/user/buy-celebration/${category}/${encodeURIComponent(id)}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center" style={{ background: '#0b0908', color: '#FFF8DC' }}>
        <div className="text-xs tracking-[0.3em] uppercase opacity-70">Loading preview…</div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen"
      style={{ background: '#0b0908', color: '#FFF8DC' }}
      data-testid="celebration-invitation-preview-page"
      data-category={category}
    >
      {/* Cinematic opening — plays once per session-per-category */}
      <AnimatePresence>
        {!openingDone && (
          <CelebrationOpening
            image={backdropImg}
            token={token}
            onComplete={finishOpening}
          />
        )}
      </AnimatePresence>

      {/* Full-bleed design backdrop (blurred) */}
      <SoftDesignBackdrop image={backdropImg} accent={accent} />

      {/* All page content is mounted AFTER the opening completes so that
          framer-motion `whileInView` observers fire correctly as the guest
          scrolls — otherwise every section would already be "seen" while
          hidden under the opacity-0 wrapper and skip its animation. */}
      {openingDone && (
      <>
      {/* Top controls */}
      <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 md:px-10 py-4"
        style={{
          background: 'linear-gradient(180deg, rgba(11,9,8,0.85) 0%, rgba(11,9,8,0) 100%)',
          backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
        }}
      >
        <button onClick={goBack}
          className="inline-flex items-center gap-2 text-xs tracking-[0.3em] uppercase px-3 py-2 rounded-md"
          style={{ color: '#FFF8DC', background: 'rgba(11,9,8,0.8)', border: `1px solid ${accent}55` }}
          data-testid="celebration-preview-back"
        >
          <ArrowLeft className="w-4 h-4" /> Designs
        </button>
        <div className="hidden sm:block text-[10px] tracking-[0.32em] uppercase"
          style={{ color: 'rgba(255,248,220,0.7)' }}>
          ◆ Preview · {token.label}
        </div>
        <button onClick={goBuy}
          className="inline-flex items-center gap-2 text-[11px] tracking-[0.25em] uppercase px-4 py-2 rounded-md font-medium"
          style={{ color: '#16110C', background: accent, border: `1px solid ${accent}` }}
          data-testid="celebration-preview-use-design"
        >
          <Sparkles className="w-3.5 h-3.5" /> Use this design
        </button>
      </div>

      {/* HERO — centered invitation card on the blurred design backdrop */}
      <main className="relative z-10" style={{ paddingTop: 90 }}>
        <section className="px-5 md:px-12 pt-10 pb-16">
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
            style={{
              filter: 'drop-shadow(0 30px 60px rgba(0,0,0,0.35))',
            }}
          >
            <HeroInvitationCard design={designMeta || {}} token={token} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 0.85 }} transition={{ delay: 1.4, duration: 0.8 }}
            className="text-center mt-10"
          >
            <span className="text-[10px] tracking-[0.5em] uppercase"
              style={{ color: accent }}>
              ▾ Scroll for the full story
            </span>
          </motion.div>
        </section>

        {/* OUR STORY */}
        <section className="px-5 md:px-12 py-16">
          <div className="max-w-3xl mx-auto rounded-2xl px-7 md:px-12 py-10 md:py-12"
            style={{
              background: 'rgba(11,9,8,0.78)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              border: `1px solid ${accent}44`,
            }}
            data-testid="celebration-preview-story"
          >
            <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
              style={{ color: accent }}>
              ◆ Our Story
            </span>
            <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-4"
              style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
              A moment we will hold forever.
            </h3>
            <p className="text-[1rem] md:text-[1.05rem] leading-relaxed text-center"
              style={{ color: 'rgba(255,248,220,0.82)' }}>
              {token.story}
            </p>
          </div>
        </section>

        {/* COUNTDOWN */}
        <section className="px-5 md:px-12 py-16">
          <CountdownBlock token={token} accent={accent} />
        </section>

        {/* EVENT DETAILS — date / time / venue + Google Maps */}
        <section className="px-5 md:px-12 py-16">
          <EventDetails token={token} accent={accent} />
        </section>

        {/* CHERISHED PHOTOS */}
        <section className="px-5 md:px-12 py-16">
          <div className="max-w-5xl mx-auto">
            <span className="block text-[10px] tracking-[0.42em] uppercase mb-3 text-center"
              style={{ color: accent }}>
              ◆ Moments to Remember
            </span>
            <h3 className="text-center font-display text-3xl md:text-4xl leading-tight mb-8"
              style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
              Cherished Photos
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
              {token.extraPhotos.map((p, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0.05 * i, ease: [0.22, 1, 0.36, 1] }}
                  className="aspect-square rounded-xl overflow-hidden"
                  style={{ border: `1px solid ${accent}33`, background: '#161210' }}
                >
                  <img src={p} alt={`Moment ${i + 1}`} loading="lazy"
                    className="w-full h-full object-cover" />
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* RSVP */}
        <section className="px-5 md:px-12 py-16">
          <RSVPDemo token={token} accent={accent} />
        </section>

        {/* BLESSINGS / WISHES WALL */}
        <section className="px-5 md:px-12 py-16">
          <BlessingsWall token={token} accent={accent} />
        </section>

        {/* LIVE PHOTO QR */}
        <section className="px-5 md:px-12 py-16">
          <LivePhotoQR token={token} accent={accent}
            link={typeof window !== 'undefined' ? window.location.href : ''} />
        </section>

        {/* AI FACE MATCHING */}
        <section className="px-5 md:px-12 py-16">
          <AIFaceMatch token={token} accent={accent} />
        </section>

        {/* CLOSING BLESSING — short cream card */}
        <section className="px-5 md:px-12 pt-8 pb-16">
          <div className="max-w-2xl mx-auto text-center px-6 py-10 rounded-2xl"
            style={{
              background: 'rgba(11,9,8,0.72)',
              backdropFilter: 'blur(10px)',
              WebkitBackdropFilter: 'blur(10px)',
              border: `1px solid ${accent}33`,
            }}
          >
            <Heart className="w-5 h-5 mx-auto mb-3" style={{ color: accent }} />
            <p className="text-base md:text-lg italic"
              style={{ color: '#FFF8DC', fontFamily: '"Cormorant Garamond", serif' }}>
              “{token.closing}”
            </p>
            <span className="block text-[10px] tracking-[0.32em] uppercase mt-4"
              style={{ color: `${accent}` }}>
              — {token.parents}
            </span>
          </div>
        </section>
      </main>

      {/* CINEMATIC CLOSING — "Thank you for visiting." with reverse Ken-Burns */}
      <CelebrationClosing image={backdropImg} token={token} accent={accent} />

      {/* Footer */}
      <footer className="relative z-10 px-6 md:px-16 py-12 text-center border-t"
        style={{ borderColor: 'rgba(212,175,55,0.18)' }} data-testid="celebration-preview-footer">
        <div className="text-3xl mb-2 italic"
          style={{ color: accent, fontFamily: '"Great Vibes", "Pinyon Script", cursive' }}>
          {token.celebrant}
        </div>
        <div className="text-xs tracking-[0.3em] uppercase"
          style={{ color: 'rgba(255,248,220,0.55)' }}>
          Crafted with reverence · MAJA Creations
        </div>
      </footer>

      {/* Sticky bottom CTA */}
      <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-5 py-2.5 rounded-full"
        style={{
          background: 'rgba(11,9,8,0.92)',
          border: `1px solid ${accent}66`,
          backdropFilter: 'blur(10px)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
        }}
      >
        <span className="text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.7)' }}>
          Sample preview
        </span>
        <span style={{ color: 'rgba(255,248,220,0.3)' }}>|</span>
        <button onClick={goBuy}
          className="text-[11px] tracking-[0.25em] uppercase font-medium inline-flex items-center gap-1.5"
          style={{ color: accent }}
          data-testid="celebration-preview-sticky-cta"
        >
          Use this design <Sparkles className="w-3 h-3" />
        </button>
      </div>
      </>
      )}
    </div>
  );
};

export default CelebrationInvitationPreview;
