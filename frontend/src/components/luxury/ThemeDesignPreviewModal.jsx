/**
 * ThemeDesignPreviewModal — Full-screen invitation preview for a SINGLE design.
 *
 * Mirrors the homepage live preview style:
 *   • Full poster image background (no white screen)
 *   • Scrollable invitation card with hero, couple section with photos
 *     animating in from left and right, story, venue, and a footer
 *   • Background music auto-starts at low volume; mute toggle in header
 *   • Smooth slide/fade scroll animations on each section
 */
import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check, Volume2, VolumeX, Heart, Calendar, MapPin, Sparkles } from 'lucide-react';
import UniversalDesignRenderer from '@/themes/UniversalDesignRenderer';

const FALLBACK_PHOTOS = {
  bride: 'https://images.unsplash.com/photo-1610207715090-46c70bbf9d8d?w=600&q=80',
  groom: 'https://images.unsplash.com/photo-1604423481895-66064a2bcd5e?w=600&q=80',
  couple: 'https://images.unsplash.com/photo-1519741497674-611481863552?w=900&q=80',
};

const ThemeDesignPreviewModal = ({
  open, design, theme, themeDesigns, event, couple = {}, onClose, onUse,
}) => {
  const [muted, setMuted] = useState(false);
  const [musicReady, setMusicReady] = useState(false);
  const audioRef = useRef(null);
  const containerRef = useRef(null);

  // Auto-start ambient music
  useEffect(() => {
    if (!open) return;
    const musicUrl = couple?.background_music_url
      || 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3';
    const a = new Audio(musicUrl);
    a.volume = 0.35;
    a.loop = true;
    audioRef.current = a;
    a.play().then(() => setMusicReady(true)).catch(() => setMusicReady(false));
    return () => { try { a.pause(); } catch (_) {} audioRef.current = null; };
  }, [open, couple?.background_music_url]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.muted = muted;
  }, [muted]);

  if (!open || !design) return null;

  const themeTokens = themeDesigns?.tokens || {
    background: '#FDF2D6', accent: '#D4AF37', text: '#2F2F2F',
    heading: '"Cormorant Garamond", serif',
  };

  const bride = couple.bride_name || 'Aanya';
  const groom = couple.groom_name || 'Arjun';
  const date  = couple.wedding_date || '2026-12-15';
  const venue = couple.venue || 'The Leela Palace';
  const couplePhoto = couple.couple_photo_url || FALLBACK_PHOTOS.couple;
  const bridePhoto  = couple.bride_photo_url  || FALLBACK_PHOTOS.bride;
  const groomPhoto  = couple.groom_photo_url  || FALLBACK_PHOTOS.groom;

  const heading = themeTokens.heading || '"Cormorant Garamond", serif';
  const accent  = themeTokens.accent || themeTokens.accentGold || '#D4AF37';
  const bg      = themeTokens.background || '#FDF2D6';
  const isDarkBg = /^#[0-2]/.test(bg);
  const onBgText = isDarkBg ? '#F5ECD7' : '#2F2F2F';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[90] flex items-stretch justify-center"
        style={{ background: 'rgba(8,5,3,0.92)' }}
        onClick={onClose}
        data-testid="design-preview-modal">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.97 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-[1100px] my-6 mx-3 lux-glass overflow-hidden flex flex-col"
          style={{ background: bg, border: '1px solid rgba(212,175,55,0.4)', maxHeight: '95vh' }}>

          {/* Header (sticky) */}
          <div className="flex items-center justify-between gap-3 px-5 py-3 border-b shrink-0"
               style={{ borderColor: 'rgba(0,0,0,0.1)', background: isDarkBg ? 'rgba(8,5,3,0.7)' : 'rgba(255,255,255,0.65)', backdropFilter: 'blur(10px)' }}>
            <div className="min-w-0">
              <div className="lux-eyebrow text-[9px] mb-0.5" style={{ color: accent }}>◆ Live Preview</div>
              <div className="font-display text-base truncate" style={{ color: onBgText, fontFamily: heading }}>
                {theme?.name} · {design.title}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button type="button" onClick={() => setMuted((m) => !m)}
                className="w-9 h-9 rounded-full grid place-items-center"
                style={{ color: onBgText, border: '1px solid rgba(0,0,0,0.15)' }}
                title={muted ? 'Unmute' : 'Mute'}
                data-testid="preview-mute-toggle">
                {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              {onUse && (
                <button type="button" onClick={() => onUse(design)}
                  className="lux-btn text-xs inline-flex items-center gap-1.5"
                  data-testid="preview-use-design">
                  <Check className="w-3.5 h-3.5" /> Use this design
                </button>
              )}
              <button type="button" onClick={onClose}
                className="w-9 h-9 rounded-full grid place-items-center"
                style={{ color: onBgText, border: '1px solid rgba(0,0,0,0.15)' }}
                data-testid="preview-close">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Scrollable content */}
          <div ref={containerRef} className="flex-1 overflow-y-auto" data-testid="preview-scroll-container">
            {/* Hero — render the actual design with the couple data */}
            <div className="relative w-full" style={{ minHeight: '70vh' }}>
              <UniversalDesignRenderer
                design={design}
                theme={{ tokens: themeTokens, motionKey: 'preview' }}
                bride={bride}
                groom={groom}
                date={date}
                venue={venue}
                photo={couplePhoto}
                showText
                eager
                testId="preview-hero-renderer"
              />
            </div>

            {/* Couple photo with slide-in animation */}
            <Section bg={bg} onBgText={onBgText} accent={accent} heading={heading}
                     eyebrow="◆ The Couple" title="Two stories, one chapter">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                <motion.div
                  initial={{ opacity: 0, x: -60 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.3 }}
                  transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                  className="relative overflow-hidden rounded-2xl"
                  data-testid="preview-bride-card">
                  <img src={bridePhoto} alt="Bride"
                       className="w-full object-cover" style={{ aspectRatio: '3/4' }} />
                  <div className="absolute bottom-0 inset-x-0 p-4"
                       style={{ background: 'linear-gradient(180deg, transparent, rgba(0,0,0,0.7))', color: '#FFF8DC' }}>
                    <div className="text-[10px] tracking-[0.3em] uppercase opacity-75">The Bride</div>
                    <div className="font-display text-2xl" style={{ fontFamily: heading }}>{bride}</div>
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, x: 60 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.3 }}
                  transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
                  className="relative overflow-hidden rounded-2xl"
                  data-testid="preview-groom-card">
                  <img src={groomPhoto} alt="Groom"
                       className="w-full object-cover" style={{ aspectRatio: '3/4' }} />
                  <div className="absolute bottom-0 inset-x-0 p-4"
                       style={{ background: 'linear-gradient(180deg, transparent, rgba(0,0,0,0.7))', color: '#FFF8DC' }}>
                    <div className="text-[10px] tracking-[0.3em] uppercase opacity-75">The Groom</div>
                    <div className="font-display text-2xl" style={{ fontFamily: heading }}>{groom}</div>
                  </div>
                </motion.div>
              </div>
            </Section>

            {/* Story */}
            <Section bg={bg} onBgText={onBgText} accent={accent} heading={heading}
                     eyebrow="◆ Our Story" title="Where it all began" alt>
              <motion.p
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                className="text-lg leading-relaxed max-w-2xl mx-auto text-center"
                style={{ color: onBgText, fontFamily: heading }}>
                {couple.story || `It started with a monsoon in Mumbai — a chance umbrella, a shared chai, and a thousand stories yet to write. ${bride} and ${groom} found in each other a partner for every season.`}
              </motion.p>
            </Section>

            {/* Wedding details */}
            <Section bg={bg} onBgText={onBgText} accent={accent} heading={heading}
                     eyebrow="◆ The Day" title="Save the date">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <DetailCard icon={Calendar} label="Date"
                  value={new Date(date).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                  accent={accent} onBgText={onBgText} heading={heading} />
                <DetailCard icon={MapPin} label="Venue" value={venue}
                  accent={accent} onBgText={onBgText} heading={heading} />
              </div>
            </Section>

            {/* Closing */}
            <Section bg={bg} onBgText={onBgText} accent={accent} heading={heading}
                     eyebrow="◆ With love" title="See you there" alt>
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.8 }}
                className="text-center">
                <Heart className="w-8 h-8 mx-auto mb-3" style={{ color: accent }} />
                <p className="font-display text-2xl" style={{ color: onBgText, fontFamily: heading }}>
                  {bride} <span style={{ color: accent }}>&</span> {groom}
                </p>
              </motion.div>
            </Section>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

