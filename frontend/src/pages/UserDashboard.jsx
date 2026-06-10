import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  Sparkles, Plus, Wallet, ArrowRight, ExternalLink, Calendar, MapPin, Copy, Check,
  Home as HomeIcon,
} from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function UserDashboard() {
  const navigate = useNavigate();
  const { user, loading, refresh, logout } = useUserAuth();
  const [profiles, setProfiles] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [busy, setBusy] = useState(true);
  const [copied, setCopied] = useState(null);

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate('/', { replace: true }); return; }
    let mounted = true;
    Promise.all([
      axios.get(`${API_URL}/api/users/profiles`, { withCredentials: true }),
      axios.get(`${API_URL}/api/users/credits/ledger`, { withCredentials: true }),
    ]).then(([p, l]) => {
      if (!mounted) return;
      setProfiles(p.data?.profiles || []);
      setLedger(l.data?.entries || []);
    }).catch(() => {}).finally(() => mounted && setBusy(false));
    return () => { mounted = false; };
  }, [loading, user, navigate]);

  const copyLink = (slug) => {
    const url = `${window.location.origin}/invite/${slug}`;
    navigator.clipboard?.writeText(url);
    setCopied(slug);
    setTimeout(() => setCopied(null), 1500);
  };

  if (loading || busy) {
    return (
      <div className="luxe min-h-screen grid place-items-center" data-testid="user-dashboard-loading">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  return (
    <div className="luxe min-h-screen relative px-5 md:px-12 py-8 md:py-12" data-testid="user-dashboard">
      {/* Prominent "Back to Home" button — fixed top-left for instant escape */}
      <button
        onClick={() => navigate('/')}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-[11px] tracking-[0.25em] uppercase transition-all hover:scale-[1.03] active:scale-95 mb-6"
        style={{
          background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(212,175,55,0.06))',
          color: '#FFE38A',
          border: '1px solid rgba(212,175,55,0.45)',
          boxShadow: '0 6px 18px rgba(0,0,0,0.25)',
        }}
        data-testid="user-back-to-home-btn"
      >
        <HomeIcon className="w-4 h-4" /> Back to Home
      </button>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
        <div>
          <span className="lux-eyebrow block mb-2">◆ My Studio</span>
          <h1 className="font-display text-3xl md:text-5xl" style={{ color: '#FFF8DC' }}>
            Welcome, <span className="font-script italic text-gold">{user?.name?.split(' ')[0] || 'friend'}.</span>
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {user?.email}{user?.phone ? ` · ${user.phone}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="lux-glass px-5 py-3 flex items-center gap-3" data-testid="user-balance">
            <Wallet className="w-5 h-5 text-gold" />
            <div>
              <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
                Balance
              </div>
              <div className="font-display text-2xl text-gold leading-none">{user?.credits ?? 0}</div>
            </div>
          </div>
          <button
            onClick={() => navigate('/user/profile')}
            className="lux-btn lux-btn-ghost"
            data-testid="user-profile-btn"
          >
            <Sparkles className="w-4 h-4" /> My Profile
          </button>
          <button
            onClick={() => navigate('/user/buy-credits')}
            className="lux-btn lux-btn-ghost"
            data-testid="user-buy-credits-btn"
          >
            <Wallet className="w-4 h-4" /> Buy Credits
          </button>
          <button
            onClick={() => navigate('/user/create-invitation')}
            className="lux-btn"
            data-testid="user-create-invitation-btn"
          >
            <Plus className="w-4 h-4" /> Create Invitation
          </button>
          <button
            onClick={() => { navigate('/'); setTimeout(() => { window.location.hash = '#themes'; }, 50); }}
            className="lux-btn lux-btn-ghost"
            data-testid="user-browse-themes-btn"
          >
            <Sparkles className="w-4 h-4" /> Browse Themes
          </button>
          <button
            onClick={async () => { await logout(); navigate('/'); }}
            className="text-[10px] tracking-[0.25em] uppercase px-3 py-1.5 rounded-full"
            style={{ border: '1px solid var(--lux-border)', color: 'rgba(255,248,220,0.65)' }}
            data-testid="user-logout-btn"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* My Invitations */}
      <div className="lux-hairline mb-8" />
      <h2 className="font-display text-2xl md:text-3xl mb-5" style={{ color: '#FFF8DC' }}>
        My Invitations <span className="text-gold text-base">· {profiles.length}</span>
      </h2>

      {profiles.length === 0 ? (
        <div className="lux-glass p-12 text-center" data-testid="user-empty-state">
          <Sparkles className="w-10 h-10 text-gold mx-auto mb-4" />
          <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>
            Your first <span className="italic font-script text-gold">memory</span> is just a click away.
          </h3>
          <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: 'rgba(255,248,220,0.65)' }}>
            Pick a cinematic design, fill in your story, and we'll craft your wedding invitation page.
            Each design uses a small number of credits.
          </p>
          <button
            onClick={() => navigate('/user/create-invitation')}
            className="lux-btn justify-center inline-flex"
            data-testid="user-empty-cta"
          >
            Create your first invitation <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="user-profiles-list">
          {profiles.map((p) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="lux-glass p-5"
              data-testid={`user-profile-card-${p.id}`}
            >
              <div className="text-[10px] tracking-[0.25em] uppercase mb-1" style={{ color: 'rgba(255,248,220,0.55)' }}>
                {p.event_type}
              </div>
              <h3 className="font-display text-xl mb-3 leading-tight" style={{ color: '#FFF8DC' }}>
                {p.bride_name} <span className="font-script italic text-gold">&amp;</span> {p.groom_name}
              </h3>
              <div className="space-y-1.5 mb-4 text-xs" style={{ color: 'rgba(255,248,220,0.7)' }}>
                <div className="flex items-center gap-2">
                  <Calendar className="w-3 h-3 text-gold" />
                  {p.event_date ? new Date(p.event_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                </div>
                {p.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3 h-3 text-gold" />
                    {p.venue}{p.city ? ` · ${p.city}` : ''}
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => window.open(p.invitation_link, '_blank')}
                  className="lux-btn lux-btn-ghost flex-1 justify-center !text-[10px]"
                  data-testid={`user-profile-view-${p.id}`}
                >
                  <ExternalLink className="w-3 h-3" /> View
                </button>
                <button
                  onClick={() => copyLink(p.slug)}
                  className="lux-btn flex-1 justify-center !text-[10px]"
                  data-testid={`user-profile-copy-${p.id}`}
                >
                  {copied === p.slug ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  {copied === p.slug ? 'Copied' : 'Copy Link'}
                </button>
              </div>
              {p.credits_charged != null && (
                <div className="mt-3 text-[10px] tracking-[0.2em] uppercase" style={{ color: 'rgba(255,248,220,0.4)' }}>
                  · {p.credits_charged} credit{p.credits_charged === 1 ? '' : 's'} used
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Recent activity */}
      {ledger.length > 0 && (
        <>
          <div className="lux-hairline mt-12 mb-8" />
          <h2 className="font-display text-xl mb-4" style={{ color: '#FFF8DC' }}>Recent Activity</h2>
          <div className="lux-glass overflow-hidden" data-testid="user-ledger">
            {ledger.slice(0, 10).map((e, i) => (
              <div
                key={e.id || i}
                className="px-5 py-3 flex items-center justify-between text-sm border-b last:border-b-0"
                style={{ borderColor: 'var(--lux-border)' }}
              >
                <div>
                  <div style={{ color: '#FFF8DC' }}>{e.reason || e.action}</div>
                  <div className="text-[10px] tracking-[0.2em] uppercase mt-0.5" style={{ color: 'rgba(255,248,220,0.45)' }}>
                    {e.created_at ? new Date(e.created_at).toLocaleString('en-IN') : ''}
                  </div>
                </div>
                <div className={`font-display text-lg ${e.amount > 0 ? 'text-gold' : ''}`} style={{ color: e.amount > 0 ? '#D4AF37' : '#FFB' }}>
                  {e.amount > 0 ? '+' : ''}{e.amount}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
