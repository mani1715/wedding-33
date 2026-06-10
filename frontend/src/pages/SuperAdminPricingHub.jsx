/**
 * /super-admin/pricing — Unified Pricing Hub
 *
 * Single page replacing 17 legacy pricing pages. Structure:
 *
 *   ┌──────────── PHOTOGRAPHER ────────────┐  ┌──────── NORMAL USER ────────┐
 *   │ 1. Credit Packs                       │  │ 1. Credit Packs            │
 *   │ 2. Monthly Subscription               │  │ 2. Theme Prices            │
 *   │ 3. Post-Subscription Credit Pricing   │  │ 3. Design Prices           │
 *   │ 4. Theme Prices                       │  │ 4. Invitation Option Prices│
 *   │ 5. Design Prices                      │  └────────────────────────────┘
 *   │ 6. Invitation Option Prices           │
 *   └───────────────────────────────────────┘
 *
 * Every price row supports:
 *   - base_price
 *   - "Enable discount" toggle  → enter discount_price (old shown struck-through)
 *   - "Free" toggle (option_prices only)
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Crown, Users, IndianRupee, Coins, Repeat, Layers,
  Palette, ListTree, ChevronLeft, Save, Plus, Trash2, Tag,
  ToggleLeft, ToggleRight, AlertCircle, CheckCircle2,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const PRICE = `${API}/api/super-admin/pricing`;

const AUDIENCES = [
  { key: 'photographer', label: 'Photographer', icon: Crown, blurb: 'Large credits • Bulk customer rates' },
  { key: 'normal_user',  label: 'Normal User',  icon: Users, blurb: 'Small credits • Retail rates' },
];

const PHOTOG_SUBTABS = [
  { key: 'credit_packs',  label: 'Credit Packs',         icon: Coins },
  { key: 'subscription',  label: 'Monthly Subscription', icon: Repeat },
  { key: 'post_sub',      label: 'Post-Sub Credits',     icon: IndianRupee },
  { key: 'tiers',         label: 'Loyalty Tiers',        icon: Crown },
  { key: 'feature_packs', label: 'Feature Packs',        icon: Layers },
  { key: 'themes',        label: 'Theme Prices',         icon: Layers },
  { key: 'designs',       label: 'Design Prices',        icon: Palette },
  { key: 'options',       label: 'Invitation Options',   icon: ListTree },
];
const NORMAL_SUBTABS = [
  { key: 'credit_packs',  label: 'Credit Packs',       icon: Coins },
  { key: 'feature_packs', label: 'Feature Packs',      icon: Layers },
  { key: 'themes',        label: 'Theme Prices',       icon: Layers },
  { key: 'designs',       label: 'Design Prices',      icon: Palette },
  { key: 'options',       label: 'Invitation Options', icon: ListTree },
];

// -------------- Generic UI building blocks --------------
const Toast = ({ msg, kind }) => msg ? (
  <div
    data-testid="pricing-toast"
    className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 ${
      kind === 'err' ? 'bg-red-700 text-white' : 'bg-emerald-700 text-white'
    }`}
  >
    {kind === 'err' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
    <span className="text-sm">{msg}</span>
  </div>
) : null;

const ToggleSwitch = ({ on, onChange, testid }) => (
  <button
    type="button" onClick={() => onChange(!on)} data-testid={testid}
    className={`inline-flex items-center transition ${on ? 'text-emerald-400' : 'text-white/40'}`}
  >
    {on ? <ToggleRight className="w-7 h-7" /> : <ToggleLeft className="w-7 h-7" />}
  </button>
);

const PriceCell = ({ value, oldValue, suffix }) => (
  <div className="flex items-baseline gap-2">
    {oldValue != null && (
      <span className="text-white/40 text-sm line-through" data-testid="price-old">
        {oldValue}{suffix}
      </span>
    )}
    <span className="text-yellow-200 font-medium text-lg" data-testid="price-new">
      {value}{suffix}
    </span>
  </div>
);

const NumberInput = ({ value, onChange, testid, placeholder, min = 0 }) => (
  <input
    type="number" min={min}
    value={value ?? ''}
    onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
    placeholder={placeholder}
    data-testid={testid}
    className="bg-black/40 border border-yellow-200/20 rounded px-3 py-2 text-yellow-50 w-28 focus:outline-none focus:border-yellow-300"
  />
);

const TextInput = ({ value, onChange, testid, placeholder, width = 'w-40' }) => (
  <input
    type="text" value={value ?? ''} onChange={(e) => onChange(e.target.value)}
    placeholder={placeholder} data-testid={testid}
    className={`bg-black/40 border border-yellow-200/20 rounded px-3 py-2 text-yellow-50 ${width} focus:outline-none focus:border-yellow-300`}
  />
);

// -------------- Reusable price row controls --------------
const DiscountControls = ({ row, onPatch, suffix, testid }) => (
  <div className="flex items-center gap-3">
    <span className="text-xs uppercase tracking-wider text-white/60">Discount</span>
    <ToggleSwitch
      on={!!row.discount_enabled}
      onChange={(v) => onPatch({ discount_enabled: v, ...(v ? {} : { discount_price: null }) })}
      testid={`${testid}-discount-toggle`}
    />
    {row.discount_enabled && (
      <NumberInput
        value={row.discount_price} onChange={(v) => onPatch({ discount_price: v })}
        testid={`${testid}-discount-input`} placeholder={`new ${suffix}`}
      />
    )}
  </div>
);

// -------------- Hook: auth header --------------
const useAuthAxios = () => {
  return useMemo(() => {
    const token = localStorage.getItem('admin_token');
    const instance = axios.create({ baseURL: API });
    if (token) instance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    return instance;
  }, []);
};

// =============================================================
// SECTION COMPONENTS (one per sub-tab)
// =============================================================

// ---- Credit Packs ----
function CreditPacksSection({ audience, http, toast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newRow, setNewRow] = useState({ credits: '', base_price: '', label: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await http.get(`/api/super-admin/pricing/credit-packs?audience=${audience}`);
      setRows(r.data);
    } catch (e) { toast(e.message || 'Failed to load packs', 'err'); }
    setLoading(false);
  }, [audience, http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async (row) => {
    try {
      await http.post('/api/super-admin/pricing/credit-packs', { ...row, audience });
      toast('Pack saved');
      load();
    } catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this pack?')) return;
    try {
      await http.delete(`/api/super-admin/pricing/credit-packs/${id}`);
      toast('Pack deleted');
      load();
    } catch (e) { toast(e.response?.data?.detail || 'Delete failed', 'err'); }
  };

  const addNew = async () => {
    if (!newRow.credits || !newRow.base_price) return toast('Enter credits + price', 'err');
    await save({ ...newRow, credits: Number(newRow.credits), base_price: Number(newRow.base_price), is_active: true });
    setNewRow({ credits: '', base_price: '', label: '' });
  };

  return (
    <div data-testid="credit-packs-section">
      <SectionHeader title="Credit Packs" blurb="Buy-credit bundles. Set credits → price. Discount toggles a struck-through old price." />
      {loading ? <Skeleton /> : (
        <div className="space-y-3">
          {rows.map((row) => (
            <PackRow key={row.id} row={row} onSave={save} onRemove={remove} testid={`pack-${row.credits}`} />
          ))}
          {!rows.length && <Empty label="No packs yet" />}
        </div>
      )}
      <div className="mt-6 p-4 rounded-lg border border-yellow-200/15 bg-black/30">
        <div className="text-xs uppercase tracking-wider text-yellow-200/70 mb-3 flex items-center gap-2"><Plus className="w-4 h-4" /> New Pack</div>
        <div className="flex flex-wrap items-end gap-3">
          <NumberInput value={newRow.credits} onChange={(v) => setNewRow({ ...newRow, credits: v })} placeholder="100" testid="new-pack-credits" />
          <span className="text-white/40 text-sm">credits =</span>
          <NumberInput value={newRow.base_price} onChange={(v) => setNewRow({ ...newRow, base_price: v })} placeholder="600" testid="new-pack-price" />
          <span className="text-white/40 text-sm">rupees</span>
          <TextInput value={newRow.label} onChange={(v) => setNewRow({ ...newRow, label: v })} placeholder="Label (optional)" testid="new-pack-label" />
          <button onClick={addNew} className="px-4 py-2 bg-yellow-300 text-black rounded font-medium hover:bg-yellow-200" data-testid="new-pack-save">Add Pack</button>
        </div>
      </div>
    </div>
  );
}

function PackRow({ row, onSave, onRemove, testid }) {
  const [local, setLocal] = useState(row);
  useEffect(() => { setLocal(row); }, [row]);
  const dirty = JSON.stringify(local) !== JSON.stringify(row);

  return (
    <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg border border-yellow-200/15 bg-black/40" data-testid={testid}>
      <div className="flex items-center gap-2 min-w-[180px]">
        <Coins className="w-4 h-4 text-yellow-300" />
        <span className="text-yellow-50 font-medium">{row.credits} credits</span>
        {row.label && <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-300/15 text-yellow-200/90">{row.label}</span>}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-white/50 text-sm">₹</span>
        <NumberInput value={local.base_price} onChange={(v) => setLocal({ ...local, base_price: v })} testid={`${testid}-base`} />
      </div>
      <DiscountControls row={local} onPatch={(p) => setLocal({ ...local, ...p })} suffix="₹" testid={testid} />
      <div className="ml-auto flex items-center gap-2">
        <PriceCell
          value={local.discount_enabled && local.discount_price != null ? local.discount_price : local.base_price}
          oldValue={local.discount_enabled && local.discount_price != null ? local.base_price : null}
          suffix="₹"
        />
        {dirty && (
          <button onClick={() => onSave(local)} className="px-3 py-2 bg-emerald-600 text-white rounded text-sm flex items-center gap-1" data-testid={`${testid}-save`}>
            <Save className="w-4 h-4" /> Save
          </button>
        )}
        <button onClick={() => onRemove(row.id)} className="p-2 text-red-400 hover:text-red-300" data-testid={`${testid}-delete`}><Trash2 className="w-4 h-4" /></button>
      </div>
    </div>
  );
}

// ---- Subscription (photographer only) ----
function SubscriptionSection({ http, toast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await http.get('/api/super-admin/pricing/subscriptions')).data); }
    catch (e) { toast(e.message, 'err'); }
    setLoading(false);
  }, [http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async (row) => {
    try {
      await http.post('/api/super-admin/pricing/subscriptions', row);
      toast('Plan saved'); load();
    } catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this plan?')) return;
    try { await http.delete(`/api/super-admin/pricing/subscriptions/${id}`); toast('Plan deleted'); load(); }
    catch (e) { toast(e.response?.data?.detail || 'Delete failed', 'err'); }
  };

  const addNew = () => save({ name: 'New Plan', credits_per_month: 400, duration_days: 30, base_price: 600, is_active: true });

  return (
    <div data-testid="subscription-section">
      <SectionHeader
        title="Monthly Subscription"
        blurb="Photographer's recurring plan. Photographer pays a fixed monthly fee and receives a credit balance refreshed each cycle."
      />
      {loading ? <Skeleton /> : (
        <div className="space-y-3">
          {rows.map((row) => <SubRow key={row.id} row={row} onSave={save} onRemove={remove} />)}
          {!rows.length && <Empty label="No subscription plans yet" />}
        </div>
      )}
      <div className="mt-4">
        <button onClick={addNew} className="px-4 py-2 border border-yellow-300/40 text-yellow-200 rounded hover:bg-yellow-300/10" data-testid="add-subscription">
          <Plus className="inline w-4 h-4 mr-1" /> Add Plan
        </button>
      </div>
    </div>
  );
}

function SubRow({ row, onSave, onRemove }) {
  const [local, setLocal] = useState(row);
  useEffect(() => { setLocal(row); }, [row]);
  const dirty = JSON.stringify(local) !== JSON.stringify(row);
  const testid = `sub-${row.id}`;
  return (
    <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg border border-yellow-200/15 bg-black/40" data-testid={testid}>
      <TextInput value={local.name} onChange={(v) => setLocal({ ...local, name: v })} testid={`${testid}-name`} />
      <span className="text-white/50 text-sm">credits/mo</span>
      <NumberInput value={local.credits_per_month} onChange={(v) => setLocal({ ...local, credits_per_month: v })} testid={`${testid}-credits`} />
      <span className="text-white/50 text-sm">days</span>
      <NumberInput value={local.duration_days} onChange={(v) => setLocal({ ...local, duration_days: v })} testid={`${testid}-days`} />
      <span className="text-white/50 text-sm">₹</span>
      <NumberInput value={local.base_price} onChange={(v) => setLocal({ ...local, base_price: v })} testid={`${testid}-price`} />
      <DiscountControls row={local} onPatch={(p) => setLocal({ ...local, ...p })} suffix="₹" testid={testid} />
      <ToggleSwitch on={!!local.is_active} onChange={(v) => setLocal({ ...local, is_active: v })} testid={`${testid}-active`} />
      <span className="text-white/50 text-xs">{local.is_active ? 'Active' : 'Inactive'}</span>
      <div className="ml-auto flex items-center gap-2">
        <PriceCell
          value={local.discount_enabled && local.discount_price != null ? local.discount_price : local.base_price}
          oldValue={local.discount_enabled && local.discount_price != null ? local.base_price : null}
          suffix="₹"
        />
        {dirty && <button onClick={() => onSave(local)} className="px-3 py-2 bg-emerald-600 text-white rounded text-sm" data-testid={`${testid}-save`}><Save className="inline w-4 h-4 mr-1" /> Save</button>}
        <button onClick={() => onRemove(row.id)} className="p-2 text-red-400" data-testid={`${testid}-delete`}><Trash2 className="w-4 h-4" /></button>
      </div>
    </div>
  );
}

// ---- Post-Subscription Config ----
function PostSubSection({ http, toast }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setConfig((await http.get('/api/super-admin/pricing/post-sub')).data); }
    catch (e) { toast(e.message, 'err'); }
    setLoading(false);
  }, [http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    try { await http.put('/api/super-admin/pricing/post-sub', config); toast('Post-sub config saved'); }
    catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  if (loading || !config) return <Skeleton />;

  return (
    <div data-testid="post-sub-section">
      <SectionHeader
        title="Post-Subscription Credit Pricing"
        blurb="When the photographer's monthly credits run out, this rate applies. Toggle between a flat per-credit rate or a list of top-up packs."
      />
      <div className="p-4 rounded-lg border border-yellow-200/15 bg-black/40 space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-white/70 text-sm">Mode:</span>
          <button
            onClick={() => setConfig({ ...config, mode: 'per_credit' })}
            className={`px-3 py-1.5 rounded text-sm ${config.mode === 'per_credit' ? 'bg-yellow-300 text-black' : 'bg-black/40 text-yellow-200 border border-yellow-200/20'}`}
            data-testid="post-sub-mode-rate"
          >
            Per-Credit Rate
          </button>
          <button
            onClick={() => setConfig({ ...config, mode: 'packs' })}
            className={`px-3 py-1.5 rounded text-sm ${config.mode === 'packs' ? 'bg-yellow-300 text-black' : 'bg-black/40 text-yellow-200 border border-yellow-200/20'}`}
            data-testid="post-sub-mode-packs"
          >
            Top-Up Packs
          </button>
        </div>

        {config.mode === 'per_credit' ? (
          <div className="flex items-center gap-3">
            <span className="text-white/70 text-sm">₹</span>
            <NumberInput value={config.per_credit_rate} onChange={(v) => setConfig({ ...config, per_credit_rate: v })} testid="post-sub-rate" />
            <span className="text-white/70 text-sm">per credit (after monthly run out)</span>
          </div>
        ) : (
          <div className="space-y-3">
            {(config.packs || []).map((p, idx) => (
              <div key={idx} className="flex items-center gap-3" data-testid={`post-sub-pack-${idx}`}>
                <NumberInput value={p.credits} onChange={(v) => {
                  const np = [...config.packs]; np[idx] = { ...p, credits: v }; setConfig({ ...config, packs: np });
                }} testid={`post-sub-pack-${idx}-credits`} />
                <span className="text-white/40 text-sm">credits =</span>
                <NumberInput value={p.base_price} onChange={(v) => {
                  const np = [...config.packs]; np[idx] = { ...p, base_price: v }; setConfig({ ...config, packs: np });
                }} testid={`post-sub-pack-${idx}-price`} />
                <span className="text-white/40 text-sm">₹</span>
                <button onClick={() => {
                  const np = config.packs.filter((_, i) => i !== idx); setConfig({ ...config, packs: np });
                }} className="text-red-400" data-testid={`post-sub-pack-${idx}-delete`}><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
            <button
              onClick={() => setConfig({
                ...config, packs: [...(config.packs || []), {
                  id: `ps_${Date.now()}`, audience: 'photographer',
                  credits: 100, base_price: 400, label: '', is_active: true,
                  discount_enabled: false, discount_price: null,
                }],
              })}
              className="px-3 py-2 border border-yellow-300/40 text-yellow-200 rounded text-sm"
              data-testid="post-sub-add-pack"
            ><Plus className="inline w-4 h-4 mr-1" /> Add Pack</button>
          </div>
        )}

        <button onClick={save} className="mt-4 px-5 py-2.5 bg-yellow-300 text-black rounded font-medium" data-testid="post-sub-save">
          <Save className="inline w-4 h-4 mr-1" /> Save Configuration
        </button>
      </div>
    </div>
  );
}

// ---- Photographer Loyalty Tiers ----
function PhotographerTiersSection({ http, toast }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setConfig((await http.get('/api/super-admin/pricing/photographer-tiers')).data); }
    catch (e) { toast(e.message || 'Failed to load tiers', 'err'); }
    setLoading(false);
  }, [http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    try {
      await http.put('/api/super-admin/pricing/photographer-tiers', config);
      toast('Loyalty tiers saved');
      load();
    } catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  const patchTier = (idx, patch) => {
    const tiers = [...config.tiers];
    tiers[idx] = { ...tiers[idx], ...patch };
    setConfig({ ...config, tiers });
  };

  if (loading || !config) return <Skeleton />;

  return (
    <div data-testid="loyalty-tiers-section">
      <SectionHeader
        title="Photographer Loyalty Tiers"
        blurb="As photographers publish more paid links they climb the loyalty ladder — Starter → Pro → Elite → Partner. Each tier unlocks a discount on credit packs AND on per-link publishing, plus bonus credits on every pack purchase. Tiers auto-upgrade server-side as `paid_links_count` crosses each threshold."
      />

      <div className="p-4 rounded-lg border border-yellow-200/15 bg-black/40 mb-5 flex items-center gap-4">
        <ToggleSwitch
          on={config.enabled}
          onChange={(v) => setConfig({ ...config, enabled: v })}
          testid="tiers-enabled-toggle"
        />
        <div>
          <div className="text-yellow-200 text-sm font-medium">
            Loyalty system {config.enabled ? 'enabled' : 'disabled'}
          </div>
          <div className="text-white/55 text-xs">
            {config.enabled
              ? 'Photographers see their tier badge and progress toward the next tier.'
              : 'All photographers are treated as Starter — no discounts applied anywhere.'}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {config.tiers.map((t, idx) => (
          <div
            key={t.key}
            className="p-4 rounded-lg border border-yellow-200/15 bg-black/30 flex flex-wrap items-end gap-4"
            data-testid={`tier-row-${t.key}`}
          >
            <div className="min-w-[110px]">
              <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Tier</div>
              <div className="text-yellow-200 font-medium flex items-center gap-2">
                <Tag className="w-3.5 h-3.5" /> {t.label}
              </div>
              <div className="text-white/40 text-xs mt-0.5">key: {t.key}</div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Label</div>
              <TextInput
                value={t.label}
                onChange={(v) => patchTier(idx, { label: v })}
                width="w-32"
                testid={`tier-${t.key}-label`}
              />
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Min paid links</div>
              <NumberInput
                value={t.min_paid_links}
                onChange={(v) => patchTier(idx, { min_paid_links: Number(v ?? 0) })}
                testid={`tier-${t.key}-min-links`}
              />
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Discount %</div>
              <NumberInput
                value={t.discount_pct}
                onChange={(v) => patchTier(idx, { discount_pct: Math.min(100, Math.max(0, Number(v ?? 0))) })}
                testid={`tier-${t.key}-discount-pct`}
              />
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Bonus credits %</div>
              <NumberInput
                value={t.bonus_pct}
                onChange={(v) => patchTier(idx, { bonus_pct: Math.min(100, Math.max(0, Number(v ?? 0))) })}
                testid={`tier-${t.key}-bonus-pct`}
              />
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={save}
        className="mt-6 px-5 py-2.5 bg-yellow-300 text-black rounded font-medium"
        data-testid="tiers-save"
      >
        <Save className="inline w-4 h-4 mr-1" /> Save loyalty tiers
      </button>
    </div>
  );
}

// ---- Theme Prices ----
function ThemePricesSection({ audience, http, toast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await http.get(`/api/super-admin/pricing/themes?audience=${audience}`)).data); }
    catch (e) { toast(e.message, 'err'); }
    setLoading(false);
  }, [audience, http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async (row) => {
    try { await http.post('/api/super-admin/pricing/themes', row); toast(`${row.theme_name || row.theme_id} saved`); load(); }
    catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  return (
    <div data-testid="themes-section">
      <SectionHeader title="Theme Prices (Whole Theme)" blurb={`Per-theme credit cost when a ${audience === 'photographer' ? 'photographer' : 'user'} buys the entire theme bundle.`} />
      {loading ? <Skeleton /> : (
        <div className="space-y-3">
          {rows.map((row) => <ThemeRow key={row.theme_id} row={row} onSave={save} />)}
        </div>
      )}
    </div>
  );
}

function ThemeRow({ row, onSave }) {
  const [local, setLocal] = useState(row);
  useEffect(() => { setLocal(row); }, [row]);
  const dirty = JSON.stringify(local) !== JSON.stringify(row);
  const testid = `theme-${row.theme_id}`;
  return (
    <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg border border-yellow-200/15 bg-black/40" data-testid={testid}>
      <div className="min-w-[200px] text-yellow-50 font-medium">{row.theme_name}</div>
      <NumberInput value={local.base_price} onChange={(v) => setLocal({ ...local, base_price: v })} testid={`${testid}-base`} />
      <span className="text-white/50 text-sm">credits</span>
      <DiscountControls row={local} onPatch={(p) => setLocal({ ...local, ...p })} suffix=" cr" testid={testid} />
      <div className="ml-auto flex items-center gap-2">
        <PriceCell
          value={local.discount_enabled && local.discount_price != null ? local.discount_price : local.base_price}
          oldValue={local.discount_enabled && local.discount_price != null ? local.base_price : null}
          suffix=" cr"
        />
        {dirty && <button onClick={() => onSave(local)} className="px-3 py-2 bg-emerald-600 text-white rounded text-sm" data-testid={`${testid}-save`}><Save className="inline w-4 h-4 mr-1" /> Save</button>}
      </div>
    </div>
  );
}

// ---- Design Prices ----
function DesignPricesSection({ audience, http, toast }) {
  const [themes, setThemes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cat = (await http.get('/api/super-admin/pricing/catalog')).data;
        setThemes(cat.themes);
        if (cat.themes?.length) setSelected(cat.themes[0].id);
      } catch (e) { toast(e.message, 'err'); }
    })();
  }, [http, toast]);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    http.get(`/api/super-admin/pricing/designs?audience=${audience}&theme_id=${selected}`)
      .then((r) => setRows(r.data))
      .catch((e) => toast(e.message, 'err'))
      .finally(() => setLoading(false));
  }, [selected, audience, http, toast]);

  const save = async (row) => {
    try { await http.post('/api/super-admin/pricing/designs', row); toast(`${row.design_key} saved`); }
    catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  return (
    <div data-testid="designs-section">
      <SectionHeader title="Design Prices (Per Design)" blurb="If the customer buys ONE design within a theme (not the whole theme bundle), this is the per-design credit cost." />
      <div className="flex flex-wrap gap-2 mb-4">
        {themes.map((t) => (
          <button
            key={t.id} onClick={() => setSelected(t.id)} data-testid={`design-theme-${t.id}`}
            className={`px-3 py-1.5 rounded text-sm ${selected === t.id ? 'bg-yellow-300 text-black' : 'bg-black/40 text-yellow-200 border border-yellow-200/20'}`}
          >{t.name}</button>
        ))}
      </div>
      {loading ? <Skeleton /> : (
        <div className="space-y-3">
          {rows.map((row) => <DesignRow key={row.design_key} row={row} onSave={save} />)}
        </div>
      )}
    </div>
  );
}

function DesignRow({ row, onSave }) {
  const [local, setLocal] = useState(row);
  useEffect(() => { setLocal(row); }, [row]);
  const dirty = JSON.stringify(local) !== JSON.stringify(row);
  const testid = `design-${row.theme_id}-${row.design_key}`;
  return (
    <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg border border-yellow-200/15 bg-black/40" data-testid={testid}>
      <div className="min-w-[160px] text-yellow-50 font-medium capitalize">{row.design_key.replace('_', ' ')}</div>
      <NumberInput value={local.base_price} onChange={(v) => setLocal({ ...local, base_price: v })} testid={`${testid}-base`} />
      <span className="text-white/50 text-sm">credits</span>
      <DiscountControls row={local} onPatch={(p) => setLocal({ ...local, ...p })} suffix=" cr" testid={testid} />
      <div className="ml-auto flex items-center gap-2">
        <PriceCell
          value={local.discount_enabled && local.discount_price != null ? local.discount_price : local.base_price}
          oldValue={local.discount_enabled && local.discount_price != null ? local.base_price : null}
          suffix=" cr"
        />
        {dirty && <button onClick={() => onSave(local)} className="px-3 py-2 bg-emerald-600 text-white rounded text-sm" data-testid={`${testid}-save`}><Save className="inline w-4 h-4 mr-1" /> Save</button>}
      </div>
    </div>
  );
}

// ---- Invitation Options ----
function OptionsSection({ audience, http, toast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await http.get(`/api/super-admin/pricing/options?audience=${audience}`)).data); }
    catch (e) { toast(e.message, 'err'); }
    setLoading(false);
  }, [audience, http, toast]);

  useEffect(() => { load(); }, [load]);

  const save = async (row) => {
    try { await http.post('/api/super-admin/pricing/options', row); toast(`${row.label || row.option_key} saved`); load(); }
    catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  return (
    <div data-testid="options-section">
      <SectionHeader title="Invitation Option Prices" blurb="Per-option credit cost. Toggle 'Free' to make the option free for this audience (cost = 0 regardless of base/discount)." />
      {loading ? <Skeleton /> : (
        <div className="space-y-3">
          {rows.map((row) => <OptionRow key={row.option_key} row={row} onSave={save} />)}
        </div>
      )}
    </div>
  );
}


/* ────────────────────────────────────────────────────────────────────
   FeaturePacksSection — admin CRUD for "All-Features Pack" / bundles
   ──────────────────────────────────────────────────────────────────── */
