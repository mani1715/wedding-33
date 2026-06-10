/**
 * NonWeddingDesignCard — visual mirror of the wedding theme card on the
 * landing page, but for non-wedding categories (baby birthday, half saree,
 * puberty, dhoti).
 *
 * The wedding card uses UniversalDesignRenderer (which renders the actual
 * design + animated overlays + couple text). Non-wedding designs are static
 * background art (no overlay system). So this component recreates the same
 * "live invitation" look by overlaying:
 *   • a top eyebrow line  (◇ FIRST BIRTHDAY ◇)
 *   • a circular celebrant photo bubble in the upper third
 *   • a soft cream / accent gradient band at the bottom containing
 *     "WITH BLESSINGS FROM OUR FAMILY", the celebrant name, date and venue.
 *
 * The styling, aspect ratio and motion timings match the wedding theme card
 * exactly so the two grids look like siblings.
 */
import React from 'react';
import { motion } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const resolveImg = (u) => {
  if (!u) return '';
  if (u.startsWith('http') || u.startsWith('data:') || u.startsWith('blob:')) return u;
  return `${API_URL}${u.startsWith('/') ? '' : '/'}${u}`;
};

/* Per-category sample data — written so each preview tells a complete
   little story, exactly like the wedding cards do (Anaya & Rohan, etc.) */
const CATEGORY_SAMPLES = {
  baby_birthday: [
    {
      eyebrow: 'First Birthday',
      familyLine: 'With Blessings From Our Family',
      celebrant: 'Manvi',
      date: 'Saturday, 15 August 2026',
      venue: 'The Royal Banquet · Hyderabad',
      accent: '#FF69B4',
      panelTint: 'rgba(255,235,243,0.94)',
      panelText: '#3B1E2B',
    },
    {
      eyebrow: 'A Joyful Year',
      familyLine: 'Together With Our Family',
      celebrant: 'Aarav',
      date: 'Sunday, 22 November 2026',
      venue: 'Lotus Pavilion · Chennai',
      accent: '#87CEEB',
      panelTint: 'rgba(232,244,253,0.94)',
      panelText: '#162B3C',
    },
    {
      eyebrow: 'Tiny Toes Tiny Heart',
      familyLine: 'With Joy We Invite You',
      celebrant: 'Ananya',
      date: 'Saturday, 10 October 2026',
      venue: 'Maple Hall · Bengaluru',
      accent: '#FFB347',
      panelTint: 'rgba(255,244,224,0.94)',
      panelText: '#3B2A14',
    },
  ],
  half_saree: [
    {
      eyebrow: 'Half Saree Ceremony',
      familyLine: 'Together With Our Family',
      celebrant: 'Meera',
      date: 'Friday, 10 July 2026',
      venue: 'Sri Krishna Mandapam · Chennai',
      accent: '#C71585',
      panelTint: 'rgba(255,232,243,0.94)',
      panelText: '#3B0F2B',
    },
    {
      eyebrow: 'Pavadai Daavani',
      familyLine: 'With Blessings From Our Family',
      celebrant: 'Hasini',
      date: 'Sunday, 16 August 2026',
      venue: 'Padmavati Hall · Tirupati',
      accent: '#FFD700',
      panelTint: 'rgba(255,248,220,0.94)',
      panelText: '#3B2E14',
    },
  ],
  puberty: [
    {
      eyebrow: 'Manjal Neerattu',
      familyLine: 'With Blessings From Our Family',
      celebrant: 'Anika',
      date: 'Sunday, 21 June 2026',
      venue: 'Andal Mahal · Madurai',
      accent: '#FF8C00',
      panelTint: 'rgba(255,240,224,0.94)',
      panelText: '#3B1F0F',
    },
    {
      eyebrow: 'Coming Of Age',
      familyLine: 'Together With Our Family',
      celebrant: 'Vaishnavi',
      date: 'Saturday, 7 September 2026',
      venue: 'Lakshmi Vilas · Salem',
      accent: '#D4AF37',
      panelTint: 'rgba(255,248,220,0.94)',
      panelText: '#3B2814',
    },
  ],
  dhoti: [
    {
      eyebrow: 'Vetti Kattum Vizha',
      familyLine: 'Together With Our Family',
      celebrant: 'Arjun',
      date: 'Saturday, 16 May 2026',
      venue: 'Sri Sankara Hall · Coimbatore',
      accent: '#7B68EE',
      panelTint: 'rgba(232,232,255,0.94)',
      panelText: '#1A1A3B',
    },
    {
      eyebrow: 'Dhoti Ceremony',
      familyLine: 'With Blessings From Our Family',
      celebrant: 'Karthik',
      date: 'Sunday, 28 June 2026',
      venue: 'Subramanya Hall · Madurai',
      accent: '#D4AF37',
      panelTint: 'rgba(255,248,220,0.94)',
      panelText: '#3B2814',
    },
  ],
};

