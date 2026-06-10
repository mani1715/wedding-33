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
import React, { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { ArrowLeft, Sparkles, Heart } from 'lucide-react';

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
      'https://images.unsplash.com/photo-1607113256158-56a934936ef1?w=600&q=80&fit=crop',
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

      {/* Photo bubble */}
      <motion.div
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
        className="absolute z-10"
        style={{ top: '22%', left: '50%', transform: 'translateX(-50%)' }}
      >
        <div className="w-28 h-28 sm:w-36 sm:h-36 rounded-full overflow-hidden"
          style={{
            border: `4px solid ${token.accent}`,
            boxShadow: '0 8px 28px rgba(0,0,0,0.4), inset 0 0 0 4px rgba(255,255,255,0.9)',
            background: `url(${token.photo}) center/cover`,
          }} />
        <div aria-hidden className="absolute -inset-2 rounded-full pointer-events-none"
          style={{ border: `1.5px dashed ${token.accent}80` }} />
      </motion.div>

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
      {/* Full-bleed design backdrop (blurred) */}
      <SoftDesignBackdrop image={backdropImg} accent={accent} />

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

        {/* CLOSING BLESSING */}
        <section className="px-5 md:px-12 pt-8 pb-32">
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
    </div>
  );
};

export default CelebrationInvitationPreview;
