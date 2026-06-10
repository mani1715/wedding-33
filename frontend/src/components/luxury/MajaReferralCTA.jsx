import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { ArrowUpRight, Camera, Sparkles } from 'lucide-react';
import { useInvitePrefetch } from '@/context/InvitePrefetchContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * MAJA Creations — Photographer-Referral Viral CTA
 * Subtle, luxe, on-brand. Shows once at the bottom of the public invitation.
 * Tracks via referral_code if available; otherwise plain signup.
 */
const MajaReferralCTA = ({ slug }) => {
  const prefetch = useInvitePrefetch(slug);
  const [code, setCode] = useState(prefetch?.referral_code || null);

  useEffect(() => {
    if (!slug) return;
    // Skip network if /full already provided the referral code (or null).
    if (prefetch && 'referral_code' in prefetch) {
      setCode(prefetch.referral_code || null);
      return;
    }
    axios.get(`${API_URL}/api/public/referral-code-by-slug/${slug}`)
      .then((r) => setCode(r.data?.referral_code || null))
      .catch(() => setCode(null));
  }, [slug, prefetch]);

  const signupUrl = code
    ? `${window.location.origin}/admin/login?ref=${code}`
    : `${window.location.origin}/admin/login`;

  return (
    <section className="px-6 md:px-12 py-20 md:py-24 relative" data-testid="public-maja-cta">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.1 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-3xl mx-auto lux-glass p-8 md:p-12 text-center relative overflow-hidden"
      >
        {/* gilt corner ornament */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-10"
             style={{ background: 'linear-gradient(to bottom, transparent, var(--lux-gold, #D4AF37))' }} />

        <motion.span
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, amount: 0.1 }}
          className="lux-eyebrow block mb-3">◆ For photographers &amp; planners</motion.span>

        <motion.h3
          initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }}
          transition={{ delay: 0.1, duration: 0.7 }}
          className="font-display text-[1.8rem] md:text-[2.6rem] leading-[1.1]"
          style={{ color: '#FFF8DC' }}>
          Crafted on <span className="font-script italic text-gold">MAJA</span>
        </motion.h3>

        <motion.p
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, amount: 0.1 }}
          transition={{ delay: 0.2 }}
          className="mt-3 max-w-xl mx-auto text-sm md:text-[15px] leading-relaxed italic"
          style={{ color: 'rgba(255,248,220,0.7)' }}>
          MAJA Creations is the AI-powered wedding experience platform built for Indian photographers — cinematic invitations, live photo walls, smart RSVPs &amp; WhatsApp at scale.
        </motion.p>

        {code && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true, amount: 0.1 }}
            transition={{ delay: 0.3 }}
            className="mt-5 inline-flex items-center gap-3 px-4 py-2 rounded-full"
            style={{ background: 'rgba(212,175,55,0.08)', border: '1px solid var(--lux-border-strong, rgba(212,175,55,0.4))' }}
            data-testid="public-maja-cta-code">
            <Sparkles className="w-3.5 h-3.5 text-gold" />
            <span className="text-[11px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.8)' }}>
              Sign up with code
            </span>
            <code className="font-mono text-sm tracking-wider px-2 py-0.5 rounded"
              style={{ background: 'rgba(212,175,55,0.18)', color: '#FFF8DC' }}>{code}</code>
            <span className="text-[11px] tracking-[0.25em] uppercase text-gold">50 free credits</span>
          </motion.div>
        )}

        <motion.a
          href={signupUrl}
          target="_blank" rel="noopener noreferrer"
          initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }}
          transition={{ delay: 0.4 }}
          whileHover={{ y: -3 }}
          className="lux-btn inline-flex items-center gap-2 mt-7"
          data-testid="public-maja-cta-button">
          <Camera className="w-4 h-4" /> See how this was made <ArrowUpRight className="w-3.5 h-3.5" />
        </motion.a>

        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-10"
             style={{ background: 'linear-gradient(to top, transparent, var(--lux-gold, #D4AF37))' }} />
      </motion.div>
    </section>
  );
};

export default MajaReferralCTA;
