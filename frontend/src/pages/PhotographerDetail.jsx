import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';
import {
  ArrowLeft, ExternalLink, Calendar, MapPin, Users, Eye, Heart, Camera,
  IndianRupee, Coins, CheckCircle2, XCircle, Clock, Loader2, Sparkles, FilePlus2,
} from 'lucide-react';
import '@/styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] } }),
};

const PhotographerDetail = () => {
  const { adminId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('invitations');

  const getAuth = () => {
    const t = localStorage.getItem('admin_token') || localStorage.getItem('adminToken') || localStorage.getItem('token');
    return t ? { Authorization: `Bearer ${t}` } : {};
  };

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API_URL}/api/super-admin/photographers/${adminId}/detail`, { headers: getAuth() });
        setData(r.data);
      } catch (e) {
        // ignore
      } finally {
        setLoading(false);
      }
    })();
  }, [adminId]);

  if (loading) {
    return <div className="luxe min-h-screen grid place-items-center"><Loader2 className="w-7 h-7 animate-spin" style={{ color: '#D4AF37' }} /></div>;
  }
  if (!data) {
    return <div className="luxe min-h-screen grid place-items-center p-6">
      <div className="lux-glass p-10 text-center max-w-md">
        <p style={{ color: 'rgba(255,248,220,0.7)' }}>Photographer not found.</p>
        <button onClick={() => navigate(-1)} className="lux-btn mt-4">Back</button>
      </div>
    </div>;
  }

  const { admin, summary, profiles, credit_ledger, purchases } = data;

  return (
    <div className="luxe min-h-screen" data-testid="photographer-detail">
      <div className="px-4 md:px-12 py-8 md:py-10 max-w-[1400px] mx-auto">
        <button onClick={() => navigate('/super-admin/dashboard')} className="lux-btn lux-btn-ghost mb-6 inline-flex items-center gap-2" data-testid="pd-back">
          <ArrowLeft className="w-4 h-4" /> Super Admin
        </button>

        {/* Hero */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="lux-eyebrow block mb-3">◆ Photographer · Pin-to-pin details</span>
            <h1 className="font-display text-[2.2rem] md:text-[3.6rem] leading-[1.05]" style={{ color: '#FFF8DC' }}>
              {admin.name || admin.email.split('@')[0]} <span className="font-script italic text-gold">studio</span>
            </h1>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
              <span className="inline-flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-gold" /> {admin.email}</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-gold" /> Role: {admin.role}</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-gold" /> Status: {admin.status || 'active'}</span>
              {summary.last_login && (
                <span className="inline-flex items-center gap-1.5"><Clock className="w-3.5 h-3.5 text-gold" /> Last seen {new Date(summary.last_login).toLocaleString('en-IN')}</span>
              )}
            </div>
          </div>
          <button
            onClick={() => navigate(`/admin/profile/new?on_behalf_of=${adminId}`)}
            className="lux-btn inline-flex items-center gap-2"
            data-testid="pd-create-invitation"
            title="Create a new invitation under this photographer's account"
          >
            <FilePlus2 className="w-4 h-4" /> Create invitation
          </button>
        </motion.div>

        {/* Stat tiles */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={1}
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-10" data-testid="pd-stats">
          <Stat icon={<Eye className="w-4 h-4" />} label="Invitations" value={summary.profiles_total} accent={summary.profiles_published > 0} />
          <Stat icon={<CheckCircle2 className="w-4 h-4" />} label="Published" value={summary.profiles_published} />
          <Stat icon={<Heart className="w-4 h-4" />} label="RSVPs" value={summary.rsvps_total} />
          <Stat icon={<Sparkles className="w-4 h-4" />} label="Views" value={summary.views_total} />
          <Stat icon={<Coins className="w-4 h-4" />} label="Credits left" value={summary.credits_available} accent />
          <Stat icon={<IndianRupee className="w-4 h-4" />} label="Revenue" value={`₹${summary.revenue_inr.toLocaleString('en-IN')}`} accent />
        </motion.div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-6 border-b" style={{ borderColor: 'rgba(212,175,55,0.18)' }} data-testid="pd-tabs">
          <TabBtn label={`Invitations (${profiles.length})`} active={tab === 'invitations'} onClick={() => setTab('invitations')} testid="pd-tab-invitations" />
          <TabBtn label={`Credit ledger (${credit_ledger.length})`} active={tab === 'ledger'} onClick={() => setTab('ledger')} testid="pd-tab-ledger" />
          <TabBtn label={`Purchases (${purchases.length})`} active={tab === 'purchases'} onClick={() => setTab('purchases')} testid="pd-tab-purchases" />
        </div>

        {/* Content */}
        {tab === 'invitations' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="pd-invitations">
            {profiles.length === 0 ? (
              <div className="md:col-span-2 lux-glass p-10 text-center text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>
                No invitations created yet.
              </div>
            ) : profiles.map((p) => (
              <motion.div key={p.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="lux-glass p-5 md:p-6" data-testid={`pd-inv-${p.id}`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <div className="lux-eyebrow text-[9px] mb-1">◆ {p.event_type || 'wedding'} · {p.is_published ? 'Published' : (p.status || 'Draft')}</div>
                    <h3 className="font-display text-xl" style={{ color: '#FFF8DC' }}>
                      {p.groom_name} <span className="text-gold italic font-script">&</span> {p.bride_name}
                    </h3>
                  </div>
                  <a href={p.public_link} target="_blank" rel="noreferrer"
                    className="shrink-0 lux-btn lux-btn-ghost text-xs inline-flex items-center gap-1.5"
                    data-testid={`pd-open-${p.id}`}>
                    Open <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
                <div className="space-y-1 text-xs" style={{ color: 'rgba(255,248,220,0.65)' }}>
                  {p.event_date && (
                    <div className="inline-flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 text-gold" /> {new Date(p.event_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
                  )}
                  {p.venue && (
                    <div className="inline-flex items-center gap-1.5 ml-3"><MapPin className="w-3.5 h-3.5 text-gold" /> {p.venue}{p.city ? `, ${p.city}` : ''}</div>
                  )}
                </div>
                <div className="text-[10px] tracking-[0.25em] uppercase mt-3 mb-1.5" style={{ color: 'rgba(255,248,220,0.4)' }}>
                  Link · /invite/{p.slug}
                </div>
                <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t" style={{ borderColor: 'rgba(212,175,55,0.12)' }}>
                  <Metric label="Views" value={p.metrics.views} />
                  <Metric label="RSVPs" value={p.metrics.rsvps} />
                  <Metric label="Wishes" value={p.metrics.wishes} />
                  <Metric label="Photos" value={p.metrics.photos} />
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {tab === 'ledger' && (
          <div className="lux-glass overflow-hidden" data-testid="pd-ledger">
            {credit_ledger.length === 0 ? (
              <div className="p-10 text-center text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>No credit activity yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead style={{ background: 'rgba(212,175,55,0.06)' }}>
                  <tr style={{ color: 'rgba(255,248,220,0.55)' }}>
                    <Th>Date</Th><Th>Action</Th><Th align="right">Amount</Th><Th align="right">Balance</Th><Th>Reason</Th>
                  </tr>
                </thead>
                <tbody>
                  {credit_ledger.map((row) => (
                    <tr key={row.credit_id || row.id} style={{ borderTop: '1px solid rgba(212,175,55,0.08)' }} data-testid={`pd-ledger-row-${row.credit_id || row.id}`}>
                      <Td>{new Date(row.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</Td>
                      <Td>
                        <span className="px-2 py-0.5 rounded-full text-[10px] tracking-wider uppercase"
                          style={{ background: row.action_type === 'add' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                                   color: row.action_type === 'add' ? '#86efac' : '#fca5a5' }}>
                          {row.action_type}
                        </span>
                      </Td>
                      <Td align="right" style={{ color: row.action_type === 'add' ? '#86efac' : '#fca5a5', fontWeight: 600 }}>
                        {row.action_type === 'add' ? '+' : '−'}{row.amount}
                      </Td>
                      <Td align="right" style={{ color: '#D4AF37', fontWeight: 600 }}>{row.balance_after}</Td>
                      <Td style={{ color: 'rgba(255,248,220,0.7)' }}>{row.reason}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'purchases' && (
          <div className="lux-glass overflow-hidden" data-testid="pd-purchases">
            {purchases.length === 0 ? (
              <div className="p-10 text-center text-sm" style={{ color: 'rgba(255,248,220,0.55)' }}>No purchases yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead style={{ background: 'rgba(212,175,55,0.06)' }}>
                  <tr style={{ color: 'rgba(255,248,220,0.55)' }}>
                    <Th>Date</Th><Th>Pack</Th><Th align="right">Amount</Th><Th align="right">Credits</Th><Th>Status</Th><Th>Razorpay ID</Th>
                  </tr>
                </thead>
                <tbody>
                  {purchases.map((p) => (
                    <tr key={p.id} style={{ borderTop: '1px solid rgba(212,175,55,0.08)' }} data-testid={`pd-purchase-row-${p.id}`}>
                      <Td>{new Date(p.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</Td>
                      <Td style={{ color: '#FFF8DC' }}>{p.pack_label}</Td>
                      <Td align="right" style={{ color: '#D4AF37', fontWeight: 600 }}>₹{p.amount_inr.toLocaleString('en-IN')}</Td>
                      <Td align="right">+{p.credits}</Td>
                      <Td>
                        <span className="px-2 py-0.5 rounded-full text-[10px] tracking-wider uppercase"
                          style={{
                            background: p.credited ? 'rgba(34,197,94,0.15)' : 'rgba(255,248,220,0.08)',
                            color: p.credited ? '#86efac' : 'rgba(255,248,220,0.6)',
                          }}>
                          {p.credited ? 'Credited' : p.status}
                        </span>
                      </Td>
                      <Td className="font-mono text-[10px]" style={{ color: 'rgba(255,248,220,0.45)' }}>
                        {p.razorpay_payment_id || p.razorpay_order_id || '—'}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const Stat = ({ icon, label, value, accent }) => (
  <div className="lux-glass p-4" style={accent ? { border: '1px solid rgba(212,175,55,0.35)' } : {}}>
    <div className="flex items-center gap-1.5 text-[10px] tracking-[0.25em] uppercase mb-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
      <span className="text-gold">{icon}</span> {label}
    </div>
    <div className="font-display text-2xl md:text-3xl text-gold leading-none">{value}</div>
  </div>
);

const TabBtn = ({ label, active, onClick, testid }) => (
  <button onClick={onClick}
    className="px-4 py-3 text-sm tracking-wide relative transition-colors"
    style={{ color: active ? '#D4AF37' : 'rgba(255,248,220,0.55)', fontFamily: 'DM Sans, sans-serif' }}
    data-testid={testid}>
    {label}
    {active && <span className="absolute bottom-0 left-0 right-0 h-px" style={{ background: '#D4AF37' }} />}
  </button>
);

const Th = ({ children, align = 'left' }) => (
  <th className="px-4 py-3 text-[10px] tracking-[0.25em] uppercase font-medium" style={{ textAlign: align }}>{children}</th>
);
const Td = ({ children, align = 'left', style, ...rest }) => (
  <td className="px-4 py-3" style={{ textAlign: align, color: 'rgba(255,248,220,0.85)', ...style }} {...rest}>{children}</td>
);
const Metric = ({ label, value }) => (
  <div className="text-center">
    <div className="font-display text-lg text-gold leading-none">{value}</div>
    <div className="text-[9px] tracking-[0.2em] uppercase mt-1" style={{ color: 'rgba(255,248,220,0.45)' }}>{label}</div>
  </div>
);

export default PhotographerDetail;