const KNOWN_FEATURE_KEYS = [
  { key: 'qr_code',            label: 'QR Code' },
  { key: 'rsvp_form',          label: 'RSVP Form' },
  { key: 'live_photo_wall',    label: 'Live Photo Wall' },
  { key: 'find_my_photos',     label: 'AI Selfie Search' },
  { key: 'music_player',       label: 'Background Music' },
  { key: 'countdown',          label: 'Countdown' },
  { key: 'maps_directions',    label: 'Maps / Directions' },
  { key: 'gift_registry',      label: 'Gift Registry' },
  { key: 'whatsapp_share',     label: 'WhatsApp Share' },
  { key: 'photo_gallery',      label: 'Post-event Gallery' },
  { key: 'calendar_add',       label: 'Calendar (.ics)' },
  { key: 'prewedding_story',   label: 'Pre-Wedding Story' },
  { key: 'ai_photo_curation',  label: 'AI Photo Curation' },
  { key: 'guest_photo_upload', label: 'Guest Pre-event Upload' },
];

function FeaturePacksSection({ audience, http, toast }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(null);    // current pack being edited (or null)

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await http.get(`/api/super-admin/pricing/feature-packs?audience=${audience}`);
      setItems(res.data.items || []);
    } catch (e) { toast(e.message || 'Failed to load packs', 'err'); }
    setLoading(false);
  }, [audience, http, toast]);

  useEffect(() => { load(); }, [load]);

  const openNew = () => setEditing({
    audience,
    name: '',
    label: 'All-Features Pack',
    feature_keys: [],
    base_price: 0,
    discount_enabled: false,
    discount_price: null,
    is_active: true,
  });

  const save = async () => {
    try {
      if (editing.id) {
        await http.put(`/api/super-admin/pricing/feature-packs/${editing.id}`, editing);
      } else {
        await http.post('/api/super-admin/pricing/feature-packs', editing);
      }
      toast('Feature pack saved');
      setEditing(null);
      load();
    } catch (e) { toast(e.response?.data?.detail || 'Save failed', 'err'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this feature pack?')) return;
    try {
      await http.delete(`/api/super-admin/pricing/feature-packs/${id}`);
      toast('Pack deleted');
      load();
    } catch (e) { toast(e.response?.data?.detail || 'Delete failed', 'err'); }
  };

  if (loading) return <Skeleton />;

  return (
    <div data-testid="feature-packs-section">
      <SectionHeader
        title={`Feature Packs · ${audience === 'photographer' ? 'Photographers' : 'Couples'}`}
        blurb="Bundle multiple invitation features at a single discounted price. Example: 'All-Features Pack' = QR + RSVP + Gallery + Music + AI Curation for 25 credits (vs 40 credits when bought individually). Shown as an upsell on the Publish step."
      />

      {/* Pack list */}
      <div className="space-y-3 mb-4">
        {items.length === 0 ? (
          <Empty label="No feature packs yet for this audience. Click 'Add pack' to create one." />
        ) : items.map((p) => (
          <div
            key={p.id}
            className="p-4 rounded-lg border border-yellow-200/15 bg-black/30 flex flex-wrap items-center gap-4"
            data-testid={`feature-pack-row-${p.id}`}
          >
            <div className="flex-1 min-w-[200px]">
              <div className="text-yellow-200 font-medium">{p.label}</div>
              <div className="text-white/55 text-xs mt-0.5">{p.name} · {p.feature_keys.length} features</div>
              <div className="flex flex-wrap gap-1 mt-2">
                {p.feature_keys.slice(0, 6).map((k) => (
                  <span key={k} className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-200/10 text-yellow-200">{k}</span>
                ))}
                {p.feature_keys.length > 6 && <span className="text-[10px] text-white/40">+{p.feature_keys.length - 6}</span>}
              </div>
            </div>
            <div className="text-right">
              {p.discount_enabled && p.discount_price !== null && (
                <div className="text-white/40 line-through text-sm">{p.base_price}c</div>
              )}
              <div className="text-yellow-300 text-xl font-display">
                {p.discount_enabled && p.discount_price !== null ? p.discount_price : p.base_price}c
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setEditing(p)} className="text-xs px-3 py-1.5 rounded border border-yellow-200/30 text-yellow-200 hover:bg-yellow-200/10"
                data-testid={`feature-pack-edit-${p.id}`}>
                Edit
              </button>
              <button onClick={() => remove(p.id)} className="text-xs px-3 py-1.5 rounded border border-red-400/30 text-red-300 hover:bg-red-400/10"
                data-testid={`feature-pack-delete-${p.id}`}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      <button onClick={openNew} className="px-4 py-2 bg-yellow-300 text-black rounded font-medium"
        data-testid="feature-pack-add">
        + Add pack
      </button>

      {/* Edit modal — inline because we already use a side-drawer-less style */}
      {editing && (
        <div
          className="fixed inset-0 z-50 grid place-items-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={(e) => { if (e.target === e.currentTarget) setEditing(null); }}
        >
          <div className="bg-stone-900 border border-yellow-200/20 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto" data-testid="feature-pack-editor">
            <h3 className="text-yellow-200 text-lg mb-4">{editing.id ? 'Edit Feature Pack' : 'New Feature Pack'}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Internal name</div>
                <TextInput value={editing.name} onChange={(v) => setEditing({ ...editing, name: v })} width="w-full" testid="feature-pack-name" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Display label</div>
                <TextInput value={editing.label} onChange={(v) => setEditing({ ...editing, label: v })} width="w-full" testid="feature-pack-label" />
              </div>
            </div>

            <div className="text-[10px] uppercase tracking-wider text-white/55 mb-2">Features included</div>
            <div className="grid grid-cols-2 gap-2 mb-4 max-h-[300px] overflow-y-auto pr-2">
              {KNOWN_FEATURE_KEYS.map((f) => {
                const checked = editing.feature_keys.includes(f.key);
                return (
                  <label key={f.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer" data-testid={`feature-pack-checkbox-${f.key}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => {
                        const next = e.target.checked
                          ? [...editing.feature_keys, f.key]
                          : editing.feature_keys.filter((k) => k !== f.key);
                        setEditing({ ...editing, feature_keys: next });
                      }}
                    />
                    {f.label}
                  </label>
                );
              })}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Base price (credits)</div>
                <NumberInput value={editing.base_price} onChange={(v) => setEditing({ ...editing, base_price: Number(v ?? 0) })} testid="feature-pack-base-price" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Discount enabled</div>
                <ToggleSwitch on={editing.discount_enabled} onChange={(v) => setEditing({ ...editing, discount_enabled: v })} testid="feature-pack-discount-on" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/55 mb-1">Discount price</div>
                <NumberInput value={editing.discount_price ?? 0} onChange={(v) => setEditing({ ...editing, discount_price: Number(v ?? 0) })} testid="feature-pack-discount-price" disabled={!editing.discount_enabled} />
              </div>
            </div>

            <div className="flex items-center gap-2 mb-5">
              <ToggleSwitch on={editing.is_active} onChange={(v) => setEditing({ ...editing, is_active: v })} testid="feature-pack-active" />
              <span className="text-yellow-200 text-sm">{editing.is_active ? 'Active' : 'Hidden'}</span>
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={() => setEditing(null)} className="px-4 py-2 text-white/70 hover:text-white">Cancel</button>
              <button onClick={save} className="px-5 py-2 bg-yellow-300 text-black rounded font-medium" data-testid="feature-pack-save">
                <Save className="inline w-4 h-4 mr-1" /> Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function OptionRow({ row, onSave }) {
  const [local, setLocal] = useState(row);
  useEffect(() => { setLocal(row); }, [row]);
  const dirty = JSON.stringify(local) !== JSON.stringify(row);
  const testid = `option-${row.option_key}`;
  const effective = local.is_free ? 0 : (local.discount_enabled && local.discount_price != null ? local.discount_price : local.base_price);
  const showOld = !local.is_free && local.discount_enabled && local.discount_price != null;
  return (
    <div className={`flex flex-wrap items-center gap-4 p-4 rounded-lg border ${local.is_free ? 'border-emerald-400/30 bg-emerald-900/10' : 'border-yellow-200/15 bg-black/40'}`} data-testid={testid}>
      <div className="min-w-[260px] text-yellow-50 font-medium">{row.label}</div>
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wider text-white/60">Free</span>
        <ToggleSwitch on={!!local.is_free} onChange={(v) => setLocal({ ...local, is_free: v })} testid={`${testid}-free-toggle`} />
      </div>
      {!local.is_free && (
        <>
          <NumberInput value={local.base_price} onChange={(v) => setLocal({ ...local, base_price: v })} testid={`${testid}-base`} />
          <span className="text-white/50 text-sm">credits</span>
          <DiscountControls row={local} onPatch={(p) => setLocal({ ...local, ...p })} suffix=" cr" testid={testid} />
        </>
      )}
      <div className="ml-auto flex items-center gap-2">
        {local.is_free ? <span className="text-emerald-300 font-medium" data-testid={`${testid}-free-label`}>FREE</span>
          : <PriceCell value={effective} oldValue={showOld ? local.base_price : null} suffix=" cr" />
        }
        {dirty && <button onClick={() => onSave(local)} className="px-3 py-2 bg-emerald-600 text-white rounded text-sm" data-testid={`${testid}-save`}><Save className="inline w-4 h-4 mr-1" /> Save</button>}
      </div>
    </div>
  );
}

// -------------- Section header + helpers --------------
const SectionHeader = ({ title, blurb }) => (
  <div className="mb-5">
    <h2 className="text-xl font-serif text-yellow-200 mb-1 flex items-center gap-2"><Tag className="w-5 h-5" /> {title}</h2>
    <p className="text-sm text-white/60">{blurb}</p>
  </div>
);
const Skeleton = () => (
  <div className="space-y-3">
    {[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-lg bg-white/5 animate-pulse" />)}
  </div>
);
const Empty = ({ label }) => (
  <div className="p-8 rounded-lg border border-dashed border-yellow-200/15 text-center text-white/40">{label}</div>
);

// =============================================================
// MAIN PAGE
// =============================================================
export default function SuperAdminPricingHub() {
  const navigate = useNavigate();
  const http = useAuthAxios();
  const [audience, setAudience] = useState('photographer');
  const [subTab, setSubTab] = useState('credit_packs');
  const [toastMsg, setToastMsg] = useState('');
  const [toastKind, setToastKind] = useState('ok');

  const toast = useCallback((msg, kind = 'ok') => {
    setToastMsg(msg); setToastKind(kind);
    setTimeout(() => setToastMsg(''), 2600);
  }, []);

  useEffect(() => {
    // Verify token; redirect to login otherwise
    if (!localStorage.getItem('admin_token')) navigate('/super-admin/login');
  }, [navigate]);

  // Reset sub-tab when audience changes if current sub-tab not available
  useEffect(() => {
    const allowed = audience === 'photographer' ? PHOTOG_SUBTABS : NORMAL_SUBTABS;
    if (!allowed.find((t) => t.key === subTab)) setSubTab(allowed[0].key);
  }, [audience, subTab]);

  const subTabs = audience === 'photographer' ? PHOTOG_SUBTABS : NORMAL_SUBTABS;

  const renderSection = () => {
    const props = { audience, http, toast };
    switch (subTab) {
      case 'credit_packs': return <CreditPacksSection {...props} />;
      case 'subscription': return <SubscriptionSection http={http} toast={toast} />;
      case 'post_sub':     return <PostSubSection http={http} toast={toast} />;
      case 'tiers':        return <PhotographerTiersSection http={http} toast={toast} />;
      case 'feature_packs':return <FeaturePacksSection {...props} />;
      case 'themes':       return <ThemePricesSection {...props} />;
      case 'designs':      return <DesignPricesSection {...props} />;
      case 'options':      return <OptionsSection {...props} />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen text-yellow-50" style={{ background: 'radial-gradient(circle at top, #1a0f0a 0%, #0a0606 60%, #000 100%)' }} data-testid="super-admin-pricing-hub">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur border-b border-yellow-200/15" style={{ background: 'rgba(10,6,6,0.85)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/super-admin/dashboard')} className="text-yellow-200/70 hover:text-yellow-200 flex items-center gap-1 text-sm" data-testid="back-to-dashboard">
            <ChevronLeft className="w-4 h-4" /> Dashboard
          </button>
          <h1 className="text-xl md:text-2xl font-serif text-yellow-200">Pricing Hub</h1>
          <span className="text-xs uppercase tracking-wider text-white/40 ml-2">Audience-aware</span>
        </div>

        {/* Audience tabs */}
        <div className="max-w-7xl mx-auto px-6 pb-4 flex gap-2 flex-wrap">
          {AUDIENCES.map((a) => {
            const Icon = a.icon;
            const active = audience === a.key;
            return (
              <button
                key={a.key} onClick={() => setAudience(a.key)} data-testid={`audience-tab-${a.key}`}
                className={`px-4 py-2.5 rounded-lg border flex items-center gap-2 transition ${active
                  ? 'bg-yellow-300 text-black border-yellow-300 font-medium'
                  : 'bg-black/40 text-yellow-200 border-yellow-200/20 hover:border-yellow-200/40'}`}
              >
                <Icon className="w-4 h-4" />
                <span>{a.label}</span>
                <span className={`text-xs ${active ? 'text-black/60' : 'text-white/40'}`}>· {a.blurb}</span>
              </button>
            );
          })}
        </div>

        {/* Sub tabs */}
        <div className="max-w-7xl mx-auto px-6 pb-3 flex gap-2 flex-wrap border-t border-yellow-200/10 pt-3">
          {subTabs.map((t) => {
            const Icon = t.icon;
            const active = subTab === t.key;
            return (
              <button
                key={t.key} onClick={() => setSubTab(t.key)} data-testid={`subtab-${t.key}`}
                className={`px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5 ${active
                  ? 'bg-yellow-200/15 text-yellow-200 border border-yellow-200/30'
                  : 'text-yellow-200/60 hover:text-yellow-200'}`}
              >
                <Icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            );
          })}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {renderSection()}
      </main>

      <Toast msg={toastMsg} kind={toastKind} />
    </div>
  );
}
