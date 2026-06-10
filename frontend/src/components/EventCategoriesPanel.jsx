import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Coins, Save, ChevronRight, Users, Camera, X, Check } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Super-admin Event Categories panel.
 *
 * Lets the super admin pick a non-wedding category, then a user type
 * (Photographer / Normal User) and assign credit costs for:
 *   • Design selection (per category)
 *   • Each feature (countdown, RSVP, AI face match, …)
 *
 * Persists overrides via POST /api/super-admin/event-categories/pricing
 */
const EventCategoriesPanel = () => {
  const [categories, setCategories] = useState([]);
  const [active, setActive] = useState(null);          // category id
  const [userType, setUserType] = useState('photographer');
  const [meta, setMeta] = useState(null);
  const [pricing, setPricing] = useState({ design_credits: 1, feature_credits: {} });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/event-categories`);
        // Skip wedding — wedding pricing is controlled by the existing pricing hub.
        const list = (data.categories || []).filter((c) => c.id !== 'wedding');
        setCategories(list);
      } catch (e) {
        console.error('Failed to load categories', e);
      }
    })();
  }, []);

  useEffect(() => {
    if (!active) { setMeta(null); return; }
    let alive = true;
    (async () => {
      try {
        const [m, p] = await Promise.all([
          axios.get(`${API_URL}/api/event-categories/${active}`),
          axios.get(`${API_URL}/api/event-categories/${active}/pricing`, { params: { user_type: userType } }),
        ]);
        if (!alive) return;
        setMeta(m.data);
        setPricing(p.data || { design_credits: 1, feature_credits: {} });
      } catch (e) {
        console.error('Failed to load category', e);
      }
    })();
    return () => { alive = false; };
  }, [active, userType]);

  const updateFeatureCredits = (key, value) => {
    setPricing((p) => ({
      ...p,
      feature_credits: { ...(p.feature_credits || {}), [key]: Number(value) || 0 },
    }));
  };

  const save = async () => {
    setSaving(true); setMsg(null);
    try {
      await axios.post(`${API_URL}/api/super-admin/event-categories/pricing`, {
        category_id: active,
        user_type: userType,
        design_credits: Number(pricing.design_credits) || 0,
        feature_credits: pricing.feature_credits || {},
      });
      setMsg({ kind: 'ok', text: 'Pricing saved successfully.' });
    } catch (e) {
      console.error('Save failed', e);
      setMsg({ kind: 'err', text: e?.response?.data?.detail || 'Save failed.' });
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  // ===========================================================
  // Render
  // ===========================================================
  if (!active) {
    return (
      <div className="lux-glass p-6 sm:p-8" data-testid="event-categories-panel">
        <div className="mb-6">
          <h3 className="font-display text-2xl mb-1" style={{ color: '#FFF8DC' }}>
            Event Categories
          </h3>
          <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Configure credit costs for non-wedding invitation categories. Click a category to set
            design + feature credits per user type.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.map((c) => (
            <motion.button
              key={c.id}
              whileHover={{ y: -4 }}
              onClick={() => setActive(c.id)}
              className="text-left rounded-xl overflow-hidden relative"
              style={{ background: '#161210', border: '1px solid rgba(212,175,55,0.18)' }}
              data-testid={`event-cat-${c.id}`}
            >
              <div className="relative h-32 overflow-hidden">
                <img src={c.cover_preview} alt={c.label} className="w-full h-full object-cover" />
                <div className="absolute inset-0"
                  style={{ background: 'linear-gradient(180deg,transparent 30%,rgba(11,9,8,0.92) 100%)' }} />
                <div className="absolute top-3 left-3 w-9 h-9 rounded-full grid place-items-center text-lg"
                  style={{ background: 'rgba(11,9,8,0.65)', border: '1px solid rgba(212,175,55,0.35)' }}>
                  {c.icon}
                </div>
              </div>
              <div className="p-4">
                <div className="font-display text-base mb-1" style={{ color: '#FFF8DC' }}>{c.label}</div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] tracking-wider uppercase"
                    style={{ color: 'rgba(255,248,220,0.5)' }}>Configure</span>
                  <ChevronRight className="w-4 h-4" style={{ color: '#D4AF37' }} />
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    );
  }

  const cat = categories.find((c) => c.id === active);
  return (
    <div className="lux-glass p-6 sm:p-8" data-testid="event-categories-config">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => { setActive(null); setMsg(null); }}
            className="lux-btn lux-btn-ghost" data-testid="back-to-cats">
            ← Back
          </button>
          <div>
            <h3 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>
              {cat?.icon} {cat?.label}
            </h3>
            <p className="text-[10px] tracking-wider uppercase"
              style={{ color: 'rgba(212,175,55,0.8)' }}>{cat?.label_traditional}</p>
          </div>
        </div>

        {/* User type toggle */}
        <div className="flex items-center gap-2 rounded-full p-1"
          style={{ background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.2)' }}>
          {[
            { id: 'photographer', label: 'Photographer', icon: Camera },
            { id: 'normal_user', label: 'Normal User', icon: Users },
          ].map((u) => (
            <button key={u.id} onClick={() => setUserType(u.id)}
              className="px-4 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all"
              style={userType === u.id
                ? { background: '#D4AF37', color: '#0b0908' }
                : { color: 'rgba(255,248,220,0.7)' }}
              data-testid={`user-type-${u.id}`}>
              <u.icon className="w-3.5 h-3.5" /> {u.label}
            </button>
          ))}
        </div>
      </div>

      {!meta ? (
        <div className="text-center py-10" style={{ color: 'rgba(255,248,220,0.5)' }}>Loading…</div>
      ) : (
        <>
          {/* Design credits */}
          <div className="mb-8">
            <h4 className="text-xs tracking-[0.3em] uppercase mb-3"
              style={{ color: '#D4AF37' }}>◆ Design Credit Cost</h4>
            <div className="lux-glass p-4 flex items-center justify-between gap-4">
              <div>
                <div className="text-sm" style={{ color: '#FFF8DC' }}>
                  Credits per design (applies to all {meta.designs?.length || 0} designs)
                </div>
                <div className="text-[10px] tracking-wider uppercase mt-1"
                  style={{ color: 'rgba(255,248,220,0.5)' }}>
                  Charged when {userType === 'photographer' ? 'photographer' : 'normal user'} selects this category{'\u2019'}s design.
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setPricing((p) => ({ ...p, design_credits: Math.max(0, (p.design_credits || 0) - 1) }))}
                  className="w-9 h-9 rounded-full grid place-items-center text-lg"
                  style={{ background: 'rgba(255,248,220,0.08)', color: '#FFF8DC' }}>−</button>
                <input type="number" min="0" value={pricing.design_credits || 0}
                  onChange={(e) => setPricing((p) => ({ ...p, design_credits: Number(e.target.value) || 0 }))}
                  className="w-16 text-center text-lg font-display rounded-md py-2 bg-transparent"
                  style={{ color: '#D4AF37', border: '1px solid rgba(212,175,55,0.3)' }}
                  data-testid="design-credits-input" />
                <button onClick={() => setPricing((p) => ({ ...p, design_credits: (p.design_credits || 0) + 1 }))}
                  className="w-9 h-9 rounded-full grid place-items-center text-lg"
                  style={{ background: '#D4AF37', color: '#0b0908' }}>+</button>
              </div>
            </div>
          </div>

          {/* Feature credits */}
          <div className="mb-6">
            <h4 className="text-xs tracking-[0.3em] uppercase mb-3"
              style={{ color: '#D4AF37' }}>◆ Feature Credit Costs</h4>
            <div className="grid md:grid-cols-2 gap-3">
              {(meta.features || []).map((f) => (
                <div key={f.key} className="lux-glass p-3 flex items-center justify-between gap-3"
                  data-testid={`feature-credit-${f.key}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-2xl">{f.icon}</span>
                    <div className="min-w-0">
                      <div className="text-sm truncate" style={{ color: '#FFF8DC' }}>{f.label}</div>
                      <div className="text-[10px] tracking-wider uppercase"
                        style={{ color: 'rgba(255,248,220,0.5)' }}>{f.key}</div>
                    </div>
                  </div>
                  <input type="number" min="0"
                    value={pricing.feature_credits?.[f.key] ?? f.credits ?? 0}
                    onChange={(e) => updateFeatureCredits(f.key, e.target.value)}
                    className="w-16 text-center text-base font-display rounded-md py-1.5 bg-transparent"
                    style={{ color: '#D4AF37', border: '1px solid rgba(212,175,55,0.3)' }} />
                </div>
              ))}
            </div>
          </div>

          {/* Save bar */}
          <div className="flex items-center justify-between gap-3 pt-4"
            style={{ borderTop: '1px solid rgba(212,175,55,0.15)' }}>
            <AnimatePresence>
              {msg && (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="text-xs px-3 py-1.5 rounded-full"
                  style={{
                    background: msg.kind === 'ok' ? 'rgba(74,222,128,0.12)' : 'rgba(255,68,68,0.12)',
                    color: msg.kind === 'ok' ? '#86EFAC' : '#FCA5A5',
                    border: `1px solid ${msg.kind === 'ok' ? 'rgba(74,222,128,0.3)' : 'rgba(255,68,68,0.3)'}`,
                  }}>
                  {msg.kind === 'ok' ? <Check className="inline w-3.5 h-3.5 mr-1" /> : <X className="inline w-3.5 h-3.5 mr-1" />}
                  {msg.text}
                </motion.div>
              )}
            </AnimatePresence>
            <div className="ml-auto flex items-center gap-2">
              <button disabled={saving} onClick={save} className="lux-btn" data-testid="save-cat-pricing">
                <Save className="w-4 h-4" /> {saving ? 'Saving…' : `Save for ${userType === 'photographer' ? 'Photographer' : 'Normal User'}`}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default EventCategoriesPanel;
