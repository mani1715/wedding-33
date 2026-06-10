import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// PHASE 10 (perf): localStorage flag we toggle on login/register/oauth-callback
// success and clear on logout. The cookie itself is httpOnly so JS can't see it;
// this flag lets us SKIP the startup `/api/users/me` probe for anonymous visitors,
// shaving a round-trip off first paint.
const USER_SESSION_FLAG = 'maja_user_session_active';

export const markUserSessionActive = () => {
  try { localStorage.setItem(USER_SESSION_FLAG, '1'); } catch (_e) {}
};
export const clearUserSessionActive = () => {
  try { localStorage.removeItem(USER_SESSION_FLAG); } catch (_e) {}
};
const hasUserSessionFlag = () => {
  try { return localStorage.getItem(USER_SESSION_FLAG) === '1'; } catch (_e) { return false; }
};

const UserAuthContext = createContext(null);

export const UserAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_URL}/api/users/me`, { withCredentials: true });
      setUser(data);
      markUserSessionActive();
    } catch (_e) {
      setUser(null);
      clearUserSessionActive();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: if returning from Google OAuth, skip the /me probe.
    // AuthCallback will exchange the session_id first.
    if (typeof window !== 'undefined' && window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }
    // PHASE 10 (perf): only probe /me if we have evidence of an existing session.
    // For anonymous visitors this saves a network round-trip on startup.
    if (!hasUserSessionFlag()) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const register = async ({ email, name, password, phone }) => {
    const { data } = await axios.post(`${API_URL}/api/users/register`, { email, name, password, phone }, { withCredentials: true });
    setUser(data);
    markUserSessionActive();
    return data;
  };

  const login = async ({ email, password }) => {
    const { data } = await axios.post(`${API_URL}/api/users/login`, { email, password }, { withCredentials: true });
    setUser(data);
    markUserSessionActive();
    return data;
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const logout = async () => {
    try { await axios.post(`${API_URL}/api/users/logout`, {}, { withCredentials: true }); } catch (_e) {}
    setUser(null);
    clearUserSessionActive();
  };

  return (
    <UserAuthContext.Provider value={{ user, loading, register, login, loginWithGoogle, logout, refresh: checkAuth }}>
      {children}
    </UserAuthContext.Provider>
  );
};

export const useUserAuth = () => {
  const ctx = useContext(UserAuthContext);
  if (!ctx) throw new Error('useUserAuth must be used within UserAuthProvider');
  return ctx;
};
