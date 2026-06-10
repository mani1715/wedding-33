import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import axios from 'axios';
import {
  Sparkles, Camera, Crown, Wallet, ShieldCheck, Layers, ArrowRight,
  Heart, Music, Image as ImageIcon, QrCode, Globe2, MessageCircle, Star, MapPin,
  X as XIcon, IndianRupee, Coins, Check,
} from 'lucide-react';
import '../styles/luxury.css';
import HeroMandala3D from '../components/luxury/HeroMandala3D';
import { resolveHeroDesign } from '../themes/themeDesignResolver';
import { getThemeById } from '../themes/masterThemes';
import UserAuthModal from '../components/UserAuthModal';
import { useUserAuth } from '../context/UserAuthContext';
import { getThemeDesignsAsync, useAllDesigns } from '../themes/allDesigns';
import { usePricing } from '../hooks/usePricing';
import HelpTour, { HelpTourTrigger } from '../components/HelpTour';
import { HOMEPAGE_USER_STEPS } from '../data/helpTourSteps';
import CelebrationPreviewModal from '@/components/luxury/CelebrationPreviewModal';
import CategoryPreviewModal from '@/components/luxury/CategoryPreviewModal';
import NonWeddingDesignCard from '@/components/luxury/NonWeddingDesignCard';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';
import UniversalDesignRenderer from '../themes/UniversalDesignRenderer';
import { getThemeSampleData } from '../themes/sampleData';

/* Default sample photo for every preview tile (the per-theme dummy text
   comes from THEME_SAMPLE_DATA). */
const SAMPLE_PHOTO = 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=400&fit=crop&q=85';

const sampleFor = (themeId) => {
  const s = getThemeSampleData(themeId) || {};
  return {
    bride: s.bride || 'Anaya',
    groom: s.groom || 'Vihaan',
    date:  s.weddingDate || '14 February 2026',
    venue: `${s.venue || 'Falaknuma Palace'}${s.city ? ' · ' + s.city.split(',')[0] : ''}`,
    photo: SAMPLE_PHOTO,
  };
};

/* ──────────────────────────────────────────────────────────────
   Premium B2B SaaS Landing for Indian Wedding Photographers
   Palette: Royal Heritage (Crimson + Champagne Gold + Ivory + Charcoal)
   ────────────────────────────────────────────────────────────── */

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.8, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] },
  }),
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

/* The 10 cinematic master themes (per spec) */
const MASTER_THEMES = [
  { id: 'royal_mughal',         name: 'Royal Mughal',         palette: ['#8B0000', '#D4AF37', '#FFF8DC'], hint: 'Crimson · Gold · Ivory' },
  { id: 'south_indian_temple',  name: 'South Indian Temple',  palette: ['#D4AF37', '#420D09', '#F5E6BE'], hint: 'Gold · Maroon · Parchment' },
  { id: 'modern_minimal',       name: 'Modern Minimal',       palette: ['#DCAE96', '#8A9A5B', '#F5F5DC'], hint: 'Dusty Rose · Sage · Sand' },
  { id: 'beach_destination',    name: 'Beach Destination',    palette: ['#005F69', '#BFA379', '#F2D2BD'], hint: 'Teal · Bronze · Peach' },
  { id: 'punjabi_sangeet',      name: 'Punjabi Sangeet',      palette: ['#4B0082', '#C0C0C0', '#FFFFFF'], hint: 'Imperial Purple · Silver' },
  { id: 'bengali_traditional',  name: 'Bengali Traditional',  palette: ['#8B0000', '#FFFFFF', '#D4AF37'], hint: 'Red · White · Gold' },
  { id: 'christian_elegant',    name: 'Christian Elegant',    palette: ['#3D2B1F', '#F5F5DC', '#DCAE96'], hint: 'Mocha · Sand · Rose' },
  { id: 'muslim_nikah',         name: 'Muslim Nikah',         palette: ['#355E3B', '#D4AF37', '#FFF8DC'], hint: 'Hunter Green · Gold' },
  { id: 'nature_eco_wedding',   name: 'Nature / Eco Wedding', palette: ['#8A9A5B', '#E97451', '#F5F5DC'], hint: 'Sage · Terracotta · Sand' },
  { id: 'kerala_backwaters',     name: 'Kerala Backwaters',    palette: ['#0B3D45', '#D4A24C', '#E85A8A'], hint: 'Teal · Gold · Lotus' },
];

const FEATURES = [
  { icon: Crown,       title: 'Locked Premium Themes',     copy: 'Photographers can never break design. Curated luxury layouts only.' },
  { icon: Wallet,      title: 'Credit-Based Publishing',   copy: 'Drafts are free. Credits consume only on publish. Never expire.' },
  { icon: Camera,      title: 'Live Photo Galleries',      copy: 'Stream wedding moments to guests in real-time, beautifully.' },
  { icon: Sparkles,    title: 'AI Story Composer',         copy: 'Cinematic captions, vows, and event copy in seconds.' },
  { icon: Music,       title: 'Persistent Ambient Music',  copy: 'Crossfaded between sections — never breaks the spell.' },
  { icon: ImageIcon,   title: '3D Unfolding Invitation',   copy: 'Wax-seal opening, scroll storytelling, parallax depth.' },
  { icon: QrCode,      title: 'QR + Digital Shagun',       copy: 'Frictionless RSVP, gifts and entry passes for every guest.' },
  { icon: Globe2,      title: 'Multi-Language',            copy: 'Hindi, Tamil, Telugu, Bengali, Urdu, English & more.' },
  { icon: ShieldCheck, title: 'Private & Secure',          copy: 'Passcode invites, anti-scraping, RBAC, audit trails.' },
];

const STATS = [
  { value: '10',  label: 'Master Themes' },
  { value: '60+', label: 'Premium Sections' },
  { value: '8',   label: 'Indian Wedding Cultures' },
  { value: '∞',   label: 'Drafts per Photographer' },
];

const PLANS = [
  { name: 'Free',     credits: '5',  price: '₹0',     perks: ['Watermark', 'Royal Mughal theme', 'Basic analytics', 'Email support'] },
  { name: 'Silver',   credits: '25', price: '₹2,499', perks: ['No watermark', '4 themes unlocked', 'Full analytics', 'Priority support'] },
  { name: 'Gold',     credits: '60', price: '₹5,999', perks: ['8 themes unlocked', 'Live gallery', 'AI story composer', 'Custom domain'] },
  { name: 'Platinum', credits: '∞',  price: '₹14,999',perks: ['All 10 themes', '3D invitations', 'Dedicated manager', 'White-label option'] },
];

const Nav = ({ onLogin, user, onOpenAuth, onLogout, onBuyCredits, onUserDashboard }) => (
  <motion.nav
    initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.22,1,0.36,1] }}
    className="fixed top-0 inset-x-0 z-50 px-4 md:px-12 py-3 md:py-5 flex items-center justify-between gap-2"
    style={{ background: 'linear-gradient(180deg, rgba(14,10,6,0.92), rgba(14,10,6,0.55))', backdropFilter: 'blur(8px)' }}
    data-testid="lux-nav"
  >
    <div className="flex items-center gap-2 md:gap-3 shrink-0 min-w-0">
      <img src="/brand/maja-icon-64.png" alt="MAJA Creations"
        className="w-8 h-8 md:w-9 md:h-9 rounded-full object-cover shrink-0"
        style={{ boxShadow: '0 0 0 1px var(--lux-border-strong), inset 0 0 0 1px rgba(232,199,102,0.18)' }} />
      <span className="font-display text-base md:text-[1.35rem] tracking-wide whitespace-nowrap truncate" style={{ color: '#FFF8DC' }}>
        MAJA<span className="text-gold"> </span>Creations
      </span>
    </div>
    <div className="hidden md:flex items-center gap-9 text-[0.82rem] tracking-[0.18em] uppercase" style={{ color: 'rgba(255,248,220,0.7)' }}>
      <a href="#themes" className="hover:text-[var(--lux-gold)] transition-colors">Themes</a>
      <a href="#features" className="hover:text-[var(--lux-gold)] transition-colors">Features</a>
      <a href="#pricing" className="hover:text-[var(--lux-gold)] transition-colors">Plans</a>
      <a href="#story" className="hover:text-[var(--lux-gold)] transition-colors">Story</a>
    </div>
    <div className="flex items-center gap-1.5 md:gap-3 shrink-0">
      {user ? (
        <>
          <button
            onClick={onUserDashboard}
            className="lux-btn lux-btn-ghost !px-3 !py-2 md:!px-5 md:!py-2.5 !text-[10px] md:!text-xs whitespace-nowrap hidden sm:inline-flex"
            data-testid="nav-user-dashboard"
          >
            My Studio
          </button>
          <button
            onClick={onBuyCredits}
            className="lux-btn !px-3 !py-2 md:!px-5 md:!py-2.5 !text-[10px] md:!text-xs whitespace-nowrap"
            data-testid="nav-buy-credits"
          >
            <Wallet className="w-3.5 h-3.5 md:w-4 md:h-4" />
            <span className="hidden xs:inline">Credits ·</span> {user.credits ?? 0}
          </button>
          <button onClick={onLogout}
            aria-label="Sign out"
            className="w-9 h-9 md:w-auto md:h-auto md:px-3 md:py-1.5 rounded-full grid place-items-center md:inline md:rounded-full text-[10px] tracking-[0.25em] uppercase hover:opacity-80 transition-opacity"
            style={{ color: 'rgba(255,248,220,0.65)', border: '1px solid var(--lux-border)' }}
            data-testid="nav-user-logout"
          >
            <span className="hidden md:inline">Sign out</span>
            <span className="md:hidden text-base">↗</span>
          </button>
        </>
      ) : (
        <button onClick={onOpenAuth}
          className="lux-btn lux-btn-ghost !px-3 !py-2 md:!px-5 md:!py-2.5 !text-[10px] md:!text-xs whitespace-nowrap"
          data-testid="nav-user-signin"
        >
          Sign in
        </button>
      )}
      {!user && (
        <a href="/pricing"
          className="lux-btn lux-btn-ghost !px-3 !py-2 md:!px-5 md:!py-2.5 !text-[10px] md:!text-xs whitespace-nowrap hidden sm:inline-flex"
          data-testid="nav-pricing"
        >
          Pricing
        </a>
      )}
      {/* Photographer Studio entry — only when no user is signed in,
          so the normal user header stays clean (Credits + Sign out + My Profile). */}
      {!user && (
        <button onClick={onLogin}
          className="lux-btn !px-3 !py-2 md:!px-5 md:!py-2.5 !text-[10px] md:!text-xs whitespace-nowrap"
          data-testid="nav-photographer-login"
        >
          <Camera className="w-3.5 h-3.5 md:w-4 md:h-4 md:hidden" />
          <span className="hidden md:inline">Photographer</span>
          <span className="md:hidden">Studio</span>
        </button>
      )}
    </div>
  </motion.nav>
);

