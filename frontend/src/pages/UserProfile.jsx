import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, ArrowLeft, Calendar, MapPin, Copy, Check, ExternalLink, Edit3, Trash2,
  Wallet, Coins, AlertTriangle, X, Save, ShoppingBag, Plus,
} from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const fieldStyle = {
  width: '100%', padding: '0.7rem 0.9rem', background: 'transparent', color: '#FFF8DC',
  border: '1px solid var(--lux-border)', borderRadius: '0.45rem', outline: 'none',
  caretColor: '#D4AF37', fontSize: '0.9rem',
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return iso; }
};
const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
};
const inputDate = (iso) => {
  if (!iso) return '';
  try { return new Date(iso).toISOString().slice(0, 10); } catch { return ''; }
};

export default function UserProfile() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { user, loading } = useUserAuth();
  const initialTab = params.get('tab') === 'history' ? 'history' : 'invitations';
  const [tab, setTab] = useState(initialTab);
  const [profiles, setProfiles] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [busy, setBusy] = useState(true);
  const [copied, setCopied] = useState(null);
  const [editing, setEditing] = useState(null);  // profile being edited
  const [deleting, setDeleting] = useState(null); // profile pending deletion
  const [addingFeatures, setAddingFeatures] = useState(null); // profile we're adding addons to
  const [addonCatalog, setAddonCatalog] = useState([]);
  const [toast, setToast] = useState('');

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    setParams((prev) => { const p = new URLSearchParams(prev); p.set('tab', tab); return p; }, { replace: true });
  }, [tab, setParams]);

  const loadAll = async () => {
    setBusy(true);
    try {
      const [p, h, l, a] = await Promise.all([
        axios.get(`${API_URL}/api/users/profiles`, { withCredentials: true }),
        axios.get(`${API_URL}/api/users/credits/purchases`, { withCredentials: true }).catch(() => ({ data: { purchases: [] } })),
        axios.get(`${API_URL}/api/users/credits/ledger`, { withCredentials: true }).catch(() => ({ data: { entries: [] } })),
        axios.get(`${API_URL}/api/public/addons`).catch(() => ({ data: { addons: [] } })),
      ]);
      setProfiles(p.data?.profiles || []);
      setPurchases(h.data?.purchases || []);
      setLedger(l.data?.entries || []);
      setAddonCatalog(a.data?.addons || []);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate('/', { replace: true }); return; }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user]);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2500); };

  const copyLink = (slug) => {
    const url = `${window.location.origin}/invite/${slug}`;
    navigator.clipboard?.writeText(url);
    setCopied(slug);
    setTimeout(() => setCopied(null), 1500);
  };

  const saveEdit = async (form) => {
    try {
      const payload = { ...form };
      if (payload.event_date) {
        payload.event_date = new Date(payload.event_date).toISOString();
      }
      const { data } = await axios.patch(
        `${API_URL}/api/users/profiles/${editing.id}`,
        payload,
        { withCredentials: true },
      );
      setProfiles((arr) => arr.map((p) => (p.id === editing.id ? { ...p, ...(data?.profile || {}) } : p)));
      setEditing(null);
      flash('Invitation updated');
    } catch (err) {
      flash(err?.response?.data?.detail || 'Update failed');
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await axios.delete(`${API_URL}/api/users/profiles/${deleting.id}`, { withCredentials: true });
      setProfiles((arr) => arr.filter((p) => p.id !== deleting.id));
      flash('Invitation deleted');
    } catch (err) {
      flash(err?.response?.data?.detail || 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  const buyAddon = async (profile, addon) => {
    try {
      const { data } = await axios.post(
        `${API_URL}/api/users/profiles/${profile.id}/buy-addon`,
        { addon_id: addon.id },
        { withCredentials: true },
      );
      if (data?.already_purchased) {
        flash(`${addon.label} already added`);
      } else {
        flash(`Added ${addon.label} · −${data?.credits_charged ?? 0} credits`);
      }
      // Update local profile add_ons + reload ledger
      setProfiles((arr) => arr.map((p) => p.id === profile.id ? (data?.profile || p) : p));
      loadAll();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.error === 'Insufficient credits') {
        flash(`Need ${detail.required} credits — balance is ${detail.balance}`);
      } else {
        flash(typeof detail === 'string' ? detail : 'Could not add feature');
      }
    }
  };

  // Merged purchase+spend history, sorted newest first
  const historyRows = useMemo(() => {
    const buys = (purchases || []).map((p) => ({
      _id: `buy-${p.id || p.purchase_id || Math.random()}`,
      kind: 'purchase',
      ts: p.created_at || p.purchased_at,
      label: `Bought ${p.credits || p.amount || '—'} credits`,
      delta: +(p.credits || 0),
      meta: p.razorpay_payment_id ? `Payment · ${p.razorpay_payment_id}` : (p.status || 'pending'),
    }));
    const spends = (ledger || []).map((e) => ({
      _id: `led-${e.id}`,
      kind: e.action === 'spend' ? 'spend' : 'credit',
      ts: e.created_at,
      label: e.reason || (e.action === 'spend' ? 'Credit spent' : 'Credit added'),
      delta: Number(e.amount || 0),
      meta: null,
    }));
    return [...buys, ...spends].sort((a, b) => new Date(b.ts || 0) - new Date(a.ts || 0));
  }, [purchases, ledger]);

  if (loading || busy) {
    return (
      <div className="luxe min-h-screen grid place-items-center" data-testid="user-profile-loading">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  return (
    <div className="luxe min-h-screen px-5 md:px-12 py-8 md:py-12" data-testid="user-profile">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <button
            onClick={() => navigate('/user/dashboard')}
            className="text-[10px] tracking-[0.25em] uppercase mb-3 inline-flex items-center gap-2 hover:opacity-80"
            style={{ color: 'rgba(255,248,220,0.6)' }}
            data-testid="profile-back-btn"
          >
            <ArrowLeft className="w-3 h-3" /> Back to studio
          </button>
          <span className="lux-eyebrow block mb-2">◆ My Profile</span>
          <h1 className="font-display text-3xl md:text-4xl" style={{ color: '#FFF8DC' }}>
            Welcome back, <span className="font-script italic text-gold">{user?.name?.split(' ')[0] || 'friend'}.</span>
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {user?.email}{user?.phone ? ` · ${user.phone}` : ''}
          </p>
        </div>
        <div className="lux-glass px-5 py-3 flex items-center gap-3" data-testid="profile-balance">
          <Wallet className="w-5 h-5 text-gold" />
          <div>
            <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>Balance</div>
            <div className="font-display text-2xl text-gold leading-none">{user?.credits ?? 0}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 lux-glass p-1.5 w-fit" data-testid="profile-tabs">
        {[
          { id: 'invitations', label: `My Invitations · ${profiles.length}` },
          { id: 'history', label: `Purchase History · ${historyRows.length}` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="px-4 py-2 rounded text-[10px] tracking-[0.22em] uppercase transition-all"
            style={{
              background: tab === t.id ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'transparent',
              color: tab === t.id ? '#16110C' : 'rgba(255,248,220,0.7)',
            }}
            data-testid={`tab-${t.id}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* My Invitations */}
      {tab === 'invitations' && (
        <div data-testid="invitations-tab">
          {profiles.length === 0 ? (
            <div className="lux-glass p-12 text-center" data-testid="invitations-empty">
              <Sparkles className="w-10 h-10 text-gold mx-auto mb-4" />
              <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>
                No invitations yet.
              </h3>
              <p className="text-sm mb-6" style={{ color: 'rgba(255,248,220,0.65)' }}>
                Create your first wedding invitation in minutes.
              </p>
              <button
                onClick={() => navigate('/user/create-invitation')}
                className="lux-btn inline-flex"
                data-testid="invitations-empty-cta"
              >
                Create an invitation
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="invitations-grid">
              {profiles.map((p) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="lux-glass p-5 flex flex-col"
                  data-testid={`invitation-card-${p.id}`}
                >
                  <div className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: 'rgba(255,248,220,0.55)' }}>
                    {p.event_type}
                  </div>
                  <h3 className="font-display text-xl leading-tight mb-2" style={{ color: '#FFF8DC' }}>
                    {p.groom_name} <span className="text-gold font-script italic">&</span> {p.bride_name}
                  </h3>
                  <div className="text-xs mb-1 inline-flex items-center gap-1.5" style={{ color: 'rgba(255,248,220,0.7)' }}>
                    <Calendar className="w-3 h-3 text-gold" /> {fmtDate(p.event_date)}
                  </div>
                  {(p.venue || p.city) && (
                    <div className="text-xs mb-3 inline-flex items-center gap-1.5" style={{ color: 'rgba(255,248,220,0.7)' }}>
                      <MapPin className="w-3 h-3 text-gold" /> {[p.venue, p.city].filter(Boolean).join(' · ')}
                    </div>
                  )}
                  <div className="text-[10px] mt-auto mb-3" style={{ color: 'rgba(255,248,220,0.4)' }}>
                    Created {fmtDateTime(p.created_at)} · {p.credits_charged || 1} credits
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => window.open(p.invitation_link, '_blank')}
                      className="lux-btn lux-btn-ghost text-xs flex-1 justify-center"
                      data-testid={`invitation-view-${p.id}`}
                    >
                      <ExternalLink className="w-3 h-3" /> View
                    </button>
                    <button
                      onClick={() => copyLink(p.slug)}
                      className="lux-btn lux-btn-ghost text-xs flex-1 justify-center"
                      data-testid={`invitation-copy-${p.id}`}
                    >
                      {copied === p.slug ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
                    </button>
                    <button
                      onClick={() => setEditing(p)}
                      className="lux-btn lux-btn-ghost text-xs flex-1 justify-center"
                      data-testid={`invitation-edit-${p.id}`}
                    >
                      <Edit3 className="w-3 h-3" /> Edit
                    </button>
                    <button
                      onClick={() => setAddingFeatures(p)}
                      className="lux-btn lux-btn-ghost text-xs flex-1 justify-center"
                      style={{ borderColor: 'rgba(212,175,55,0.55)', color: '#E8C766' }}
                      data-testid={`invitation-add-features-${p.id}`}
                    >
                      <Plus className="w-3 h-3" /> Add features
                    </button>
                    <button
                      onClick={() => setDeleting(p)}
                      className="lux-btn lux-btn-ghost text-xs flex-1 justify-center"
                      style={{ borderColor: 'rgba(255,80,80,0.45)', color: '#FFB47C' }}
                      data-testid={`invitation-delete-${p.id}`}
                    >
                      <Trash2 className="w-3 h-3" /> Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Purchase History */}
      {tab === 'history' && (
        <div data-testid="history-tab">
          {historyRows.length === 0 ? (
            <div className="lux-glass p-12 text-center" data-testid="history-empty">
              <ShoppingBag className="w-10 h-10 text-gold mx-auto mb-4" />
              <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>
                No history yet.
              </h3>
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.65)' }}>
                Your credit purchases and spends will appear here.
              </p>
            </div>
          ) : (
            <div className="lux-glass overflow-hidden" data-testid="history-table">
              <div className="grid grid-cols-12 px-5 py-3 text-[10px] tracking-[0.22em] uppercase"
                style={{ color: 'rgba(255,248,220,0.55)', borderBottom: '1px solid var(--lux-border)' }}>
                <div className="col-span-5">Activity</div>
                <div className="col-span-3">When</div>
                <div className="col-span-2">Status</div>
                <div className="col-span-2 text-right">Credits</div>
              </div>
              {historyRows.map((r) => {
                const positive = r.delta > 0;
                return (
                  <div
                    key={r._id}
                    className="grid grid-cols-12 px-5 py-3.5 text-sm items-center"
                    style={{ color: 'rgba(255,248,220,0.85)', borderBottom: '1px solid rgba(255,248,220,0.06)' }}
                    data-testid={`history-row-${r._id}`}
                  >
                    <div className="col-span-5 flex items-center gap-2">
                      {r.kind === 'purchase'
                        ? <ShoppingBag className="w-4 h-4 text-gold shrink-0" />
                        : <Coins className="w-4 h-4 text-gold shrink-0" />}
                      <span className="truncate">{r.label}</span>
                    </div>
                    <div className="col-span-3 text-[11px]" style={{ color: 'rgba(255,248,220,0.6)' }}>
                      {fmtDateTime(r.ts)}
                    </div>
                    <div className="col-span-2 text-[10px] tracking-[0.18em] uppercase" style={{ color: 'rgba(255,248,220,0.5)' }}>
                      {r.kind === 'purchase' ? (r.meta || '—') : r.kind}
                    </div>
                    <div className="col-span-2 text-right font-display text-lg"
                      style={{ color: positive ? '#D4AF37' : '#FFB47C' }}>
                      {positive ? '+' : ''}{r.delta}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Edit Modal */}
      <AnimatePresence>
        {editing && (
          <EditInvitationModal
            profile={editing}
            onClose={() => setEditing(null)}
            onSave={saveEdit}
          />
        )}
      </AnimatePresence>

      {/* Delete Confirmation */}
      <AnimatePresence>
        {addingFeatures && (
          <AddFeaturesModal
            profile={addingFeatures}
            addonCatalog={addonCatalog}
            balance={user?.credits ?? 0}
            onClose={() => setAddingFeatures(null)}
            onBuy={async (addon) => { await buyAddon(addingFeatures, addon); }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {deleting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleting(null)}
            className="fixed inset-0 z-50 grid place-items-center p-4"
            style={{ background: 'rgba(10,6,2,0.85)', backdropFilter: 'blur(8px)' }}
            data-testid="delete-confirm-modal"
          >
            <motion.div
              initial={{ scale: 0.95, y: 10 }}
              animate={{ scale: 1, y: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="lux-glass p-7 max-w-md w-full"
            >
              <AlertTriangle className="w-9 h-9 mx-auto mb-3" style={{ color: '#FFB47C' }} />
              <h3 className="font-display text-xl text-center mb-2" style={{ color: '#FFF8DC' }}>
                Delete this invitation?
              </h3>
              <p className="text-sm text-center mb-5" style={{ color: 'rgba(255,248,220,0.7)' }}>
                <span className="font-display text-gold">{deleting.groom_name} & {deleting.bride_name}</span><br />
                This is permanent. Credits already spent cannot be refunded.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleting(null)}
                  className="lux-btn lux-btn-ghost flex-1 justify-center"
                  data-testid="delete-cancel"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="lux-btn flex-1 justify-center"
                  style={{ background: 'linear-gradient(135deg,#8B0000,#5a0000)', color: '#FFD7C9' }}
                  data-testid="delete-confirm"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 lux-glass px-5 py-3 text-sm z-50"
            style={{ color: '#FFF8DC' }}
            data-testid="profile-toast"
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EditInvitationModal({ profile, onClose, onSave }) {
  const [form, setForm] = useState({
    groom_name: profile.groom_name || '',
    bride_name: profile.bride_name || '',
    event_date: inputDate(profile.event_date),
    venue: profile.venue || '',
    city: profile.city || '',
    invitation_message: profile.invitation_message || '',
  });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e?.preventDefault?.();
    setSaving(true);
    await onSave(form);
    setSaving(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 grid place-items-center p-4"
      style={{ background: 'rgba(10,6,2,0.85)', backdropFilter: 'blur(8px)' }}
      data-testid="edit-modal"
    >
      <motion.form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.95, y: 10 }}
        animate={{ scale: 1, y: 0 }}
        className="lux-glass p-7 max-w-2xl w-full relative max-h-[90vh] overflow-y-auto"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full hover:opacity-80"
          style={{ background: 'rgba(255,248,220,0.08)', border: '1px solid var(--lux-border)' }}
          data-testid="edit-modal-close"
        >
          <X className="w-4 h-4" style={{ color: '#FFF8DC' }} />
        </button>
        <span className="lux-eyebrow block mb-2">◆ Edit Invitation</span>
        <h3 className="font-display text-2xl mb-5" style={{ color: '#FFF8DC' }}>
          Update <span className="italic font-script text-gold">your details.</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <label>
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>Groom's name</span>
            <input style={fieldStyle} value={form.groom_name} onChange={set('groom_name')} data-testid="edit-groom-name" />
          </label>
          <label>
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>Bride's name</span>
            <input style={fieldStyle} value={form.bride_name} onChange={set('bride_name')} data-testid="edit-bride-name" />
          </label>
          <label>
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>Event date</span>
            <input type="date" style={fieldStyle} value={form.event_date} onChange={set('event_date')} data-testid="edit-event-date" />
          </label>
          <label>
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>City</span>
            <input style={fieldStyle} value={form.city} onChange={set('city')} data-testid="edit-city" />
          </label>
          <label className="sm:col-span-2">
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>Venue</span>
            <input style={fieldStyle} value={form.venue} onChange={set('venue')} data-testid="edit-venue" />
          </label>
          <label className="sm:col-span-2">
            <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>Invitation message</span>
            <textarea rows={3} style={fieldStyle} value={form.invitation_message} onChange={set('invitation_message')} data-testid="edit-message" />
          </label>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="lux-btn lux-btn-ghost flex-1 justify-center"
            data-testid="edit-cancel"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="lux-btn flex-1 justify-center"
            data-testid="edit-save"
          >
            <Save className="w-4 h-4" /> {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </motion.form>
    </motion.div>
  );
}


function AddFeaturesModal({ profile, addonCatalog, balance, onClose, onBuy }) {
  const ownedIds = new Set((profile.add_ons || []).map((a) => a.id));
  const [busyId, setBusyId] = useState(null);

  const handleBuy = async (addon) => {
    setBusyId(addon.id);
    await onBuy(addon);
    setBusyId(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 grid place-items-center p-4"
      style={{ background: 'rgba(10,6,2,0.85)', backdropFilter: 'blur(8px)' }}
      data-testid="add-features-modal"
    >
      <motion.div
        onClick={(e) => e.stopPropagation()}
        initial={{ scale: 0.95, y: 10 }}
        animate={{ scale: 1, y: 0 }}
        className="lux-glass p-7 max-w-3xl w-full relative max-h-[90vh] overflow-y-auto"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full hover:opacity-80"
          style={{ background: 'rgba(255,248,220,0.08)', border: '1px solid var(--lux-border)' }}
          data-testid="add-features-close"
        >
          <X className="w-4 h-4" style={{ color: '#FFF8DC' }} />
        </button>
        <span className="lux-eyebrow block mb-2">◆ Add features</span>
        <h3 className="font-display text-2xl mb-1" style={{ color: '#FFF8DC' }}>
          Upgrade <span className="italic font-script text-gold">{profile.groom_name} &amp; {profile.bride_name}</span>
        </h3>
        <p className="text-xs mb-6" style={{ color: 'rgba(255,248,220,0.6)' }}>
          Each add-on charges credits from your wallet. Balance: <span className="text-gold">{balance}</span>
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="add-features-grid">
          {addonCatalog.map((a) => {
            const owned = ownedIds.has(a.id);
            const cantAfford = !owned && balance < (a.credits || 0);
            return (
              <div
                key={a.id}
                className="lux-glass p-4 flex flex-col"
                style={{ borderColor: owned ? '#D4AF37' : 'var(--lux-border)' }}
                data-testid={`add-feature-row-${a.id}`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="font-display text-base" style={{ color: '#FFF8DC' }}>{a.label}</h4>
                  <span
                    className="px-2 py-1 rounded-full text-[10px] tracking-[0.15em] uppercase inline-flex items-center gap-1 shrink-0"
                    style={{
                      background: owned ? 'rgba(212,175,55,0.18)' : 'rgba(255,248,220,0.06)',
                      color: owned ? '#E8C766' : 'rgba(255,248,220,0.7)',
                    }}
                  >
                    <Coins className="w-3 h-3" /> {a.credits}
                  </span>
                </div>
                <p className="text-[11px] mb-3 flex-1" style={{ color: 'rgba(255,248,220,0.6)' }}>{a.description}</p>
                {owned ? (
                  <div className="inline-flex items-center justify-center gap-1.5 text-[11px] tracking-[0.15em] uppercase text-gold" data-testid={`add-feature-owned-${a.id}`}>
                    <Check className="w-3.5 h-3.5" /> Already added
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleBuy(a)}
                    disabled={busyId === a.id || cantAfford}
                    className="lux-btn justify-center text-xs"
                    data-testid={`add-feature-buy-${a.id}`}
                  >
                    {busyId === a.id ? 'Adding…' : cantAfford ? 'Not enough credits' : <>Add · {a.credits} credit{a.credits === 1 ? '' : 's'}</>}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
