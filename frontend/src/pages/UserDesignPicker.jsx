import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ArrowRight, Coins, Wallet, ArrowLeft, Lock, X, AlertTriangle } from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';
import { ALL_DESIGNS, EVENTS, useAllDesigns } from '../themes/allDesigns';
import UniversalDesignRenderer from '../themes/UniversalDesignRenderer';
import { resolveHeroDesign } from '../themes/themeDesignResolver';
import { getThemeSampleData } from '../themes/sampleData';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const SAMPLE_PHOTO = 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=400&fit=crop&q=85';

const sampleFor = (themeId) => {
  const s = getThemeSampleData(themeId) || {};
  return {
    bride: s.bride || 'Anaya',
    groom: s.groom || 'Vihaan',
    date: s.weddingDate || '14 February 2026',
    venue: `${s.venue || 'Falaknuma Palace'}${s.city ? ' · ' + s.city.split(',')[0] : ''}`,
    photo: SAMPLE_PHOTO,
  };
};

const EVENT_LABELS = {
  Engagement: 'Engagement',
  Haldi: 'Haldi',
  Mehandi: 'Mehandi',
  Marriage: 'Marriage',
  Reception: 'Reception',
  Sangeeth: 'Sangeet',
};

const THEME_NAMES = {
  south_indian_temple: 'South Indian Temple',
  royal_mughal: 'Royal Mughal',
  muslim_nikah: 'Muslim Nikah',
  christian_elegant: 'Christian Elegant',
  bengali_traditional: 'Bengali Traditional',
  punjabi_sangeet: 'Punjabi Sangeet',
  beach_destination: 'Beach Destination',
  nature_eco_wedding: 'Nature / Eco',
  modern_minimal: 'Modern Minimal',
};