/* Bucket 2 — Floating mandala decoration for the landing hero. Pure CSS keyframe,
   GPU-friendly transform, no scroll listeners. */
const FloatingHeroMandala = ({ size = 120, top, left, right, bottom, duration = 16, delay = 0, opacity = 0.3, flip = false }) => (
  <div
    aria-hidden
    style={{
      position: 'absolute',
      top, left, right, bottom,
      width: size, height: size,
      opacity,
      pointerEvents: 'none',
      transform: flip ? 'scaleX(-1)' : undefined,
      animation: `landing-mandala-float ${duration}s ease-in-out ${delay}s infinite`,
      zIndex: 1,
    }}
  >
    <style>{`@keyframes landing-mandala-float {
      0%,100% { transform: translateY(0) rotate(0deg) ${flip ? 'scaleX(-1)' : ''}; }
      50%     { transform: translateY(-18px) rotate(10deg) ${flip ? 'scaleX(-1)' : ''}; }
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

const Hero = ({ onLogin, user, userProfilesCount = 0 }) => {
  // Removed scroll-tied parallax — useScroll/useTransform was firing every
  // frame and causing mid-page scroll jank. Kept the entry animation only.
  const reduce = useReducedMotion();

  return (
    <section className="relative min-h-screen flex flex-col justify-center pt-24 md:pt-32 pb-16 md:pb-24 px-5 md:px-16 overflow-hidden">
      {/* Sprint 11 — Cinematic 3D rotating gold mandala + dust */}
      <HeroMandala3D />

      {/* Decorative orbits */}
      <div className="lux-orbit" style={{ width: 720, height: 720, top: -180, right: -180 }} />
      <div className="lux-orbit" style={{ width: 1100, height: 1100, top: -360, right: -360, opacity: 0.5 }} />

      {/* Bucket 2 — Floating mandala decorations (gentle CSS-only float). */}
      {!reduce && (
        <>
          <FloatingHeroMandala size={120} top="14%" left="4%" duration={14} delay={0} opacity={0.30} />
          <FloatingHeroMandala size={150} bottom="18%" left="10%" duration={18} delay={3} opacity={0.22} flip />
          <FloatingHeroMandala size={100} top="38%" right="18%" duration={16} delay={1.5} opacity={0.26} />
        </>
      )}

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 max-w-6xl"
      >
        <motion.span variants={fadeUp} initial="hidden" animate="visible" custom={0} className="lux-eyebrow inline-block mb-4 md:mb-6 text-[10px] md:text-xs">
          ◆ Universal Event Invitations · Crafted in Code
        </motion.span>

        <motion.h1
          variants={fadeUp} initial="hidden" animate="visible" custom={1}
          className="font-display leading-[0.98] text-[2.4rem] xs:text-[2.8rem] sm:text-[3.4rem] md:text-[6.6rem] tracking-tight"
          style={{ color: '#FFF8DC' }}
        >
          Cinematic <span className="text-gold italic font-script font-light">invitations</span>
          <br />
          for every <em className="not-italic text-gold">celebration.</em>
        </motion.h1>

        <motion.p
          variants={fadeUp} initial="hidden" animate="visible" custom={2}
          className="mt-5 md:mt-8 max-w-2xl text-[0.95rem] md:text-[1.18rem] leading-[1.6] md:leading-[1.7]"
          style={{ color: 'rgba(255,248,220,0.72)' }}
        >
          Weddings · Baby Birthdays · Half Saree · Puberty · Dhoti Ceremonies — one luxury studio
          for couples, families and the photographers who serve them.
          You choose the story. We protect the design.
        </motion.p>

        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={3} className="mt-7 md:mt-10 flex flex-wrap items-center gap-3 md:gap-4">
          <button className="lux-btn w-full sm:w-auto justify-center" onClick={onLogin} data-testid="hero-cta-login">
            Enter Studio <ArrowRight className="w-4 h-4" />
          </button>
          <a href="#themes" className="lux-btn lux-btn-ghost w-full sm:w-auto justify-center" data-testid="hero-cta-themes">
            Explore Themes
          </a>
        </motion.div>

        <motion.div
          variants={fadeUp} initial="hidden" animate="visible" custom={4}
          className="mt-10 md:mt-16 flex items-center gap-4 md:gap-6 text-[10px] md:text-xs tracking-widest uppercase"
          style={{ color: 'rgba(255,248,220,0.55)' }}
        >
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_,i)=>(<Star key={i} className="w-3 h-3 md:w-3.5 md:h-3.5" style={{ color: '#D4AF37' }} fill="#D4AF37" />))}
          </div>
          <span className="leading-tight">Trusted by 1,200+ Indian photographers · 38 cities</span>
        </motion.div>
      </motion.div>
    </section>
  );
};

const SectionHeader = ({ eyebrow, title, kicker }) => (
  <motion.div
    variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.4 }}
    className="max-w-3xl mb-16"
  >
    <motion.span variants={fadeUp} className="lux-eyebrow block mb-5">◆ {eyebrow}</motion.span>
    <motion.h2 variants={fadeUp} className="font-display text-[2.4rem] md:text-[3.6rem] leading-[1.05] tracking-tight" style={{ color: '#FFF8DC' }}>
      {title}
    </motion.h2>
    {kicker && (
      <motion.p variants={fadeUp} className="mt-5 text-[1.02rem] leading-relaxed max-w-xl" style={{ color: 'rgba(255,248,220,0.65)' }}>
        {kicker}
      </motion.p>
    )}
  </motion.div>
);

// ============================================================
// 2026 — Invitation Categories Section (landing page)
// Renders the 5 invitation types with their hero images so any
// visitor sees that the studio supports more than weddings.
// ============================================================
const InvitationCategoriesSection = () => {
  const navigate = useNavigate();
  const [cats, setCats] = useState([]);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/event-categories`);
        if (alive) setCats(data.categories || []);
      } catch (e) {
        console.warn('Failed to load categories', e);
      }
    })();
    return () => { alive = false; };
  }, []);
  if (!cats.length) return null;
  return (
    <section id="invitation-types" className="relative px-6 md:px-16 py-28 z-10">
      <SectionHeader
        eyebrow="Universal Invitations"
        title="Not just weddings. Every milestone."
        kicker="Pick the ceremony you're celebrating — each invitation type has its own cultural designs, custom fields and the same luxury flow."
      />
      <motion.div
        variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.05 }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5"
        data-testid="categories-grid"
      >
        {cats.map((c, i) => (
          <motion.button
            key={c.id}
            variants={fadeUp} custom={i}
            onClick={() => navigate('/admin/login')}
            whileHover={{ y: -6 }}
            className="group text-left rounded-2xl overflow-hidden relative"
            style={{ border: '1px solid rgba(212,175,55,0.18)', background: '#161210' }}
            data-testid={`landing-category-${c.id}`}
          >
            <div className="relative h-44 overflow-hidden">
              <img src={c.cover_preview} alt={c.label}
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                onError={(e) => { e.currentTarget.style.opacity = 0; }} />
              <div className="absolute inset-0"
                style={{ background: 'linear-gradient(180deg, transparent 0%, rgba(11,9,8,0.7) 75%, rgba(11,9,8,0.95) 100%)' }} />
              <div className="absolute top-3 left-3 w-10 h-10 rounded-full grid place-items-center text-xl"
                style={{ background: 'rgba(11,9,8,0.6)', backdropFilter: 'blur(8px)', border: '1px solid rgba(212,175,55,0.35)' }}>
                {c.icon}
              </div>
            </div>
            <div className="p-4">
              <h3 className="font-display text-lg mb-1" style={{ color: '#FFF8DC' }}>{c.label}</h3>
              <p className="text-[10px] tracking-wider uppercase mb-2"
                style={{ color: c.accent_color }}>{c.label_traditional}</p>
              <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,248,220,0.6)' }}>
                {c.tagline}
              </p>
            </div>
          </motion.button>
        ))}
      </motion.div>
    </section>
  );
};


