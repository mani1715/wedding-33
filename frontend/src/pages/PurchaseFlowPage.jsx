/**
 * PurchaseFlowPage — design → features → duration → live total → confirm.
 *
 * Consumes:
 *   GET  /api/user/purchase/designs            — list of designs with role-based prices
 *   GET  /api/user/purchase/features/{event}   — features available for this event
 *   GET  /api/user/purchase/durations          — duration options
 *   POST /api/user/purchase/calculate          — live breakdown
 *   POST /api/user/purchase/confirm            — spends credits via use_credits()
 *
 * Super-admins see "FREE" instead of a credit total (back-end skips charge).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Sparkles, AlertCircle, ChevronRight } from 'lucide-react';
import BackButton from '@/components/BackButton';

const API = process.env.REACT_APP_BACKEND_URL || '';

export default function PurchaseFlowPage() {
  const token = (typeof window !== 'undefined' && window.localStorage)
    ? localStorage.getItem('admin_token') || localStorage.getItem('user_token')
    : null;
  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }), [token]);

  const [step, setStep]       = useState(1); // 1=design, 2=features, 3=duration, 4=review
  const [designs, setDesigns] = useState([]);
  const [features, setFeatures] = useState([]);
  const [durations, setDurations] = useState([]);
  const [balance, setBalance] = useState(null);

  // Selections
  const [design, setDesign]           = useState(null);
  const [selectedFeatures, setSelFeat] = useState([]);
  const [duration, setDuration]       = useState(null);
  const [isMixed, setIsMixed]         = useState(false);

  // Live calculation
  const [calc, setCalc]               = useState(null);
  const [calcing, setCalcing]         = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [confirmation, setConfirmation] = useState(null); // { credits_deducted, purchase_id }
  const [error, setError]             = useState('');

  // ───── data load ─────────────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API}/api/user/purchase/designs`, { headers })
      .then(r => r.json()).then(d => setDesigns(d?.designs || []));
    fetch(`${API}/api/user/purchase/durations`, { headers })
      .then(r => r.json()).then(d => setDurations(d?.durations || []));
    fetch(`${API}/api/account/credits`, { headers })
      .then(r => r.json()).then(setBalance).catch(() => {});
  }, [headers]);

  useEffect(() => {
    if (!design?.event_type) return;
    fetch(`${API}/api/user/purchase/features/${design.event_type}`, { headers })
      .then(r => r.json()).then(d => setFeatures(d?.features || []));
  }, [design, headers]);

  // ───── live recalculation ────────────────────────────────────────────
  const recalc = useCallback(async () => {
    if (!design || !duration) { setCalc(null); return; }
    setCalcing(true);
    try {
      const r = await fetch(`${API}/api/user/purchase/calculate`, {
        method: 'POST', headers,
        body: JSON.stringify({
          design_id: design.design_id,
          event_type: design.event_type,
          selected_features: selectedFeatures,
          duration_id: duration.duration_id,
          is_mixed_theme: isMixed,
          user_type: 'user',  // overridden server-side by actor's role
        }),
      });
      const data = await r.json();
      if (data?.calculation) setCalc(data.calculation);
    } catch (_) { /* swallow */ }
    setCalcing(false);
  }, [design, duration, selectedFeatures, isMixed, headers]);

  useEffect(() => { recalc(); }, [recalc]);

  // ───── confirm ───────────────────────────────────────────────────────
  const confirm = async () => {
    if (!design || !duration) return;
    setSubmitting(true);
    setError('');
    try {
      const r = await fetch(`${API}/api/user/purchase/confirm`, {
        method: 'POST', headers,
        body: JSON.stringify({
          design_id: design.design_id,
          event_type: design.event_type,
          selected_features: selectedFeatures,
          duration_id: duration.duration_id,
          is_mixed_theme: isMixed,
          user_type: 'user',
        }),
      });
      const data = await r.json();
      if (!r.ok) {
        setError(data?.detail || 'Could not complete purchase');
      } else {
        setConfirmation(data);
      }
    } catch (_) {
      setError('Network error');
    }
    setSubmitting(false);
  };

  // ───── success view ──────────────────────────────────────────────────
  if (confirmation) {
    return (
      <div className="min-h-screen px-5 py-16 grid place-items-center" style={{ background: '#0a0a0a', color: '#F5ECD7' }}>
        <motion.div
          initial={{ scale: 0.94, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          className="max-w-md rounded-2xl p-8 text-center"
          style={{ background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.4)' }}
          data-testid="purchase-success"
        >
          <div className="w-16 h-16 mx-auto rounded-full grid place-items-center mb-4" style={{ background: 'rgba(16,185,129,0.18)' }}>
            <Check className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="font-display text-3xl mb-2" style={{ color: '#FFF8DC' }}>Purchase confirmed</h2>
          <p className="text-sm" style={{ color: 'rgba(245,236,215,0.65)' }}>
            {confirmation.credits_deducted > 0
              ? `${confirmation.credits_deducted} credits used.`
              : 'No charge — super-admin purchase.'}
          </p>
          {confirmation.expiry_date && (
            <p className="text-xs mt-2" style={{ color: 'rgba(245,236,215,0.5)' }}>
              Active until {confirmation.expiry_date.slice(0, 10)}
            </p>
          )}
          <div className="mt-6 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(245,236,215,0.45)' }}>
            ID: {confirmation.purchase_id?.slice(0, 8)}…
          </div>
        </motion.div>
      </div>
    );
  }

  // ───── main view ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen px-5 sm:px-10 py-10" style={{ background: '#0a0a0a', color: '#F5ECD7' }} data-testid="purchase-flow-page">
      <div className="max-w-5xl mx-auto">
        <BackButton label="Back" />
        <div className="flex items-baseline justify-between gap-4 flex-wrap mb-7 mt-4">
          <div>
            <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: 'rgba(245,236,215,0.55)' }}>New invitation</div>
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: '#FFF8DC' }}>Pick &amp; pay</h1>
          </div>
          {balance && (
            <div className="text-right">
              <div className="text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(245,236,215,0.55)' }}>Available credits</div>
              <div className="font-display text-2xl" style={{ color: '#D4AF37' }} data-testid="purchase-balance">{balance.available_credits}</div>
            </div>
          )}
        </div>

        <Stepper step={step} />

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 mt-6">

          <div className="rounded-2xl p-5" style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(245,236,215,0.12)' }}>
            {step === 1 && (
              <Section title="Choose a design" testId="step-design">
                {designs.length === 0 && <Empty msg="No designs published yet." />}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {designs.map((d) => (
                    <button
                      key={d.design_id}
                      onClick={() => { setDesign(d); setStep(2); }}
                      data-testid={`design-card-${d.design_id}`}
                      className="text-left p-4 rounded-xl transition-all"
                      style={{
                        background: design?.design_id === d.design_id ? 'rgba(212,175,55,0.12)' : 'rgba(10,10,10,0.5)',
                        border: `1px solid ${design?.design_id === d.design_id ? '#D4AF37' : 'rgba(245,236,215,0.12)'}`,
                      }}
                    >
                      <div className="font-display text-lg" style={{ color: '#FFF8DC' }}>{d.design_name}</div>
                      <div className="text-[11px] mt-1" style={{ color: 'rgba(245,236,215,0.55)' }}>
                        {d.theme} · {d.event_type}{d.is_premium ? ' · Premium' : ''}
                      </div>
                      <div className="mt-3 text-amber-300 text-sm">{d.base_credits ?? 0} credits</div>
                    </button>
                  ))}
                </div>
              </Section>
            )}

            {step === 2 && design && (
              <Section title="Add features" testId="step-features"
                       onBack={() => setStep(1)} onNext={() => setStep(3)}>
                {features.length === 0 && <Empty msg="No optional features for this event type." />}
                <div className="space-y-2">
                  {features.map((f) => {
                    const sel = selectedFeatures.includes(f.feature_id);
                    return (
                      <label key={f.feature_id} data-testid={`feature-${f.feature_id}`}
                             className="flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer"
                             style={{ background: sel ? 'rgba(212,175,55,0.10)' : 'rgba(10,10,10,0.5)',
                                      border: `1px solid ${sel ? 'rgba(212,175,55,0.5)' : 'rgba(245,236,215,0.12)'}` }}>
                        <input
                          type="checkbox" checked={sel}
                          onChange={() => setSelFeat(sel
                            ? selectedFeatures.filter(x => x !== f.feature_id)
                            : [...selectedFeatures, f.feature_id])}
                          className="accent-amber-500"
                        />
                        <div className="flex-1">
                          <div className="text-sm" style={{ color: '#FFF8DC' }}>{f.feature_name}</div>
                          {f.description && <div className="text-[11px]" style={{ color: 'rgba(245,236,215,0.55)' }}>{f.description}</div>}
                        </div>
                        <div className="text-sm text-amber-300">
                          {f.is_free ? 'Free' : `${f.credits ?? 0} cr`}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </Section>
            )}

            {step === 3 && (
              <Section title="Pick a duration" testId="step-duration"
                       onBack={() => setStep(2)} onNext={() => duration && setStep(4)}>
                {durations.length === 0 && <Empty msg="No duration options configured." />}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {durations.map((d) => (
                    <button key={d.duration_id} onClick={() => setDuration(d)}
                            data-testid={`duration-${d.duration_id}`}
                            className="px-4 py-3 rounded-xl text-center"
                            style={{
                              background: duration?.duration_id === d.duration_id ? 'rgba(212,175,55,0.12)' : 'rgba(10,10,10,0.5)',
                              border: `1px solid ${duration?.duration_id === d.duration_id ? '#D4AF37' : 'rgba(245,236,215,0.12)'}`,
                            }}>
                      <div className="font-display text-base" style={{ color: '#FFF8DC' }}>{d.label}</div>
                      <div className="text-xs mt-1 text-amber-300">{d.credits ?? 0} cr</div>
                    </button>
                  ))}
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <input type="checkbox" id="mixed" checked={isMixed} onChange={(e) => setIsMixed(e.target.checked)} data-testid="mixed-theme-toggle" />
                  <label htmlFor="mixed" className="text-sm" style={{ color: 'rgba(245,236,215,0.7)' }}>
                    My selection mixes designs from multiple themes
                  </label>
                </div>
              </Section>
            )}

            {step === 4 && (
              <Section title="Review" testId="step-review" onBack={() => setStep(3)}>
                <div className="space-y-2">
                  <Line label="Design" value={design?.design_name} />
                  <Line label="Event" value={design?.event_type} />
                  <Line label="Features" value={selectedFeatures.length ? `${selectedFeatures.length} selected` : 'None'} />
                  <Line label="Duration" value={duration?.label} />
                  {isMixed && <Line label="Mixed theme" value="Yes" />}
                </div>
                {error && (
                  <div className="mt-4 px-3 py-2 rounded text-sm flex items-center gap-2 text-rose-300"
                       style={{ background: 'rgba(220,38,38,0.1)' }} data-testid="purchase-error">
                    <AlertCircle className="w-4 h-4" /> {error}
                  </div>
                )}
                <button
                  onClick={confirm}
                  disabled={submitting || !calc}
                  data-testid="confirm-purchase-btn"
                  className="mt-5 w-full px-5 py-3 rounded-xl text-[11px] tracking-[0.3em] uppercase font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                  style={{ background: '#D4AF37', color: '#1A0F08' }}
                >
                  {submitting ? 'Confirming…' : <>
                    <Sparkles className="w-4 h-4" />
                    Confirm &amp; pay {calc?.total_credits ?? 0} cr
                  </>}
                </button>
              </Section>
            )}
          </div>

          {/* Live total side panel */}
          <aside className="rounded-2xl p-5 lg:sticky lg:top-6 h-fit"
                 style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(245,236,215,0.12)' }}
                 data-testid="purchase-summary">
            <div className="text-[10px] tracking-[0.3em] uppercase mb-3" style={{ color: 'rgba(245,236,215,0.55)' }}>Live total</div>
            <div className="font-display text-5xl mb-1" style={{ color: '#FFF8DC' }} data-testid="live-total">
              {calcing ? '…' : (calc?.total_credits ?? 0)}
            </div>
            <div className="text-[11px] tracking-[0.2em] uppercase mb-5" style={{ color: '#D4AF37' }}>credits</div>

            {calc?.breakdown && (
              <div className="space-y-1.5 mb-5">
                {calc.breakdown.map((b, i) => (
                  <div key={i} className="flex items-baseline justify-between text-sm">
                    <span style={{ color: 'rgba(245,236,215,0.7)' }}>{b.item}</span>
                    <span style={{ color: '#FFF8DC' }}>{b.credits}</span>
                  </div>
                ))}
              </div>
            )}

            {balance && (
              <div className="pt-4 mt-4 text-xs flex items-center justify-between"
                   style={{ borderTop: '1px solid rgba(245,236,215,0.08)', color: 'rgba(245,236,215,0.65)' }}>
                <span>After purchase</span>
                <span className={(balance.available_credits - (calc?.total_credits ?? 0)) >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                  {balance.available_credits - (calc?.total_credits ?? 0)} cr
                </span>
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

const Stepper = ({ step }) => {
  const items = ['Design', 'Features', 'Duration', 'Review'];
  return (
    <ol className="flex items-center gap-2 flex-wrap" data-testid="purchase-stepper">
      {items.map((label, i) => {
        const n = i + 1;
        const active = step === n;
        const done = step > n;
        return (
          <li key={label} className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-full grid place-items-center text-xs font-medium"
                  style={{
                    background: done ? '#D4AF37' : (active ? 'rgba(212,175,55,0.18)' : 'rgba(245,236,215,0.05)'),
                    color: done ? '#1A0F08' : (active ? '#D4AF37' : 'rgba(245,236,215,0.45)'),
                    border: active ? '1px solid #D4AF37' : '1px solid transparent',
                  }}>
              {done ? <Check className="w-3.5 h-3.5" /> : n}
            </span>
            <span className="text-[11px] tracking-[0.2em] uppercase" style={{ color: active ? '#D4AF37' : 'rgba(245,236,215,0.55)' }}>{label}</span>
            {n < items.length && <ChevronRight className="w-4 h-4 opacity-30" />}
          </li>
        );
      })}
    </ol>
  );
};

const Section = ({ title, children, onBack, onNext, testId }) => (
  <div data-testid={testId}>
    <div className="flex items-center justify-between mb-4">
      <h2 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>{title}</h2>
      <div className="flex gap-2">
        {onBack && (
          <button onClick={onBack} className="text-[11px] tracking-[0.3em] uppercase px-3 py-1.5 rounded"
                  style={{ background: 'rgba(245,236,215,0.06)', color: '#F5ECD7' }} data-testid={`${testId}-back`}>
            Back
          </button>
        )}
        {onNext && (
          <button onClick={onNext} className="text-[11px] tracking-[0.3em] uppercase px-3 py-1.5 rounded"
                  style={{ background: '#D4AF37', color: '#1A0F08' }} data-testid={`${testId}-next`}>
            Continue
          </button>
        )}
      </div>
    </div>
    {children}
  </div>
);

const Line = ({ label, value }) => (
  <div className="flex items-center justify-between px-3 py-2 rounded"
       style={{ background: 'rgba(10,10,10,0.5)', border: '1px solid rgba(245,236,215,0.08)' }}>
    <span className="text-[11px] tracking-[0.2em] uppercase" style={{ color: 'rgba(245,236,215,0.55)' }}>{label}</span>
    <span className="text-sm" style={{ color: '#FFF8DC' }}>{value || '—'}</span>
  </div>
);

const Empty = ({ msg }) => (
  <div className="py-10 text-center text-sm" style={{ color: 'rgba(245,236,215,0.55)' }}>{msg}</div>
);
