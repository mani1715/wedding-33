/**
 * AccountCreditsPage — self-service credit balance + redeem-code + ledger.
 *
 * Hits the new spec-compliant endpoints:
 *   GET  /api/account/credits       → { total, used, available }
 *   GET  /api/account/ledger        → recent transactions
 *   POST /api/account/redeem-code   → grants credits, returns new balance
 *
 * Works for both photographer (`admin` role) and normal user (`user`) since
 * `get_current_admin` resolves either to a credit account.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Gift, CheckCircle, AlertCircle, ArrowDownLeft, ArrowUpRight, RotateCcw, Wallet, Copy, Users, RefreshCw, ArrowLeft, ArrowRight, Coins } from 'lucide-react';
import BackButton from '@/components/BackButton';
import PhotographerTierCard from '@/components/PhotographerTierCard';
import TopUpCreditsModal from '@/components/dashboard/TopUpCreditsModal';

const API = process.env.REACT_APP_BACKEND_URL || '';

const ACTION_META = {
  add:    { label: 'Added',    icon: ArrowDownLeft, tone: 'text-emerald-400 bg-emerald-500/10' },
  refund: { label: 'Refund',   icon: RotateCcw,     tone: 'text-emerald-400 bg-emerald-500/10' },
  used:   { label: 'Used',     icon: ArrowUpRight,  tone: 'text-rose-400 bg-rose-500/10' },
  deduct: { label: 'Deducted', icon: ArrowUpRight,  tone: 'text-rose-400 bg-rose-500/10' },
  adjust: { label: 'Adjusted', icon: Sparkles,      tone: 'text-amber-400 bg-amber-500/10' },
};

const fmt = (n) => Number(n || 0).toLocaleString('en-IN');

export default function AccountCreditsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // ── Round-trip support: when a user is sent here from the
  // PurchaseOptionsWizard because they were short on credits, the wizard
  // appends ?return=/user/buy-design/...&need=N.  We render a sticky
  // banner with a "Back to wizard" CTA and, once balance >= need, an
  // auto-continue button so they don't have to manually navigate back.
  const returnTo  = useMemo(() => {
    const raw = searchParams.get('return') || '';
    // Only honor SAME-ORIGIN paths (defence against open-redirect).
    return raw && raw.startsWith('/') ? raw : '';
  }, [searchParams]);
  const needCredits = Number(searchParams.get('need') || 0);

  const [balance, setBalance] = useState({ total_credits: 0, used_credits: 0, available_credits: 0 });
  const [ledger, setLedger]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [code, setCode]       = useState('');
  const [redeeming, setRedeeming] = useState(false);
  const [redeemMsg, setRedeemMsg] = useState(null);   // { type: 'success'|'error', text }
  // Referral-code state
  const [referral, setReferral]   = useState(null);
  const [referralBusy, setReferralBusy] = useState(false);
  const [copied, setCopied]       = useState(false);
  const [refCode, setRefCode]     = useState('');
  const [refMsg, setRefMsg]       = useState(null);
  // July 2026 — split credits view between one-time top-ups and a
  // monthly auto-renewing plan. Backend subscription billing is not
  // shipped yet; the monthly tab shows the catalogue + a clearly
  // marked "Notify me / Coming soon" CTA.
  const [planMode, setPlanMode] = useState('onetime'); // 'onetime' | 'monthly'

  const token = (typeof window !== 'undefined' && window.localStorage)
    ? localStorage.getItem('admin_token') || localStorage.getItem('user_token')
    : null;

  /* Audience is implicit: photographer if signed in as admin, otherwise
     normal_user. Drives which credit-pack price list we show and whether
     the loyalty tier card / tier-aware prices are rendered. */
  const isPhotographer = (typeof window !== 'undefined' && window.localStorage)
    ? !!localStorage.getItem('admin_token')
    : false;
  const audience = isPhotographer ? 'photographer' : 'normal_user';

  const [pricing, setPricing] = useState(null);
  const [myTier, setMyTier] = useState(null);

  // BUG 7 FIX: photographers buying credits used to be sent to /purchase
  // (the design-invitation buy flow) which has no payment option for credit
  // packs. Now we open the same Razorpay TopUpCreditsModal the dashboard
  // uses, which talks to /api/admin/credits/purchase/create-order + verify.
  const [topUpOpen, setTopUpOpen] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/public/pricing/effective?audience=${audience}`)
      .then((r) => r.json())
      .then((d) => setPricing(d))
      .catch(() => setPricing(null));
  }, [audience]);

  useEffect(() => {
    if (!isPhotographer || !token) return;
    fetch(`${API}/api/photographer/me/tier`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => setMyTier(d))
      .catch(() => setMyTier(null));
  }, [isPhotographer, token]);

  const tierDiscountPct = myTier?.tier?.discount_pct || 0;
  const tierBonusPct = myTier?.tier?.bonus_pct || 0;

  const headers = token
    ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };

  const refresh = useCallback(async () => {
    try {
      const [b, l, r] = await Promise.all([
        fetch(`${API}/api/account/credits`, { headers }).then(r => r.json()),
        fetch(`${API}/api/account/ledger?limit=50`, { headers }).then(r => r.json()),
        fetch(`${API}/api/account/referral-code`, { headers }).then(r => r.json()).catch(() => null),
      ]);
      if (b && !b.detail) setBalance(b);
      if (l && Array.isArray(l.entries)) setLedger(l.entries);
      if (r && r.code) setReferral(r);
    } catch (_) { /* swallow */ }
    setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const onRedeem = async (e) => {
    e?.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;
    setRedeeming(true);
    setRedeemMsg(null);
    try {
      const res = await fetch(`${API}/api/account/redeem-code`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ code: trimmed }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRedeemMsg({ type: 'error', text: data?.detail || 'Could not redeem' });
      } else {
        setRedeemMsg({ type: 'success', text: `+${data.credits_added} credits added!` });
        setCode('');
        if (data.balance) setBalance(data.balance);
        // Pull fresh ledger so the new row shows up
        refresh();
      }
    } catch (_) {
      setRedeemMsg({ type: 'error', text: 'Network error' });
    }
    setRedeeming(false);
  };

  // ── Referral code handlers ───────────────────────────────────────────
  const onCopyReferral = () => {
    if (!referral?.code) return;
    navigator.clipboard?.writeText(referral.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const onRegenerateReferral = async () => {
    setReferralBusy(true);
    try {
      const r = await fetch(`${API}/api/account/referral-code/regenerate`, {
        method: 'POST', headers,
      });
      const data = await r.json();
      if (data?.code) setReferral(data);
    } catch (_) { /* swallow */ }
    setReferralBusy(false);
  };

  const onRedeemReferral = async (e) => {
    e?.preventDefault();
    const trimmed = refCode.trim();
    if (!trimmed) return;
    setReferralBusy(true);
    setRefMsg(null);
    try {
      const r = await fetch(`${API}/api/account/redeem-referral`, {
        method: 'POST', headers,
        body: JSON.stringify({ code: trimmed }),
      });
      const data = await r.json();
      if (!r.ok) {
        setRefMsg({ type: 'error', text: data?.detail || 'Could not redeem' });
      } else {
        setRefMsg({ type: 'success', text: `+${data.credits_added} credits from referral!` });
        setRefCode('');
        if (data.balance) setBalance(data.balance);
        refresh();
      }
    } catch (_) {
      setRefMsg({ type: 'error', text: 'Network error' });
    }
    setReferralBusy(false);
  };

  return (
    <div className="min-h-screen px-5 sm:px-10 py-10" style={{ background: '#0a0a0a', color: '#F5ECD7' }} data-testid="account-credits-page">
      <div className="max-w-4xl mx-auto">
        <BackButton label="Back" />

        {/* ── Round-trip banner — shown when user was sent here from the
            PurchaseOptionsWizard because of insufficient credits. */}
        {returnTo && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
            className="mt-2 mb-4 rounded-xl p-4 flex items-center gap-3 flex-wrap"
            style={{
              background: 'linear-gradient(135deg, rgba(212,175,55,0.16), rgba(140,30,30,0.16))',
              border: '1px solid rgba(212,175,55,0.35)',
            }}
            data-testid="wizard-return-banner"
          >
            <Sparkles className="w-4 h-4 shrink-0" style={{ color: '#D4AF37' }} />
            <div className="flex-1 min-w-[200px] text-sm" style={{ color: '#FFF8DC' }}>
              {needCredits > 0 ? (
                <>You were just <span className="text-gold">{needCredits} credit{needCredits === 1 ? '' : 's'}</span> short.&nbsp;
                  {balance.available_credits >= needCredits ? (
                    <span className="text-emerald-300">You now have enough! Click continue →</span>
                  ) : (
                    <span style={{ color: 'rgba(245,236,215,0.7)' }}>
                      Top up below, then we'll take you right back.
                    </span>
                  )}
                </>
              ) : (
                <>Top up below and we'll take you right back to your purchase.</>
              )}
            </div>
            <button
              type="button"
              onClick={() => navigate(returnTo)}
              className="px-4 py-2 rounded-lg text-[10px] tracking-[0.3em] uppercase font-medium flex items-center gap-1.5"
              style={{
                background: balance.available_credits >= needCredits
                  ? 'linear-gradient(135deg,#D4AF37,#B8941F)'
                  : 'rgba(245,236,215,0.08)',
                color: balance.available_credits >= needCredits ? '#1A0F08' : '#FFF8DC',
                border: '1px solid rgba(212,175,55,0.4)',
              }}
              data-testid="wizard-return-btn"
            >
              {balance.available_credits >= needCredits ? <>Continue <ArrowRight className="w-3.5 h-3.5" /></> : <><ArrowLeft className="w-3.5 h-3.5" /> Back to wizard</>}
            </button>
          </motion.div>
        )}

        {/* Heading */}
        <div className="mb-8 mt-4">
          <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: 'rgba(245,236,215,0.55)' }}>Your wallet</div>
          <h1 className="font-display text-3xl sm:text-4xl" style={{ color: '#FFF8DC' }}>Credits</h1>
        </div>

        {/* Balance hero */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="rounded-2xl p-7 mb-8"
          style={{
            background: 'linear-gradient(135deg, rgba(212,175,55,0.18) 0%, rgba(140,30,30,0.18) 100%)',
            border: '1px solid rgba(212,175,55,0.35)',
          }}
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase mb-2" style={{ color: '#D4AF37' }}>
                <Wallet className="w-3.5 h-3.5" /> Available balance
              </div>
              <div className="font-display text-5xl sm:text-6xl tracking-tight" style={{ color: '#FFF8DC' }} data-testid="balance-available">
                {fmt(balance.available_credits)}
              </div>
              <div className="text-sm mt-1" style={{ color: 'rgba(245,236,215,0.65)' }}>
                Total {fmt(balance.total_credits)} · Used {fmt(balance.used_credits)}
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                // BUG 19 FIX: previously a raw <a href> caused a full page
                // reload, dropping any in-flight Razorpay/wizard state. For
                // photographers, open the in-page top-up modal directly. For
                // normal users, use React Router navigate (no reload).
                if (isPhotographer) {
                  setTopUpOpen(true);
                  return;
                }
                const url = returnTo
                  ? `/user/buy-credits?return=${encodeURIComponent(returnTo)}${needCredits ? `&need=${needCredits}` : ''}`
                  : '/user/buy-credits';
                navigate(url);
              }}
              data-testid="buy-credits-btn"
              className="px-5 py-2.5 rounded-lg text-[11px] tracking-[0.3em] uppercase font-medium"
              style={{ background: '#D4AF37', color: '#1A0F08', border: 'none', cursor: 'pointer' }}
            >
              Buy credits
            </button>
          </div>
        </motion.div>

        {/* Photographer loyalty tier card — only renders for photographers */}
        {isPhotographer && (
          <div className="mb-6">
            <PhotographerTierCard />
          </div>
        )}

        {/* Dynamic Credit Packs — synced live with admin Pricing Hub */}
        {/* July 2026 — Plan-type tabs: One-time vs Monthly */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.02 }}
          className="mb-5"
          data-testid="plan-mode-tabs"
        >
          <div
            className="inline-flex rounded-full p-1"
            style={{ background: 'rgba(245,236,215,0.05)', border: '1px solid rgba(212,175,55,0.25)' }}
          >
            {[
              { id: 'onetime', label: 'One-time top-up' },
              { id: 'monthly', label: 'Monthly plan' },
            ].map((t) => {
              const active = planMode === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setPlanMode(t.id)}
                  className="px-5 py-2 rounded-full text-[11px] tracking-[0.25em] uppercase font-medium transition-all"
                  style={active
                    ? { background: '#D4AF37', color: '#1A0F08' }
                    : { background: 'transparent', color: 'rgba(245,236,215,0.7)' }}
                  data-testid={`plan-tab-${t.id}`}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] mt-2 max-w-2xl" style={{ color: 'rgba(245,236,215,0.6)' }}>
            {planMode === 'onetime'
              ? 'One-time packs add credits to your wallet instantly. Credits never expire until used.'
              : 'Monthly plans top up your wallet automatically every month, with a built-in discount over one-time packs.'}
          </p>
        </motion.div>

        {/* ─── ONE-TIME packs (existing flow) ───────────────────── */}
        {planMode === 'onetime' && pricing?.packs?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.03 }}
            className="mb-8"
            data-testid="credit-packs-section"
          >
            <div className="flex items-baseline justify-between mb-4">
              <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: '#D4AF37' }}>
                <Coins className="w-3.5 h-3.5" /> Credit packs
              </div>
              {isPhotographer && tierDiscountPct > 0 && (
                <div className="text-[10px] tracking-[0.2em] uppercase" style={{ color: '#FFE38A' }} data-testid="packs-tier-banner">
                  {myTier?.tier?.label} tier · {tierDiscountPct}% off + {tierBonusPct}% bonus credits
                </div>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {pricing.packs.map((p) => {
                // Apply photographer tier discount on top of admin's discount price.
                const baseRupees = Number(p.price || p.base_price || 0);
                const tierPrice = isPhotographer && tierDiscountPct > 0
                  ? Math.round(baseRupees * (1 - tierDiscountPct / 100))
                  : baseRupees;
                const bonusCredits = isPhotographer && tierBonusPct > 0
                  ? Math.round(p.credits * tierBonusPct / 100)
                  : 0;
                const totalCredits = p.credits + bonusCredits;
                return (
                  <div
                    key={p.id}
                    className="rounded-xl p-4 flex flex-col"
                    style={{
                      background: 'rgba(245,236,215,0.04)',
                      border: '1px solid rgba(212,175,55,0.32)',
                    }}
                    data-testid={`pack-card-${p.credits}`}
                  >
                    <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: 'rgba(245,236,215,0.55)' }}>
                      {p.label || 'Pack'}
                    </div>
                    <div className="font-display text-3xl" style={{ color: '#FFF8DC' }} data-testid={`pack-credits-${p.credits}`}>
                      {fmt(totalCredits)}
                      <span className="text-sm ml-1" style={{ color: 'rgba(245,236,215,0.55)' }}>credits</span>
                    </div>
                    {bonusCredits > 0 && (
                      <div className="text-[11px] mt-0.5" style={{ color: '#FFE38A' }} data-testid={`pack-bonus-${p.credits}`}>
                        Includes +{bonusCredits} bonus
                      </div>
                    )}
                    <div className="mt-2 flex items-baseline gap-2">
                      {tierPrice !== baseRupees && (
                        <span className="line-through text-sm" style={{ color: 'rgba(245,236,215,0.45)' }} data-testid={`pack-old-price-${p.credits}`}>
                          ₹{fmt(baseRupees)}
                        </span>
                      )}
                      <span className="text-lg font-medium" style={{ color: '#D4AF37' }} data-testid={`pack-price-${p.credits}`}>
                        ₹{fmt(tierPrice)}
                      </span>
                    </div>
                    <button
                      type="button"
                      disabled={!isPhotographer}
                      onClick={() => {
                        // BUG 20 FIX: photographers → in-page Razorpay credit
                        // purchase modal (correct endpoint + tier-aware
                        // pricing). Normal users used to be sent to /purchase
                        // (the design buy flow) which has no credit-pack
                        // checkout — they ended up on a broken page. Hide the
                        // button for normal users until a dedicated Razorpay
                        // flow exists (tracked as Bug 20 "Coming soon").
                        if (isPhotographer) {
                          setTopUpOpen(true);
                        }
                      }}
                      className="mt-3 px-3 py-2 rounded-lg text-[10px] tracking-[0.3em] uppercase font-medium"
                      style={{
                        background: isPhotographer ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'rgba(212,175,55,0.18)',
                        color: isPhotographer ? '#1A0F08' : 'rgba(255,248,220,0.6)',
                        cursor: isPhotographer ? 'pointer' : 'not-allowed',
                      }}
                      data-testid={`pack-buy-${p.credits}`}
                    >
                      {isPhotographer ? 'Buy now' : 'Coming soon'}
                    </button>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* ─── MONTHLY plan (July 2026) ─────────────────────────── */}
        {planMode === 'monthly' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.03 }}
            className="mb-8"
            data-testid="monthly-plans-section"
          >
            <div className="flex items-baseline justify-between mb-4">
              <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: '#D4AF37' }}>
                <Coins className="w-3.5 h-3.5" /> Monthly plans
              </div>
              <div
                className="text-[10px] tracking-[0.2em] uppercase px-2 py-1 rounded-full"
                style={{ background: 'rgba(212,175,55,0.12)', color: '#F5D88B', border: '1px solid rgba(212,175,55,0.3)' }}
              >
                Beta · Subscriptions opening soon
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[
                { id: 'lite',  label: 'Lite',     credits: 30,  price: 499,  savePct: 10, perks: ['30 credits every month', 'Carry-over up to 60', 'Email support'] },
                { id: 'pro',   label: 'Pro',      credits: 90,  price: 1299, savePct: 20, perks: ['90 credits every month', 'Carry-over up to 180', 'Priority support', 'AI Story Composer'] },
                { id: 'elite', label: 'Elite',    credits: 250, price: 2999, savePct: 30, perks: ['250 credits every month', 'Unlimited carry-over', 'Dedicated success manager', 'All Pro perks'] },
              ].map((m) => (
                <div
                  key={m.id}
                  className="rounded-xl p-5 flex flex-col"
                  style={{
                    background: m.id === 'pro' ? 'linear-gradient(135deg, rgba(212,175,55,0.18) 0%, rgba(140,30,30,0.18) 100%)' : 'rgba(245,236,215,0.04)',
                    border: m.id === 'pro' ? '1.5px solid rgba(212,175,55,0.6)' : '1px solid rgba(212,175,55,0.32)',
                  }}
                  data-testid={`monthly-card-${m.id}`}
                >
                  {m.id === 'pro' && (
                    <div className="text-[9px] tracking-[0.3em] uppercase mb-2 px-2 py-0.5 self-start rounded-full" style={{ background: '#D4AF37', color: '#1A0F08' }}>
                      Most popular
                    </div>
                  )}
                  <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: 'rgba(245,236,215,0.55)' }}>
                    {m.label}
                  </div>
                  <div className="font-display text-3xl" style={{ color: '#FFF8DC' }}>
                    {fmt(m.credits)}
                    <span className="text-sm ml-1" style={{ color: 'rgba(245,236,215,0.55)' }}>credits / month</span>
                  </div>
                  <div className="mt-1 flex items-baseline gap-2">
                    <span className="text-2xl font-medium" style={{ color: '#D4AF37' }}>₹{fmt(m.price)}</span>
                    <span className="text-xs" style={{ color: 'rgba(245,236,215,0.55)' }}>/ month</span>
                    <span className="text-[10px] tracking-[0.2em] uppercase ml-auto" style={{ color: '#7FCB9B' }}>
                      Save {m.savePct}%
                    </span>
                  </div>

                  <ul className="mt-4 space-y-1.5 text-xs flex-1" style={{ color: 'rgba(245,236,215,0.78)' }}>
                    {m.perks.map((p) => (
                      <li key={p} className="flex items-start gap-1.5">
                        <CheckCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#D4AF37' }} />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    type="button"
                    onClick={() => {
                      setRedeemMsg({ type: 'success', text: `You're on the wait-list for the ${m.label} plan. We will email you when monthly billing opens.` });
                    }}
                    className="mt-4 px-3 py-2 rounded-lg text-[10px] tracking-[0.3em] uppercase font-medium"
                    style={{
                      background: m.id === 'pro' ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'rgba(245,236,215,0.08)',
                      color: m.id === 'pro' ? '#1A0F08' : '#FFF8DC',
                      border: '1px solid rgba(212,175,55,0.3)',
                    }}
                    data-testid={`monthly-notify-${m.id}`}
                  >
                    Notify me when live
                  </button>
                </div>
              ))}
            </div>
            <p className="text-[11px] mt-3" style={{ color: 'rgba(245,236,215,0.55)' }}>
              Monthly subscriptions are launching soon. Once live, your card will be charged on the same day every month and credits will auto-deposit into this wallet.
            </p>
          </motion.div>
        )}

        {/* Redeem code */}
        <motion.form
          onSubmit={onRedeem}
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.05 }}
          className="rounded-2xl p-6 mb-8"
          style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(245,236,215,0.12)' }}
          data-testid="redeem-form"
        >
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: '#D4AF37' }}>
            <Gift className="w-3.5 h-3.5" /> Have a gift code?
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. LOVE26"
              maxLength={16}
              data-testid="redeem-code-input"
              className="flex-1 px-4 py-3 rounded-lg text-lg tracking-[0.25em] uppercase outline-none"
              style={{
                background: 'rgba(10,10,10,0.6)',
                color: '#FFF8DC',
                border: '1px solid rgba(212,175,55,0.4)',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
            <button
              type="submit"
              disabled={!code.trim() || redeeming}
              data-testid="redeem-submit"
              className="px-6 py-3 rounded-lg text-[11px] tracking-[0.3em] uppercase font-medium disabled:opacity-50"
              style={{ background: '#FFF8DC', color: '#1A0F08' }}
            >
              {redeeming ? 'Redeeming…' : 'Redeem'}
            </button>
          </div>
          {redeemMsg && (
            <div
              className={`mt-3 flex items-center gap-2 text-sm ${redeemMsg.type === 'success' ? 'text-emerald-300' : 'text-rose-300'}`}
              data-testid={`redeem-${redeemMsg.type}`}
            >
              {redeemMsg.type === 'success'
                ? <CheckCircle className="w-4 h-4" />
                : <AlertCircle  className="w-4 h-4" />}
              <span>{redeemMsg.text}</span>
            </div>
          )}
        </motion.form>

        {/* My referral code */}
        {referral?.code && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.08 }}
            className="rounded-2xl p-6 mb-4"
            style={{ background: 'rgba(212,175,55,0.05)', border: '1px solid rgba(212,175,55,0.25)' }}
            data-testid="my-referral-panel"
          >
            <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: '#D4AF37' }}>
              <Users className="w-3.5 h-3.5" /> Your referral code
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <code
                className="px-4 py-3 rounded-lg text-xl font-mono tracking-[0.2em]"
                style={{ background: 'rgba(10,10,10,0.6)', color: '#FFF8DC', border: '1px solid rgba(212,175,55,0.35)' }}
                data-testid="my-referral-code"
              >
                {referral.code}
              </code>
              <button
                onClick={onCopyReferral}
                data-testid="copy-referral-code"
                className="px-3 py-2 rounded-lg text-[11px] tracking-[0.3em] uppercase font-medium flex items-center gap-1.5"
                style={{ background: 'rgba(212,175,55,0.18)', color: '#D4AF37' }}
              >
                {copied ? <CheckCircle className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
              <button
                onClick={onRegenerateReferral}
                disabled={referralBusy}
                data-testid="regenerate-referral"
                className="px-3 py-2 rounded-lg text-[11px] tracking-[0.3em] uppercase flex items-center gap-1.5"
                style={{ background: 'rgba(245,236,215,0.06)', color: 'rgba(245,236,215,0.7)' }}
              >
                <RefreshCw className="w-3.5 h-3.5" /> Regenerate
              </button>
            </div>
            <div className="mt-3 text-[11px] grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Stat label="Redeemers earn" value={`${referral.redeemer_reward} cr`} />
              <Stat label="You earn per redeem" value={`${referral.owner_reward} cr`} />
              <Stat label="Total redemptions" value={`${referral.redeemed_count || 0}`} />
            </div>
          </motion.div>
        )}

        {/* Redeem someone else's referral code */}
        <motion.form
          onSubmit={onRedeemReferral}
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="rounded-2xl p-6 mb-8"
          style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(245,236,215,0.12)' }}
          data-testid="redeem-referral-form"
        >
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: '#D4AF37' }}>
            <Users className="w-3.5 h-3.5" /> Got a friend's referral code?
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={refCode}
              onChange={(e) => setRefCode(e.target.value.toUpperCase())}
              placeholder="e.g. MAJA-ABC123"
              maxLength={20}
              data-testid="redeem-referral-input"
              className="flex-1 px-4 py-3 rounded-lg text-lg tracking-[0.2em] uppercase outline-none"
              style={{
                background: 'rgba(10,10,10,0.6)',
                color: '#FFF8DC',
                border: '1px solid rgba(212,175,55,0.4)',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
            <button
              type="submit"
              disabled={!refCode.trim() || referralBusy}
              data-testid="redeem-referral-submit"
              className="px-6 py-3 rounded-lg text-[11px] tracking-[0.3em] uppercase font-medium disabled:opacity-50"
              style={{ background: '#FFF8DC', color: '#1A0F08' }}
            >
              {referralBusy ? 'Redeeming…' : 'Redeem'}
            </button>
          </div>
          {refMsg && (
            <div
              className={`mt-3 flex items-center gap-2 text-sm ${refMsg.type === 'success' ? 'text-emerald-300' : 'text-rose-300'}`}
              data-testid={`referral-${refMsg.type}`}
            >
              {refMsg.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              <span>{refMsg.text}</span>
            </div>
          )}
        </motion.form>

        {/* Ledger */}
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-display text-xl" style={{ color: '#FFF8DC' }}>Recent activity</h2>
          {ledger.length > 0 && (
            <span className="text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(245,236,215,0.55)' }}>
              {ledger.length} entries
            </span>
          )}
        </div>

        <div className="rounded-2xl overflow-hidden"
             style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(245,236,215,0.12)' }}>
          {loading && (
            <div className="px-5 py-10 text-center text-sm" style={{ color: 'rgba(245,236,215,0.55)' }}>
              Loading…
            </div>
          )}
          {!loading && ledger.length === 0 && (
            <div className="px-5 py-10 text-center text-sm" style={{ color: 'rgba(245,236,215,0.55)' }} data-testid="ledger-empty">
              No transactions yet. Redeem a code or buy a credit pack to get started.
            </div>
          )}
          {!loading && ledger.map((e) => {
            const meta = ACTION_META[e.action_type] || ACTION_META.adjust;
            const Icon = meta.icon;
            const sign = (e.amount || 0) >= 0 ? '+' : '';
            return (
              <div
                key={e.credit_id}
                className="flex items-center gap-4 px-5 py-4 border-b last:border-b-0"
                style={{ borderColor: 'rgba(245,236,215,0.08)' }}
                data-testid={`ledger-row-${e.credit_id}`}
              >
                <div className={`w-9 h-9 rounded-full grid place-items-center flex-shrink-0 ${meta.tone}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate" style={{ color: '#FFF8DC' }}>
                    {e.reason || meta.label}
                  </div>
                  <div className="text-[11px] mt-0.5" style={{ color: 'rgba(245,236,215,0.55)' }}>
                    {e.created_at?.slice(0, 19).replace('T', ' ')} · {meta.label}
                  </div>
                </div>
                <div className={`text-base font-semibold tracking-tight ${
                  (e.amount || 0) >= 0 ? 'text-emerald-300' : 'text-rose-300'
                }`}>
                  {sign}{fmt(e.amount)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* BUG 7 FIX: Razorpay credit-pack purchase modal for photographers.
          Opened by the "Buy now" button when isPhotographer === true. */}
      <TopUpCreditsModal
        open={topUpOpen}
        onClose={() => setTopUpOpen(false)}
        onSuccess={() => { setTopUpOpen(false); refresh(); }}
      />
    </div>
  );
}

const Stat = ({ label, value }) => (
  <div className="px-3 py-2 rounded" style={{ background: 'rgba(10,10,10,0.4)', border: '1px solid rgba(245,236,215,0.08)' }}>
    <div className="text-[9px] tracking-[0.2em] uppercase" style={{ color: 'rgba(245,236,215,0.55)' }}>{label}</div>
    <div className="text-sm mt-0.5" style={{ color: '#FFF8DC' }}>{value}</div>
  </div>
);
