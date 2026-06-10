/**
 * PhotographerTierHistory — vertical timeline of every tier the photographer
 * has unlocked, plus the most recent ledger entries that contributed to it.
 *
 * Fetches `/api/photographer/me/tier-history`. Renders as a sticky-right
 * widget on the photographer dashboard.
 */
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { History, Sparkles, ArrowUpRight, BookOpen } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

const TIER_HUE = {
  starter: '#cfcfcf',
  pro:     '#E8C766',
  elite:   '#FFB774',
  partner: '#FFE38A',
};

const fmt = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return iso; }
};

export default function PhotographerTierHistory({ className = '' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) { setLoading(false); return; }
    axios.get(`${API}/api/photographer/me/tier-history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) return null;

  const climb = data.climb || [];
  const entries = data.entries || [];
  const currentTier = data.current_tier || {};

  return (
    <div
      className={`relative rounded-2xl p-5 md:p-6 ${className}`}
      style={{
        background: 'rgba(245,236,215,0.04)',
        border: '1px solid rgba(212,175,55,0.22)',
      }}
      data-testid="photographer-tier-history"
    >
      <div className="flex items-center justify-between mb-4 gap-3">
        <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase"
          style={{ color: TIER_HUE[currentTier.key] || '#D4AF37' }}>
          <History className="w-3.5 h-3.5" /> Tier history
        </div>
        <button
          type="button"
          onClick={() => setOpen((x) => !x)}
          className="text-[10px] tracking-[0.25em] uppercase px-2.5 py-1 rounded-full"
          style={{
            background: open ? 'rgba(212,175,55,0.15)' : 'rgba(245,236,215,0.05)',
            border: '1px solid rgba(212,175,55,0.3)',
            color: '#FFE38A',
          }}
          data-testid="tier-history-toggle"
        >
          {open ? 'Hide ledger' : `Show ledger (${entries.length})`}
        </button>
      </div>

      {/* Tier climb timeline */}
      {climb.length === 0 ? (
        <div className="text-xs py-2" style={{ color: 'rgba(245,236,215,0.55)' }}>
          Publish your first paid link to start climbing the loyalty ladder.
        </div>
      ) : (
        <ol className="relative pl-5 space-y-3" data-testid="tier-history-climb">
          <span aria-hidden className="absolute left-1.5 top-2 bottom-2 w-px"
                style={{ background: 'linear-gradient(180deg, rgba(212,175,55,0.5), rgba(212,175,55,0.05))' }} />
          {climb.map((c) => (
            <li key={c.ledger_id} className="relative" data-testid={`tier-climb-${c.tier.key}`}>
              <span
                className="absolute -left-[18px] top-1 w-3 h-3 rounded-full"
                style={{ background: TIER_HUE[c.tier.key] || '#D4AF37', boxShadow: `0 0 12px ${TIER_HUE[c.tier.key] || '#D4AF37'}aa` }}
              />
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-display text-base" style={{ color: TIER_HUE[c.tier.key] || '#FFF8DC' }}>
                  Unlocked {c.tier.label}
                </span>
                <span className="text-[10px] tracking-[0.2em] uppercase" style={{ color: 'rgba(245,236,215,0.55)' }}>
                  {fmt(c.unlocked_at)}
                </span>
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: 'rgba(245,236,215,0.55)' }}>
                {c.tier.discount_pct}% off packs · +{c.tier.bonus_pct}% bonus credits
              </div>
            </li>
          ))}
        </ol>
      )}

      {/* Ledger preview */}
      {open && (
        <div className="mt-5 pt-4" style={{ borderTop: '1px solid rgba(212,175,55,0.15)' }}>
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase mb-3"
            style={{ color: 'rgba(245,236,215,0.65)' }}>
            <BookOpen className="w-3 h-3" /> Recent ledger entries
          </div>
          {entries.length === 0 ? (
            <div className="text-xs" style={{ color: 'rgba(245,236,215,0.45)' }}>No matching ledger entries.</div>
          ) : (
            <ul className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
              {entries.map((e) => (
                <li
                  key={e.id}
                  className="flex items-start gap-2 text-[12px] py-1.5"
                  data-testid={`tier-history-entry-${e.id}`}
                >
                  {e.kind === 'publish' ? (
                    <ArrowUpRight className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#FFE38A' }} />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#86EFAC' }} />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="truncate" style={{ color: 'rgba(245,236,215,0.78)' }}>{e.reason}</div>
                    <div className="text-[10px] tracking-[0.2em] uppercase mt-0.5" style={{ color: 'rgba(245,236,215,0.45)' }}>
                      {fmt(e.created_at)}{e.tier_key ? ` · ${e.tier_key}` : ''}
                    </div>
                  </div>
                  <span style={{ color: e.amount > 0 ? '#86EFAC' : '#FFB0A0' }}>
                    {e.amount > 0 ? `+${e.amount}` : e.amount}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