const Themes = ({ navigate, requireUserAuth, userSignedIn }) => {
  const [hovered, setHovered] = useState({});
  const pricing = usePricing('normal_user');
  // 2026 — Universal categories: which tab is active
  const [activeCat, setActiveCat] = useState('wedding');
  const [cats, setCats] = useState([]);
  const [catDesigns, setCatDesigns] = useState({}); // {category_id: [...designs]}
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/event-categories`);
        if (alive) setCats(data.categories || []);
      } catch (e) { console.warn('cats load', e); }
    })();
    return () => { alive = false; };
  }, []);
  // Pre-fetch designs for the active non-wedding tab
  useEffect(() => {
    if (activeCat === 'wedding' || catDesigns[activeCat]) return;
    let alive = true;
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/event-categories/${activeCat}/designs`);
        if (alive) setCatDesigns((m) => ({ ...m, [activeCat]: data.designs || [] }));
      } catch (e) { console.warn('cat designs load', e); }
    })();
    return () => { alive = false; };
  }, [activeCat, catDesigns]);

  // 2026-09 — Click on a non-wedding design card now OPENS A PREVIEW MODAL
  // first (user explicitly asked: "first I want to see the preview, then
  // select theme/design"). The modal's "Use this design" button then takes
  // them to the purchase wizard at /user/buy-celebration/:cat/:designId.
  const [previewState, setPreviewState] = useState({ open: false, category: null, design: null });

  // 2026-09 (follow-up) — Category-level preview (Wedding / Baby Birthday
  // / Half Saree / Puberty / Dhoti). Used by:
  //   • "Preview this invitation type" link under the tab bar
  //   • "Preview" pill on every wedding theme card
  // Mirrors the wedding payment story so the customer can visualize all
  // included features BEFORE committing.
  const [categoryPreview, setCategoryPreview] = useState({ open: false, category: null });
  const openCategoryPreview = (catId) => setCategoryPreview({ open: true, category: catId });
  const closeCategoryPreview = () => setCategoryPreview({ open: false, category: null });

  const handleCategoryBrowseDesigns = (catId) => {
    closeCategoryPreview();
    setActiveCat(catId);
    // Smooth-scroll back to the themes grid so the user lands on the
    // freshly-filtered designs.
    setTimeout(() => {
      try { document.getElementById('themes')?.scrollIntoView({ behavior: 'smooth' }); } catch (_) { /* noop */ }
    }, 50);
  };

  const handleCategorySignIn = (catId) => {
    closeCategoryPreview();
    if (userSignedIn) {
      // Already signed in — jump to user dashboard so they can create.
      navigate('/user/dashboard');
      return;
    }
    if (typeof requireUserAuth === 'function') {
      requireUserAuth('/user/dashboard');
    } else {
      navigate('/?signin=1&return=/user/dashboard');
    }
  };

  const handleNonWeddingDesignClick = (catId, design) => {
    setPreviewState({ open: true, category: catId, design });
  };

  const handleUseDesignFromPreview = (catId, design) => {
    setPreviewState({ open: false, category: null, design: null });
    const target = `/user/buy-celebration/${catId}/${encodeURIComponent(design.design_id)}`;
    if (userSignedIn) {
      navigate(target);
    } else if (typeof requireUserAuth === 'function') {
      requireUserAuth(target);
    } else {
      navigate(`/?signin=1&return=${encodeURIComponent(target)}`);
    }
  };

  // Subscribe to the global design cache so cards re-render once each
  // theme's chunk lands (Christian/Muslim/Nature/Kerala previously showed
  // empty preview tiles on first paint because their chunks hadn't loaded
  // yet and the page never re-rendered).
  useAllDesigns();
  return (
  <section id="themes" className="relative px-6 md:px-16 py-28 z-10">
    <SectionHeader
      eyebrow="Universal Designs Library"
      title="Pick a ceremony. Pick a design. Make it yours."
      kicker="Every invitation type has its own curated design gallery — wedding, baby birthday, half saree, puberty and dhoti. Same locked-luxury experience, same simple flow."
    />

    {/* 2026 — Category tabs. Wedding is the default; clicking any other tab
        replaces the design grid below with that category's gallery. */}
    {cats.length > 0 && (
      <div className="flex flex-col items-center justify-center mb-10 -mt-6 overflow-x-auto"
        data-testid="themes-category-tabs">
        <div className="inline-flex items-center gap-1 p-1 rounded-full"
          style={{ background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.18)' }}>
          {cats.map((c) => {
            const isActive = activeCat === c.id;
            return (
              <button key={c.id} type="button" onClick={() => setActiveCat(c.id)}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[11px] tracking-[0.18em] uppercase whitespace-nowrap transition-all"
                style={isActive
                  ? { background: 'linear-gradient(135deg,#D4AF37,#B48C28)', color: '#16110C', fontWeight: 700 }
                  : { color: 'rgba(255,248,220,0.7)' }}
                data-testid={`themes-tab-${c.id}`}>
                <span className="text-base">{c.icon}</span>
                <span>{c.label}</span>
              </button>
            );
          })}
        </div>
        {/* 2026-09 — "Preview this invitation type" CTA. Opens a category-level
            modal showing ALL features bundled with this invitation type so the
            customer can visualize the experience before picking a design. */}
        <button
          type="button"
          onClick={() => openCategoryPreview(activeCat)}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full text-[10px] tracking-[0.28em] uppercase transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(212,175,55,0.08)',
            border: '1px solid rgba(212,175,55,0.32)',
            color: '#E8C766',
          }}
          data-testid={`themes-preview-category-${activeCat}`}
        >
          <Sparkles className="w-3 h-3" />
          Preview this invitation type
        </button>
      </div>
    )}

    {activeCat === 'wedding' && (
    <motion.div
      key="wedding-grid"
      variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.01 }}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
      data-testid="themes-grid"
    >
      {MASTER_THEMES.map((t, i) => {
        const themeDesign = resolveHeroDesign(t.id);
        const SAMPLE = sampleFor(t.id);
        const masterTheme = getThemeById(t.id);
        // Dynamic credit cost from /api/public/pricing/effective with fallback
        // to the locked masterThemes value if the API hasn't responded yet.
        const themeCredits = pricing.themeCost(t.id, masterTheme?.creditCost ?? 1);
        const themePlan = masterTheme?.planRequired || 'FREE';
        return (
        <motion.div
          role="button"
          tabIndex={0}
          key={t.id} variants={fadeUp} custom={i}
          whileHover={{ scale: 1.01, transition: { duration: 0.25, ease: 'easeOut' } }}
          onMouseEnter={() => {
            try { setHovered((h) => ({ ...h, [t.id]: true })); } catch (_) { /* noop */ }
            // PHASE 9 (perf): warm the theme chunk + first design image on hover so
            // click feels instant. No-op if chunk already cached.
            try { getThemeDesignsAsync(t.id); } catch (_) { /* noop */ }
          }}
          onTouchStart={() => {
            try { setHovered((h) => ({ ...h, [t.id]: true })); } catch (_) { /* noop */ }
            try { getThemeDesignsAsync(t.id); } catch (_) { /* noop */ }
          }}
          onClick={() => navigate(`/themes/${t.id}/events`)}
          onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/themes/${t.id}/events`); }}
          className="lux-glass p-5 group cursor-pointer text-left w-full overflow-hidden relative"
          data-testid={`theme-card-${t.id}`}
          aria-label={`Preview ${t.name}`}
        >
          {/* Credit badge — top-right corner */}
          <div
            className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-3 py-1 rounded-full"
            style={{
              background: 'linear-gradient(135deg, rgba(212,175,55,0.95), rgba(180,140,40,0.9))',
              boxShadow: '0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.25)',
              border: '1px solid rgba(255,248,220,0.35)',
            }}
            data-testid={`theme-credit-badge-${t.id}`}
          >
            <Coins className="w-3 h-3" style={{ color: '#16110C' }} strokeWidth={2.4} />
            <span className="font-display text-xs leading-none" style={{ color: '#16110C', fontWeight: 700 }}>
              {themeCredits} credit{themeCredits > 1 ? 's' : ''}
            </span>
          </div>
          {/* Plan badge — top-left corner */}
          <div
            className="absolute top-3 left-3 z-10 px-2 py-1 rounded-full text-[9px] tracking-[0.2em] uppercase"
            style={{
              background: themePlan === 'FREE' ? 'rgba(138,154,91,0.2)'
                       : themePlan === 'SILVER' ? 'rgba(192,192,192,0.2)'
                       : themePlan === 'GOLD' ? 'rgba(212,175,55,0.2)'
                       : 'rgba(139,0,0,0.25)',
              color: themePlan === 'FREE' ? '#A8C076'
                  : themePlan === 'SILVER' ? '#D8D8D8'
                  : themePlan === 'GOLD' ? '#E8C766'
                  : '#FFB0A0',
              border: '1px solid rgba(255,248,220,0.2)',
            }}
            data-testid={`theme-plan-badge-${t.id}`}
          >
            {themePlan}
          </div>
          {/* Live invitation preview — 2026-07 fix: render eagerly for
              ALL theme cards so Christian/Muslim/Nature/Kerala (positions
              7-10) don't appear blank until hover. The renderer itself
              defers heavy work via its own intersection observer. */}
          {themeDesign?.design && themeDesign?.theme && (
            <div className="relative w-full mb-5 overflow-hidden rounded-md transition-transform duration-300 group-hover:scale-[1.01]">
              <UniversalDesignRenderer
                design={themeDesign.design}
                theme={themeDesign.theme}
                bride={SAMPLE.bride}
                groom={SAMPLE.groom}
                date={SAMPLE.date}
                venue={SAMPLE.venue}
                photo={SAMPLE.photo}
                eager={i < 3}
                testId={`theme-preview-${t.id}`}
              />
            </div>
          )}

          <div className="flex items-center justify-between mb-3">
            <span className="text-xs tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.45)' }}>
              {String(i + 1).padStart(2, '0')}
            </span>
            <div className="flex -space-x-1.5">
              {t.palette.map((c, idx) => (
                <span key={idx}
                  className="w-5 h-5 rounded-full border"
                  style={{ background: c, borderColor: 'rgba(255,248,220,0.2)' }}
                />
              ))}
            </div>
          </div>
          <h3 className="font-display text-2xl md:text-[1.55rem] leading-tight mb-2" style={{ color: '#FFF8DC' }}>
            {t.name}
          </h3>
          <p className="text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>{t.hint}</p>
          <div className="lux-hairline my-4" />
          <div className="flex items-center justify-between text-xs tracking-widest uppercase"
            style={{ color: 'rgba(255,248,220,0.55)' }}>
            <span>18 designs · 6 events</span>
            <span className="group-hover:text-[var(--lux-gold)] transition-colors flex items-center gap-1">
              Explore <ArrowRight className="w-3 h-3" />
            </span>
          </div>
          {/* July 2026 — Two-CTA footer for wedding theme cards.
              "Preview" opens the category preview modal (full features +
              sample designs) BEFORE the user commits; "Buy theme" goes
              straight to the purchase wizard like before. */}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); openCategoryPreview('wedding'); }}
              className="px-3 py-2 rounded-full text-[10px] tracking-[0.22em] uppercase inline-flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]"
              style={{
                background: 'rgba(255,248,220,0.06)',
                border: '1px solid rgba(255,248,220,0.18)',
                color: '#FFF8DC',
              }}
              data-testid={`theme-preview-btn-${t.id}`}
            >
              <Sparkles className="w-3 h-3" /> Preview
            </button>
            <div
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); navigate(`/user/buy-theme/${t.id}`); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); navigate(`/user/buy-theme/${t.id}`); } }}
              className="lux-btn justify-center !text-[11px]"
              data-testid={`theme-buy-btn-${t.id}`}
            >
              <Coins className="w-3.5 h-3.5" /> {themeCredits} credit{themeCredits > 1 ? 's' : ''}
            </div>
          </div>
        </motion.div>
        );
      })}
    </motion.div>
    )}

    {/* 2026 — Non-wedding category gallery */}
    {activeCat !== 'wedding' && (() => {
      const designs = catDesigns[activeCat] || [];
      const meta = cats.find((c) => c.id === activeCat);
      if (!designs.length) {
        return (
          <div className="text-center py-12" style={{ color: 'rgba(255,248,220,0.5)' }}>
            Loading {meta?.label} designs…
          </div>
        );
      }
      return (
        <motion.div
          key={`grid-${activeCat}`}
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          data-testid={`category-grid-${activeCat}`}
        >
          {designs.map((d, i) => {
            // Build a 3-swatch palette for the category — mirrors the
            // 3-dot palette swatches on wedding theme cards.
            const catPalette = [
              meta?.primary_color || '#D4AF37',
              meta?.accent_color  || '#8B0000',
              '#FFF8DC',
            ];
            return (
            <motion.div
              key={d.design_id}
              role="button"
              tabIndex={0}
              variants={fadeUp} custom={i}
              whileHover={{ scale: 1.01, transition: { duration: 0.25, ease: 'easeOut' } }}
              onClick={() => handleNonWeddingDesignClick(activeCat, d)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleNonWeddingDesignClick(activeCat, d); }}
              className="lux-glass p-5 group cursor-pointer text-left w-full overflow-hidden relative"
              data-testid={`cat-design-card-${d.design_id}`}
              aria-label={`Preview ${d.name}`}
            >
              {/* Credit badge — top-right corner (same as wedding) */}
              <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-3 py-1 rounded-full"
                style={{
                  background: 'linear-gradient(135deg, rgba(212,175,55,0.95), rgba(180,140,40,0.9))',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.25)',
                  border: '1px solid rgba(255,248,220,0.35)',
                }}
                data-testid={`cat-design-credit-badge-${d.design_id}`}
              >
                <Coins className="w-3 h-3" style={{ color: '#16110C' }} strokeWidth={2.4} />
                <span className="font-display text-xs leading-none" style={{ color: '#16110C', fontWeight: 700 }}>
                  {d.credit_cost || 1} credit{(d.credit_cost || 1) > 1 ? 's' : ''}
                </span>
              </div>
              {/* Category badge — top-left corner (mirrors wedding plan badge) */}
              <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-full text-[9px] tracking-[0.2em] uppercase flex items-center gap-1"
                style={{
                  background: 'rgba(11,9,8,0.7)',
                  backdropFilter: 'blur(8px)',
                  border: '1px solid rgba(212,175,55,0.3)',
                  color: meta?.accent_color || '#D4AF37',
                }}
                data-testid={`cat-design-cat-badge-${d.design_id}`}
              >
                <span>{meta?.icon}</span>
                <span>{meta?.label}</span>
              </div>
              {/* Live invitation preview — wedding-card-style overlay with
                  sample celebrant name, date and venue. */}
              <div className="relative w-full mb-5">
                <NonWeddingDesignCard
                  design={d}
                  category={activeCat}
                  index={i}
                />
              </div>

              <div className="flex items-center justify-between mb-3">
                <span className="text-xs tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.45)' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="flex -space-x-1.5">
                  {catPalette.map((c, idx) => (
                    <span key={idx}
                      className="w-5 h-5 rounded-full border"
                      style={{ background: c, borderColor: 'rgba(255,248,220,0.2)' }}
                    />
                  ))}
                </div>
              </div>
              <h3 className="font-display text-2xl md:text-[1.55rem] leading-tight mb-2" style={{ color: '#FFF8DC' }}>
                {d.name}
              </h3>
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
                {meta?.tagline}
              </p>
              <div className="lux-hairline my-4" />
              <div className="flex items-center justify-between text-xs tracking-widest uppercase"
                style={{ color: 'rgba(255,248,220,0.55)' }}>
                <span>{meta?.label} · {designs.length} designs</span>
                <span className="group-hover:text-[var(--lux-gold)] transition-colors flex items-center gap-1">
                  Explore <ArrowRight className="w-3 h-3" />
                </span>
              </div>
              {/* Two-CTA footer — Preview + Buy, mirrors wedding card */}
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button type="button"
                  onClick={(e) => { e.stopPropagation(); handleNonWeddingDesignClick(activeCat, d); }}
                  className="px-3 py-2 rounded-full text-[10px] tracking-[0.22em] uppercase inline-flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]"
                  style={{
                    background: 'rgba(255,248,220,0.06)',
                    border: '1px solid rgba(255,248,220,0.18)',
                    color: '#FFF8DC',
                  }}
                  data-testid={`cat-design-preview-${d.design_id}`}
                >
                  <Sparkles className="w-3 h-3" /> Preview
                </button>
                <div role="button" tabIndex={0}
                  onClick={(e) => { e.stopPropagation(); handleNonWeddingDesignClick(activeCat, d); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); handleNonWeddingDesignClick(activeCat, d); } }}
                  className="lux-btn justify-center !text-[11px]"
                  data-testid={`cat-design-buy-${d.design_id}`}>
                  <Coins className="w-3.5 h-3.5" /> {d.credit_cost || 1} credit{(d.credit_cost || 1) > 1 ? 's' : ''}
                </div>
              </div>
            </motion.div>
            );
          })}
        </motion.div>
      );
    })()}
    <CelebrationPreviewModal
      open={previewState.open}
      category={previewState.category}
      design={previewState.design}
      onClose={() => setPreviewState({ open: false, category: null, design: null })}
      onUseDesign={handleUseDesignFromPreview}
    />
    <CategoryPreviewModal
      open={categoryPreview.open}
      category={categoryPreview.category}
      onClose={closeCategoryPreview}
      onBrowseDesigns={handleCategoryBrowseDesigns}
      onSignIn={handleCategorySignIn}
    />
  </section>
  );
};

const Features = () => (
  <section id="features" className="relative px-6 md:px-16 py-28 z-10">
    <SectionHeader
      eyebrow="Photographer Toolkit"
      title="Every detail crafted for your business."
      kicker="A wizard-driven studio that protects your design integrity while giving guests an experience they will never forget."
    />
    <motion.div
      variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.15 }}
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
      data-testid="features-grid"
    >
      {FEATURES.map((f, i) => (
        <motion.div
          key={f.title} variants={fadeUp} custom={i}
          className="lux-glass p-7 flex flex-col gap-4 hover:scale-[1.01] transition-transform duration-700"
          data-testid={`feature-card-${i}`}
        >
          <div className="w-11 h-11 rounded-xl grid place-items-center"
            style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(139,0,0,0.18))', border: '1px solid var(--lux-border-strong)' }}>
            <f.icon className="w-5 h-5" style={{ color: '#D4AF37' }} strokeWidth={1.6} />
          </div>
          <h3 className="font-heading text-xl" style={{ color: '#FFF8DC' }}>{f.title}</h3>
          <p className="text-[0.95rem] leading-relaxed" style={{ color: 'rgba(255,248,220,0.6)' }}>{f.copy}</p>
        </motion.div>
      ))}
    </motion.div>
  </section>
);

const Stats = () => (
  <section className="px-6 md:px-16 py-20 z-10 relative">
    <div className="lux-hairline mb-16" />
    <motion.div
      variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.5 }}
      className="grid grid-cols-2 md:grid-cols-4 gap-8"
    >
      {STATS.map((s, i) => (
        <motion.div key={i} variants={fadeUp} custom={i} className="text-center md:text-left">
          <div className="font-display text-5xl md:text-6xl text-gold mb-2">{s.value}</div>
          <div className="text-xs tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>{s.label}</div>
        </motion.div>
      ))}
    </motion.div>
    <div className="lux-hairline mt-16" />
  </section>
);

const Story = () => (
  <section id="story" className="relative px-6 md:px-16 py-28 z-10">
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
      <motion.div
        variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }}
      >
        <motion.span variants={fadeUp} className="lux-eyebrow block mb-5">◆ Our Philosophy</motion.span>
        <motion.h2 variants={fadeUp} className="font-display text-[2.4rem] md:text-[3.4rem] leading-[1.1] mb-7" style={{ color: '#FFF8DC' }}>
          Indian weddings deserve <span className="text-gold italic font-script">cinema</span>, not templates.
        </motion.h2>
        <motion.p variants={fadeUp} className="text-[1.05rem] leading-[1.85] mb-6" style={{ color: 'rgba(255,248,220,0.7)' }}>
          We built MAJA Creations for the artist behind the camera — the photographer who has shot 200 weddings
          and is tired of cheap, flashy invitation builders that ruin their brand.
        </motion.p>
        <motion.p variants={fadeUp} className="text-[1.05rem] leading-[1.85]" style={{ color: 'rgba(255,248,220,0.7)' }}>
          Every theme here is curated like a Bollywood title sequence: slow, royal, immersive.
          Wax-seal openings. Parallax stories. Glassmorphism. Mandalas that breathe.
          Your couples will weep. Your competitors will scramble.
        </motion.p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, rotateY: -15, scale: 0.94 }} whileInView={{ opacity: 1, rotateY: 0, scale: 1 }}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }} viewport={{ once: true, amount: 0.1 }}
        className="lux-glass p-10 relative"
        style={{ transformStyle: 'preserve-3d' }}
      >
        <div className="absolute -top-3 -right-3 w-16 h-16 rounded-full grid place-items-center"
          style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}>
          <Crown className="w-6 h-6" style={{ color: '#16110C' }} />
        </div>
        <div className="lux-eyebrow mb-4">Customer Verdict</div>
        <p className="font-heading text-2xl md:text-[1.85rem] leading-[1.35] italic mb-6" style={{ color: '#FFF8DC' }}>
          “We doubled our wedding package price the month we moved to MAJA Creations.
          Couples opened the invite and cried before the wedding even happened.”
        </p>
        <div className="lux-hairline mb-4" />
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full" style={{ background: 'linear-gradient(135deg, #8B0000, #D4AF37)' }} />
          <div>
            <div className="font-heading text-lg" style={{ color: '#FFF8DC' }}>Anaya Mehta</div>
            <div className="text-xs tracking-widest uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>Studio Aurora · Mumbai</div>
          </div>
        </div>
      </motion.div>
    </div>
  </section>
);

/* ──────────────────────────────────────────────────────────────
   Invitation Options — all features included in an invitation link
   with default credit pricing visible to visitors.
   ────────────────────────────────────────────────────────────── */
const INVITATION_OPTIONS = [
  // `key` matches a row in the Super-Admin Pricing Hub → "Invitation option prices"
  // for the `normal_user` audience. When admin updates the row, `usePricing`
  // reads the new credits and the badge here updates on next page-load.
  { key: 'wax_seal_opening',  icon: Heart,         title: 'Wax-Seal Opening',       desc: 'Cinematic 3D unfolding intro.',                     credits: 0,  included: true  },
  { key: 'couple_photos',     icon: ImageIcon,     title: 'Couple + Bride/Groom Photos', desc: 'Portrait gallery with full bios.',             credits: 0,  included: true  },
  { key: 'background_music',  icon: Music,         title: 'Background Music',       desc: '60+ curated tracks across 6 categories.',           credits: 0,  included: true  },
  { key: 'countdown_timer',   icon: Sparkles,      title: 'Live Countdown',         desc: 'Real-time ticker to the muhurat.',                  credits: 0,  included: true  },
  { key: 'rsvp_basic',        icon: MessageCircle, title: 'Guest Wishes & RSVP',    desc: 'Public wishes wall + RSVP form.',                   credits: 0,  included: true  },
  { key: 'multi_language',    icon: Globe2,        title: 'Multi-language Invite',  desc: 'Hindi · Tamil · Telugu · Bengali · Urdu · English', credits: 1,  included: false },
  { key: 'qr_code_pass',      icon: QrCode,        title: 'QR Code Entry Pass',     desc: 'Per-guest scannable QR codes.',                     credits: 2,  included: false },
  { key: 'ai_story',          icon: Sparkles,      title: 'AI Story Composer',      desc: 'Gemini-powered love story & event copy.',           credits: 2,  included: false },
  { key: 'live_gallery',      icon: Camera,        title: 'Live Photo Gallery',     desc: 'Stream wedding moments to guests in real-time.',    credits: 3,  included: false },
  { key: 'gift_registry',     icon: IndianRupee,   title: 'Digital Shagun · UPI/QR',desc: 'Accept gifts via Razorpay / UPI / QR.',             credits: 3,  included: false },
  { key: 'venue_maps',        icon: MapPin,        title: 'Smart Venue Maps',       desc: 'Per-event Google Maps + parking guidance.',         credits: 1,  included: false },
  { key: 'passcode_lock',     icon: ShieldCheck,   title: 'Passcode-Protected Link',desc: 'Private invite — only your guests can enter.',      credits: 1,  included: false },
];

// MapPin/IndianRupee are imported below
const InvitationOptions = () => {
  const pricing = usePricing('normal_user');
  return (
  <section id="invitation-options" className="relative px-6 md:px-16 py-28 z-10">
    <SectionHeader
      eyebrow="What's Inside The Invite"
      title="Every option, transparently priced."
      kicker="Five staples are baked into every link for free. Premium features add a few credits — pick only what your couple needs."
    />
    <motion.div
      variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.05 }}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
      data-testid="invitation-options-grid"
    >
      {INVITATION_OPTIONS.map((opt, i) => {
        // Override the local fallback with the live admin-controlled value.
        const liveCredits = pricing.optionCredits(opt.key, opt.credits);
        const liveFree    = pricing.optionIsFree(opt.key, opt.included);
        const credits = liveCredits;
        const included = liveFree || credits === 0;
        return (
        <motion.div
          key={opt.title} variants={fadeUp} custom={i}
          whileHover={{ y: -4 }}
          className="lux-glass p-6 relative overflow-hidden"
          data-testid={`option-card-${opt.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
        >
          {/* Credit badge top-right */}
          <div
            className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
            style={{
              background: included
                ? 'linear-gradient(135deg, rgba(138,154,91,0.85), rgba(100,120,70,0.85))'
                : 'linear-gradient(135deg, rgba(212,175,55,0.95), rgba(180,140,40,0.9))',
              boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
              border: '1px solid rgba(255,248,220,0.3)',
            }}
            data-testid={`option-credit-${opt.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
          >
            {included ? (
              <>
                <Check className="w-3 h-3" style={{ color: '#0F1A06' }} strokeWidth={3} />
                <span className="font-display text-[10px] tracking-wider uppercase leading-none" style={{ color: '#0F1A06', fontWeight: 700 }}>
                  Included
                </span>
              </>
            ) : (
              <>
                <Coins className="w-3 h-3" style={{ color: '#16110C' }} strokeWidth={2.4} />
                <span className="font-display text-xs leading-none" style={{ color: '#16110C', fontWeight: 700 }}>
                  +{credits}
                </span>
              </>
            )}
          </div>

          <div className="w-11 h-11 rounded-xl grid place-items-center mb-4"
            style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(139,0,0,0.18))',
                     border: '1px solid var(--lux-border-strong)' }}>
            <opt.icon className="w-5 h-5" style={{ color: '#D4AF37' }} strokeWidth={1.6} />
          </div>
          <h3 className="font-heading text-lg mb-2 pr-20" style={{ color: '#FFF8DC' }}>{opt.title}</h3>
          <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,248,220,0.65)' }}>{opt.desc}</p>
        </motion.div>
        );
      })}
    </motion.div>
    <motion.p
      initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, amount: 0.1 }}
      transition={{ duration: 0.8, delay: 0.4 }}
      className="text-center text-xs tracking-[0.25em] uppercase mt-10"
      style={{ color: 'rgba(255,248,220,0.55)' }}
      data-testid="invitation-options-note"
    >
      ◆ Base theme cost is shown on each theme card · Credits add up only on publish ◆
    </motion.p>
  </section>
  );
};

const PERK_PRESETS = {
  // Soft mapping keyed by pack label so admins can rename packs in the hub
  // and the perk list still shows reasonable copy. Unknown labels fall back
  // to a credits-based perk list.
  Free:     ['Watermark', 'Royal Mughal theme', 'Basic analytics', 'Email support'],
  Silver:   ['No watermark', '4 themes unlocked', 'Full analytics', 'Priority support'],
  Gold:     ['8 themes unlocked', 'Live gallery', 'AI story composer', 'Custom domain'],
  Platinum: ['All 10 themes', '3D invitations', 'Dedicated manager', 'White-label option'],
};
const _formatRupees = (n) => {
  if (typeof n !== 'number') return '';
  if (n === 0) return '₹0';
  return `₹${n.toLocaleString('en-IN')}`;
};

const Pricing = () => {
  const pricing = usePricing('normal_user');
  const livePacks = (pricing.packs || []).slice(0, 4);
  return (
  <section id="pricing" className="relative px-6 md:px-16 py-28 z-10">
    <SectionHeader
      eyebrow="Credit Plans"
      title="Pay for credits. Never for time."
      kicker="Credits never expire. Drafts are free. Every plan below is a credit pack — pick the size that fits and only spend a credit when you publish a wedding link."
    />
    <motion.div
      variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.15 }}
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5"
      data-testid="pricing-grid"
    >
      {livePacks.length === 0 && (
        <div className="col-span-full text-center text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
          Loading credit plans…
        </div>
      )}
      {livePacks.map((pack, i) => {
        const featured = i === 2; // 3rd card as the Studio Pick (Gold-equivalent)
        const name = pack.label || `Pack ${i + 1}`;
        const perks = PERK_PRESETS[name] || [
          `${pack.credits} credits at ₹${pack.base_price > 0 ? Math.round(pack.base_price / Math.max(pack.credits, 1)) : 0} / credit`,
          'Credits never expire',
          'All free invitation options',
          'Razorpay secure checkout',
        ];
        const price = _formatRupees(pack.price);
        const baseStrike = pack.discount_enabled && pack.base_price !== pack.price;
        return (
          <motion.div
            key={pack.id || name} variants={fadeUp} custom={i}
            whileHover={{ y: -6 }}
            className={`lux-glass p-7 flex flex-col ${featured ? 'ring-1' : ''}`}
            style={featured ? { borderColor: 'var(--lux-gold)', background: 'rgba(212,175,55,0.07)' } : undefined}
            data-testid={`plan-card-${name.toLowerCase()}`}
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>{name}</h3>
              {featured && <span className="text-[10px] tracking-[0.25em] uppercase px-2 py-1 rounded-full" style={{ color: '#16110C', background: '#D4AF37' }}>Best Value</span>}
            </div>
            <div className="font-display text-5xl text-gold mb-1">{pack.credits}</div>
            <div className="text-xs tracking-[0.2em] uppercase mb-2" style={{ color: 'rgba(255,248,220,0.55)' }}>credits included</div>
            <div className="flex items-baseline gap-2 mb-6" data-testid={`plan-price-${name.toLowerCase()}`}>
              <span className="font-display text-xl" style={{ color: '#FFF8DC' }}>{price}</span>
              {baseStrike && (
                <span className="font-display text-sm line-through" style={{ color: 'rgba(255,248,220,0.45)' }}>
                  {_formatRupees(pack.base_price)}
                </span>
              )}
              <span className="text-[10px] tracking-[0.2em] uppercase" style={{ color: 'rgba(255,248,220,0.5)' }}>/ pack</span>
            </div>
            <div className="lux-hairline mb-5" />
            <ul className="flex-1 space-y-3 text-sm" style={{ color: 'rgba(255,248,220,0.75)' }}>
              {perks.map((perk) => (
                <li key={perk} className="flex items-start gap-2">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full" style={{ background: '#D4AF37' }} />
                  {perk}
                </li>
              ))}
            </ul>
            <button className={`mt-7 ${featured ? 'lux-btn' : 'lux-btn lux-btn-ghost'} justify-center`} data-testid={`plan-cta-${name.toLowerCase()}`}>
              Choose {name}
            </button>
          </motion.div>
        );
      })}
    </motion.div>
  </section>
  );
};

const PhotographerAdvantages = ({ onPhotographer }) => {
  // Pull live photographer tier configuration from the super-admin pricing hub.
  // Each tier has { key, label, min_paid_links, discount_pct, bonus_pct }.
  const photographerPricing = usePricing('photographer');
  const rawTiers = photographerPricing?.photographer_tiers?.tiers || [];
  // Filter out the starter (0 link) tier — only milestones that actually
  // unlock a reward are worth showcasing on the public homepage.
  const milestoneTiers = rawTiers.filter((t) => (t.min_paid_links || 0) > 0);
  const firstMilestone = milestoneTiers[0];
  // Public stats — total published weddings + photographers active. The
  // endpoint is read-only and cheap (uses count_documents).
  const [stats, setStats] = useState({ published_total: null, photographers_total: null, bonus_credits_granted: null });
  useEffect(() => {
    let cancelled = false;
    axios.get(`${API_URL}/api/public/photographer-stats`)
      .then((r) => { if (!cancelled) setStats(r.data || {}); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const advantages = [
    { icon: Layers,      title: 'Unlimited Drafts',         copy: 'Build every couple\'s wedding link in the panel. Drafts cost zero credits — pay only on publish.' },
    { icon: Crown,       title: 'Studio Branding',          copy: 'Co-branded invitation footer, white-label option on Platinum, and a public studio profile.' },
    { icon: ShieldCheck, title: 'RBAC + Audit Trails',      copy: 'Add team members with role-based access. Every action is logged — perfect for large studios.' },
    { icon: Wallet,      title: 'Bulk Credit Discounts',    copy: 'Bigger packs auto-discount. Buy the largest pack in one go for the lowest per-credit price.' },
    {
      icon: Sparkles,
      title: 'Loyalty Offers',
      copy: milestoneTiers.length
        ? `Cross ${milestoneTiers[0].min_paid_links} paid links to unlock the ${milestoneTiers[0].label} tier — ${milestoneTiers[0].discount_pct}% off every credit pack + ${milestoneTiers[0].bonus_pct}% bonus credits on top.`
        : 'After every milestone you publish, you unlock a richer offer — bonus credits on every pack and lower per-credit price.',
    },
    {
      icon: Star,
      title: 'Elite & Partner Tiers',
      copy: milestoneTiers.length >= 3
        ? `${milestoneTiers[1].label} (${milestoneTiers[1].min_paid_links}+ links): ${milestoneTiers[1].discount_pct}% off & ${milestoneTiers[1].bonus_pct}% bonus. ${milestoneTiers[2].label} (${milestoneTiers[2].min_paid_links}+ links): ${milestoneTiers[2].discount_pct}% off & ${milestoneTiers[2].bonus_pct}% bonus credits — the top tier.`
        : 'Higher tiers unlock bigger discounts and bigger bonus-credit percentages on every credit-pack purchase.',
    },
  ];

  return (
    <section id="photographer-advantages" className="relative px-6 md:px-16 py-28 z-10" data-testid="photographer-advantages">
      <SectionHeader
        eyebrow="Photographer Panel · Advantages"
        title="Built for studios. Rewards that grow with you."
        kicker="Photographers who manage couples through MAJA unlock a separate luxury panel with bulk tools, branding controls and loyalty-based credit offers."
      />

      {/* Live counters — populated from /api/public/photographer-stats */}
      {(stats.published_total != null || stats.photographers_total != null) && (
        <motion.div
          initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.8 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-10"
          data-testid="photographer-live-stats"
        >
          {[
            { label: 'Weddings Published', value: stats.published_total },
            { label: 'Active Photographers', value: stats.photographers_total },
            { label: 'Loyalty Credits Granted', value: stats.bonus_credits_granted },
          ].map((s) => (
            <div key={s.label} className="lux-glass px-5 py-4 flex items-baseline gap-3" data-testid={`photographer-stat-${s.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <span className="font-display text-3xl text-gold">{s.value ?? '—'}</span>
              <span className="text-[11px] tracking-[0.2em] uppercase" style={{ color: 'rgba(255,248,220,0.7)' }}>{s.label}</span>
            </div>
          ))}
        </motion.div>
      )}

      <motion.div
        variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.15 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
        data-testid="photographer-advantages-grid"
      >
        {advantages.map(({ icon: Icon, title, copy }, i) => (
          <motion.div
            key={title} variants={fadeUp} custom={i}
            className="lux-glass p-7 flex flex-col"
            whileHover={{ y: -6 }}
            data-testid={`photographer-advantage-${i}`}
          >
            <Icon className="w-7 h-7 text-gold mb-4" />
            <h3 className="font-display text-xl mb-2" style={{ color: '#FFF8DC' }}>{title}</h3>
            <p className="text-sm leading-relaxed flex-1" style={{ color: 'rgba(255,248,220,0.7)' }}>
              {copy}
            </p>
          </motion.div>
        ))}
      </motion.div>

      {/* Real-tier loyalty banner — driven by live super-admin tier config */}
      <motion.div
        initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.9, ease: [0.22,1,0.36,1] }}
        className="lux-glass mt-10 p-7 md:p-10 flex flex-col md:flex-row md:items-center md:justify-between gap-5"
        style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(139,0,0,0.12))' }}
        data-testid="photographer-offer-banner"
      >
        <div className="flex-1">
          <div className="lux-eyebrow mb-2">◆ Loyalty Reward</div>
          {firstMilestone ? (
            <>
              <h3 className="font-display text-2xl md:text-3xl mb-2" style={{ color: '#FFF8DC' }}>
                Publish <span className="text-gold italic font-script">{firstMilestone.min_paid_links} {firstMilestone.min_paid_links === 1 ? 'invitation' : 'invitations'}</span>, unlock the <span className="text-gold">{firstMilestone.label}</span> tier.
              </h3>
              <p className="text-sm md:text-base mb-3" style={{ color: 'rgba(255,248,220,0.75)' }}>
                {milestoneTiers.length > 1 ? (
                  <>The Photographer Panel tracks every published link. Each milestone (
                    {milestoneTiers.map((t) => t.min_paid_links).join(' → ')}
                    ) unlocks a richer offer — bonus credits, lower pack prices and exclusive themes.</>
                ) : (
                  <>The Photographer Panel tracks every published link. Crossing this milestone enables bonus credits on every pack and a permanent discount.</>
                )}
              </p>
              <div className="flex flex-wrap gap-2 mt-2" data-testid="photographer-tier-chips">
                {milestoneTiers.map((t) => (
                  <span
                    key={t.key}
                    className="text-[10px] tracking-[0.2em] uppercase px-3 py-1.5 rounded-full inline-flex items-center gap-2"
                    style={{
                      background: 'rgba(212,175,55,0.18)',
                      color: '#FFE38A',
                      border: '1px solid rgba(212,175,55,0.45)',
                    }}
                    data-testid={`photographer-tier-chip-${t.key}`}
                  >
                    {t.label} · {t.min_paid_links}+ links · {t.discount_pct}% off · +{t.bonus_pct}% bonus
                  </span>
                ))}
              </div>
            </>
          ) : (
            <h3 className="font-display text-2xl md:text-3xl mb-2" style={{ color: '#FFF8DC' }}>
              Loyalty tiers configured by your admin — sign in to see your status.
            </h3>
          )}
        </div>
        <button onClick={onPhotographer} className="lux-btn shrink-0" data-testid="photographer-panel-cta">
          Photographer Panel <ArrowRight className="w-4 h-4" />
        </button>
      </motion.div>
    </section>
  );
};

