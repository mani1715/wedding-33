import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Crown, Sparkles, ShieldCheck, Phone, AtSign, User, Lock, Camera } from 'lucide-react';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const fadeUp = {
  hidden: { opacity: 0, y: 16, filter: 'blur(6px)' },
  visible: (i = 0) => ({
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.7, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] },
  }),
};

const inputStyle = {
  color: '#FFF8DC',
  border: '1px solid var(--lux-border)',
  caretColor: '#D4AF37',
};

const Field = ({ label, icon: Icon, ...props }) => (
  <div>
    <label className="block text-[10px] tracking-[0.3em] uppercase mb-2.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
      {label}
    </label>
    <div className="relative">
      {Icon && (
        <Icon className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'rgba(255,248,220,0.45)' }} />
      )}
      <input
        {...props}
        className="w-full pl-10 pr-4 py-3.5 bg-transparent rounded-lg outline-none transition-all font-body text-sm"
        style={inputStyle}
        onFocus={(e) => (e.target.style.borderColor = '#D4AF37')}
        onBlur={(e) => (e.target.style.borderColor = 'var(--lux-border)')}
      />
    </div>
  </div>
);

const AdminSignup = () => {
  const navigate = useNavigate();
  const { setSessionFromSignup } = useAuth();
  const [step, setStep] = useState(1); // 1: details, 2: OTP, 3: success
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [devOtp, setDevOtp] = useState(''); // shown in dev mode
  const [form, setForm] = useState({
    name: '',
    username: '',
    email: '',
    phone: '',
    password: '',
    confirm: '',
  });
  const [otp, setOtp] = useState('');

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  const setField = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  const validateStep1 = () => {
    if (!form.name.trim()) return 'Please enter your full name.';
    if (!/^[a-z0-9_.]{3,30}$/.test(form.username.trim().toLowerCase()))
      return 'Username must be 3–30 chars: lowercase letters, digits, dot, underscore.';
    if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(form.email.trim()))
      return 'Enter a valid email address.';
    if (!/^\+[1-9]\d{6,14}$/.test(form.phone.trim()))
      return 'Phone must be in E.164 format (e.g., +919876543210).';
    if (form.password.length < 8) return 'Password must be at least 8 characters.';
    if (form.password !== form.confirm) return 'Passwords do not match.';
    return null;
  };

  const handleSendOtp = async (e) => {
    e?.preventDefault?.();
    const err = validateStep1();
    if (err) {
      setError(err);
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await axios.post(`${API_URL}/api/auth/send-otp`, { phone: form.phone.trim() });
      setInfo(`We sent a 6-digit verification code to ${form.phone.trim()}.`);
      setDevOtp(data?.otp || '');
      setStep(2);
    } catch (e2) {
      setError(e2?.response?.data?.detail || 'Could not send OTP. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAndRegister = async (e) => {
    e?.preventDefault?.();
    if (!/^\d{4,8}$/.test(otp.trim())) {
      setError('Enter the 6-digit verification code.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_URL}/api/auth/verify-otp`, { phone: form.phone.trim(), otp: otp.trim() });
    } catch (e2) {
      setLoading(false);
      setError(e2?.response?.data?.detail || 'Verification failed. Try a fresh OTP.');
      return;
    }
    try {
      const { data } = await axios.post(`${API_URL}/api/auth/register`, {
        name: form.name.trim(),
        username: form.username.trim().toLowerCase(),
        email: form.email.trim().toLowerCase(),
        phone: form.phone.trim(),
        password: form.password,
      });
      setSessionFromSignup({ access_token: data.access_token, admin: data.admin });
      setStep(3);
      setTimeout(() => navigate('/admin/dashboard'), 1100);
    } catch (e3) {
      setError(e3?.response?.data?.detail || 'Could not create your account.');
    } finally {
      setLoading(false);
    }
  };

  const resendOtp = async () => {
    try {
      setError('');
      setLoading(true);
      const { data } = await axios.post(`${API_URL}/api/auth/send-otp`, { phone: form.phone.trim() });
      setInfo(`Fresh OTP sent to ${form.phone.trim()}.`);
      setDevOtp(data?.otp || '');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not resend OTP.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="luxe min-h-screen flex items-center justify-center px-6 py-12 relative">
      <div className="lux-orbit" style={{ width: 720, height: 720, top: -260, left: -260 }} />
      <div className="lux-orbit" style={{ width: 1100, height: 1100, bottom: -460, right: -460, opacity: 0.5 }} />

      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7 }}
        onClick={() => navigate('/admin/login')}
        className="absolute top-8 left-8 flex items-center gap-2 text-xs tracking-[0.25em] uppercase z-20"
        style={{ color: 'rgba(255,248,220,0.65)' }}
        data-testid="signup-back-login"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Login
      </motion.button>

      <motion.div
        initial="hidden"
        animate="visible"
        variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.07 } } }}
        className="w-full max-w-[520px] relative z-10"
      >
        <motion.div variants={fadeUp} custom={0} className="text-center mb-8">
          <div
            className="inline-flex items-center justify-center w-14 h-14 rounded-full mb-5"
            style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}
          >
            <Camera className="w-6 h-6" style={{ color: '#16110C' }} strokeWidth={2.4} />
          </div>
          <span className="lux-eyebrow block mb-3">◆ Photographer Studio</span>
          <h1 className="font-display text-4xl md:text-5xl leading-tight" style={{ color: '#FFF8DC' }}>
            Open your <span className="text-gold italic font-script">studio.</span>
          </h1>
          <p className="mt-3 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
            Verify your phone, claim your handle and start crafting invitations in minutes.
          </p>
        </motion.div>

        {/* Stepper */}
        <motion.div variants={fadeUp} custom={1} className="flex items-center justify-center gap-3 mb-8" data-testid="signup-stepper">
          {[1, 2, 3].map((n) => {
            const active = step >= n;
            return (
              <div key={n} className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-full grid place-items-center text-xs font-semibold transition-all"
                  style={{
                    background: active ? '#D4AF37' : 'transparent',
                    color: active ? '#16110C' : 'rgba(255,248,220,0.55)',
                    border: '1px solid ' + (active ? '#D4AF37' : 'var(--lux-border)'),
                  }}
                >
                  {n}
                </div>
                {n < 3 && (
                  <div className="w-10 h-px" style={{ background: 'var(--lux-border-strong)' }} />
                )}
              </div>
            );
          })}
        </motion.div>

        <motion.div variants={fadeUp} custom={2} className="lux-glass p-8 md:p-10">
          {step === 1 && (
            <form onSubmit={handleSendOtp} className="space-y-5" data-testid="signup-form-details">
              <Field
                label="Full Name"
                icon={User}
                type="text"
                value={form.name}
                onChange={(e) => setField('name', e.target.value)}
                placeholder="Raju Photography"
                data-testid="signup-name"
                required
              />
              <Field
                label="Username"
                icon={AtSign}
                type="text"
                value={form.username}
                onChange={(e) => setField('username', e.target.value.toLowerCase())}
                placeholder="raju_studio"
                data-testid="signup-username"
                required
              />
              <Field
                label="Email"
                icon={AtSign}
                type="email"
                value={form.email}
                onChange={(e) => setField('email', e.target.value)}
                placeholder="hello@yourstudio.com"
                data-testid="signup-email"
                required
              />
              <Field
                label="Phone (E.164)"
                icon={Phone}
                type="tel"
                value={form.phone}
                onChange={(e) => setField('phone', e.target.value)}
                placeholder="+919876543210"
                data-testid="signup-phone"
                required
              />
              <Field
                label="Password"
                icon={Lock}
                type="password"
                value={form.password}
                onChange={(e) => setField('password', e.target.value)}
                placeholder="At least 8 characters"
                data-testid="signup-password"
                required
              />
              <Field
                label="Confirm Password"
                icon={Lock}
                type="password"
                value={form.confirm}
                onChange={(e) => setField('confirm', e.target.value)}
                placeholder="Repeat password"
                data-testid="signup-confirm"
                required
              />

              {error && (
                <div
                  className="px-4 py-3 rounded-lg text-sm"
                  data-testid="signup-error"
                  style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
                >
                  {error}
                </div>
              )}

              <button type="submit" disabled={loading} className="lux-btn w-full justify-center" data-testid="signup-send-otp">
                {loading ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-pulse" /> Sending verification…
                  </>
                ) : (
                  <>
                    Verify phone & continue <ShieldCheck className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={handleVerifyAndRegister} className="space-y-5" data-testid="signup-form-otp">
              <div className="text-center mb-4">
                <ShieldCheck className="w-10 h-10 mx-auto mb-3" style={{ color: '#D4AF37' }} />
                <h2 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>Verify your phone</h2>
                <p className="text-sm mt-1" style={{ color: 'rgba(255,248,220,0.6)' }}>
                  {info || `Code sent to ${form.phone}`}
                </p>
                {devOtp && (
                  <p className="text-xs mt-2 font-mono" style={{ color: '#D4AF37' }} data-testid="signup-dev-otp">
                    DEV mode OTP: <span className="text-gold">{devOtp}</span>
                  </p>
                )}
              </div>

              <div>
                <label className="block text-[10px] tracking-[0.3em] uppercase mb-2.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
                  6-digit OTP
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="\d*"
                  maxLength={8}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="••••••"
                  data-testid="signup-otp-input"
                  className="w-full text-center tracking-[0.7em] text-xl px-4 py-4 bg-transparent rounded-lg outline-none transition-all font-mono"
                  style={inputStyle}
                  onFocus={(e) => (e.target.style.borderColor = '#D4AF37')}
                  onBlur={(e) => (e.target.style.borderColor = 'var(--lux-border)')}
                />
              </div>

              {error && (
                <div
                  className="px-4 py-3 rounded-lg text-sm"
                  data-testid="signup-otp-error"
                  style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
                >
                  {error}
                </div>
              )}

              <button type="submit" disabled={loading} className="lux-btn w-full justify-center" data-testid="signup-verify-submit">
                {loading ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-pulse" /> Creating studio…
                  </>
                ) : (
                  <>
                    Verify & create account <Crown className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="hover:opacity-80 transition-opacity"
                  style={{ color: 'rgba(255,248,220,0.55)' }}
                  data-testid="signup-back-to-details"
                >
                  ← Edit details
                </button>
                <button
                  type="button"
                  onClick={resendOtp}
                  disabled={loading}
                  className="hover:opacity-80 transition-opacity"
                  style={{ color: '#D4AF37' }}
                  data-testid="signup-resend-otp"
                >
                  Resend OTP
                </button>
              </div>
            </form>
          )}

          {step === 3 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="text-center py-8"
              data-testid="signup-success"
            >
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-5"
                style={{ background: 'radial-gradient(circle at 30% 30%, #E8C766, #8C6A1A)' }}
              >
                <Crown className="w-8 h-8" style={{ color: '#16110C' }} />
              </div>
              <h2 className="font-display text-3xl" style={{ color: '#FFF8DC' }}>
                Studio ready, <span className="text-gold italic font-script">welcome!</span>
              </h2>
              <p className="mt-2 text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
                Redirecting you to the dashboard…
              </p>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
};

export default AdminSignup;
