import React, { useEffect, useState, useMemo, lazy, Suspense } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import {
  Users, UserPlus, Wallet, ShieldCheck, ShieldOff, Plus, Minus,
  Search, TrendingUp, FileText, Crown, X, Check, Eye, Coins, FilePlus2,
  IndianRupee, BarChart3, Trophy, Tag, Gift, Calendar, Layers,
  Ban, Mail, Phone, UserCheck, Heart,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import LuxuryShell from '@/components/luxury/LuxuryShell';
import MandalaLoader from '@/components/luxury/MandalaLoader';
import ScrollSection from '@/components/luxury/ScrollSection';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Area, AreaChart,
} from 'recharts';
import '@/styles/luxury.css';

// Pricing tab now redirects to the unified /super-admin/pricing hub.
// The legacy GuidedPricingFlow, SuperAdminPricingEditor, etc. have been
// consolidated into a single audience-aware page.

const PRICING_SUBTABS = [];

const PlansPricingHub = () => {
  const navigate = useNavigate();
  useEffect(() => { navigate('/super-admin/pricing'); }, [navigate]);
  return (
    <div data-testid="plans-pricing-hub" className="py-12 text-center">
      <p className="text-sm" style={{ color: 'rgba(245,236,215,0.6)' }}>
        Redirecting to the unified Pricing Hub…
      </p>
    </div>
  );
};

// Lazy-load SuperAdminGiftCodes only when its tab is opened
const SuperAdminGiftCodes = lazy(() => import('./SuperAdminGiftCodes'));
// 2026 — Universal categories
const EventCategoriesPanel = lazy(() => import('@/components/EventCategoriesPanel'));

// Embed the gift-codes admin component without its outer LuxuryShell.
// We just lazy-load SuperAdminGiftCodes inside an offset wrapper so its
// own back-button can take you back here.
const InlineGiftCodes = () => (
  <div className="-mx-1 -my-1" data-testid="inline-gift-codes-embed">
    <SuperAdminGiftCodes />
  </div>
);

const ExternalLink = ({ to, title, desc }) => (
  <div className="text-center py-12 px-6" data-testid="external-link-block">
    <h4 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>{title}</h4>
    <p className="text-sm mb-5 max-w-xl mx-auto" style={{ color: 'rgba(255,248,220,0.6)' }}>{desc}</p>
    <a
      href={to}
      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-[11px] tracking-[0.3em] uppercase font-medium"
      style={{ background: '#D4AF37', color: '#1A0F08' }}
    >
      Open editor →
    </a>
  </div>
);

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const fadeUp = {
  hidden: { opacity: 0, y: 16, filter: 'blur(6px)' },
  visible: (i = 0) => ({ opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.6, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] } }),
};

