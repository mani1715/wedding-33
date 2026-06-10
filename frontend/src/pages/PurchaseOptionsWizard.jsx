/**
 * PurchaseOptionsWizard — single wizard that lets a normal user
 * (couple) configure an invitation purchase before publishing:
 *
 *   1. Pick add-ons (each carries a credit cost)
 *   2. Pick a link-expiry tier (days + credits)
 *   3. See a running total
 *   4. Checkout (uses wallet credits) OR top-up if balance is short
 *
 * Routes (registered in App.js):
 *   • /user/buy-design/:themeId/:event/:designId   (per-design flow)
 *   • /user/buy-theme/:themeId                     (theme-level flow)
 *
 * On checkout for a per-design flow the user is sent to
 *   /user/create-invitation/:themeId/:event/:designId?addons=a,b,c&expiry=1_month
 * so the invitation form can mark those add-ons as "Purchased — included".
 *
 * For the theme-level flow we route the user to the design picker for
 * that theme with the same query string so they keep the chosen
 * add-ons through the picker → form flow.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  ArrowLeft, ArrowRight, Sparkles, Coins, Wallet, Check, Clock, AlertTriangle, ShoppingBag,
} from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';
import { getThemeById } from '@/themes/masterThemes';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const SECTION_TITLE = { color: '#FFF8DC' };
const eyebrowGold = { color: 'rgba(255,248,220,0.6)' };

export default function PurchaseOptionsWizard() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { themeId, event, designId } = params;
  const mode = designId ? 'design' : 'theme';

  const { user, loading } = useUserAuth();
  const themeMeta = useMemo(() => getThemeById(themeId), [themeId]);

  /* July 2025 — Pre-populate from query string so the user doesn't have to
     re-pick add-ons / expiry when they bounce between the wizard and the
     EventDesignPicker.
       /user/buy-design/T/E/D?addons=a,b,c&expiry=1_month
     Both addons & expiry round-trip through EventDesignPicker → here. */
  const initialSearch = new URLSearchParams(location.search);
  const initialAddonsCsv = initialSearch.get('addons') || '';
  const initialExpiry    = initialSearch.get('expiry') || null;
  const preselectedAddons = useMemo(() => {
    const out = {};
    initialAddonsCsv.split(',').filter(Boolean).forEach((id) => { out[id] = true; });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [addons, setAddons] = useState([]);          // catalogue
  const [tiers, setTiers] = useState([]);            // expiry tiers
  const [selectedAddons, setSelectedAddons] = useState(preselectedAddons); // {id: true}
  const [selectedTier, setSelectedTier] = useState(initialExpiry);   // tier.id
  const [baseCost, setBaseCost] = useState(themeMeta?.creditCost ?? 1);
  const [busy, setBusy] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // ── Auth gate
  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      // Previously: navigate('/', { replace: true }) — this silently bounced
      // the user back to the landing page when they clicked "Buy this theme"
      // without being signed in (it looked like a broken page reload).
      // Now we send them home with a query that auto-opens the sign-in modal
      // and remembers where to come back to after login.
      const here = window.location.pathname + window.location.search;
      navigate(`/?signin=1&return=${encodeURIComponent(here)}`, { replace: true });
      return;
    }
  }, [loading, user, navigate]);

  // ── Load catalogue + pricing
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [addonsRes, tiersRes, pricingRes] = await Promise.all([
          axios.get(`${API_URL}/api/public/addons`),
          axios.get(`${API_URL}/api/public/expiry-tiers`),
          axios.get(`${API_URL}/api/public/design-pricing`).catch(() => ({ data: { pricing: {} } })),
        ]);
        if (cancelled) return;
        setAddons(addonsRes.data?.addons || []);
        setTiers(tiersRes.data?.tiers || []);
        // Default-select cheapest tier so total is never zero-confusing,
        // BUT respect a user-provided ?expiry= query param (set in initial
        // state) so we don't clobber a pre-selected tier when bouncing in
        // from the design picker.
        const sortedTiers = [...(tiersRes.data?.tiers || [])].sort((a, b) => (a.credits || 0) - (b.credits || 0));
        if (sortedTiers.length) {
          setSelectedTier((prev) => {
            if (prev && sortedTiers.some((t) => t.id === prev)) return prev;
            return sortedTiers[0].id;
          });
        }

        if (mode === 'design' && designId) {
          const cred = pricingRes.data?.pricing?.[designId]?.credits;
          if (typeof cred === 'number') setBaseCost(cred);
          else setBaseCost(themeMeta?.creditCost ?? 1);
        } else {
          setBaseCost(themeMeta?.creditCost ?? 1);
        }
      } catch (e) {
        setError('Could not load the add-on catalogue. Please try again.');
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [designId, themeId, mode]);

  // ── Derived total
  const addonTotal = useMemo(() => {
    return addons.reduce((sum, a) => (selectedAddons[a.id] ? sum + (a.credits || 0) : sum), 0);
  }, [addons, selectedAddons]);

  const tierCost = useMemo(() => {
    const t = tiers.find((x) => x.id === selectedTier);
    return t?.credits || 0;
  }, [tiers, selectedTier]);

  const totalCost = baseCost + addonTotal + tierCost;
  const balance = user?.credits ?? 0;
  const shortfall = Math.max(0, totalCost - balance);

  // ── Toggle helpers
  const toggleAddon = (id) => setSelectedAddons((m) => ({ ...m, [id]: !m[id] }));

  // ── Checkout
  const handleCheckout = () => {
    setError('');
    if (shortfall > 0) {
      // Send to top-up with return URL — return-url preserves the wizard
      // path AND the user's current add-on/expiry selections (we re-encode
      // them in the return URL so the wizard restores them on bounce-back).
      const chosen = Object.keys(selectedAddons).filter((k) => selectedAddons[k]);
      const qs = new URLSearchParams();
      if (chosen.length) qs.set('addons', chosen.join(','));
      if (selectedTier) qs.set('expiry', selectedTier);
      const here = window.location.pathname + (qs.toString() ? `?${qs.toString()}` : '');
      const ret = encodeURIComponent(here);
      navigate(`/user/buy-credits?return=${ret}&need=${shortfall}`);
      return;
    }
    setSubmitting(true);

    const chosen = Object.keys(selectedAddons).filter((k) => selectedAddons[k]);
    const qs = new URLSearchParams();
    if (chosen.length) qs.set('addons', chosen.join(','));
    if (selectedTier) qs.set('expiry', selectedTier);

    if (mode === 'design') {
      navigate(`/user/create-invitation/${themeId}/${event}/${designId}?${qs.toString()}`);
    } else {
      // Theme-level checkout → push them into the design picker for that theme
      // carrying the selected add-ons through.
      navigate(`/themes/${themeId}/events?${qs.toString()}`);
    }
    setSubmitting(false);
  };

  if (loading || busy) {
    return (
      <div className="luxe min-h-screen grid place-items-center" data-testid="wizard-loading">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  return (
    <div className="luxe min-h-screen px-5 md:px-12 py-8 md:py-12" data-testid="purchase-options-wizard">
      {/* ────────────────────────────────────────────────────────── */}
      {/* Header                                                    */}
      {/* ────────────────────────────────────────────────────────── */}
      <button
        onClick={() => navigate(-1)}
        className="text-[10px] tracking-[0.25em] uppercase mb-5 inline-flex items-center gap-2 hover:opacity-80"
        style={{ color: 'rgba(255,248,220,0.6)' }}
        data-testid="wizard-back-btn"
      >
        <ArrowLeft className="w-3 h-3" /> Back
      </button>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
        <div>
          <span className="lux-eyebrow block mb-2">◆ Purchase Options</span>
          <h1 className="font-display text-3xl md:text-5xl leading-tight" style={SECTION_TITLE}>
            Compose your <span className="font-script italic text-gold">invitation.</span>
          </h1>
          <p className="mt-2 text-sm max-w-xl" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {mode === 'design'
              ? `${themeMeta?.name || themeId} · ${event} · Design ${String(designId).slice(0, 6)}`
              : `${themeMeta?.name || themeId} — pick the features you'd like, then we'll take you to the design picker.`}
          </p>
        </div>
        <div className="lux-glass px-5 py-3 flex items-center gap-3" data-testid="wizard-balance">
          <Wallet className="w-5 h-5 text-gold" />
          <div>
            <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>Balance</div>
            <div className="font-display text-2xl text-gold leading-none">{balance}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ────────────────────────── Left: catalog ───────────────── */}
        <div className="lg:col-span-2 space-y-8">
          {/* Add-ons */}
          <section data-testid="wizard-addons-section">
            <span className="lux-eyebrow block mb-3">◆ Pick your add-ons</span>
            <h2 className="font-display text-2xl mb-5" style={SECTION_TITLE}>
              The <span className="text-gold italic font-script">extras.</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {addons.map((a) => {
                const on = !!selectedAddons[a.id];
                return (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => toggleAddon(a.id)}
                    className="lux-glass p-4 text-left transition-all hover:scale-[1.01] relative"
                    style={{
                      borderColor: on ? '#D4AF37' : 'var(--lux-border)',
                      boxShadow: on ? '0 0 0 1px #D4AF37 inset' : undefined,
                    }}
                    data-testid={`wizard-addon-${a.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h3 className="font-display text-base mb-1" style={SECTION_TITLE}>{a.label}</h3>
                        <p className="text-[11px] leading-relaxed" style={{ color: 'rgba(255,248,220,0.6)' }}>
                          {a.description}
                        </p>
                      </div>
                      <div
                        className="px-2 py-1 rounded-full text-[10px] tracking-[0.15em] uppercase shrink-0 inline-flex items-center gap-1"
                        style={{ background: on ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'rgba(255,248,220,0.06)', color: on ? '#16110C' : 'rgba(255,248,220,0.7)' }}
                      >
                        <Coins className="w-3 h-3" /> {a.credits}
                      </div>
                    </div>
                    {on && (
                      <span className="absolute top-2 right-2 w-5 h-5 rounded-full grid place-items-center" style={{ background: '#D4AF37' }}>
                        <Check className="w-3 h-3" style={{ color: '#16110C' }} />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </section>

          {/* Expiry tier */}
          <section data-testid="wizard-tier-section">
            <span className="lux-eyebrow block mb-3">◆ How long should the link live?</span>
            <h2 className="font-display text-2xl mb-5" style={SECTION_TITLE}>
              The <span className="text-gold italic font-script">lifetime.</span>
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {tiers.map((t) => {
                const active = selectedTier === t.id;
                return (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => setSelectedTier(t.id)}
                    className="lux-glass p-4 text-left transition-all hover:scale-[1.02]"
                    style={{
                      borderColor: active ? '#D4AF37' : 'var(--lux-border)',
                      boxShadow: active ? '0 0 0 1px #D4AF37 inset' : undefined,
                    }}
                    data-testid={`wizard-tier-${t.id}`}
                  >
                    <Clock className="w-4 h-4 text-gold mb-2" />
                    <div className="font-display text-lg" style={SECTION_TITLE}>{t.label}</div>
                    <div className="text-[10px] tracking-[0.2em] uppercase mt-0.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                      {t.days} days
                    </div>
                    <div className="mt-3 text-xs inline-flex items-center gap-1 text-gold">
                      <Coins className="w-3 h-3" /> {t.credits} credit{t.credits === 1 ? '' : 's'}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        {/* ────────────────────────── Right: cart ───────────────── */}
        <aside className="lg:sticky lg:top-8 self-start" data-testid="wizard-summary">
          <div className="lux-glass p-6">
            <span className="lux-eyebrow block mb-3">◆ Order Summary</span>
            <h3 className="font-display text-2xl mb-5" style={SECTION_TITLE}>
              Your <span className="text-gold italic font-script">total.</span>
            </h3>

            <ul className="space-y-3 mb-5 text-sm" style={{ color: 'rgba(255,248,220,0.85)' }}>
              <li className="flex items-center justify-between" data-testid="summary-base">
                <span>{mode === 'design' ? 'Design (base)' : `${themeMeta?.name || 'Theme'} (base)`}</span>
                <span className="text-gold font-display">{baseCost}</span>
              </li>
              {addons.filter((a) => selectedAddons[a.id]).map((a) => (
                <li key={a.id} className="flex items-center justify-between text-xs" data-testid={`summary-addon-${a.id}`} style={{ color: 'rgba(255,248,220,0.75)' }}>
                  <span>+ {a.label}</span>
                  <span className="text-gold">{a.credits}</span>
                </li>
              ))}
              {selectedTier && (
                <li className="flex items-center justify-between text-xs" data-testid="summary-tier" style={{ color: 'rgba(255,248,220,0.75)' }}>
                  <span>+ Link expiry · {tiers.find((t) => t.id === selectedTier)?.label}</span>
                  <span className="text-gold">{tierCost}</span>
                </li>
              )}
            </ul>

            <div className="lux-hairline my-4" />
            <div className="flex items-center justify-between mb-5">
              <span className="text-[10px] tracking-[0.3em] uppercase" style={eyebrowGold}>Total</span>
              <span className="font-display text-3xl text-gold inline-flex items-center gap-2" data-testid="summary-total">
                <Coins className="w-5 h-5" /> {totalCost}
              </span>
            </div>

            {shortfall > 0 ? (
              <div className="px-3 py-2 rounded-md text-xs mb-4 flex items-start gap-2"
                style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
                data-testid="wizard-shortfall"
              >
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>You need <strong>{shortfall}</strong> more credit{shortfall === 1 ? '' : 's'}. Click below to top-up — we&apos;ll bring you back here.</span>
              </div>
            ) : (
              <div className="text-[10px] tracking-[0.2em] uppercase mb-4" style={{ color: 'rgba(255,248,220,0.55)' }}>
                Balance after: <span className="text-gold">{balance - totalCost}</span>
              </div>
            )}

            <button
              onClick={handleCheckout}
              disabled={submitting}
              className="lux-btn w-full justify-center"
              data-testid="wizard-checkout-btn"
            >
              {shortfall > 0 ? (
                <><Wallet className="w-4 h-4" /> Top-up &amp; continue</>
              ) : (
                <><ShoppingBag className="w-4 h-4" /> {mode === 'design' ? 'Continue to invitation' : 'Continue to designs'} <ArrowRight className="w-4 h-4" /></>
              )}
            </button>

            {error && (
              <div className="mt-3 px-3 py-2 rounded-md text-xs"
                style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
                data-testid="wizard-error"
              >
                {error}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
