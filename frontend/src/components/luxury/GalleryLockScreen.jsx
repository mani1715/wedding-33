import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Eye, EyeOff, Loader2, ShieldCheck, AlertCircle } from 'lucide-react';

/**
 * GalleryLockScreen — elegant access-code prompt shown before a guest enters
 * the private wedding gallery (or the AI face-match flow).
 *
 * Props:
 *   onUnlock: async (code, remember) => Promise (throws on failure)
 *   defaultRemember?: boolean
 *   title?: string
 *   subtitle?: string
 *   testid?: string  (root data-testid)
 */
const GalleryLockScreen = ({
  onUnlock,
  defaultRemember = true,
  title = 'Private Wedding Gallery',
  subtitle = 'Enter the access code shared by the couple to continue.',
  testid = 'gallery-lock-screen',
}) => {
  const [code, setCode] = useState('');
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(defaultRemember);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e?.preventDefault?.();
    setErr('');
    if (code.trim().length < 4) {
      setErr('Please enter the access code.');
      return;
    }
    setBusy(true);
    try {
      await onUnlock(code.trim(), remember);
    } catch (ex) {
      setErr(ex.message || 'Unlock failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="lux-glass rounded-2xl px-7 py-9 md:px-12 md:py-12 max-w-md w-full mx-auto"
      data-testid={testid}
    >
      <div
        className="w-16 h-16 mx-auto rounded-full grid place-items-center mb-6"
        style={{
          background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(212,175,55,0.05))',
          border: '1px solid rgba(212,175,55,0.35)',
        }}
      >
        <Lock className="w-7 h-7" style={{ color: '#D4AF37' }} />
      </div>

      <h2
        className="font-display text-2xl md:text-3xl text-center mb-2"
        style={{ color: '#FFF8DC' }}
      >
        {title}
      </h2>
      <p
        className="text-xs md:text-sm text-center mb-7"
        style={{ color: 'rgba(255,248,220,0.65)' }}
      >
        {subtitle}
      </p>

      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span
            className="block text-[10px] tracking-[0.3em] uppercase mb-2"
            style={{ color: 'rgba(255,248,220,0.55)' }}
          >
            Access Code
          </span>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. MANI2026"
              autoComplete="one-time-code"
              autoFocus
              spellCheck={false}
              className="w-full text-center tracking-[0.3em] uppercase font-mono"
              data-testid="gallery-unlock-input"
              style={{
                padding: '0.95rem 2.8rem',
                background: 'rgba(255,248,220,0.04)',
                color: '#FFF8DC',
                border: '1px solid var(--lux-border)',
                borderRadius: '0.6rem',
                outline: 'none',
                caretColor: '#D4AF37',
                fontSize: '1rem',
                letterSpacing: '0.3em',
              }}
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-7 h-7 grid place-items-center rounded-md hover:bg-white/5"
              aria-label={show ? 'Hide code' : 'Show code'}
              data-testid="gallery-unlock-toggle-visibility"
            >
              {show ? <EyeOff className="w-4 h-4" style={{ color: 'rgba(255,248,220,0.55)' }} /> :
                       <Eye className="w-4 h-4" style={{ color: 'rgba(255,248,220,0.55)' }} />}
            </button>
          </div>
        </label>

        <label className="flex items-center gap-2 text-xs cursor-pointer"
          style={{ color: 'rgba(255,248,220,0.7)' }}
          data-testid="gallery-remember-device-label">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="accent-amber-400 w-3.5 h-3.5"
            data-testid="gallery-remember-device-checkbox"
          />
          Remember this device
        </label>

        {err && (
          <div
            className="flex items-start gap-2 text-xs px-3 py-2 rounded-md"
            style={{
              background: 'rgba(255,176,160,0.08)',
              border: '1px solid rgba(255,176,160,0.25)',
              color: '#FFB0A0',
            }}
            data-testid="gallery-unlock-error"
          >
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{err}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full lux-btn justify-center"
          data-testid="gallery-unlock-submit"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ShieldCheck className="w-4 h-4" /> Unlock Gallery</>}
        </button>
      </form>

      <div
        className="text-[10px] text-center mt-7 tracking-widest uppercase"
        style={{ color: 'rgba(255,248,220,0.4)' }}
      >
        Protected · 5 wrong attempts pause access for 5 minutes
      </div>
    </motion.div>
  );
};

export default GalleryLockScreen;
