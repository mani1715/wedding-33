import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { Crown, ArrowLeft, Gift, Heart, Sparkles } from 'lucide-react';
import '../styles/luxury.css';

const fadeUp = {
  hidden: { opacity: 0, y: 20, filter: 'blur(6px)' },
  visible: (i = 0) => ({
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.9, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
  }),
};

const AdminLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');  // accepts email OR username
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [referralCode, setReferralCode] = useState('');
  const [referralMessage, setReferralMessage] = useState('');

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    const refCode = searchParams.get('ref');
    if (refCode) {
      setReferralCode(refCode.toUpperCase());
      setReferralMessage(`Using referral code: ${refCode.toUpperCase()} — 50 free credits unlocked`);
      sessionStorage.setItem('referral_code', refCode.toUpperCase());
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const result = await login(email, password);
    if (result.success) {
      if (referralCode) sessionStorage.setItem('referral_code', referralCode);
      // Route based on role
      const role = result.admin?.role || '';
      if (role === 'super_admin' || role === 'SUPER_ADMIN') {
        navigate('/super-admin/dashboard');
        return;
      }
      navigate('/admin/dashboard');
    } else {
      setError(result.error || 'Invalid credentials');
    }
    setLoading(false);
  };

  return (
    <div className="luxe min-h-screen flex items-center justify-center px-6 py-12 relative">
      {/* Decorative orbits */}
      <div className="lux-orbit" style={{ width: 720, height: 720, top: -260, left: -260 }} />
      <div className="lux-orbit" style={{ width: 1100, height: 1100, bottom: -460, right: -460, opacity: 0.5 }} />

      <motion.button
        initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8 }}
        onClick={() => navigate('/')}
        className="absolute top-8 left-8 flex items-center gap-2 text-xs tracking-[0.25em] uppercase z-20"
        style={{ color: 'rgba(255,248,220,0.65)' }}
        data-testid="back-to-home"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Studio
      </motion.button>

      <motion.div
        initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }}
        className="w-full max-w-[440px] relative z-10"
      >
        <motion.div variants={fadeUp} custom={0} className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full mb-5"
            style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}>
            <Heart className="w-6 h-6" style={{ color: '#16110C' }} strokeWidth={2.4} />
          </div>
          <span className="lux-eyebrow block mb-3">◆ Photographer Studio</span>
          <h1 className="font-display text-4xl md:text-5xl leading-tight" style={{ color: '#FFF8DC' }}>
            Welcome <span className="text-gold italic font-script">back.</span>
          </h1>
          <p className="mt-3 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Enter your credentials to access your studio.
          </p>
        </motion.div>

        <motion.div variants={fadeUp} custom={1} className="lux-glass p-8 md:p-10">
          {referralMessage && (
            <div className="mb-6 flex items-start gap-3 p-4 rounded-xl"
              style={{ background: 'rgba(212,175,55,0.08)', border: '1px solid var(--lux-border-strong)' }}>
              <Gift className="w-4 h-4 mt-0.5" style={{ color: '#D4AF37' }} />
              <p className="text-xs tracking-wide" style={{ color: 'rgba(255,248,220,0.8)' }}>{referralMessage}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[10px] tracking-[0.3em] uppercase mb-2.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                Email or Username
              </label>
              <input
                type="text" value={email} onChange={(e) => setEmail(e.target.value)} required
                placeholder="studio@maharani.com or your username"
                data-testid="admin-login-email"
                className="w-full px-4 py-3.5 bg-transparent rounded-lg outline-none transition-all font-body text-sm"
                style={{
                  color: '#FFF8DC',
                  border: '1px solid var(--lux-border)',
                  caretColor: '#D4AF37',
                }}
                onFocus={(e) => e.target.style.borderColor = '#D4AF37'}
                onBlur={(e) => e.target.style.borderColor = 'var(--lux-border)'}
              />
            </div>

            <div>
              <label className="block text-[10px] tracking-[0.3em] uppercase mb-2.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                Password
              </label>
              <input
                type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                placeholder="••••••••"
                data-testid="admin-login-password"
                className="w-full px-4 py-3.5 bg-transparent rounded-lg outline-none transition-all font-body text-sm"
                style={{
                  color: '#FFF8DC',
                  border: '1px solid var(--lux-border)',
                  caretColor: '#D4AF37',
                }}
                onFocus={(e) => e.target.style.borderColor = '#D4AF37'}
                onBlur={(e) => e.target.style.borderColor = 'var(--lux-border)'}
              />
            </div>

            {!searchParams.get('ref') && (
              <div>
                <label className="block text-[10px] tracking-[0.3em] uppercase mb-2.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                  Referral Code <span className="opacity-50">(optional)</span>
                </label>
                <input
                  type="text" value={referralCode} onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
                  placeholder="Earn 50 free credits"
                  maxLength={12}
                  data-testid="admin-login-referral"
                  className="w-full px-4 py-3.5 bg-transparent rounded-lg outline-none transition-all font-body text-sm tracking-widest"
                  style={{
                    color: '#FFF8DC',
                    border: '1px solid var(--lux-border)',
                    caretColor: '#D4AF37',
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#D4AF37'}
                  onBlur={(e) => e.target.style.borderColor = 'var(--lux-border)'}
                />
              </div>
            )}

            {error && (
              <div className="px-4 py-3 rounded-lg text-sm" data-testid="admin-login-error"
                style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="lux-btn w-full justify-center" data-testid="admin-login-submit">
              {loading ? (
                <>
                  <Sparkles className="w-4 h-4 animate-pulse" /> Authenticating
                </>
              ) : (
                <>
                  Enter Studio <Crown className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="lux-hairline my-6" />

          <div className="text-center space-y-3">
            <button
              type="button"
              onClick={() => navigate('/admin/signup')}
              className="text-sm font-medium tracking-wide hover:opacity-80 transition-opacity"
              style={{ color: '#D4AF37' }}
              data-testid="admin-login-signup-link"
            >
              New photographer? Create studio account →
            </button>
            <div className="text-xs" style={{ color: 'rgba(255,248,220,0.45)' }}>
              <p className="tracking-widest uppercase mb-1">Default Demo</p>
              <p className="font-mono">admin@wedding.com · admin123</p>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default AdminLogin;