const LuxurySuperAdminDashboard = () => {
  const navigate = useNavigate();
  const { admin, loading: authLoading } = useAuth();
  const [tab, setTab] = useState('admins');
  const [admins, setAdmins] = useState([]);
  // ── Normal-user (couple / guest) management — July 2025
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [userStatusFilter, setUserStatusFilter] = useState('all');
  const [userDetailFor, setUserDetailFor] = useState(null);          // { user_id }
  const [userCreditModal, setUserCreditModal] = useState(null);      // { user }
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creditModal, setCreditModal] = useState(null);  // { admin, mode: 'add'|'deduct' }
  const [ledgerFor, setLedgerFor] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [analytics, setAnalytics] = useState({
    summary: null,
    series: [],
    leaderboard: [],
    range: 30,
  });
  const [analyticsBusy, setAnalyticsBusy] = useState(false);

  useEffect(() => {
    if (authLoading) return; // wait for auth to hydrate from localStorage
    if (!admin) { navigate('/super-admin/login'); return; }
    if (admin.role !== 'super_admin' && admin.role !== 'SUPER_ADMIN') { navigate('/admin/dashboard'); return; }
    fetchAdmins();
    fetchAuditLogs();
    fetchAnalytics(30);
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin, authLoading]);

  const fetchAnalytics = async (days = 30) => {
    setAnalyticsBusy(true);
    try {
      const [sum, ts, lb] = await Promise.all([
        axios.get(`${API_URL}/api/super-admin/v2/revenue/summary?days=${days}`).then(r => r.data).catch(() => null),
        axios.get(`${API_URL}/api/super-admin/v2/revenue/timeseries?days=${days}`).then(r => r.data).catch(() => ({ series: [] })),
        axios.get(`${API_URL}/api/super-admin/v2/leaderboard/photographers?by=revenue`).then(r => r.data).catch(() => ({ items: [] })),
      ]);
      setAnalytics({
        summary: sum,
        series: ts?.series || [],
        leaderboard: lb?.items || [],
        range: days,
      });
    } finally {
      setAnalyticsBusy(false);
    }
  };

  const fetchAdmins = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/super-admin/admins`);
      setAdmins(res.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  // ── Normal-user management (July 2025)
  const fetchUsers = async (q, statusFilter) => {
    setUsersLoading(true);
    try {
      const params = {};
      const qVal = (q !== undefined ? q : userSearch).trim();
      if (qVal) params.q = qVal;
      const sf = statusFilter !== undefined ? statusFilter : userStatusFilter;
      if (sf && sf !== 'all') params.status = sf;
      const res = await axios.get(`${API_URL}/api/super-admin/users`, { params });
      setUsers(res.data?.users || []);
    } catch (e) {
      console.error(e);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  const toggleUserStatus = async (u, nextStatus) => {
    const wanted = nextStatus || (u.status === 'active' ? 'suspended' : 'active');
    const reason = wanted === 'active'
      ? 'Re-activated by super-admin'
      : window.prompt(`Reason for setting status to "${wanted}" (optional):`, '') || '';
    try {
      await axios.put(`${API_URL}/api/super-admin/users/${u.user_id}/status`, {
        status: wanted, reason,
      });
      fetchUsers();
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update user status');
    }
  };

  const userStats = useMemo(() => {
    const total = users.length;
    const active = users.filter((u) => (u.status || 'active') === 'active').length;
    const suspended = users.filter((u) => u.status === 'suspended').length;
    const blocked = users.filter((u) => u.status === 'blocked').length;
    const totalCredits = users.reduce((s, u) => s + (u.credits || 0), 0);
    return { total, active, suspended, blocked, totalCredits };
  }, [users]);

  const fetchAuditLogs = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/audit-logs`);
      setAuditLogs(res.data || []);
    } catch (e) { /* optional */ }
  };

  const fetchLedger = async (a) => {
    try {
      const res = await axios.get(`${API_URL}/api/super-admin/credits/ledger/${a.id}`);
      setLedger(res.data || []);
      setLedgerFor(a);
    } catch (e) { setLedger([]); setLedgerFor(a); }
  };

  const stats = useMemo(() => {
    const photographers = admins.filter((a) => a.role === 'admin');
    const totalCredits = photographers.reduce((s, a) => s + (a.total_credits || 0), 0);
    const usedCredits  = photographers.reduce((s, a) => s + (a.used_credits || 0), 0);
    const activeCount  = photographers.filter((a) => a.status === 'active').length;
    return {
      photographers: photographers.length,
      active: activeCount,
      totalCredits, usedCredits,
      availableCredits: totalCredits - usedCredits,
    };
  }, [admins]);

  const filteredAdmins = useMemo(() => {
    const photographers = admins.filter((a) => a.role === 'admin');
    if (!search.trim()) return photographers;
    const q = search.toLowerCase();
    return photographers.filter((a) =>
      (a.email || '').toLowerCase().includes(q) ||
      (a.name || '').toLowerCase().includes(q)
    );
  }, [admins, search]);

  const toggleStatus = async (a) => {
    const newStatus = a.status === 'active' ? 'suspended' : 'active';
    try {
      await axios.put(`${API_URL}/api/super-admin/admins/${a.id}/status`, { status: newStatus });
      fetchAdmins();
    } catch (e) { alert(e.response?.data?.detail || 'Failed to update status'); }
  };

  return (
    <LuxuryShell
      eyebrow="◆ Platform Sovereignty"
      title="Super Admin Console"
      showCredits={false}
      testid="luxury-super-admin-dashboard"
    >
      <div className="px-6 md:px-10 py-10 max-w-[1400px] mx-auto">
        {/* Header */}
        <ScrollSection className="mb-12">
          <span className="lux-eyebrow block mb-4">◆ Platform Control</span>
          <h1 className="font-display text-[2.6rem] md:text-[4rem] leading-[1.02] tracking-tight" style={{ color: '#FFF8DC' }}>
            Sovereign <span className="text-gold italic font-script">command.</span>
          </h1>
          <p className="mt-4 max-w-xl text-[1.02rem]" style={{ color: 'rgba(255,248,220,0.65)' }}>
            Manage every photographer, credit, theme and feature flag from one console.
          </p>
        </ScrollSection>

        {/* Stat tiles */}
        <motion.div initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.05 } } }}
          className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Stat label="Photographers"    value={stats.photographers} icon={Users}      testid="stat-photographers" />
          <Stat label="Active Studios"   value={stats.active}        icon={ShieldCheck} testid="stat-active" />
          <Stat label="Normal Users"     value={userStats.total}     icon={Heart}      testid="stat-users-total" />
          <Stat label="Credits Issued"   value={stats.totalCredits}  icon={Wallet}     testid="stat-credits-issued" />
          <Stat label="Credits Consumed" value={stats.usedCredits}   icon={TrendingUp} testid="stat-credits-used" />
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { id: 'analytics',  label: 'Analytics' },
            { id: 'admins',     label: 'Photographers' },
            { id: 'users',      label: 'Normal Users' },
            { id: 'audit',      label: 'Audit Log' },
            { id: 'plans',      label: 'Plans & Pricing' },
            { id: 'events',     label: 'Event Categories' },
            // BUG 5 FIX: SuperAdminGiftCodes + InlineGiftCodes were
            // already imported/defined but had no tab entry, so the page
            // was effectively orphaned in the super-admin shell.
            { id: 'gift_codes', label: 'Gift Codes' },
          ].map((t) => (
            <button
              key={t.id} onClick={() => setTab(t.id)}
              className="px-5 py-2 rounded-full text-xs tracking-[0.25em] uppercase transition-all"
              style={tab === t.id
                ? { background: '#D4AF37', color: '#16110C', fontWeight: 600 }
                : { background: 'transparent', color: 'rgba(255,248,220,0.7)', border: '1px solid var(--lux-border)' }}
              data-testid={`tab-${t.id}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Action bar */}
        {tab === 'admins' && (
          <div className="lux-glass p-5 mb-6 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              <button onClick={() => navigate('/admin/profile/new?as=super-admin')} className="lux-btn" data-testid="sa-create-invitation-btn">
                <FilePlus2 className="w-4 h-4" /> Create Invitation
              </button>
              <button onClick={() => navigate('/super-admin/pricing')} className="lux-btn lux-btn-ghost" data-testid="pricing-hub-btn">
                <Coins className="w-4 h-4" /> Credits &amp; Pricing
              </button>
              <button onClick={() => navigate('/super-admin/expiry-tiers')} className="lux-btn lux-btn-ghost" data-testid="expiry-tiers-btn">
                <Coins className="w-4 h-4" /> Expiry Tiers
              </button>
            </div>
            <div className="relative w-full md:w-64">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgba(255,248,220,0.45)' }} />
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or email"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-transparent outline-none text-sm"
                style={{ color: '#FFF8DC', border: '1px solid var(--lux-border)' }}
                data-testid="search-admins"
              />
            </div>
          </div>
        )}

        {/* Tab content */}
        {tab === 'analytics' && (
          <AnalyticsPanel data={analytics} busy={analyticsBusy} onRange={fetchAnalytics} />
        )}

        {tab === 'admins' && (
          loading ? (
            <div className="py-20 grid place-items-center"><MandalaLoader /></div>
          ) : filteredAdmins.length === 0 ? (
            <div className="lux-glass p-10 text-center">
              <p className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>No photographers yet</p>
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>Create your first studio above.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="admins-list">
              {filteredAdmins.map((a, i) => (
                <motion.div key={a.id} variants={fadeUp} custom={i} initial="hidden" animate="visible"
                  className="lux-glass p-6"
                  data-testid={`admin-row-${a.id}`}
                >
                  <div className="flex items-start justify-between mb-3 gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-display text-xl mb-0.5 truncate" style={{ color: '#FFF8DC' }}>{a.name || a.email}</h3>
                      <p className="text-xs truncate" style={{ color: 'rgba(255,248,220,0.55)' }}>{a.email}</p>
                    </div>
                    <span className="text-[9px] tracking-[0.25em] uppercase px-2 py-1 rounded-full shrink-0"
                      style={a.status === 'active'
                        ? { background: 'rgba(138,154,91,0.16)', color: '#A5B97A', border: '1px solid rgba(138,154,91,0.35)' }
                        : { background: 'rgba(139,0,0,0.18)', color: '#FFB0A0', border: '1px solid rgba(139,0,0,0.4)' }}>
                      {a.status}
                    </span>
                  </div>

                  <div className="lux-hairline mb-4" />

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <Mini label="Total"     value={a.total_credits ?? 0} />
                    <Mini label="Used"      value={a.used_credits ?? 0} />
                    <Mini label="Available" value={(a.total_credits ?? 0) - (a.used_credits ?? 0)} highlight />
                  </div>

                  <div className="flex flex-wrap gap-2 text-xs">
                    <ActionBtn icon={Eye}      label="Details" onClick={() => navigate(`/super-admin/photographers/${a.id}`)} testid={`view-detail-${a.id}`} />
                    <ActionBtn icon={Plus}    label="Add"    onClick={() => setCreditModal({ admin: a, mode: 'add' })}    testid={`add-credits-${a.id}`} />
                    <ActionBtn icon={Minus}   label="Deduct" onClick={() => setCreditModal({ admin: a, mode: 'deduct' })} testid={`deduct-credits-${a.id}`} />
                    <ActionBtn icon={FileText} label="Ledger" onClick={() => fetchLedger(a)} testid={`ledger-${a.id}`} />
                    <ActionBtn icon={a.status === 'active' ? ShieldOff : ShieldCheck}
                      label={a.status === 'active' ? 'Suspend' : 'Activate'}
                      onClick={() => toggleStatus(a)} testid={`toggle-status-${a.id}`} danger={a.status === 'active'} />
                  </div>
                </motion.div>
              ))}
            </div>
          )
        )}

        {tab === 'users' && (
          <div data-testid="users-panel">
            {/* Action bar — search + status filter */}
            <div className="lux-glass p-5 mb-6 flex flex-wrap items-center justify-between gap-3">
              <div className="flex gap-2 flex-wrap" data-testid="users-status-filter">
                {[
                  { id: 'all',       label: 'All' },
                  { id: 'active',    label: 'Active' },
                  { id: 'suspended', label: 'Suspended' },
                  { id: 'blocked',   label: 'Blocked' },
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() => { setUserStatusFilter(s.id); fetchUsers(undefined, s.id); }}
                    className="px-4 py-1.5 rounded-full text-[10px] tracking-[0.25em] uppercase"
                    style={userStatusFilter === s.id
                      ? { background: '#D4AF37', color: '#16110C', fontWeight: 600 }
                      : { background: 'transparent', color: 'rgba(255,248,220,0.7)', border: '1px solid var(--lux-border)' }}
                    data-testid={`user-status-${s.id}`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => { e.preventDefault(); fetchUsers(userSearch); }}
                className="relative w-full md:w-72"
              >
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgba(255,248,220,0.45)' }} />
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search by name, email, phone"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-transparent outline-none text-sm"
                  style={{ color: '#FFF8DC', border: '1px solid var(--lux-border)' }}
                  data-testid="search-users"
                />
              </form>
            </div>

            {/* Mini user stat tiles */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <MiniStat label="Active"    value={userStats.active}       tone="ok"     testid="ustat-active" />
              <MiniStat label="Suspended" value={userStats.suspended}    tone="warn"   testid="ustat-suspended" />
              <MiniStat label="Blocked"   value={userStats.blocked}      tone="bad"    testid="ustat-blocked" />
              <MiniStat label="Credits in Wallets" value={userStats.totalCredits} tone="gold" testid="ustat-credits" />
            </div>

            {/* User list */}
            {usersLoading ? (
              <div className="py-20 grid place-items-center"><MandalaLoader /></div>
            ) : users.length === 0 ? (
              <div className="lux-glass p-10 text-center">
                <p className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>No users found</p>
                <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
                  Couples haven't signed up yet, or your filter is too narrow.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="users-list">
                {users.map((u, i) => (
                  <motion.div
                    key={u.user_id}
                    variants={fadeUp} custom={i} initial="hidden" animate="visible"
                    className="lux-glass p-6"
                    data-testid={`user-row-${u.user_id}`}
                  >
                    <div className="flex items-start justify-between mb-3 gap-3">
                      <div className="min-w-0 flex-1">
                        <h3 className="font-display text-xl mb-0.5 truncate" style={{ color: '#FFF8DC' }}>
                          {u.name || u.email}
                        </h3>
                        <p className="text-xs truncate flex items-center gap-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                          <Mail className="w-3 h-3 shrink-0" /> {u.email}
                        </p>
                        {u.phone && (
                          <p className="text-xs truncate mt-0.5 flex items-center gap-1.5" style={{ color: 'rgba(255,248,220,0.45)' }}>
                            <Phone className="w-3 h-3 shrink-0" /> {u.phone}
                          </p>
                        )}
                      </div>
                      <UserStatusPill status={u.status || 'active'} />
                    </div>

                    <div className="lux-hairline mb-4" />

                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <Mini label="Credits"     value={u.credits || 0} highlight />
                      <Mini label="Invitations" value={u.profiles_count || 0} />
                      <Mini label="Joined"      value={u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'} small />
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs">
                      <ActionBtn icon={Eye} label="Details"
                        onClick={() => setUserDetailFor(u)}
                        testid={`view-user-${u.user_id}`} />
                      <ActionBtn icon={Gift} label="Grant Credits"
                        onClick={() => setUserCreditModal({ user: u })}
                        testid={`grant-user-credits-${u.user_id}`} />
                      {(u.status || 'active') === 'active' && (
                        <>
                          <ActionBtn icon={ShieldOff} label="Suspend"
                            onClick={() => toggleUserStatus(u, 'suspended')}
                            danger testid={`suspend-user-${u.user_id}`} />
                          <ActionBtn icon={Ban} label="Block"
                            onClick={() => toggleUserStatus(u, 'blocked')}
                            danger testid={`block-user-${u.user_id}`} />
                        </>
                      )}
                      {(u.status === 'suspended' || u.status === 'blocked') && (
                        <ActionBtn icon={UserCheck} label="Re-activate"
                          onClick={() => toggleUserStatus(u, 'active')}
                          testid={`activate-user-${u.user_id}`} />
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'audit' && (
          <div className="lux-glass p-6">
            <h3 className="font-display text-2xl mb-4" style={{ color: '#FFF8DC' }}>Audit Trail</h3>
            {auditLogs.length === 0 ? (
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>No audit entries yet.</p>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2" data-testid="audit-logs-list">
                {auditLogs.slice(0, 100).map((log) => (
                  <div key={log.id} className="px-4 py-3 rounded-lg flex items-center justify-between gap-4"
                    style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }}>
                    <div className="min-w-0 flex-1">
                      <div className="font-heading text-sm truncate" style={{ color: '#FFF8DC' }}>{log.action || log.event}</div>
                      <div className="text-xs truncate" style={{ color: 'rgba(255,248,220,0.5)' }}>{log.details || log.description || ''}</div>
                    </div>
                    <div className="text-xs whitespace-nowrap" style={{ color: 'rgba(255,248,220,0.45)' }}>
                      {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'plans' && (
          <div className="lux-glass p-6 sm:p-8" data-testid="credit-packs-panel">
            <PlansPricingHub />
          </div>
        )}

        {tab === 'events' && (
          <Suspense fallback={<div className="lux-glass p-12 text-center" style={{ color: 'rgba(255,248,220,0.5)' }}>Loading…</div>}>
            <EventCategoriesPanel />
          </Suspense>
        )}

        {/* BUG 5 FIX: render the Gift Codes admin panel (lazy-loaded
            from SuperAdminGiftCodes via the InlineGiftCodes wrapper). */}
        {tab === 'gift_codes' && (
          <Suspense fallback={<div className="lux-glass p-12 text-center" style={{ color: 'rgba(255,248,220,0.5)' }}>Loading…</div>}>
            <InlineGiftCodes />
          </Suspense>
        )}
      </div>

      {showCreate && <CreateAdminModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchAdmins(); }} />}
      {creditModal && <CreditModal data={creditModal} onClose={() => setCreditModal(null)} onDone={() => { setCreditModal(null); fetchAdmins(); }} />}
      {ledgerFor && <LedgerModal admin={ledgerFor} ledger={ledger} onClose={() => { setLedgerFor(null); setLedger([]); }} />}
      {userDetailFor && (
        <UserDetailModal
          userRow={userDetailFor}
          onClose={() => setUserDetailFor(null)}
          onChange={() => fetchUsers()}
          onGrantCredits={(u) => { setUserDetailFor(null); setUserCreditModal({ user: u }); }}
          toggleStatus={toggleUserStatus}
        />
      )}
      {userCreditModal && (
        <UserCreditModal
          user={userCreditModal.user}
          onClose={() => setUserCreditModal(null)}
          onDone={() => { setUserCreditModal(null); fetchUsers(); }}
        />
      )}
    </LuxuryShell>
  );
};

const Stat = ({ label, value, icon: Icon, testid }) => (
  <motion.div variants={fadeUp} className="lux-glass p-5 flex flex-col gap-3" data-testid={testid}>
    <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
      <Icon className="w-3.5 h-3.5" style={{ color: '#D4AF37' }} /> {label}
    </div>
    <div className="font-display text-4xl text-gold leading-none">{value}</div>
  </motion.div>
);

const Mini = ({ label, value, highlight }) => (
  <div className="text-center">
    <div className="text-[9px] tracking-[0.25em] uppercase mb-1" style={{ color: 'rgba(255,248,220,0.5)' }}>{label}</div>
    <div className={`font-display text-xl ${highlight ? 'text-gold' : ''}`} style={!highlight ? { color: '#FFF8DC' } : {}}>{value}</div>
  </div>
);

const ActionBtn = ({ icon: Icon, label, onClick, testid, danger }) => (
  <button onClick={onClick} data-testid={testid}
    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all"
    style={{
      background: 'transparent',
      color: danger ? '#FFB0A0' : 'rgba(255,248,220,0.78)',
      border: `1px solid ${danger ? 'rgba(139,0,0,0.4)' : 'var(--lux-border)'}`,
    }}
  >
    <Icon className="w-3 h-3" /> {label}
  </button>
);

const ModalShell = ({ title, eyebrow, onClose, children, testid }) => (
  <motion.div
    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="fixed inset-0 z-[70] flex items-center justify-center p-4 luxe luxe-grain"
    style={{ background: 'rgba(8,5,3,0.7)', backdropFilter: 'blur(8px)' }}
    onClick={onClose}
    data-testid={testid}
  >
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
      onClick={(e) => e.stopPropagation()}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="lux-glass relative w-full max-w-lg max-h-[90vh] overflow-y-auto p-8"
      style={{ background: 'rgba(14,10,6,0.95)' }}
    >
      <button onClick={onClose} className="absolute top-4 right-4 w-9 h-9 rounded-full grid place-items-center"
        style={{ color: 'rgba(255,248,220,0.6)', border: '1px solid var(--lux-border)' }}>
        <X className="w-4 h-4" />
      </button>
      {eyebrow && <span className="lux-eyebrow block mb-3">◆ {eyebrow}</span>}
      <h2 className="font-display text-2xl md:text-3xl mb-6" style={{ color: '#FFF8DC' }}>{title}</h2>
      {children}
    </motion.div>
  </motion.div>
);

const labelStyle = { color: 'rgba(255,248,220,0.55)' };
const inputStyle = {
  width: '100%', padding: '0.85rem 1rem', background: 'transparent', color: '#FFF8DC',
  border: '1px solid var(--lux-border)', borderRadius: '0.5rem', outline: 'none',
  fontFamily: 'Manrope, sans-serif', fontSize: '0.92rem', caretColor: '#D4AF37',
};

const CreateAdminModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ email: '', password: '', name: '', initial_credits: 50 });
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);

  // Friendly error formatter — converts pydantic validation arrays into readable lines
  const friendlyError = (detail) => {
    if (!detail) return 'Failed to create photographer';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => {
        const field = (d.loc || []).slice(-1)[0] || 'field';
        return `${field}: ${d.msg || 'invalid'}`;
      }).join(' · ');
    }
    return JSON.stringify(detail);
  };

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    if ((form.password || '').length < 8) {
      setErr('Password must be at least 8 characters long');
      setBusy(false);
      return;
    }
    try {
      await axios.post(`${API_URL}/api/super-admin/admins`, {
        email: form.email, password: form.password, name: form.name,
        initial_credits: parseInt(form.initial_credits, 10) || 0,
      });
      onCreated();
    } catch (ex) { setErr(friendlyError(ex.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <ModalShell title="Create Photographer" eyebrow="New Studio" onClose={onClose} testid="create-admin-modal">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Studio Name"><input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="Mani's Studio" data-testid="new-admin-name" /></Field>
        <Field label="Email"><input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} style={inputStyle} placeholder="studio@example.com" data-testid="new-admin-email" /></Field>
        <Field label="Password (min 8 characters)"><input type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={inputStyle} placeholder="At least 8 characters" data-testid="new-admin-password" /></Field>
        <Field label="Initial Credits"><input type="number" min={0} required value={form.initial_credits} onChange={(e) => setForm({ ...form, initial_credits: e.target.value })} style={inputStyle} data-testid="new-admin-credits" /></Field>
        {err && <div className="text-sm px-3 py-2.5 rounded-md flex items-start gap-2" style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9', border: '1px solid rgba(139,0,0,0.4)' }} data-testid="create-admin-error">
          <X className="w-4 h-4 shrink-0 mt-0.5" /> {err}
        </div>}
        <button type="submit" disabled={busy} className="lux-btn w-full justify-center" data-testid="submit-create-admin">
          {busy ? 'Creating…' : 'Create Studio'} <Crown className="w-4 h-4" />
        </button>
      </form>
    </ModalShell>
  );
};

const CreditModal = ({ data, onClose, onDone }) => {
  const { admin, mode } = data;
  const [amount, setAmount] = useState(10); const [reason, setReason] = useState('');
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    const path = mode === 'add' ? 'credits/add' : 'credits/deduct';
    try {
      await axios.post(`${API_URL}/api/super-admin/${path}`, {
        admin_id: admin.id, amount: parseInt(amount, 10) || 0, reason: reason || `Manual ${mode}`,
      });
      onDone();
    } catch (e) { setErr(e.response?.data?.detail || 'Failed'); }
    finally { setBusy(false); }
  };

  return (
    <ModalShell
      title={`${mode === 'add' ? 'Add' : 'Deduct'} Credits`}
      eyebrow={admin.name || admin.email}
      onClose={onClose} testid="credit-modal"
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Amount"><input type="number" min={1} required value={amount} onChange={(e) => setAmount(e.target.value)} style={inputStyle} data-testid="credit-amount" /></Field>
        <Field label="Reason"><input type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Welcome bonus" style={inputStyle} data-testid="credit-reason" /></Field>
        {err && <div className="text-sm px-3 py-2 rounded-md" style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9' }}>{err}</div>}
        <button type="submit" disabled={busy} className="lux-btn w-full justify-center" data-testid="submit-credit-op">
          {busy ? 'Processing…' : `${mode === 'add' ? 'Add' : 'Deduct'} ${amount} credits`} <Check className="w-4 h-4" />
        </button>
      </form>
    </ModalShell>
  );
};

const LedgerModal = ({ admin, ledger, onClose }) => (
  <ModalShell title="Credit Ledger" eyebrow={admin.name || admin.email} onClose={onClose} testid="ledger-modal">
    {ledger.length === 0 ? (
      <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>No entries yet.</p>
    ) : (
      <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1" data-testid="ledger-entries">
        {ledger.map((entry) => {
          const positive = (entry.amount || 0) >= 0 && entry.transaction_type !== 'deduct' && entry.transaction_type !== 'consume';
          return (
            <div key={entry.id} className="px-4 py-3 rounded-lg flex items-center justify-between gap-4"
              style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }}>
              <div className="min-w-0 flex-1">
                <div className="font-heading text-sm truncate" style={{ color: '#FFF8DC' }}>
                  {entry.transaction_type || entry.action || 'transaction'}
                </div>
                <div className="text-xs truncate" style={{ color: 'rgba(255,248,220,0.5)' }}>{entry.reason || ''}</div>
              </div>
              <div className="font-display text-lg whitespace-nowrap"
                style={{ color: positive ? '#D4AF37' : '#FFB0A0' }}>
                {positive ? '+' : ''}{entry.amount}
              </div>
            </div>
          );
        })}
      </div>
    )}
  </ModalShell>
);

const Field = ({ label, children }) => (
  <label className="block">
    <span className="block text-[10px] tracking-[0.3em] uppercase mb-2" style={labelStyle}>{label}</span>
    {children}
  </label>
);

// ──────────────────────────────────────────────────────────────────
// Phase 8 — Analytics panel: summary tiles, revenue chart, leaderboard
// ──────────────────────────────────────────────────────────────────
const AnalyticsPanel = ({ data, busy, onRange }) => {
  const fmtINR = (n) => '₹' + (Number(n || 0)).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  const fmtNum = (n) => (Number(n || 0)).toLocaleString('en-IN');
  const summary = data.summary || { revenue_inr: 0, credits_sold: 0, purchases: 0, days: data.range };
  const rangeOpts = [
    { v: 7, l: '7d' },
    { v: 30, l: '30d' },
    { v: 90, l: '90d' },
    { v: 365, l: '1y' },
  ];

  const tooltipStyle = {
    background: 'rgba(20, 12, 4, 0.95)',
    border: '1px solid rgba(212,175,55,0.45)',
    borderRadius: 6,
    fontSize: 12,
    color: '#FFF8DC',
    padding: '8px 12px',
  };

  return (
    <div data-testid="analytics-panel">
      {/* Range selector */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-gold" />
          <h3 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>Revenue Analytics</h3>
        </div>
        <div className="lux-glass p-1 inline-flex gap-1" data-testid="analytics-range">
          {rangeOpts.map((r) => (
            <button
              key={r.v}
              onClick={() => onRange(r.v)}
              className="px-3 py-1.5 rounded text-[10px] tracking-[0.22em] uppercase"
              style={{
                background: data.range === r.v ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'transparent',
                color: data.range === r.v ? '#16110C' : 'rgba(255,248,220,0.7)',
              }}
              data-testid={`range-${r.v}`}
            >
              {r.l}
            </button>
          ))}
        </div>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="lux-glass p-5" data-testid="metric-revenue">
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
            <IndianRupee className="w-3.5 h-3.5 text-gold" /> Revenue
          </div>
          <div className="font-display text-4xl mt-2 text-gold">{fmtINR(summary.revenue_inr)}</div>
          <div className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.5)' }}>last {summary.days || data.range} days</div>
        </div>
        <div className="lux-glass p-5" data-testid="metric-credits-sold">
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
            <Coins className="w-3.5 h-3.5 text-gold" /> Credits sold
          </div>
          <div className="font-display text-4xl mt-2" style={{ color: '#FFF8DC' }}>{fmtNum(summary.credits_sold)}</div>
          <div className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.5)' }}>last {summary.days || data.range} days</div>
        </div>
        <div className="lux-glass p-5" data-testid="metric-purchases">
          <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
            <TrendingUp className="w-3.5 h-3.5 text-gold" /> Transactions
          </div>
          <div className="font-display text-4xl mt-2" style={{ color: '#FFF8DC' }}>{fmtNum(summary.purchases)}</div>
          <div className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.5)' }}>last {summary.days || data.range} days</div>
        </div>
      </div>

      {/* Revenue chart */}
      <div className="lux-glass p-5 mb-6" data-testid="revenue-chart">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-display text-lg" style={{ color: '#FFF8DC' }}>Daily Revenue (₹)</h4>
          {busy && <span className="text-[10px] tracking-[0.22em] uppercase text-gold animate-pulse">Loading…</span>}
        </div>
        {data.series.length === 0 ? (
          <div className="h-64 grid place-items-center text-sm" style={{ color: 'rgba(255,248,220,0.5)' }}>
            No revenue data yet — purchases will populate this chart.
          </div>
        ) : (
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={data.series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="rev-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#D4AF37" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#D4AF37" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,248,220,0.08)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'rgba(255,248,220,0.5)' }}
                  tickFormatter={(d) => { try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }); } catch { return d; } }}
                  axisLine={{ stroke: 'rgba(255,248,220,0.12)' }}
                  tickLine={false}
                  minTickGap={20}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'rgba(255,248,220,0.5)' }}
                  axisLine={{ stroke: 'rgba(255,248,220,0.12)' }}
                  tickLine={false}
                  tickFormatter={(n) => n >= 1000 ? `₹${(n / 1000).toFixed(1)}k` : `₹${n}`}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelFormatter={(d) => { try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); } catch { return d; } }}
                  formatter={(v, n) => [n === 'revenue_inr' ? fmtINR(v) : fmtNum(v), n === 'revenue_inr' ? 'Revenue' : n]}
                />
                <Area
                  type="monotone"
                  dataKey="revenue_inr"
                  stroke="#D4AF37"
                  strokeWidth={2}
                  fill="url(#rev-grad)"
                  isAnimationActive
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Credits sold chart */}
      <div className="lux-glass p-5 mb-6" data-testid="credits-chart">
        <h4 className="font-display text-lg mb-4" style={{ color: '#FFF8DC' }}>Daily Credits Sold</h4>
        {data.series.length === 0 ? (
          <div className="h-48 grid place-items-center text-sm" style={{ color: 'rgba(255,248,220,0.5)' }}>
            No data
          </div>
        ) : (
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={data.series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,248,220,0.08)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'rgba(255,248,220,0.5)' }}
                  tickFormatter={(d) => { try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }); } catch { return d; } }}
                  axisLine={{ stroke: 'rgba(255,248,220,0.12)' }} tickLine={false} minTickGap={20} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,248,220,0.5)' }}
                  axisLine={{ stroke: 'rgba(255,248,220,0.12)' }} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="credits" stroke="#FFF8DC" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Leaderboard */}
      <div className="lux-glass p-5" data-testid="leaderboard">
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="w-5 h-5 text-gold" />
          <h4 className="font-display text-lg" style={{ color: '#FFF8DC' }}>Top Photographers (by revenue)</h4>
        </div>
        {data.leaderboard.length === 0 ? (
          <div className="py-8 text-center text-sm" style={{ color: 'rgba(255,248,220,0.5)' }}>
            No photographers ranked yet.
          </div>
        ) : (
          <div className="space-y-2">
            {data.leaderboard.slice(0, 10).map((row, idx) => (
              <div
                key={row.admin_id}
                className="flex items-center justify-between px-4 py-3 rounded-md"
                style={{ background: 'rgba(255,248,220,0.04)', border: '1px solid var(--lux-border)' }}
                data-testid={`leaderboard-row-${row.admin_id}`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div
                    className="w-7 h-7 rounded-full grid place-items-center font-display text-sm"
                    style={{
                      background: idx === 0 ? 'linear-gradient(135deg,#D4AF37,#B8941F)' : 'rgba(255,248,220,0.08)',
                      color: idx === 0 ? '#16110C' : '#FFF8DC',
                    }}
                  >
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <div className="font-heading text-sm truncate" style={{ color: '#FFF8DC' }}>{row.name || '—'}</div>
                    <div className="text-[11px] truncate" style={{ color: 'rgba(255,248,220,0.5)' }}>{row.email || ''}</div>
                  </div>
                </div>
                <div className="font-display text-lg text-gold whitespace-nowrap">
                  {fmtINR(row.metric)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};


// ════════════════════════════════════════════════════════════════════
// NORMAL-USER MANAGEMENT — supporting components (July 2025)
// ════════════════════════════════════════════════════════════════════
const MiniStat = ({ label, value, tone = 'gold', testid }) => {
  const TONES = {
    gold: { c: '#D4AF37', bg: 'rgba(212,175,55,0.10)' },
    ok:   { c: '#7FD18E', bg: 'rgba(127,209,142,0.10)' },
    warn: { c: '#E8B86B', bg: 'rgba(232,184,107,0.10)' },
    bad:  { c: '#FFB0A0', bg: 'rgba(255,176,160,0.10)' },
  };
  const t = TONES[tone] || TONES.gold;
  return (
    <div className="lux-glass p-4 flex flex-col gap-1" data-testid={testid}
      style={{ background: t.bg }}>
      <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.6)' }}>{label}</div>
      <div className="font-display text-2xl" style={{ color: t.c }}>{value}</div>
    </div>
  );
};

const UserStatusPill = ({ status }) => {
  const map = {
    active:    { c: '#7FD18E', bg: 'rgba(127,209,142,0.15)', label: 'Active' },
    suspended: { c: '#E8B86B', bg: 'rgba(232,184,107,0.15)', label: 'Suspended' },
    blocked:   { c: '#FFB0A0', bg: 'rgba(255,176,160,0.15)', label: 'Blocked' },
  };
  const s = map[status] || map.active;
  return (
    <span
      className="px-2.5 py-0.5 rounded-full text-[10px] tracking-[0.25em] uppercase shrink-0"
      style={{ color: s.c, background: s.bg, border: `1px solid ${s.c}40` }}
      data-testid={`user-status-pill-${status}`}
    >
      {s.label}
    </span>
  );
};

const UserCreditModal = ({ user, onClose, onDone }) => {
  const [amount, setAmount] = useState(10);
  const [reason, setReason] = useState('Free credits gifted by MAJA');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      await axios.post(`${API_URL}/api/super-admin/users/${user.user_id}/credits`, {
        amount: parseInt(amount, 10) || 0,
        reason,
      });
      onDone();
    } catch (e2) {
      setErr(e2.response?.data?.detail || 'Failed to grant credits');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalShell title="Grant Free Credits" eyebrow={user.name || user.email} onClose={onClose} testid="user-credit-modal">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Amount">
          <input type="number" min={1} max={10000} required
            value={amount} onChange={(e) => setAmount(e.target.value)}
            style={inputStyle} data-testid="user-grant-amount" />
        </Field>
        <Field label="Reason (shown in user's wallet)">
          <input type="text" value={reason} onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Welcome gift, festival bonus, complaint resolution"
            style={inputStyle} data-testid="user-grant-reason" />
        </Field>
        {err && (
          <div className="text-sm px-3 py-2 rounded-md flex items-start gap-2"
            style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9', border: '1px solid rgba(139,0,0,0.4)' }}>
            <X className="w-4 h-4 shrink-0 mt-0.5" /> {err}
          </div>
        )}
        <button type="submit" disabled={busy} className="lux-btn w-full justify-center" data-testid="submit-user-grant">
          {busy ? 'Granting…' : `Gift ${amount} credits`} <Gift className="w-4 h-4" />
        </button>
      </form>
    </ModalShell>
  );
};

const UserDetailModal = ({ userRow, onClose, onChange, onGrantCredits, toggleStatus }) => {
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      setBusy(true); setErr('');
      try {
        const res = await axios.get(`${API_URL}/api/super-admin/users/${userRow.user_id}`);
        if (alive) setDetail(res.data);
      } catch (e) {
        if (alive) setErr(e.response?.data?.detail || 'Failed to load user');
      } finally {
        if (alive) setBusy(false);
      }
    })();
    return () => { alive = false; };
  }, [userRow.user_id]);

  const user = detail?.user || userRow;
  const profiles = detail?.profiles || [];
  const ledger   = detail?.credit_ledger || [];

  const handleStatus = async (next) => {
    await toggleStatus(user, next);
    // Refresh local view
    try {
      const res = await axios.get(`${API_URL}/api/super-admin/users/${userRow.user_id}`);
      setDetail(res.data);
    } catch (e) {/* ignore */}
    onChange?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 luxe luxe-grain"
      style={{ background: 'rgba(8,5,3,0.7)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
      data-testid="user-detail-modal"
    >
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="lux-glass relative w-full max-w-3xl max-h-[92vh] overflow-y-auto p-8"
        style={{ background: 'rgba(14,10,6,0.96)' }}
      >
        <button onClick={onClose} className="absolute top-4 right-4 w-9 h-9 rounded-full grid place-items-center"
          style={{ color: 'rgba(255,248,220,0.6)', border: '1px solid var(--lux-border)' }}>
          <X className="w-4 h-4" />
        </button>

        <span className="lux-eyebrow block mb-3">◆ User Profile</span>
        <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
          <div className="min-w-0">
            <h2 className="font-display text-3xl truncate" style={{ color: '#FFF8DC' }}>
              {user.name || user.email}
            </h2>
            <p className="text-sm mt-1" style={{ color: 'rgba(255,248,220,0.6)' }}>{user.email}</p>
            {user.phone && <p className="text-xs mt-0.5" style={{ color: 'rgba(255,248,220,0.45)' }}>📱 {user.phone}</p>}
          </div>
          <UserStatusPill status={user.status || 'active'} />
        </div>

        {busy && <p className="text-sm mt-4" style={{ color: 'rgba(255,248,220,0.55)' }}>Loading…</p>}
        {err && <p className="text-sm mt-4" style={{ color: '#FFB0A0' }}>{err}</p>}

        {!busy && !err && (
          <>
            <div className="lux-hairline my-5" />
            {/* Top stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <Mini label="Credits"    value={user.credits || 0} highlight />
              <Mini label="Invitations" value={profiles.length} />
              <Mini label="Auth"       value={user.auth_provider || 'email'} small />
              <Mini label="Joined"     value={user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'} small />
            </div>

            {/* Action row */}
            <div className="flex flex-wrap gap-2 mb-6">
              <button
                onClick={() => onGrantCredits(user)}
                className="lux-btn lux-btn-sm"
                data-testid="ud-grant-credits"
              >
                <Gift className="w-4 h-4" /> Grant Credits
              </button>
              {(user.status || 'active') === 'active' && (
                <>
                  <button onClick={() => handleStatus('suspended')}
                    className="px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase"
                    style={{ color: '#E8B86B', border: '1px solid rgba(232,184,107,0.4)' }}
                    data-testid="ud-suspend"
                  >
                    <ShieldOff className="w-3.5 h-3.5 inline -mt-0.5 mr-1.5" /> Suspend
                  </button>
                  <button onClick={() => handleStatus('blocked')}
                    className="px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase"
                    style={{ color: '#FFB0A0', border: '1px solid rgba(255,176,160,0.4)' }}
                    data-testid="ud-block"
                  >
                    <Ban className="w-3.5 h-3.5 inline -mt-0.5 mr-1.5" /> Block
                  </button>
                </>
              )}
              {(user.status === 'suspended' || user.status === 'blocked') && (
                <button onClick={() => handleStatus('active')}
                  className="px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase"
                  style={{ color: '#7FD18E', border: '1px solid rgba(127,209,142,0.4)' }}
                  data-testid="ud-reactivate"
                >
                  <UserCheck className="w-3.5 h-3.5 inline -mt-0.5 mr-1.5" /> Re-activate
                </button>
              )}
            </div>

            {/* Invitations */}
            <h3 className="font-display text-xl mb-3" style={{ color: '#FFF8DC' }}>
              Invitations ({profiles.length})
            </h3>
            {profiles.length === 0 ? (
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
                This user hasn&apos;t created any invitations yet.
              </p>
            ) : (
              <div className="space-y-2 mb-6" data-testid="ud-profile-list">
                {profiles.slice(0, 20).map((p) => (
                  <div key={p.id || p.profile_id || p.slug} className="px-4 py-3 rounded-lg flex items-center justify-between gap-3"
                    style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }}>
                    <div className="min-w-0 flex-1">
                      <div className="font-heading text-sm truncate" style={{ color: '#FFF8DC' }}>
                        {(p.bride_name || p.bride || '—')} &amp; {(p.groom_name || p.groom || '—')}
                      </div>
                      <div className="text-xs truncate" style={{ color: 'rgba(255,248,220,0.5)' }}>
                        {p.event_type || 'wedding'} · {p.venue || p.city || ''} · {p.event_date ? new Date(p.event_date).toLocaleDateString() : '—'}
                      </div>
                    </div>
                    {p.slug && (
                      <a href={`/invite/${p.slug}`} target="_blank" rel="noreferrer"
                        className="text-[10px] tracking-[0.22em] uppercase text-gold whitespace-nowrap">
                        Open ↗
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Credit ledger */}
            <h3 className="font-display text-xl mb-3" style={{ color: '#FFF8DC' }}>
              Recent Credit Activity
            </h3>
            {ledger.length === 0 ? (
              <p className="text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>No credit activity yet.</p>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1" data-testid="ud-ledger">
                {ledger.slice(0, 30).map((entry) => {
                  const positive = (entry.amount || 0) >= 0;
                  return (
                    <div key={entry.id} className="px-4 py-2.5 rounded-lg flex items-center justify-between gap-4"
                      style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }}>
                      <div className="min-w-0 flex-1">
                        <div className="font-heading text-sm truncate" style={{ color: '#FFF8DC' }}>
                          {entry.type || 'transaction'}
                        </div>
                        <div className="text-xs truncate" style={{ color: 'rgba(255,248,220,0.5)' }}>{entry.reason || ''}</div>
                      </div>
                      <div className="font-display text-base whitespace-nowrap"
                        style={{ color: positive ? '#D4AF37' : '#FFB0A0' }}>
                        {positive ? '+' : ''}{entry.amount}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </motion.div>
    </motion.div>
  );
};


export default LuxurySuperAdminDashboard;
