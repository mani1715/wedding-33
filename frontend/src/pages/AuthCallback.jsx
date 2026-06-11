import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Crown, Sparkles } from 'lucide-react';
import '@/styles/luxury.css';
import { markUserSessionActive, useUserAuth } from '@/context/UserAuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Handles `#session_id=...` returned by Emergent Google Auth.
 * Exchanges the session_id with the backend, which sets the user_session_token
 * cookie + creates/updates the users record, then routes the visitor home.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
const AuthCallback = () => {
  const navigate = useNavigate();
  const { refresh } = useUserAuth();
  const hasProcessed = useRef(false);
  const [status, setStatus] = useState('Verifying your sign-in…');

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const run = async () => {
      try {
        const hash = window.location.hash || '';
        const m = hash.match(/session_id=([^&]+)/);
        if (!m) {
          setStatus('Missing session — redirecting…');
          setTimeout(() => navigate('/'), 800);
          return;
        }
        const session_id = decodeURIComponent(m[1]);
        await axios.post(
          `${API_URL}/api/users/auth/session`,
          { session_id },
          { withCredentials: true },
        );
        // PHASE 10: flag the cookie session so UserAuthContext probes /me next mount.
        markUserSessionActive();
        // FEB 2026 FIX: pull fresh /me NOW so the homepage header re-renders
        // signed-in without forcing a manual refresh.
        try { await refresh(); } catch (_e) {}
        // BUG 18 FIX: restore the pre-OAuth return path (stashed by
        // loginWithGoogle in UserAuthContext) so users land back on the page
        // they tried to reach (e.g. /user/buy-design/…) instead of always
        // being dumped on the homepage.
        let nextRoute = '/';
        try {
          const saved = sessionStorage.getItem('oauth_return');
          if (saved && saved.startsWith('/') && !saved.startsWith('//')) {
            nextRoute = saved;
          }
          sessionStorage.removeItem('oauth_return');
        } catch (_e) { /* sessionStorage unavailable */ }
        // Drop the fragment then navigate
        window.history.replaceState({}, '', nextRoute);
        navigate(nextRoute, { replace: true });
      } catch (e) {
        setStatus('Sign-in failed. Returning home…');
        setTimeout(() => navigate('/'), 1200);
      }
    };
    run();
  }, [navigate, refresh]);

  return (
    <div className="luxe min-h-screen grid place-items-center px-6" data-testid="auth-callback">
      <div className="lux-glass p-10 md:p-12 text-center max-w-md w-full">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full mb-5"
          style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}>
          <Crown className="w-7 h-7" style={{ color: '#16110C' }} />
        </div>
        <h1 className="font-display text-3xl mb-2" style={{ color: '#FFF8DC' }}>
          One <span className="text-gold italic font-script">moment.</span>
        </h1>
        <p className="text-sm mb-4 flex items-center justify-center gap-2" style={{ color: 'rgba(255,248,220,0.7)' }}>
          <Sparkles className="w-4 h-4 animate-pulse" style={{ color: '#D4AF37' }} />
          {status}
        </p>
      </div>
    </div>
  );
};

export default AuthCallback;
