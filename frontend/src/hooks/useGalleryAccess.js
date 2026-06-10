import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const lsKey = (slug) => `gallery_device_token_${slug}`;
const lsExpKey = (slug) => `gallery_device_exp_${slug}`;

/**
 * useGalleryAccess(slug)
 * Centralised hook that:
 *   • fetches the public privacy info for the gallery,
 *   • restores any saved trusted-device token from localStorage,
 *   • exposes `unlock(code, remember)` which calls the unlock endpoint
 *     and persists the returned JWT for `remember_days`.
 *
 * Returns:
 *   { loading, privacy, deviceToken, isProtected, isUnlocked, unlock(code, remember), logout(), error }
 */
export function useGalleryAccess(slug) {
  const [loading, setLoading] = useState(true);
  const [privacy, setPrivacy] = useState(null);
  const [deviceToken, setDeviceToken] = useState(null);
  const [error, setError] = useState('');

  const loadStored = useCallback(() => {
    try {
      const tok = localStorage.getItem(lsKey(slug));
      const exp = localStorage.getItem(lsExpKey(slug));
      if (tok && exp && Date.parse(exp) > Date.now()) {
        setDeviceToken(tok);
        return tok;
      }
      // expired — clean up
      if (tok) {
        localStorage.removeItem(lsKey(slug));
        localStorage.removeItem(lsExpKey(slug));
      }
    } catch (e) { /* SSR / private mode — ignore */ }
    return null;
  }, [slug]);

  const fetchPrivacy = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await axios.get(`${API_URL}/api/public/gallery/${slug}/privacy`);
      setPrivacy(r.data);
      loadStored();
    } catch (e) {
      // Endpoint failure shouldn't break the page — just treat as unprotected
      setPrivacy({
        enabled: false,
        is_protected: false,
        ai_face_match_enabled: true,
        allow_downloads: true,
        allow_share: true,
        public_highlights_enabled: true,
        private_full_gallery_enabled: true,
      });
    } finally {
      setLoading(false);
    }
  }, [slug, loadStored]);

  useEffect(() => {
    if (slug) fetchPrivacy();
  }, [slug, fetchPrivacy]);

  const unlock = useCallback(async (code, remember = true) => {
    setError('');
    try {
      const r = await axios.post(
        `${API_URL}/api/public/gallery/${slug}/unlock`,
        { code, remember },
      );
      const token = r.data?.device_token;
      const exp = r.data?.expires_at;
      if (token) {
        setDeviceToken(token);
        if (remember && exp) {
          try {
            localStorage.setItem(lsKey(slug), token);
            localStorage.setItem(lsExpKey(slug), exp);
          } catch (e) { /* ignore quota errors */ }
        }
      }
      return r.data;
    } catch (e) {
      const detail = e.response?.data?.detail || 'Unlock failed';
      setError(typeof detail === 'string' ? detail : 'Unlock failed');
      const err = new Error(detail);
      err.status = e.response?.status;
      throw err;
    }
  }, [slug]);

  const logout = useCallback(() => {
    setDeviceToken(null);
    try {
      localStorage.removeItem(lsKey(slug));
      localStorage.removeItem(lsExpKey(slug));
    } catch (e) { /* ignore */ }
  }, [slug]);

  const isProtected = !!(privacy?.is_protected);
  const isUnlocked = !isProtected || !!deviceToken;

  return { loading, privacy, deviceToken, isProtected, isUnlocked, unlock, logout, error, refresh: fetchPrivacy };
}

/** Helper to add the device-token header on outbound axios requests. */
export const authHeader = (deviceToken) =>
  deviceToken ? { 'X-Gallery-Device-Token': deviceToken } : {};