export default function UserDesignPicker() {
  const navigate = useNavigate();
  const { user, loading } = useUserAuth();
  // PHASE 8: subscribe to lazy-loaded theme cache so we re-render once chunks land.
  const designsCache = useAllDesigns();
  const [pricing, setPricing] = useState({});
  const [bundles, setBundles] = useState({});
  const [theme, setTheme] = useState('all');
  const [eventFilter, setEventFilter] = useState('all');
  const [loadingPricing, setLoadingPricing] = useState(true);
  const [previewCard, setPreviewCard] = useState(null);
  const [insufficientRedirectTimer, setInsufficientRedirectTimer] = useState(0);

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate('/', { replace: true }); return; }
    Promise.all([
      axios.get(`${API_URL}/api/public/design-pricing`),
      axios.get(`${API_URL}/api/public/theme-bundle-pricing`),
    ])
      .then(([p, b]) => {
        setPricing(p.data?.pricing || {});
        setBundles(b.data?.bundles || {});
      })
      .finally(() => setLoadingPricing(false));
  }, [loading, user, navigate]);

  /* Flatten all themes → designs with theme metadata */
  const allCards = useMemo(() => {
    const cards = [];
    Object.entries(designsCache || {}).forEach(([themeId, t]) => {
      Object.entries(t.events || {}).forEach(([evt, list]) => {
        (list || []).forEach((d) => {
          cards.push({
            ...d,
            themeId,
            themeName: THEME_NAMES[themeId] || themeId,
            event: evt,
          });
        });
      });
    });
    return cards;
  }, [designsCache]);

  const themesList = useMemo(
    () => Object.keys(designsCache || {}).map((id) => ({ id, name: THEME_NAMES[id] || id })),
    [designsCache],
  );

  const filtered = useMemo(
    () => allCards.filter(
      (c) => (theme === 'all' || c.themeId === theme) && (eventFilter === 'all' || c.event === eventFilter),
    ),
    [allCards, theme, eventFilter],
  );

  const select = (card) => {
    setPreviewCard(card);
    setInsufficientRedirectTimer(0);
  };

  // Auto-redirect to buy credits when modal is shown for an unaffordable design
  useEffect(() => {
    if (!previewCard) return;
    const cost = pricing[previewCard.id]?.credits ?? 1;
    const balance = user?.credits ?? 0;
    if (balance >= cost) {
      // Edge case: user topped up in another tab while the modal was open.
      // Cancel any pending auto-redirect so we don't bounce them away.
      setInsufficientRedirectTimer(0);
      return;
    }
    // Start 5-second auto-redirect. Always include a `return` URL so the
    // user lands back on this picker after their top-up.
    setInsufficientRedirectTimer(5);
    const ret = encodeURIComponent(window.location.pathname + window.location.search);
    const interval = setInterval(() => {
      setInsufficientRedirectTimer((t) => {
        if (t <= 1) {
          clearInterval(interval);
          navigate(`/user/buy-credits?required=${cost}&design=${previewCard.id}&return=${ret}`);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [previewCard, pricing, user, navigate]);

  /* July 2025 — Path B (Dashboard → Create Invitation → UserDesignPicker)
     previously navigated straight to /user/create-invitation/… and bypassed
     the PurchaseOptionsWizard entirely, meaning the user never saw the
     add-on / expiry upsell and only paid the base design credit.
     Now we route them through /user/buy-design/… so they get the same
     wizard as Path A (Landing → ThemeEventPicker → EventDesignPicker). */
  const confirmUseDesign = (card) => {
    setPreviewCard(null);
    navigate(`/user/buy-design/${card.themeId}/${card.event}/${card.id}`);
  };

  const goBuyCredits = (card) => {
    const cost = pricing[card.id]?.credits ?? 1;
    setPreviewCard(null);
    // Carry a return URL so the user lands back on this picker after the
    // Razorpay verify roundtrip — no dead-end stranding on the credits page.
    const ret = encodeURIComponent(window.location.pathname + window.location.search);
    navigate(`/user/buy-credits?required=${cost}&design=${card.id}&return=${ret}`);
  };

  if (loading || loadingPricing) {
    return (
      <div className="luxe min-h-screen grid place-items-center">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  return (
    <div className="luxe min-h-screen px-5 md:px-12 py-8 md:py-12" data-testid="user-design-picker">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <button
            onClick={() => navigate('/user/dashboard')}
            className="text-[10px] tracking-[0.25em] uppercase mb-3 inline-flex items-center gap-2 hover:opacity-80"
            style={{ color: 'rgba(255,248,220,0.6)' }}
            data-testid="user-picker-back"
          >
            <ArrowLeft className="w-3 h-3" /> Back to studio
          </button>
          <span className="lux-eyebrow block mb-2">◆ Choose Your Design</span>
          <h1 className="font-display text-3xl md:text-4xl" style={{ color: '#FFF8DC' }}>
            Pick a <span className="italic font-script text-gold">design</span> for your invitation.
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Each design has its own credit price set by the studio.
          </p>
        </div>
        <div className="lux-glass px-5 py-3 flex items-center gap-3 self-start" data-testid="user-picker-balance">
          <Wallet className="w-5 h-5 text-gold" />
          <div>
            <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
              Your Balance
            </div>
            <div className="font-display text-2xl text-gold leading-none">{user?.credits ?? 0}</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="lux-glass p-3 mb-6 flex flex-wrap gap-2 items-center" data-testid="user-picker-filters">
        <span className="text-[10px] tracking-[0.25em] uppercase mr-2" style={{ color: 'rgba(255,248,220,0.5)' }}>Theme</span>
        <button onClick={() => setTheme('all')} className={`px-3 py-1.5 rounded-full text-[10px] tracking-[0.18em] uppercase ${theme === 'all' ? 'text-gold' : ''}`} style={{ border: '1px solid var(--lux-border)', background: theme === 'all' ? 'rgba(212,175,55,0.1)' : 'transparent', color: theme === 'all' ? '#D4AF37' : 'rgba(255,248,220,0.7)' }} data-testid="filter-theme-all">All</button>
        {themesList.map((t) => (
          <button
            key={t.id}
            onClick={() => setTheme(t.id)}
            className={`px-3 py-1.5 rounded-full text-[10px] tracking-[0.18em] uppercase ${theme === t.id ? 'text-gold' : ''}`}
            style={{ border: '1px solid var(--lux-border)', background: theme === t.id ? 'rgba(212,175,55,0.1)' : 'transparent', color: theme === t.id ? '#D4AF37' : 'rgba(255,248,220,0.7)' }}
            data-testid={`filter-theme-${t.id}`}
          >
            {t.name}
          </button>
        ))}
      </div>
      <div className="lux-glass p-3 mb-8 flex flex-wrap gap-2 items-center">
        <span className="text-[10px] tracking-[0.25em] uppercase mr-2" style={{ color: 'rgba(255,248,220,0.5)' }}>Event</span>
        <button onClick={() => setEventFilter('all')} className={`px-3 py-1.5 rounded-full text-[10px] tracking-[0.18em] uppercase`} style={{ border: '1px solid var(--lux-border)', background: eventFilter === 'all' ? 'rgba(212,175,55,0.1)' : 'transparent', color: eventFilter === 'all' ? '#D4AF37' : 'rgba(255,248,220,0.7)' }} data-testid="filter-event-all">All</button>
        {Object.entries(EVENT_LABELS).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setEventFilter(k)}
            className={`px-3 py-1.5 rounded-full text-[10px] tracking-[0.18em] uppercase`}
            style={{ border: '1px solid var(--lux-border)', background: eventFilter === k ? 'rgba(212,175,55,0.1)' : 'transparent', color: eventFilter === k ? '#D4AF37' : 'rgba(255,248,220,0.7)' }}
            data-testid={`filter-event-${k}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Theme-bundle banner — only when one specific theme is selected and a bundle exists */}
      {theme !== 'all' && bundles[theme] && (
        <div
          className="lux-glass p-5 mb-6 flex flex-wrap items-center justify-between gap-4"
          style={{ border: '1px solid rgba(212,175,55,0.5)' }}
          data-testid={`bundle-banner-${theme}`}
        >
          <div>
            <span className="lux-eyebrow block mb-1.5">◆ Theme Bundle</span>
            <div className="font-display text-xl" style={{ color: '#FFF8DC' }}>
              Unlock <span className="font-script italic text-gold">all</span> {THEME_NAMES[theme] || theme} designs
            </div>
            <div className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.65)' }}>
              {bundles[theme].label || 'One purchase covers every design in this theme'}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>Bundle</div>
              <div className="font-display text-2xl text-gold leading-none">
                {bundles[theme].credits || '—'} cr
              </div>
              {bundles[theme].inr_price ? (
                <div className="text-[11px] mt-0.5" style={{ color: 'rgba(255,248,220,0.7)' }}>
                  ₹{bundles[theme].inr_price}
                </div>
              ) : null}
            </div>
            <button
              onClick={() => {
                const ret = encodeURIComponent(window.location.pathname + window.location.search);
                navigate(`/user/buy-credits?required=${bundles[theme].credits || 0}&theme=${theme}&return=${ret}`);
              }}
              className="lux-btn"
              data-testid={`bundle-buy-${theme}`}
            >
              Get the bundle
            </button>
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="user-picker-grid">
        {filtered.map((card) => {
          const cost = pricing[card.id]?.credits ?? 1;
          const inrPrice = pricing[card.id]?.inr_price ?? 0;
          const balance = user?.credits ?? 0;
          const affordable = balance >= cost;
          const themeRes = resolveHeroDesign(card.themeId);
          const SAMPLE = sampleFor(card.themeId);
          return (
            <motion.button
              key={`${card.themeId}-${card.id}`}
              type="button"
              onClick={() => select(card)}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              whileHover={{ y: -4 }}
              className="lux-glass p-4 text-left relative group"
              data-testid={`design-card-${card.id}`}
            >
              <div className="absolute -top-2 right-3 z-10 px-2.5 py-1 rounded-full text-[10px] tracking-[0.2em] uppercase inline-flex items-center gap-1"
                style={{
                  background: affordable ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'rgba(139,0,0,0.4)',
                  color: affordable ? '#16110C' : '#FFD7C9',
                  border: affordable ? '1px solid #D4AF37' : '1px solid rgba(255,80,80,0.5)',
                }}
              >
                {affordable ? <Coins className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                {cost} {cost === 1 ? 'credit' : 'credits'}
                {inrPrice ? <span className="ml-1 opacity-80">· ₹{inrPrice}</span> : null}
              </div>
              {themeRes?.design && themeRes?.theme && (
                <div className="overflow-hidden rounded-md mb-3">
                  <UniversalDesignRenderer
                    design={{ ...themeRes.design, image: card.image, id: card.id }}
                    theme={themeRes.theme}
                    bride={SAMPLE.bride}
                    groom={SAMPLE.groom}
                    date={SAMPLE.date}
                    venue={SAMPLE.venue}
                    photo={SAMPLE.photo}
                    testId={`design-preview-${card.id}`}
                  />
                </div>
              )}
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
                  {EVENT_LABELS[card.event] || card.event}
                </span>
                <span className="text-[10px] tracking-[0.18em] uppercase" style={{ color: 'rgba(255,248,220,0.4)' }}>
                  {card.themeName}
                </span>
              </div>
              <h3 className="font-display text-base leading-tight mb-2" style={{ color: '#FFF8DC' }}>
                {card.title}
              </h3>
              <div className="text-[10px] tracking-[0.25em] uppercase inline-flex items-center gap-1 group-hover:text-gold transition-colors" style={{ color: affordable ? '#D4AF37' : 'rgba(255,180,120,0.7)' }}>
                {affordable ? 'Use this design' : 'Buy credits to use'} <ArrowRight className="w-3 h-3" />
              </div>
            </motion.button>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
          No designs match the filters.
        </div>
      )}

      {/* Preview Modal — Phase 3 */}
      <AnimatePresence>
        {previewCard && (() => {
          const cost = pricing[previewCard.id]?.credits ?? 1;
          const inrPrice = pricing[previewCard.id]?.inr_price ?? 0;
          const balance = user?.credits ?? 0;
          const affordable = balance >= cost;
          const themeRes = resolveHeroDesign(previewCard.themeId);
          const SAMPLE = sampleFor(previewCard.themeId);
          return (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8"
              style={{ background: 'rgba(10,6,2,0.85)', backdropFilter: 'blur(8px)' }}
              onClick={() => setPreviewCard(null)}
              data-testid="design-preview-modal"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 16 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 16 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
                onClick={(e) => e.stopPropagation()}
                className="lux-glass relative max-w-5xl w-full max-h-[92vh] overflow-y-auto p-6 md:p-8 rounded-lg"
                style={{ border: '1px solid var(--lux-border)' }}
              >
                <button
                  onClick={() => setPreviewCard(null)}
                  className="absolute top-4 right-4 z-10 p-2 rounded-full hover:opacity-80"
                  style={{ background: 'rgba(255,248,220,0.08)', border: '1px solid var(--lux-border)' }}
                  data-testid="design-preview-close"
                  aria-label="Close preview"
                >
                  <X className="w-4 h-4" style={{ color: '#FFF8DC' }} />
                </button>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-8">
                  {/* Left: Large Preview */}
                  <div className="lg:col-span-3">
                    <div
                      className="rounded-md overflow-hidden"
                      style={{ border: '1px solid var(--lux-border)' }}
                      data-testid="design-preview-large"
                    >
                      {themeRes?.design && themeRes?.theme && (
                        <UniversalDesignRenderer
                          design={{ ...themeRes.design, image: previewCard.image, id: previewCard.id }}
                          theme={themeRes.theme}
                          bride={SAMPLE.bride}
                          groom={SAMPLE.groom}
                          date={SAMPLE.date}
                          venue={SAMPLE.venue}
                          photo={SAMPLE.photo}
                          testId={`design-preview-large-${previewCard.id}`}
                        />
                      )}
                    </div>
                  </div>

                  {/* Right: Details + CTA */}
                  <div className="lg:col-span-2 flex flex-col">
                    <span className="lux-eyebrow block mb-2">◆ Design Preview</span>
                    <h2
                      className="font-display text-2xl md:text-3xl leading-tight mb-2"
                      style={{ color: '#FFF8DC' }}
                      data-testid="design-preview-title"
                    >
                      {previewCard.title}
                    </h2>
                    <div className="flex items-center gap-3 mb-4 text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.6)' }}>
                      <span data-testid="design-preview-theme-name">{previewCard.themeName}</span>
                      <span style={{ color: 'rgba(255,248,220,0.3)' }}>·</span>
                      <span data-testid="design-preview-event">{EVENT_LABELS[previewCard.event] || previewCard.event}</span>
                    </div>

                    {/* Price card */}
                    <div
                      className="p-4 rounded-md mb-5"
                      style={{
                        background: 'rgba(212,175,55,0.06)',
                        border: '1px solid rgba(212,175,55,0.25)',
                      }}
                      data-testid="design-preview-pricing"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
                          Design Cost
                        </span>
                        <div className="flex items-center gap-1.5 font-display text-2xl text-gold">
                          <Coins className="w-4 h-4" />
                          <span data-testid="design-preview-cost">{cost}</span>
                          <span className="text-sm">{cost === 1 ? 'credit' : 'credits'}</span>
                        </div>
                      </div>
                      {inrPrice ? (
                        <div className="text-[11px]" style={{ color: 'rgba(255,248,220,0.55)' }}>
                          Equivalent to ₹{inrPrice}
                        </div>
                      ) : null}
                      <div className="mt-3 pt-3 flex items-center justify-between" style={{ borderTop: '1px solid rgba(212,175,55,0.15)' }}>
                        <span className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
                          Your Balance
                        </span>
                        <div className="flex items-center gap-1.5 font-display text-lg" style={{ color: affordable ? '#D4AF37' : '#FFB47C' }}>
                          <Wallet className="w-4 h-4" />
                          <span data-testid="design-preview-balance">{balance}</span>
                        </div>
                      </div>
                    </div>

                    {/* CTA / Insufficient */}
                    {affordable ? (
                      <button
                        onClick={() => confirmUseDesign(previewCard)}
                        className="lux-btn w-full justify-center py-4 text-sm tracking-[0.18em]"
                        data-testid="design-preview-use-cta"
                      >
                        Use this design ({cost} {cost === 1 ? 'credit' : 'credits'}) <ArrowRight className="w-4 h-4 ml-2" />
                      </button>
                    ) : (
                      <div data-testid="design-preview-insufficient">
                        <div
                          className="p-4 rounded-md mb-3 flex items-start gap-3"
                          style={{
                            background: 'rgba(139,0,0,0.18)',
                            border: '1px solid rgba(255,80,80,0.35)',
                          }}
                        >
                          <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0" style={{ color: '#FFB47C' }} />
                          <div>
                            <div className="font-display text-base mb-1" style={{ color: '#FFD7C9' }}>
                              Insufficient credits
                            </div>
                            <div className="text-xs" style={{ color: 'rgba(255,215,201,0.85)' }}>
                              You need <strong>{cost - balance}</strong> more {(cost - balance) === 1 ? 'credit' : 'credits'} to use this design.
                              {insufficientRedirectTimer > 0 && (
                                <span> Redirecting in {insufficientRedirectTimer}s…</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => goBuyCredits(previewCard)}
                          className="lux-btn w-full justify-center py-4 text-sm tracking-[0.18em]"
                          data-testid="design-preview-buy-credits-cta"
                        >
                          <Coins className="w-4 h-4 mr-2" />
                          Buy credits now <ArrowRight className="w-4 h-4 ml-2" />
                        </button>
                      </div>
                    )}

                    <p className="text-[10px] mt-4 italic text-center" style={{ color: 'rgba(255,248,220,0.4)' }}>
                      Credits are deducted only after you submit the invitation form.
                    </p>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          );
        })()}
      </AnimatePresence>
    </div>
  );
}