const Section = ({ children, bg, onBgText, accent, heading, eyebrow, title, alt }) => {
  const bandBg = alt
    ? (bg === '#FDF2D6' ? 'rgba(212,175,55,0.06)' : 'rgba(255,255,255,0.04)')
    : 'transparent';
  return (
    <section className="px-6 md:px-10 py-16" style={{ background: bandBg }}>
      <div className="max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7 }}
          className="mb-6 text-center">
          <span className="text-[10px] tracking-[0.35em] uppercase block mb-3"
                style={{ color: accent }}>{eyebrow}</span>
          <h3 className="font-display text-3xl md:text-4xl"
              style={{ color: onBgText, fontFamily: heading }}>{title}</h3>
        </motion.div>
        {children}
      </div>
    </section>
  );
};

const DetailCard = ({ icon: Icon, label, value, accent, onBgText, heading }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, amount: 0.3 }}
    transition={{ duration: 0.7 }}
    className="p-6 rounded-xl text-center"
    style={{ background: 'rgba(212,175,55,0.08)', border: `1px solid ${accent}33` }}>
    <Icon className="w-6 h-6 mx-auto mb-3" style={{ color: accent }} />
    <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: accent }}>{label}</div>
    <div className="font-display text-lg" style={{ color: onBgText, fontFamily: heading }}>{value}</div>
  </motion.div>
);

export default ThemeDesignPreviewModal;