const CTA = ({ onLogin }) => (
  <section className="relative px-6 md:px-16 py-32 z-10">
    <motion.div
      initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }}
      transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      className="lux-glass relative overflow-hidden p-12 md:p-20 text-center"
      style={{ background: 'linear-gradient(135deg, rgba(139,0,0,0.25), rgba(212,175,55,0.08))', borderColor: 'var(--lux-border-strong)' }}
    >
      <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(600px 300px at 50% 0%, rgba(212,175,55,0.18), transparent 70%)' }} />
      <span className="lux-eyebrow block mb-4">◆ Begin Your Studio</span>
      <h2 className="font-display text-[2.6rem] md:text-[4.2rem] leading-[1.05] mb-6" style={{ color: '#FFF8DC' }}>
        Your next couple deserves <span className="text-gold italic font-script">a masterpiece.</span>
      </h2>
      <p className="max-w-xl mx-auto text-[1.05rem] mb-9" style={{ color: 'rgba(255,248,220,0.7)' }}>
        Sign in to your studio. Build a wedding in 12 minutes. Publish in one credit.
        Make couples cry the elegant way.
      </p>
      <div className="flex flex-wrap justify-center gap-4">
        <button onClick={onLogin} className="lux-btn" data-testid="footer-cta-login">
          Enter Studio <ArrowRight className="w-4 h-4" />
        </button>
        <a href="#themes" className="lux-btn lux-btn-ghost" data-testid="footer-cta-themes">View Themes</a>
      </div>
    </motion.div>
  </section>
);

