/**
 * allDesigns.js — Lazy aggregator for per-theme design configs.
 *
 * PHASE 8 refactor (perf): the 9 theme catalogs are no longer eager-imported.
 * Each lives in its own webpack chunk and loads on demand:
 *
 *   • `useAllDesigns()` (React hook) — subscribes the consumer to the global
 *     `ALL_DESIGNS` map and kicks off a parallel preload of every theme. Used
 *     by picker pages that iterate all themes.
 *
 *   • `useThemeDesigns(themeId)` (React hook) — loads ONLY the requested
 *     theme. Used by single-theme pages.
 *
 *   • `getThemeDesignsAsync(themeId)` — imperative promise loader.
 *
 *   • `ALL_DESIGNS` — still exported for legacy sync access. Starts empty and
 *     populates as chunks resolve. Consumers that want reactive updates must
 *     use the hooks above (the cache is mutated in-place).
 *
 *   • `EVENTS` — canonical event ordering used across the app.
 *
 * Kerala is intentionally NOT included here — it has its own dedicated catalog
 * file (kerala_backwaters/kerala.designs.js).
 */
import { useEffect, useReducer, useState } from 'react';

// Mutable cache populated as theme chunks resolve. Exported for legacy
// synchronous consumers — see hooks above for reactive access.
export const ALL_DESIGNS = {};

export const EVENTS = ['Engagement', 'Haldi', 'Mehandi', 'Marriage', 'Reception', 'Sangeeth'];

const LOADERS = {
  south_indian_temple: () => import(/* webpackChunkName: "theme-temple" */ './configs/temple.designs'),
  royal_mughal:        () => import(/* webpackChunkName: "theme-mughal" */ './configs/mughal.designs'),
  muslim_nikah:        () => import(/* webpackChunkName: "theme-muslim" */ './configs/muslim.designs'),
  christian_elegant:   () => import(/* webpackChunkName: "theme-christian" */ './configs/christian.designs'),
  bengali_traditional: () => import(/* webpackChunkName: "theme-bengali" */ './configs/bengali.designs'),
  punjabi_sangeet:     () => import(/* webpackChunkName: "theme-punjabi" */ './configs/punjabi.designs'),
  beach_destination:   () => import(/* webpackChunkName: "theme-beach" */ './configs/beach.designs'),
  nature_eco_wedding:  () => import(/* webpackChunkName: "theme-nature" */ './configs/nature.designs'),
  modern_minimal:      () => import(/* webpackChunkName: "theme-minimal" */ './configs/minimal.designs'),
};

// Subscription bus so React consumers re-render when chunks land.
const listeners = new Set();
const notify = () => { for (const l of listeners) { try { l(); } catch (_e) {} } };

// Per-theme load tracking — prevents duplicate imports.
const themePromises = {};
let allPromise = null;

const loadTheme = (themeId) => {
  if (ALL_DESIGNS[themeId]) return Promise.resolve(ALL_DESIGNS[themeId]);
  if (themePromises[themeId]) return themePromises[themeId];
  const loader = LOADERS[themeId];
  if (!loader) return Promise.resolve(null);
  themePromises[themeId] = loader().then((mod) => {
    const data = mod.default || mod;
    ALL_DESIGNS[themeId] = data;
    notify();
    return data;
  }).catch((e) => {
    // Allow retry on next call
    delete themePromises[themeId];
    // eslint-disable-next-line no-console
    console.error(`[allDesigns] failed to load theme "${themeId}"`, e);
    return null;
  });
  return themePromises[themeId];
};

export const preloadAllDesigns = () => {
  if (allPromise) return allPromise;
  allPromise = Promise.all(Object.keys(LOADERS).map(loadTheme)).then(() => ALL_DESIGNS);
  return allPromise;
};

// PHASE 8: kick off a low-priority preload of every theme so picker pages
// have data ready by the time the user reaches them — without blocking
// initial paint or the first-page route.
if (typeof window !== 'undefined') {
  const start = () => preloadAllDesigns();
  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(start, { timeout: 1500 });
  } else {
    setTimeout(start, 200);
  }
}

/**
 * useAllDesigns — Subscribes the caller to the global `ALL_DESIGNS` cache,
 * triggers a parallel preload, and re-renders as chunks land. Returns the
 * live cache object (mutated in place). Pair with a loading check via
 * `Object.keys(designs).length` or use `useAllDesignsReady()`.
 */
export const useAllDesigns = () => {
  const [, force] = useReducer((x) => x + 1, 0);
  useEffect(() => {
    listeners.add(force);
    preloadAllDesigns();
    return () => { listeners.delete(force); };
  }, []);
  return ALL_DESIGNS;
};

/**
 * useAllDesignsReady — Returns `true` once every theme chunk has resolved.
 */
export const useAllDesignsReady = () => {
  const [ready, setReady] = useState(Object.keys(ALL_DESIGNS).length === Object.keys(LOADERS).length);
  useEffect(() => {
    if (ready) return;
    let cancelled = false;
    preloadAllDesigns().then(() => { if (!cancelled) setReady(true); });
    return () => { cancelled = true; };
  }, [ready]);
  return ready;
};

/**
 * useThemeDesigns — Loads ONLY the requested theme. Returns the theme config
 * (or `null` while loading / on unknown id).
 */
export const useThemeDesigns = (themeId) => {
  const [data, setData] = useState(themeId ? ALL_DESIGNS[themeId] || null : null);
  useEffect(() => {
    if (!themeId) { setData(null); return; }
    if (ALL_DESIGNS[themeId]) { setData(ALL_DESIGNS[themeId]); return; }
    let cancelled = false;
    loadTheme(themeId).then((d) => { if (!cancelled) setData(d); });
    return () => { cancelled = true; };
  }, [themeId]);
  return data;
};

// Imperative helpers retained from the original API ------------------------

export const getThemeDesigns = (themeId) => ALL_DESIGNS[themeId];
export const getEventDesigns = (themeId, event) =>
  ALL_DESIGNS[themeId]?.events?.[event] || [];

export const getThemeDesignsAsync = (themeId) => loadTheme(themeId);
