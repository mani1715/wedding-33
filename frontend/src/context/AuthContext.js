import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import axios from 'axios';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

const AuthContext = createContext();

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export const AuthProvider = ({ children }) => {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('admin_token'));

  // Apply current legacy token to axios on mount + when it changes
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const fetchAdminInfo = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/me`);
      setAdmin(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch admin info:', error);
      // Don't auto-logout here — caller decides. Just return null.
      return null;
    }
  }, []);

  // Bridge: when a Supabase session exists (e.g. user signed in via supabase-js
  // — email/password, magic link, Google later), exchange it for the legacy
  // admin token via /api/auth/me-supabase so the rest of the app keeps working.
  const hydrateFromSupabase = useCallback(async (sbSession) => {
    if (!sbSession?.access_token) return null;
    try {
      const { data } = await axios.get(`${API_URL}/api/auth/me-supabase`, {
        headers: { Authorization: `Bearer ${sbSession.access_token}` },
      });
      // Drop the legacy app token into localStorage so existing axios calls work
      if (data?.access_token) {
        localStorage.setItem('admin_token', data.access_token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        setToken(data.access_token);
      }
      if (data?.admin) setAdmin(data.admin);
      return data?.admin || null;
    } catch (err) {
      const detail = err?.response?.data?.detail;
      // 404 + error=no_admin_record → caller should send user to a "complete profile" form.
      if (err?.response?.status === 404 && detail?.error === 'no_admin_record') {
        return { needsSignup: true, supabaseUser: { id: detail.supabase_user_id, email: detail.email } };
      }
      console.warn('Supabase → backend bridge failed:', err?.response?.data || err.message);
      return null;
    }
  }, []);

  // Boot: prefer Supabase session, fall back to legacy token
  useEffect(() => {
    let mounted = true;

    const boot = async () => {
      // 1) Try Supabase first
      if (isSupabaseConfigured) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session && mounted) {
            const result = await hydrateFromSupabase(session);
            if (result && !result.needsSignup) {
              setLoading(false);
              return;
            }
          }
        } catch (e) {
          console.warn('supabase.getSession failed:', e?.message);
        }
      }

      // 2) Fall back to legacy admin_token
      const legacy = localStorage.getItem('admin_token');
      if (legacy) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${legacy}`;
        const info = await fetchAdminInfo();
        if (!info) {
          // Token is stale — clear it
          localStorage.removeItem('admin_token');
          delete axios.defaults.headers.common['Authorization'];
          setToken(null);
        }
      }
      if (mounted) setLoading(false);
    };

    boot();

    // 3) React to Supabase auth events (sign in via magic link, OAuth, etc.)
    let sub;
    if (isSupabaseConfigured) {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (!mounted) return;
        if (event === 'SIGNED_IN' && session) {
          await hydrateFromSupabase(session);
        } else if (event === 'SIGNED_OUT') {
          // Only clear if our current admin came from supabase (has supabase_user_id)
          if (admin?.supabase_user_id) {
            localStorage.removeItem('admin_token');
            delete axios.defaults.headers.common['Authorization'];
            setToken(null);
            setAdmin(null);
          }
        }
      });
      sub = data?.subscription;
    }

    return () => {
      mounted = false;
      try { sub?.unsubscribe?.(); } catch (_) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  //   Public API
  // ---------------------------------------------------------------------------

  // Legacy email/password login (FastAPI). Still the default path for the
  // existing UI — Supabase login lives on the dedicated /auth pages.
  const login = async (emailOrUsername, password) => {
    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        username_or_email: emailOrUsername,
        password,
      });
      const { access_token, admin: nextAdmin } = response.data;
      localStorage.setItem('admin_token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setToken(access_token);
      setAdmin(nextAdmin);
      return { success: true, admin: nextAdmin };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      };
    }
  };

  // Supabase email/password sign-in → bridge to admin record
  const loginWithSupabasePassword = async (email, password) => {
    if (!isSupabaseConfigured) {
      return { success: false, error: 'Supabase is not configured' };
    }
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) return { success: false, error: error.message };
      const result = await hydrateFromSupabase(data.session);
      if (result?.needsSignup) {
        return {
          success: false,
          needsSignup: true,
          supabaseUser: result.supabaseUser,
          error: 'No admin profile linked to this account. Complete signup first.',
        };
      }
      return { success: true, admin: result };
    } catch (err) {
      return { success: false, error: err.message || 'Supabase login failed' };
    }
  };

  // Send a magic link (passwordless email) — Supabase
  const sendMagicLink = async (email, redirectTo) => {
    if (!isSupabaseConfigured) return { success: false, error: 'Supabase is not configured' };
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: redirectTo || `${window.location.origin}/admin/auth/callback`,
          shouldCreateUser: false, // don't silently create accounts via magic link
        },
      });
      if (error) return { success: false, error: error.message };
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // Supabase signup (email/password). The user must verify their email
  // unless email confirmations are disabled in Supabase. After verify, the
  // callback page calls completeSupabaseSignup() to create the admin row.
  const signupWithSupabase = async (email, password, name, extra = {}) => {
    if (!isSupabaseConfigured) return { success: false, error: 'Supabase is not configured' };
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/admin/auth/callback`,
          data: { name, ...extra },
        },
      });
      if (error) return { success: false, error: error.message };

      // If email-confirm is OFF, we already have a session — go ahead and
      // create the admin row immediately.
      if (data.session) {
        const synced = await completeSupabaseSignup({ name, ...extra }, data.session);
        if (synced) return { success: true, admin: synced, immediate: true };
      }
      return { success: true, requiresEmailVerification: !data.session };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // After Supabase confirms the user (or returns from OAuth/magic link), make
  // sure they have a MongoDB admin row. Idempotent.
  const completeSupabaseSignup = async (profile = {}, sessionOverride = null) => {
    if (!isSupabaseConfigured) return null;
    let session = sessionOverride;
    if (!session) {
      const { data } = await supabase.auth.getSession();
      session = data?.session;
    }
    if (!session?.access_token) return null;

    try {
      const { data } = await axios.post(
        `${API_URL}/api/auth/sync-supabase-user`,
        profile,
        { headers: { Authorization: `Bearer ${session.access_token}` } }
      );
      if (data?.access_token) {
        localStorage.setItem('admin_token', data.access_token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        setToken(data.access_token);
      }
      if (data?.admin) setAdmin(data.admin);
      return data?.admin || null;
    } catch (err) {
      console.error('completeSupabaseSignup failed:', err?.response?.data || err.message);
      return null;
    }
  };

  // Helper kept for backward-compat with /signup pages that hit the legacy
  // /api/auth/register endpoint and get back { access_token, admin } already.
  const setSessionFromSignup = ({ access_token, admin: newAdmin }) => {
    localStorage.setItem('admin_token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setToken(access_token);
    setAdmin(newAdmin);
  };

  const logout = async () => {
    try {
      if (isSupabaseConfigured) {
        await supabase.auth.signOut();
      }
    } catch (e) { /* ignore */ }
    localStorage.removeItem('admin_token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setAdmin(null);
  };

  return (
    <AuthContext.Provider value={{
      admin,
      loading,
      token,
      login,
      loginWithSupabasePassword,
      sendMagicLink,
      signupWithSupabase,
      completeSupabaseSignup,
      setSessionFromSignup,
      logout,
      refresh: fetchAdminInfo,
      supabaseConfigured: isSupabaseConfigured,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