const Footer = ({ onSuperAdmin }) => (
  <footer className="relative z-10 px-6 md:px-16 py-12 border-t" style={{ borderColor: 'var(--lux-border)' }}>
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 text-sm">
      <div className="flex items-center gap-3">
        <img src="/brand/maja-icon-64.png" alt="MAJA Creations"
          className="w-7 h-7 rounded-full object-cover"
          style={{ boxShadow: '0 0 0 1px var(--lux-border-strong)' }} />
        <span className="font-display text-lg" style={{ color: '#FFF8DC' }}>MAJA<span className="text-gold"> </span>Creations</span>
      </div>
      <div className="flex flex-wrap items-center gap-6" style={{ color: 'rgba(255,248,220,0.55)' }}>
        <span>© {new Date().getFullYear()} MAJA Creations · Made in India</span>
        <a href="#features" className="hover:text-[var(--lux-gold)] transition-colors">Features</a>
        <a href="#pricing" className="hover:text-[var(--lux-gold)] transition-colors">Plans</a>
        <button onClick={onSuperAdmin} className="hover:text-[var(--lux-gold)] transition-colors text-left" data-testid="footer-super-admin-link">
          Super Admin
        </button>
      </div>
    </div>
  </footer>
);

const loadRazorpayScript = () =>
  new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement('script');
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.async = true;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });

export const PublicCreditsModal = ({ open, onClose, user, onPurchased }) => {
  const [packs, setPacks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [buying, setBuying] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setError('');
    setLoading(true);
    axios.get(`${API_URL}/api/public/credit-packs`)
      .then((r) => setPacks(r.data?.packs || []))
      .catch(() => setPacks([]))
      .finally(() => setLoading(false));
  }, [open]);

  const buy = async (pack) => {
    setBuying(pack.id);
    setError('');
    try {
      const ok = await loadRazorpayScript();
      if (!ok) throw new Error('Could not load Razorpay checkout.');

      const { data: order } = await axios.post(
        `${API_URL}/api/users/credits/purchase/create-order`,
        { pack_id: pack.id },
        { withCredentials: true }
      );

      await new Promise((resolve, reject) => {
        const options = {
          key: order.razorpay_key_id,
          amount: order.amount_paise,
          currency: order.currency || 'INR',
          name: 'MAJA Creations',
          description: `${order.pack_label} · ${order.credits} credits`,
          order_id: order.order_id,
          prefill: {
            name: order.user_name || user?.name || '',
            email: order.user_email || user?.email || '',
            contact: order.user_phone || user?.phone || '',
          },
          notes: { pack_id: pack.id, kind: 'user_credit_pack' },
          theme: { color: '#D4AF37' },
          method: { upi: true, card: true, netbanking: true, wallet: true },
          handler: async (rzp) => {
            try {
              await axios.post(
                `${API_URL}/api/users/credits/purchase/verify`,
                {
                  razorpay_order_id: rzp.razorpay_order_id,
                  razorpay_payment_id: rzp.razorpay_payment_id,
                  razorpay_signature: rzp.razorpay_signature,
                },
                { withCredentials: true }
              );
              onPurchased?.();
              resolve();
            } catch (e) {
              reject(new Error(e?.response?.data?.detail || 'Verification failed'));
            }
          },
          modal: { ondismiss: () => reject(new Error('Checkout cancelled')) },
        };
        const rzp = new window.Razorpay(options);
        rzp.on('payment.failed', (resp) => reject(new Error(resp.error?.description || 'Payment failed')));
        rzp.open();
      });

      onClose?.();
    } catch (e) {
      setError(e?.message || 'Could not start checkout.');
    } finally {
      setBuying(null);
    }
  };

  if (!open) return null;
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[110] flex items-center justify-center px-4 py-8"
        style={{ background: 'rgba(8,5,3,0.82)', backdropFilter: 'blur(10px)' }}
        onClick={onClose}
        data-testid="public-credits-modal"
      >
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.97 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="lux-glass w-full max-w-2xl max-h-[90vh] overflow-y-auto p-7 md:p-9 relative"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={onClose} className="absolute top-4 right-4 w-9 h-9 rounded-full grid place-items-center" style={{ border: '1px solid var(--lux-border)', color: 'rgba(255,248,220,0.7)' }} data-testid="public-credits-close">
            <XIcon className="w-4 h-4" />
          </button>
          <span className="lux-eyebrow block mb-2">◆ Credit packs</span>
          <h2 className="font-display text-3xl mb-1" style={{ color: '#FFF8DC' }}>
            Buy <span className="text-gold italic font-script">credits</span>
          </h2>
          <p className="text-xs mb-6" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Use credits to unlock premium designs, gallery downloads and AI photo matching. Account: <span className="text-gold">{user?.email || '—'}</span> · Current balance: <strong className="text-gold">{user?.credits ?? 0}</strong>
          </p>

          {loading ? (
            <div className="grid place-items-center py-10">
              <Sparkles className="w-5 h-5 animate-pulse" style={{ color: '#D4AF37' }} />
            </div>
          ) : packs.length === 0 ? (
            <div className="text-center py-12 px-4 rounded-lg" style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }} data-testid="public-credits-empty">
              <Coins className="w-9 h-9 mx-auto mb-3" style={{ color: '#D4AF37' }} />
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.7)' }}>
                No public credit packs yet. The studio is preparing them — check back soon.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="public-credits-list">
              {packs.map((p) => (
                <div key={p.id} className="lux-glass p-5 relative" style={p.badge ? { border: '1px solid rgba(212,175,55,0.55)' } : {}}>
                  {p.badge && (
                    <div className="absolute -top-3 left-5 px-3 py-1 rounded-full text-[9px] tracking-[0.25em] uppercase"
                      style={{ background: 'linear-gradient(135deg,#D4AF37,#B8941F)', color: '#16110C', fontFamily: 'DM Sans, sans-serif' }}>
                      {p.badge}
                    </div>
                  )}
                  <div className="font-display text-xl" style={{ color: '#FFF8DC' }}>{p.label}</div>
                  <div className="flex items-baseline gap-1 mt-2">
                    <IndianRupee className="w-4 h-4 text-gold" />
                    <span className="font-display text-3xl text-gold leading-none">{p.price_inr.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="text-xs tracking-[0.25em] uppercase mt-1" style={{ color: 'rgba(255,248,220,0.55)' }}>
                    = {p.credits.toLocaleString('en-IN')} credits
                  </div>
                  {p.design_id && (
                    <div className="text-[10px] tracking-[0.25em] uppercase mt-2 px-2 py-1 rounded-full inline-block" style={{ background: 'rgba(255,248,220,0.04)', border: '1px solid var(--lux-border)', color: 'rgba(255,248,220,0.7)' }}>
                      For {p.design_id.replace(/_/g, ' ')}
                    </div>
                  )}
                  {p.description && (
                    <p className="text-xs italic mt-3" style={{ color: 'rgba(255,248,220,0.7)' }}>{p.description}</p>
                  )}
                  <button
                    onClick={() => buy(p)}
                    disabled={buying === p.id}
                    className="lux-btn w-full justify-center mt-4"
                    data-testid={`public-credits-buy-${p.id}`}
                  >
                    {buying === p.id ? <Sparkles className="w-4 h-4 animate-pulse" /> : <Check className="w-4 h-4" />}
                    {buying === p.id ? 'Opening checkout…' : 'Buy now'}
                  </button>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-5 px-3 py-2 rounded-md text-xs"
              style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}>
              {error}
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

const LandingPage = () => {
  const navigate = useNavigate();
  const { user, logout, refresh } = useUserAuth();
  const [authModal, setAuthModal] = useState({ open: false, mode: 'login' });
  const [showCredits, setShowCredits] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [userProfilesCount, setUserProfilesCount] = useState(0);
  // Honour `?signin=1&return=/user/buy-theme/<id>` so the "Buy this theme"
  // button on each card can ask unauthenticated users to sign in and then
  // bounce them straight to the purchase wizard.
  const [returnAfterLogin, setReturnAfterLogin] = useState(null);

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  // Fetch the signed-in user's invitations count for the Studio Pulse card.
  useEffect(() => {
    if (!user) { setUserProfilesCount(0); return; }
    let cancelled = false;
    axios.get(`${API_URL}/api/users/profiles`, { withCredentials: true })
      .then((r) => { if (!cancelled) setUserProfilesCount((r.data?.profiles || []).length); })
      .catch(() => { if (!cancelled) setUserProfilesCount(0); });
    return () => { cancelled = true; };
  }, [user]);

  // On mount: if the URL is /?signin=1&return=..., open the auth modal.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('signin') === '1') {
      const ret = params.get('return') || '';
      // Same-origin guard: only honour relative paths.
      if (ret.startsWith('/') && !ret.startsWith('//')) setReturnAfterLogin(ret);
      setAuthModal({ open: true, mode: 'login' });
      // Clean the URL so refreshes don't keep re-opening the modal.
      const url = new URL(window.location.href);
      url.searchParams.delete('signin');
      url.searchParams.delete('return');
      window.history.replaceState({}, '', url.pathname + (url.search ? `?${url.searchParams}` : '') + url.hash);
    }
  }, []);

  // Once the user is signed in and a return path was captured, ship them there.
  useEffect(() => {
    if (user && returnAfterLogin) {
      const target = returnAfterLogin;
      setReturnAfterLogin(null);
      setAuthModal({ open: false, mode: 'login' });
      navigate(target);
    }
  }, [user, returnAfterLogin, navigate]);

  const openBuyCredits = () => {
    if (!user) { setAuthModal({ open: true, mode: 'signup' }); return; }
    setShowCredits(true);
  };

  /**
   * Hero & CTA "Enter Studio" — open the NORMAL USER studio.
   *   - If user is signed in → go straight to /user/dashboard
   *   - Otherwise → open the user auth modal and remember to bounce to
   *     /user/dashboard right after sign-in.
   */
  const enterUserStudio = () => {
    if (user) { navigate('/user/dashboard'); return; }
    setReturnAfterLogin('/user/dashboard');
    setAuthModal({ open: true, mode: 'login' });
  };

  // Opens the auth modal for a non-wedding design click, remembering the
  // destination so the user lands on the celebration form after sign-in.
  const requireUserAuth = (returnPath) => {
    if (user) { navigate(returnPath); return; }
    setReturnAfterLogin(returnPath);
    setAuthModal({ open: true, mode: 'signup' });
  };

  return (
    <div className="luxe relative" style={{ minHeight: '100vh', overflow: 'visible' }} data-testid="landing-page">
      <Nav
        onLogin={() => navigate('/admin/login')}
        user={user}
        onOpenAuth={() => setAuthModal({ open: true, mode: 'login' })}
        onLogout={logout}
        onBuyCredits={openBuyCredits}
        onUserDashboard={() => navigate('/user/dashboard')}
      />
      <Hero onLogin={enterUserStudio} user={user} userProfilesCount={userProfilesCount} />
      <Themes navigate={navigate} requireUserAuth={requireUserAuth} userSignedIn={!!user} />
      <Stats />
      <InvitationOptions />
      <Features />
      <Story />
      <Pricing />
      <PhotographerAdvantages onPhotographer={() => navigate('/admin/login')} />
      <CTA onLogin={enterUserStudio} />
      <Footer onSuperAdmin={() => navigate('/super-admin/login')} />

      <UserAuthModal
        open={authModal.open}
        initialMode={authModal.mode}
        onClose={() => setAuthModal({ ...authModal, open: false })}
      />

      <PublicCreditsModal open={showCredits} onClose={() => setShowCredits(false)} user={user} onPurchased={() => { refresh?.(); }} />

      {/* Floating "How to create your link" help button — fixed bottom-right */}
      <div className="fixed bottom-5 right-5 z-40">
        <HelpTourTrigger
          onClick={() => setTourOpen(true)}
          label="How to create link"
          testId="homepage-help-tour-trigger"
        />
      </div>
      <HelpTour
        open={tourOpen}
        onClose={() => setTourOpen(false)}
        steps={HOMEPAGE_USER_STEPS}
        title="How to create your wedding link"
      />
    </div>
  );
};

export default LandingPage;
