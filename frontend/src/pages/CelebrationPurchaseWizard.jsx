/**
 * CelebrationPurchaseWizard — non-wedding analogue of `PurchaseOptionsWizard`.
 *
 * Route: /user/buy-celebration/:category/:designId
 *
 * Flow (matches the wedding wizard the user is familiar with):
 *   1. Show base design cost
 *   2. List category-specific features with checkboxes + credit cost each
 *   3. Let the user pick a link-expiry tier
 *   4. Show running total + wallet balance + shortfall warning
 *   5. On checkout → /user/celebration/new?category=X&design_id=Y&features=a,b,c&expiry=tier
 *      (if shortfall > 0 → /user/buy-credits?... with return URL preserving selections)
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  ArrowLeft, ArrowRight, Sparkles, Coins, Wallet, Check, Clock, AlertTriangle,
} from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';
const SECTION_TITLE = { color: '#FFF8DC' };

const CATEGORY_HERO = {
  baby_birthday: { icon: '🎂', label: 'Baby Birthday', tagline: 'A joyful first celebration' },
  half_saree:    { icon: '👗', label: 'Half Saree',    tagline: 'A coming-of-age tradition' },
  puberty:       { icon: '🌸', label: 'Puberty',       tagline: 'Manjal Neerattu — a sacred threshold' },
  dhoti:         { icon: '👔', label: 'Dhoti',         tagline: 'Vetti Kattum Vizha — a young man emerges' },
};

export default function CelebrationPurchaseWizard() {
  const navigate = useNavigate();
  const { category, designId } = useParams();
  const { user, loading } = useUserAuth();
  const heroMeta = CATEGORY_HERO[category] || { icon: '✨', label: category, tagline: '' };

  const [features, setFeatures] = useState([]);     // [{key,label,credits,default,icon}]
  const [pricing, setPricing]   = useState({ design_credits: 1, feature_credits: {} });
  const [design, setDesign]     = useState(null);   // {design_id, name, preview_image, credit_cost}
  const [tiers, setTiers]       = useState([]);
  const [selectedFeatures, setSelectedFeatures] = useState({}); // {featureKey: true}
  const [selectedTier, setSelectedTier] = useState(null);
  const [busy, setBusy]         = useState(true);
  const [error, setError]       = useState('');

  // ── Lux body styling
  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  // ── Auth gate
  useEffect(() => {
    if (loading) return;
    if (!user) {
      const here = window.location.pathname + window.location.search;
      navigate(`/?signin=1&return=${encodeURIComponent(here)}`, { replace: true });
    }
  }, [loading, user, navigate]);

  // ── Load catalogue
  useEffect(() => {
    if (!category || !designId) return;
    let cancelled = false;
    (async () => {
      try {
        const [featsRes, priceRes, tiersRes, designsRes] = await Promise.all([
          axios.get(`${API_URL}/api/event-categories/${category}/features`),
          axios.get(`${API_URL}/api/event-categories/${category}/pricing?user_type=normal_user`),
          axios.get(`${API_URL}/api/public/expiry-tiers`),
          axios.get(`${API_URL}/api/event-categories/${category}/designs`),
        ]);
        if (cancelled) return;

        const featsList = featsRes.data?.features || [];
        setFeatures(featsList);
        setPricing(priceRes.data || { design_credits: 1, feature_credits: {} });
        setTiers(tiersRes.data?.tiers || []);

        const allDesigns = designsRes.data?.designs || [];
        const found = allDesigns.find((d) => d.design_id === designId);
        setDesign(found || { design_id: designId, name: designId, credit_cost: 1 });

        // Default-select every feature that has `default: true`
        const defaults = {};
        featsList.forEach((f) => { if (f.default) defaults[f.key] = true; });
        setSelectedFeatures(defaults);

        // Default cheapest expiry tier
        const sortedTiers = [...(tiersRes.data?.tiers || [])].sort((a, b) => (a.credits || 0) - (b.credits || 0));
        if (sortedTiers.length) setSelectedTier(sortedTiers[0].id);
      } catch (e) {
        console.error('purchase wizard load', e);
        setError('Could not load the celebration catalogue. Please try again.');
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => { cancelled = true; };
  }, [category, designId]);

  // ── Derived totals
  const baseCost = pricing.design_credits || design?.credit_cost || 1;
  const featuresCost = useMemo(() => {
    return features.reduce((sum, f) => {
      if (!selectedFeatures[f.key]) return sum;
      const c = (pricing.feature_credits && pricing.feature_credits[f.key] != null)
        ? pricing.feature_credits[f.key] : (f.credits || 0);
      return sum + c;
    }, 0);
  }, [features, selectedFeatures, pricing]);
  const tierCost = useMemo(() => {
    const t = tiers.find((x) => x.id === selectedTier);
    return t?.credits || 0;
  }, [tiers, selectedTier]);

  const totalCost = baseCost + featuresCost + tierCost;
  const balance = user?.credits ?? 0;
  const shortfall = Math.max(0, totalCost - balance);

  // ── Helpers
  const toggleFeature = (key) => setSelectedFeatures((m) => ({ ...m, [key]: !m[key] }));

  const handleCheckout = () => {
    setError('');
    const chosenFeatures = Object.keys(selectedFeatures).filter((k) => selectedFeatures[k]);
    const qs = new URLSearchParams({
      category,
      design_id: designId,
    });
    if (chosenFeatures.length) qs.set('features', chosenFeatures.join(','));
    if (selectedTier) qs.set('expiry', selectedTier);

    if (shortfall > 0) {
      const here = `/user/buy-celebration/${category}/${encodeURIComponent(designId)}?${qs.toString()}`;
      navigate(`/user/buy-credits?return=${encodeURIComponent(here)}&need=${shortfall}`);
      return;
    }
    navigate(`/user/celebration/new?${qs.toString()}`);
  };

  if (loading || busy) {
    return (
      <div className="luxe min-h-screen grid place-items-center" data-testid="celebration-wizard-loading">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  return (
    <div className="luxe min-h-screen px-5 md:px-12 py-8 md:py-12"
      data-testid="celebration-purchase-wizard"
      data-category={category}>
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="text-[10px] tracking-[0.25em] uppercase mb-5 inline-flex items-center gap-2 hover:opacity-80"
        style={{ color: 'rgba(255,248,220,0.6)' }}
        data-testid="celebration-wizard-back"
      >
        <ArrowLeft className="w-3 h-3" /> Back
      </button>

      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
        <div>
          <span className="lux-eyebrow block mb-2">
            ◆ {heroMeta.icon} {heroMeta.label} · Purchase Options
          </span>
          <h1 className="font-display text-3xl md:text-5xl leading-tight" style={SECTION_TITLE}>
            Pick your <span className="font-script italic text-gold">features.</span>
          </h1>
          <p className="mt-2 text-sm max-w-xl" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {design?.name} · {heroMeta.tagline}. Choose the experiences you&apos;d like — the total
            updates live below, and we&apos;ll only charge your wallet on the final step.
          </p>
        </div>
        <div className="lux-glass px-5 py-3 flex items-center gap-3" data-testid="celebration-wizard-balance">
          <Wallet className="w-5 h-5 text-gold" />
          <div>
            <div className="text-[9px] tracking-[0.32em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
              Wallet
            </div>
            <div className="font-display text-2xl" style={SECTION_TITLE}>
              {balance} <span className="text-xs font-sans" style={{ color: 'rgba(255,248,220,0.6)' }}>credits</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
        {/* LEFT — features + tiers */}
        <div className="space-y-8">
          {/* Base design */}
          <div className="lux-glass p-6" data-testid="celebration-wizard-base">
            <div className="flex items-start gap-4">
              {design?.preview_image && (
                <img
                  src={design.preview_image.startsWith('http')
                    ? design.preview_image
                    : `${API_URL}${design.preview_image}`}
                  alt={design.name}
                  className="w-20 h-28 object-cover rounded-lg flex-shrink-0"
                />
              )}
              <div className="flex-1">
                <span className="text-[9px] tracking-[0.32em] uppercase" style={{ color: 'rgba(255,248,220,0.5)' }}>
                  Base Design
                </span>
                <h3 className="font-display text-xl mt-1" style={SECTION_TITLE}>
                  {design?.name}
                </h3>
                <p className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.6)' }}>
                  Includes the category hero, blessings wall, RSVP form, photo gallery and the venue map.
                </p>
              </div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full"
                style={{ background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.3)' }}>
                <Coins className="w-4 h-4 text-gold" />
                <span className="font-display text-sm" style={SECTION_TITLE}>{baseCost}</span>
              </div>
            </div>
          </div>

          {/* Features */}
          <div>
            <h2 className="lux-eyebrow mb-4">◆ Features (optional)</h2>
            <div className="grid sm:grid-cols-2 gap-3" data-testid="celebration-wizard-features">
              {features.map((f) => {
                const credits = (pricing.feature_credits && pricing.feature_credits[f.key] != null)
                  ? pricing.feature_credits[f.key] : (f.credits || 0);
                const checked = !!selectedFeatures[f.key];
                return (
                  <button
                    type="button"
                    key={f.key}
                    onClick={() => toggleFeature(f.key)}
                    className="lux-glass p-4 text-left flex items-start gap-3 transition-all"
                    style={{
                      borderColor: checked ? 'rgba(212,175,55,0.55)' : 'rgba(255,248,220,0.1)',
                      background: checked ? 'rgba(212,175,55,0.08)' : 'rgba(255,248,220,0.03)',
                    }}
                    data-testid={`celebration-feature-${f.key}`}
                    data-selected={checked}
                  >
                    <div className="w-9 h-9 rounded-lg grid place-items-center flex-shrink-0"
                      style={{ background: checked ? 'rgba(212,175,55,0.25)' : 'rgba(255,248,220,0.05)' }}>
                      <span className="text-lg">{f.icon || '✦'}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-display text-sm" style={SECTION_TITLE}>
                          {f.label}
                        </span>
                        {checked && <Check className="w-4 h-4 text-gold flex-shrink-0" />}
                      </div>
                      <div className="text-[11px] mt-1 flex items-center gap-1.5"
                        style={{ color: 'rgba(255,248,220,0.6)' }}>
                        <Coins className="w-3 h-3 text-gold" />
                        {credits === 0 ? 'Included free' : `${credits} credit${credits > 1 ? 's' : ''}`}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Expiry */}
          <div>
            <h2 className="lux-eyebrow mb-4">◆ How long should the link stay live?</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="celebration-wizard-tiers">
              {tiers.map((t) => {
                const isSel = selectedTier === t.id;
                return (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => setSelectedTier(t.id)}
                    className="lux-glass p-4 text-left transition-all"
                    style={{
                      borderColor: isSel ? 'rgba(212,175,55,0.55)' : 'rgba(255,248,220,0.1)',
                      background: isSel ? 'rgba(212,175,55,0.08)' : 'rgba(255,248,220,0.03)',
                    }}
                    data-testid={`celebration-tier-${t.id}`}
                  >
                    <Clock className="w-4 h-4 text-gold mb-2" />
                    <div className="font-display text-sm" style={SECTION_TITLE}>{t.label}</div>
                    <div className="text-[11px] mt-1 inline-flex items-center gap-1"
                      style={{ color: 'rgba(255,248,220,0.65)' }}>
                      <Coins className="w-3 h-3 text-gold" />
                      {t.credits} credit{t.credits > 1 ? 's' : ''}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT — sticky total */}
        <div>
          <div className="lux-glass p-6 sticky top-6 space-y-5" data-testid="celebration-wizard-summary">
            <div>
              <span className="lux-eyebrow block mb-3">◆ Summary</span>
              <ul className="space-y-2 text-sm" style={{ color: 'rgba(255,248,220,0.8)' }}>
                <li className="flex items-center justify-between">
                  <span>Base design</span>
                  <span className="inline-flex items-center gap-1">
                    <Coins className="w-3 h-3 text-gold" />
                    {baseCost}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Features ({Object.values(selectedFeatures).filter(Boolean).length})</span>
                  <span className="inline-flex items-center gap-1"
                    data-testid="celebration-summary-features-cost">
                    <Coins className="w-3 h-3 text-gold" />
                    {featuresCost}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Expiry</span>
                  <span className="inline-flex items-center gap-1">
                    <Coins className="w-3 h-3 text-gold" />
                    {tierCost}
                  </span>
                </li>
              </ul>
              <div className="lux-hairline my-4" />
              <div className="flex items-center justify-between">
                <span className="font-display text-base" style={SECTION_TITLE}>Total</span>
                <span className="inline-flex items-center gap-2"
                  data-testid="celebration-summary-total">
                  <Coins className="w-5 h-5 text-gold" />
                  <span className="font-display text-3xl" style={SECTION_TITLE}>{totalCost}</span>
                  <span className="text-xs" style={{ color: 'rgba(255,248,220,0.6)' }}>credits</span>
                </span>
              </div>
            </div>

            {shortfall > 0 && (
              <div className="flex items-start gap-2 p-3 rounded-lg"
                style={{
                  background: 'rgba(180,40,40,0.12)',
                  border: '1px solid rgba(255,120,120,0.3)',
                  color: '#FFB0A0',
                }}
                data-testid="celebration-summary-shortfall">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div className="text-xs">
                  You&apos;re short by <span className="font-display text-base">{shortfall}</span> credits.
                  Continue to top up your wallet.
                </div>
              </div>
            )}

            {error && (
              <div className="text-xs text-rose-400" data-testid="celebration-summary-error">{error}</div>
            )}

            <motion.button
              type="button"
              whileTap={{ scale: 0.98 }}
              onClick={handleCheckout}
              className="lux-btn w-full justify-center"
              data-testid="celebration-wizard-checkout"
            >
              <Sparkles className="w-4 h-4" />
              {shortfall > 0 ? `Top up & continue` : `Continue to create invitation`}
              <ArrowRight className="w-4 h-4" />
            </motion.button>

            <p className="text-[10px] text-center"
              style={{ color: 'rgba(255,248,220,0.45)' }}>
              Credits are charged only when you publish the invitation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