/* Sample celebrant photo (single image used as the bubble photo for every
   card — same pattern wedding cards use for the couple photo). */
const SAMPLE_PHOTO = 'https://images.unsplash.com/photo-1519689680058-324335c77eba?w=300&h=300&fit=crop&q=80';

const getSample = (category, index) => {
  const samples = CATEGORY_SAMPLES[category] || CATEGORY_SAMPLES.baby_birthday;
  return samples[index % samples.length];
};

const NonWeddingDesignCard = ({ design, category, index = 0, photo }) => {
  const sample = getSample(category, index);
  const heroPhoto = photo || SAMPLE_PHOTO;
  const accent = sample.accent;
  const panelBg = sample.panelTint;
  const panelText = sample.panelText;

  return (
    <div
      className="relative w-full overflow-hidden rounded-md transition-transform duration-300 group-hover:scale-[1.01]"
      style={{ aspectRatio: '3 / 4', background: '#161210' }}
      data-testid={`non-wedding-card-preview-${design.design_id}`}
    >
      {/* Base art (the actual design image — kept full-bleed) */}
      <img
        src={resolveImg(design.preview_image || design.thumbnail)}
        alt={design.name}
        loading="lazy"
        className="absolute inset-0 w-full h-full object-cover"
        onError={(e) => { e.currentTarget.style.opacity = 0.6; }}
      />

      {/* Soft top wash so the eyebrow stays readable on busy art */}
      <div
        className="absolute top-0 inset-x-0 h-24 pointer-events-none"
        style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 100%)' }}
      />

      {/* Top eyebrow — diamond decorations match the wedding cards */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
        className="absolute top-5 inset-x-0 text-center px-3 z-10"
      >
        <span
          className="font-display text-[11px] sm:text-xs tracking-[0.42em] uppercase"
          style={{ color: panelText, textShadow: '0 1px 6px rgba(255,255,255,0.4)' }}
        >
          ◇ {sample.eyebrow} ◇
        </span>
      </motion.div>

      {/* Celebrant photo bubble — same circular framing the wedding cards use */}
      <motion.div
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.25 }}
        className="absolute z-10"
        style={{ top: '22%', left: '50%', transform: 'translateX(-50%)' }}
      >
        <div
          className="w-20 h-20 sm:w-24 sm:h-24 rounded-full overflow-hidden"
          style={{
            border: `3px solid ${accent}`,
            boxShadow: '0 6px 22px rgba(0,0,0,0.35), inset 0 0 0 3px rgba(255,255,255,0.85)',
            background: `url(${heroPhoto}) center/cover`,
          }}
        />
        {/* Tiny decorative dots ringing the bubble — mimics wedding photo dial */}
        <div
          className="absolute -inset-2 rounded-full pointer-events-none"
          style={{ border: `1px dashed ${accent}80` }}
        />
      </motion.div>

      {/* Bottom invitation panel — cream/tinted band with celebrant name + date */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.95, ease: [0.22, 1, 0.36, 1], delay: 0.35 }}
        className="absolute bottom-0 inset-x-0 px-4 pt-12 pb-5 text-center"
        style={{
          background: `linear-gradient(180deg, rgba(255,255,255,0) 0%, ${panelBg} 38%, ${panelBg} 100%)`,
        }}
      >
        <span
          className="block text-[9px] sm:text-[10px] tracking-[0.32em] uppercase mb-1.5"
          style={{ color: `${panelText}AA` }}
        >
          {sample.familyLine}
        </span>
        <h4
          className="font-display leading-tight"
          style={{
            color: panelText,
            fontFamily: '"Cormorant Garamond", serif',
            fontSize: 'clamp(1.4rem, 2.2vw, 1.8rem)',
            fontWeight: 600,
          }}
        >
          {sample.celebrant}
        </h4>
        <span
          className="block text-[10px] sm:text-[11px] tracking-[0.28em] uppercase mt-2"
          style={{ color: panelText }}
        >
          {sample.date}
        </span>
        <span
          className="block text-[9px] sm:text-[10px] tracking-[0.22em] uppercase mt-1.5"
          style={{ color: `${panelText}99` }}
        >
          {sample.venue}
        </span>
      </motion.div>
    </div>
  );
};

export default NonWeddingDesignCard;
