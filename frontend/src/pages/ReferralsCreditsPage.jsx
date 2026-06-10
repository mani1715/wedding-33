import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Gift, Wallet, Sparkles, Crown, TrendingUp } from 'lucide-react';
import ReferralDashboard from '../components/ReferralDashboard';
import CreditWallet from '../components/CreditWallet';
import '@/styles/luxury.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30, filter: 'blur(8px)' },
  visible: (i = 0) => ({
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.95, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
  }),
};

/**
 * Prompt 20 — Credits & Monetization (luxury edition)
 */
const ReferralsCreditsPage = () => {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('credits');

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => {};
  }, []);

  return (
    <div className="luxe min-h-screen relative" data-testid="referrals-credits-page">
      <div className="lux-orbit" style={{ width: 800, height: 800, top: -260, left: -260 }} />
      <div className="lux-orbit" style={{ width: 1100, height: 1100, top: -360, left: -360, opacity: 0.35 }} />

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 md:px-12 py-10">
        <button
          onClick={() => navigate('/admin/dashboard')}
          className="lux-btn lux-btn-ghost text-xs mb-6"
          data-testid="rc-back"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Studio
        </button>

        <motion.div variants={fadeUp} initial="hidden" animate="visible" className="mb-10">
          <span className="lux-eyebrow block mb-4">◆ Studio Treasury · Credit Vault</span>
          <h1 className="font-display text-[2.6rem] md:text-[4.2rem] leading-[1.04]" style={{ color: '#FFF8DC' }}>
            Bless every wedding<br/>
            with <span className="text-gold font-script italic">cinematic</span> credits.
          </h1>
          <p className="mt-5 max-w-2xl text-base" style={{ color: 'rgba(255,248,220,0.65)' }}>
            Each credit publishes one royal invitation. Credits never expire. Drafts are free —
            you only spend when a wedding goes live.
          </p>
        </motion.div>

        {/* Tabs */}
        <motion.div
          variants={fadeUp} initial="hidden" animate="visible" custom={1}
          className="flex flex-wrap gap-2 mb-8"
        >
          {[
            { id: 'credits',   label: 'Credit Wallet', icon: Wallet, eyebrow: 'Treasury' },
            { id: 'referrals', label: 'Referrals',     icon: Gift,   eyebrow: 'Earn More' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="group inline-flex items-center gap-2.5 px-5 py-3 rounded-full transition-all"
              style={activeTab === t.id
                ? { background: 'linear-gradient(135deg, #B8902B 0%, #D4AF37 60%, #E8C766 100%)', color: '#16110C', fontWeight: 600 }
                : { background: 'transparent', border: '1px solid var(--lux-border)', color: 'rgba(255,248,220,0.85)' }}
              data-testid={`rc-tab-${t.id}`}
            >
              <t.icon className="w-4 h-4" />
              <span className="text-xs tracking-[0.2em] uppercase">{t.label}</span>
            </button>
          ))}
        </motion.div>

        {/* Plans showcase strip (visual only) */}
        <motion.div
          variants={fadeUp} initial="hidden" animate="visible" custom={2}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12"
        >
          {[
            { name: 'Starter',     credits: '3',  price: '₹5,000',  popular: false },
            { name: 'Professional',credits: '10', price: '₹15,000', popular: true },
            { name: 'Studio',      credits: '25', price: '₹30,000', popular: false },
            { name: 'Platinum',    credits: '50', price: '₹50,000', popular: false },
          ].map((p, i) => (
            <motion.div
              key={p.name}
              whileHover={{ y: -6 }}
              className="lux-glass p-6 relative"
              style={p.popular ? { borderColor: 'var(--lux-gold)', background: 'rgba(212,175,55,0.07)' } : undefined}
              data-testid={`rc-plan-${p.name.toLowerCase()}`}
            >
              {p.popular && (
                <span className="absolute -top-2.5 right-4 text-[9px] tracking-[0.3em] uppercase px-2 py-1 rounded-full"
                  style={{ color: '#16110C', background: '#D4AF37' }}>
                  Most Picked
                </span>
              )}
              <div className="font-display text-5xl text-gold mb-1">{p.credits}</div>
              <div className="text-[0.7rem] tracking-[0.25em] uppercase mb-3" style={{ color: 'rgba(255,248,220,0.55)' }}>credits</div>
              <div className="lux-hairline my-3" />
              <div className="flex items-end justify-between">
                <span className="font-heading text-lg" style={{ color: '#FFF8DC' }}>{p.name}</span>
                <span className="font-display text-xl" style={{ color: '#FFF8DC' }}>{p.price}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="lux-glass p-6 md:p-10"
        >
          {activeTab === 'referrals' && <ReferralDashboard profileId={profileId} />}
          {activeTab === 'credits' && <CreditWallet profileId={profileId} />}
        </motion.div>

        {/* Trust strip */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Crown, title: 'Never Expire', copy: 'Credits stay yours forever — no monthly burn.' },
            { icon: Sparkles, title: 'Free Drafts',  copy: 'Build as many drafts as you wish. Pay only on publish.' },
            { icon: TrendingUp, title: 'Referral Bonus', copy: 'Earn extra credits when peers join through your link.' },
          ].map((t, i) => (
            <motion.div
              key={t.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: i * 0.08 }}
              viewport={{ once: true, amount: 0.1 }}
              className="lux-glass p-5 flex items-start gap-3"
            >
              <div className="w-10 h-10 rounded-xl grid place-items-center"
                style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(139,0,0,0.18))', border: '1px solid var(--lux-border-strong)' }}>
                <t.icon className="w-4 h-4" style={{ color: '#D4AF37' }} strokeWidth={1.6} />
              </div>
              <div>
                <div className="font-heading text-base mb-0.5" style={{ color: '#FFF8DC' }}>{t.title}</div>
                <div className="text-xs leading-relaxed" style={{ color: 'rgba(255,248,220,0.6)' }}>{t.copy}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReferralsCreditsPage;
