/**
 * /super-admin/expiry-tiers — Manage publish-link expiry tiers.
 *
 * Lets the platform owner customise the tier list shown in the
 * photographer's Publish step (1 month / 3 months / 6 months / 1 year
 * by default — but the owner can change the days and credit cost to
 * anything, e.g. 45 days for 2 credits).
 *
 * Backed by:
 *   GET  /api/admin/expiry-tiers
 *   PUT  /api/admin/expiry-tiers   (super-admin only)
 */
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Save, Plus, Trash2, ChevronLeft, Clock, Coins, AlertCircle, CheckCircle2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const slugify = (s) =>
  String(s || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || `tier_${Math.random().toString(36).slice(2, 6)}`;

const SuperAdminExpiryTiers = () => {
  const nav = useNavigate();
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, kind = 'ok') => {
    setToast({ msg, kind });
    setTimeout(() => setToast(null), 2500);
  };

  const token = () => localStorage.getItem('admin_token') || localStorage.getItem('super_admin_token') || '';

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API}/api/admin/expiry-tiers`, {
          headers: { Authorization: `Bearer ${token()}` },
        });
        if (cancelled) return;
        setTiers(res.data?.tiers || []);
      } catch (e) {
        showToast('Failed to load tiers — log in as super-admin', 'err');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const updateRow = (idx, key, value) => {
    setTiers((rows) => rows.map((r, i) => (i === idx ? { ...r, [key]: value } : r)));
  };
  const deleteRow = (idx) => setTiers((rows) => rows.filter((_, i) => i !== idx));
  const addRow = () =>
    setTiers((rows) => [
      ...rows,
      {
        id: `tier_${rows.length + 1}`,
        label: `${rows.length + 1} New Tier`,
        days: 30,
        credits: 1,
        order: rows.length + 1,
      },
    ]);

  const save = async () => {
    // Normalise & validate
    const cleaned = tiers
      .map((t, i) => ({
        id: slugify(t.id || t.label),
        label: String(t.label || '').trim() || 'Untitled',
        days: Math.max(1, parseInt(t.days, 10) || 30),
        credits: Math.max(0, parseInt(t.credits, 10) || 0),
        order: parseInt(t.order, 10) || i + 1,
      }))
      .sort((a, b) => a.order - b.order);
    // Ensure unique ids
    const seen = new Set();
    for (const t of cleaned) {
      if (seen.has(t.id)) {
        showToast(`Duplicate tier id "${t.id}" — rename one of them.`, 'err');
        return;
      }
      seen.add(t.id);
    }

    setSaving(true);
    try {
      await axios.put(`${API}/api/admin/expiry-tiers`, cleaned, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      setTiers(cleaned);
      showToast('Saved!');
    } catch (e) {
      showToast(e.response?.data?.detail || 'Save failed', 'err');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen p-6" style={{ background: '#0B0805', color: '#FFF8DC' }}
         data-testid="expiry-tiers-page">
      <div className="max-w-4xl mx-auto">
        <button onClick={() => nav('/super-admin/dashboard')}
          className="text-xs tracking-[0.3em] uppercase mb-6 inline-flex items-center gap-2 opacity-70 hover:opacity-100"
          data-testid="expiry-tiers-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Super Admin
        </button>

        <header className="mb-8">
          <div className="text-[10px] tracking-[0.4em] uppercase mb-2" style={{ color: '#D4AF37' }}>
            ◆ Pricing Hub
          </div>
          <h1 className="font-display text-4xl mb-2">Link Expiry Tiers</h1>
          <p className="text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
            These tiers appear in the photographer's <strong>Publish</strong> step. You can fully
            customise the days and credits per tier — e.g. <em>45 days = 2 credits</em>.
          </p>
        </header>

        {loading ? (
          <div className="lux-glass p-8 text-center" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Loading…
          </div>
        ) : (
          <>
            <div className="lux-glass overflow-hidden" data-testid="expiry-tiers-table">
              <div className="grid grid-cols-12 gap-3 px-4 py-3 text-[10px] tracking-[0.3em] uppercase border-b"
                   style={{ borderColor: 'rgba(212,175,55,0.18)', color: 'rgba(255,248,220,0.55)' }}>
                <div className="col-span-1">Order</div>
                <div className="col-span-3">ID (slug)</div>
                <div className="col-span-3">Label</div>
                <div className="col-span-2">Days</div>
                <div className="col-span-2">Credits</div>
                <div className="col-span-1"></div>
              </div>
              {tiers.length === 0 && (
                <div className="px-4 py-6 text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
                  No tiers configured. Add one below.
                </div>
              )}
              {tiers.map((t, i) => (
                <div key={i} className="grid grid-cols-12 gap-3 px-4 py-3 items-center border-b"
                     style={{ borderColor: 'rgba(255,248,220,0.06)' }}
                     data-testid={`tier-row-${i}`}>
                  <input type="number" className="col-span-1 lux-input" value={t.order}
                    onChange={(e) => updateRow(i, 'order', e.target.value)}
                    data-testid={`tier-order-${i}`} />
                  <input className="col-span-3 lux-input" value={t.id}
                    onChange={(e) => updateRow(i, 'id', e.target.value)}
                    placeholder="e.g. 45_days"
                    data-testid={`tier-id-${i}`} />
                  <input className="col-span-3 lux-input" value={t.label}
                    onChange={(e) => updateRow(i, 'label', e.target.value)}
                    placeholder="e.g. 45 Days"
                    data-testid={`tier-label-${i}`} />
                  <div className="col-span-2 flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 opacity-60" />
                    <input type="number" className="lux-input flex-1" value={t.days}
                      onChange={(e) => updateRow(i, 'days', e.target.value)}
                      data-testid={`tier-days-${i}`} />
                  </div>
                  <div className="col-span-2 flex items-center gap-2">
                    <Coins className="w-3.5 h-3.5 opacity-60" style={{ color: '#D4AF37' }} />
                    <input type="number" className="lux-input flex-1" value={t.credits}
                      onChange={(e) => updateRow(i, 'credits', e.target.value)}
                      data-testid={`tier-credits-${i}`} />
                  </div>
                  <button type="button" onClick={() => deleteRow(i)}
                    className="col-span-1 grid place-items-center rounded-md p-2 hover:bg-red-700/30 transition-colors"
                    data-testid={`tier-delete-${i}`}>
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between mt-5 gap-3 flex-wrap">
              <button type="button" onClick={addRow}
                className="lux-btn lux-btn-ghost inline-flex items-center gap-2 text-xs"
                data-testid="expiry-tiers-add">
                <Plus className="w-3.5 h-3.5" /> Add Tier
              </button>
              <button type="button" onClick={save} disabled={saving}
                className="lux-btn inline-flex items-center gap-2"
                data-testid="expiry-tiers-save">
                {saving ? 'Saving…' : 'Save Changes'}
                <Save className="w-4 h-4" />
              </button>
            </div>

            <p className="text-[11px] mt-6" style={{ color: 'rgba(255,248,220,0.45)' }}>
              Tip: Lower the credit cost on the 1-month tier to convert hesitant photographers, and
              charge a small premium on the 1-year tier — the revenue maths almost always favours
              long-lifetime links.
            </p>
          </>
        )}

        {toast && (
          <div
            data-testid="expiry-tiers-toast"
            className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 ${
              toast.kind === 'err' ? 'bg-red-700 text-white' : 'bg-emerald-700 text-white'
            }`}
          >
            {toast.kind === 'err' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            <span className="text-sm">{toast.msg}</span>
          </div>
        )}
      </div>

      <style>{`
        .lux-input {
          background: rgba(255,248,220,0.04);
          border: 1px solid rgba(255,248,220,0.12);
          border-radius: 8px;
          padding: 8px 10px;
          color: #FFF8DC;
          font-size: 13px;
          width: 100%;
          outline: none;
          transition: border-color 0.2s;
        }
        .lux-input:focus { border-color: #D4AF37; }
        .lux-glass {
          background: rgba(255,248,220,0.03);
          border: 1px solid rgba(212,175,55,0.18);
          border-radius: 12px;
        }
        .lux-btn {
          background: #D4AF37;
          color: #16110C;
          padding: 10px 18px;
          border-radius: 999px;
          font-size: 12px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          transition: opacity 0.2s;
        }
        .lux-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .lux-btn-ghost {
          background: transparent;
          color: #FFF8DC;
          border: 1px solid rgba(212,175,55,0.4);
        }
      `}</style>
    </div>
  );
};

export default SuperAdminExpiryTiers;
