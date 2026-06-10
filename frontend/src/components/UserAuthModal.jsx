import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mail, Lock, User, Sparkles, ShieldCheck, Phone } from 'lucide-react';
import { useUserAuth } from '@/context/UserAuthContext';

const inp = {
  width: '100%', padding: '0.95rem 1rem 0.95rem 2.6rem', background: 'transparent', color: '#FFF8DC',
  border: '1px solid var(--lux-border)', borderRadius: '0.55rem', outline: 'none',
  caretColor: '#D4AF37', fontSize: '0.95rem',
};

const Field = ({ icon: Icon, ...rest }) => (
  <div className="relative">
    {Icon && <Icon className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'rgba(255,248,220,0.5)' }} />}
    <input {...rest} style={inp}
      onFocus={(e) => (e.target.style.borderColor = '#D4AF37')}
      onBlur={(e) => (e.target.style.borderColor = 'var(--lux-border)')} />
  </div>
);

const UserAuthModal = ({ open, onClose, initialMode = 'login' }) => {
  const { register, login, loginWithGoogle } = useUserAuth();
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  React.useEffect(() => { setMode(initialMode); setError(''); }, [initialMode, open]);

  const setField = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  const submit = async (e) => {
    e?.preventDefault?.();
    setBusy(true);
    setError('');
    try {
      if (mode === 'signup') {
        if (!form.name.trim()) throw new Error('Please enter your name.');
        if (form.password.length < 8) throw new Error('Password must be at least 8 characters.');
        if (!form.phone.trim()) throw new Error('Please enter your phone number.');
        await register({
          email: form.email.trim().toLowerCase(),
          name: form.name.trim(),
          phone: form.phone.trim(),
          password: form.password,
        });
      } else {
        await login({ email: form.email.trim().toLowerCase(), password: form.password });
      }
      onClose?.();
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[120] flex items-center justify-center px-4 py-8"
        style={{ background: 'rgba(8,5,3,0.82)', backdropFilter: 'blur(10px)' }}
        onClick={onClose}
        data-testid="user-auth-modal"
      >
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.97 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="lux-glass w-full max-w-md p-7 md:p-9 relative"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={onClose} className="absolute top-4 right-4 w-9 h-9 rounded-full grid place-items-center" style={{ border: '1px solid var(--lux-border)', color: 'rgba(255,248,220,0.7)' }} data-testid="user-auth-close">
            <X className="w-4 h-4" />
          </button>

          <span className="lux-eyebrow block mb-2">◆ {mode === 'signup' ? 'Create account' : 'Welcome back'}</span>
          <h2 className="font-display text-3xl mb-1" style={{ color: '#FFF8DC' }}>
            {mode === 'signup' ? <>Join the <span className="font-script italic text-gold">memory.</span></> : <>Sign in to <span className="font-script italic text-gold">your photos.</span></>}
          </h2>
          <p className="text-xs mb-5" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {mode === 'signup'
              ? 'Buy credits, save events you attended, get matched photos with one selfie.'
              : 'Pick up where you left off — purchases, saved albums and AI matches.'}
          </p>

          {/* Google CTA */}
          <button
            type="button"
            onClick={loginWithGoogle}
            className="w-full mb-4 inline-flex items-center justify-center gap-3 px-4 py-3 rounded-lg transition-all"
            style={{ background: '#FFF8DC', color: '#16110C', fontWeight: 600 }}
            data-testid="user-auth-google"
          >
            <GoogleMark /> Continue with Google
          </button>

          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px" style={{ background: 'var(--lux-border)' }} />
            <span className="text-[10px] tracking-[0.35em] uppercase" style={{ color: 'rgba(255,248,220,0.45)' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'var(--lux-border)' }} />
          </div>

          <form onSubmit={submit} className="space-y-3" data-testid={`user-auth-form-${mode}`}>
            {mode === 'signup' && (
              <Field icon={User} type="text" required placeholder="Your name"
                value={form.name} onChange={(e) => setField('name', e.target.value)}
                data-testid="user-auth-name" />
            )}
            <Field icon={Mail} type="email" required placeholder="you@email.com"
              value={form.email} onChange={(e) => setField('email', e.target.value)}
              data-testid="user-auth-email" />
            {mode === 'signup' && (
              <Field icon={Phone} type="tel" required placeholder="+91 99999 99999"
                value={form.phone} onChange={(e) => setField('phone', e.target.value)}
                data-testid="user-auth-phone" />
            )}
            <Field icon={Lock} type="password" required placeholder={mode === 'signup' ? 'Choose a password (8+ chars)' : 'Password'}
              value={form.password} onChange={(e) => setField('password', e.target.value)}
              data-testid="user-auth-password" />

            {error && (
              <div className="px-3 py-2 rounded-md text-xs"
                style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
                data-testid="user-auth-error"
              >
                {error}
              </div>
            )}

            <button type="submit" disabled={busy} className="lux-btn w-full justify-center" data-testid="user-auth-submit">
              {busy ? (
                <>
                  <Sparkles className="w-4 h-4 animate-pulse" /> Please wait…
                </>
              ) : mode === 'signup' ? (
                <>
                  Create account <ShieldCheck className="w-4 h-4" />
                </>
              ) : (
                <>
                  Sign in <ShieldCheck className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-5 text-center text-xs" style={{ color: 'rgba(255,248,220,0.6)' }}>
            {mode === 'signup' ? (
              <>
                Already have an account?{' '}
                <button onClick={() => setMode('login')} className="text-gold hover:opacity-80" data-testid="user-auth-switch-login">
                  Sign in
                </button>
              </>
            ) : (
              <>
                New here?{' '}
                <button onClick={() => setMode('signup')} className="text-gold hover:opacity-80" data-testid="user-auth-switch-signup">
                  Create account
                </button>
              </>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

const GoogleMark = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.614z" fill="#4285F4"/>
    <path d="M9 18c2.43 0 4.467-.806 5.956-2.181l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
    <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
    <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
  </svg>
);

export default UserAuthModal;
