import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  Sparkles, ArrowLeft, ArrowRight, Calendar, MapPin, Heart, MessageCircle, Coins,
  Copy, Check, Share2, Download,
} from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { useUserAuth } from '@/context/UserAuthContext';
import { ALL_DESIGNS, useThemeDesigns } from '../themes/allDesigns';
import UniversalDesignRenderer from '../themes/UniversalDesignRenderer';
import { resolveHeroDesign } from '../themes/themeDesignResolver';
import PhotoUploadField from '../components/luxury/PhotoUploadField';
import GuestRoomsEditor from '../components/luxury/GuestRoomsEditor';
import PreWeddingLinksEditor from '../components/luxury/PreWeddingLinksEditor';
import GalleryPrivacyEditor, { validatePrivacy } from '../components/luxury/GalleryPrivacyEditor';
import PublicCreditsModal from '../components/PublicCreditsModal';
import { usePricing } from '../hooks/usePricing';
import { getThemeById } from '../themes/masterThemes';
import { ExternalLink } from 'lucide-react';
import '../styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const EVENT_TYPE_MAP = {
  Engagement: 'engagement',
  Haldi: 'haldi',
  Mehandi: 'mehandi',
  Marriage: 'marriage',
  Reception: 'reception',
  Sangeeth: 'sangeet',
};

const fieldStyle = {
  width: '100%', padding: '0.85rem 1rem', background: 'transparent', color: '#FFF8DC',
  border: '1px solid var(--lux-border)', borderRadius: '0.55rem', outline: 'none',
  caretColor: '#D4AF37', fontSize: '0.95rem',
};

const Field = ({ label, hint, children, testId }) => (
  <label className="block" data-testid={testId ? `field-${testId}` : undefined}>
    <span className="text-[10px] tracking-[0.25em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.6)' }}>
      {label}
    </span>
    {children}
    {hint && <div className="text-[10px] mt-1 italic" style={{ color: 'rgba(255,248,220,0.4)' }}>{hint}</div>}
  </label>
);

/* Feb 2026 — Per-slot photo enable/disable toggle for the user invitation
   form. Mirrors PhotoSlotToggle in LuxuryProfileForm so the experience is
   identical across the photographer and normal-user create flows. */
const UserPhotoSlot = ({ enabled, onToggle, testid, children }) => (
  <div
    className="rounded-lg p-3"
    style={{
      background: enabled ? 'rgba(212,175,55,0.05)' : 'rgba(255,248,220,0.02)',
      border: `1px solid ${enabled ? 'rgba(212,175,55,0.25)' : 'rgba(255,248,220,0.08)'}`,
      transition: 'background 0.25s, border-color 0.25s',
    }}
  >
    <label className="flex items-center gap-2 cursor-pointer mb-2 select-none">
      <input
        type="checkbox"
        checked={!!enabled}
        onChange={(e) => onToggle(e.target.checked)}
        className="sr-only"
        data-testid={testid}
      />
      <span
        role="switch"
        aria-checked={!!enabled}
        className="relative inline-flex items-center w-9 h-5 rounded-full transition-colors shrink-0"
        style={{ background: enabled ? '#D4AF37' : 'rgba(255,248,220,0.15)' }}
      >
        <span
          className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
          style={{ left: 2, transform: enabled ? 'translateX(16px)' : 'translateX(0)' }}
        />
      </span>
      <span className="text-[10px] tracking-[0.22em] uppercase" style={{ color: enabled ? '#E8C766' : 'rgba(255,248,220,0.45)' }}>
        {enabled ? 'Enabled' : 'Disabled · hidden on invitation'}
      </span>
    </label>
    <div style={{ opacity: enabled ? 1 : 0.45, pointerEvents: enabled ? 'auto' : 'none', transition: 'opacity 0.2s' }}>
      {children}
    </div>
  </div>
);


export default function UserInvitationForm() {
  const { themeId, event, designId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, loading, refresh } = useUserAuth();

  // ── Add-ons carried over from PurchaseOptionsWizard via ?addons=a,b,c
  // and ?expiry=1_month.  These are already "paid" in the wizard flow,
  // so we display them as ✓ Purchased — included.
  const purchasedAddonIds = useMemo(() => {
    const raw = searchParams.get('addons') || '';
    return raw.split(',').map((s) => s.trim()).filter(Boolean);
  }, [searchParams]);
  const expiryTierId = searchParams.get('expiry') || null;
  const [addonCatalog, setAddonCatalog] = useState([]);
  const [expiryTiers, setExpiryTiers] = useState([]);

  // PHASE 8: lazy-load this specific theme's design config.
  const themeData = useThemeDesigns(themeId) || ALL_DESIGNS?.[themeId];
  const allEventDesigns = themeData?.events?.[event] || [];
  const design = allEventDesigns.find((d) => d.id === designId);
  const themeRes = resolveHeroDesign(themeId);

  const [cost, setCost] = useState(1);
  const [form, setForm] = useState({
    groom_name: '',
    bride_name: '',
    event_date: '',
    venue: '',
    city: '',
    invitation_message: '',
    whatsapp_groom: '',
    whatsapp_bride: '',
    about_couple: '',
    love_story: '',
    bride_about: '',
    groom_about: '',
    // Joint couple story + ceremony details — surfaced in the rich preview
    // (Together slide + Wedding Details panel). Same fields used by the
    // photographer form.
    couple_about: '',
    nakshatram: '',
    muhurtam: '',
    bride_photo_url: '',
    groom_photo_url: '',
    couple_photo_url: '',
    // Per-photo enable/disable toggles (Feb 2026)
    show_bride_photo: true,
    show_groom_photo: true,
    show_couple_photo: true,
    // Opening (link-open) animation background — picker (couple / bride / groom / custom / none)
    opening_bg_source: 'couple',
    opening_photo_url: '',
    guest_rooms: [],
    pre_wedding_links: [],
    gallery_privacy: { enabled: false, code: '', confirm_code: '', remember_days: 30,
                       public_highlights_enabled: true, private_full_gallery_enabled: true,
                       ai_face_match_enabled: true, allow_downloads: true, allow_share: true,
                       expires_at: '', has_password: false },
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);
  // BUG P FIX: track which add-ons failed to activate after the invitation
  // was created so the success screen can surface a clear warning.
  const [addonFailures, setAddonFailures] = useState([]);
  const [topUpOpen, setTopUpOpen] = useState(false);
  const pricing = usePricing('normal_user');

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) { navigate('/', { replace: true }); return; }
    if (!design) { navigate('/user/create-invitation', { replace: true }); return; }
    axios.get(`${API_URL}/api/public/design-pricing`)
      .then((r) => setCost(r.data?.pricing?.[designId]?.credits ?? 1));
    // Load the add-on catalogue + expiry tiers so we can render the
    // "Purchased — included" badges (and show their human-readable labels).
    if (purchasedAddonIds.length || expiryTierId) {
      Promise.all([
        axios.get(`${API_URL}/api/public/addons`).catch(() => ({ data: { addons: [] } })),
        axios.get(`${API_URL}/api/public/expiry-tiers`).catch(() => ({ data: { tiers: [] } })),
      ]).then(([a, t]) => {
        setAddonCatalog(a.data?.addons || []);
        setExpiryTiers(t.data?.tiers || []);
      });
    }
  }, [loading, user, design, designId, navigate, purchasedAddonIds.length, expiryTierId]);

  /* Feb 2026 — Auto-hide groom + couple photo slots when the event picked
     upstream (in the URL: /user/create-invitation/{theme}/{event}/{design})
     is a single-person ceremony (Haldi or Mehendi). The user can still
     toggle them back on manually via the per-slot switches. */
  const SINGLE_PERSON_EVENTS = ['haldi', 'mehendi', 'mehndi'];
  const isSinglePersonEvent = SINGLE_PERSON_EVENTS.includes((event || '').toLowerCase());
  const eventPresetApplied = useRef(false);
  useEffect(() => {
    if (eventPresetApplied.current) return;
    if (!event) return;
    eventPresetApplied.current = true;
    if (isSinglePersonEvent) {
      setForm((f) => ({
        ...f,
        show_groom_photo: false,
        show_couple_photo: false,
        show_bride_photo: true,
      }));
    }
  }, [event, isSinglePersonEvent]);


  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e?.preventDefault?.();
    setError('');
    if (!form.bride_name.trim() || !form.groom_name.trim()) {
      setError('Please fill bride and groom names.');
      return;
    }
    if (!form.event_date) {
      setError('Please pick the event date.');
      return;
    }
    // Privacy validation
    if (form.gallery_privacy?.enabled) {
      const pvErr = validatePrivacy(form.gallery_privacy);
      if (pvErr) {
        setError(pvErr);
        return;
      }
    }
    setSubmitting(true);
    try {
      const payload = {
        design_id: designId,
        groom_name: form.groom_name.trim(),
        bride_name: form.bride_name.trim(),
        event_type: EVENT_TYPE_MAP[event] || event.toLowerCase(),
        event_date: new Date(form.event_date).toISOString(),
        venue: form.venue.trim(),
        city: form.city.trim(),
        invitation_message: form.invitation_message.trim(),
        whatsapp_groom: form.whatsapp_groom.trim() || null,
        whatsapp_bride: form.whatsapp_bride.trim() || null,
        about_couple: form.about_couple.trim() || null,
        love_story: form.love_story.trim() || null,
        bride_about: form.bride_about.trim() || null,
        groom_about: form.groom_about.trim() || null,
        couple_about: form.couple_about?.trim() || null,
        nakshatram: form.nakshatram?.trim() || null,
        muhurtam: form.muhurtam?.trim() || null,
        bride_photo_url: form.bride_photo_url.trim() || null,
        groom_photo_url: form.groom_photo_url.trim() || null,
        couple_photo_url: form.couple_photo_url.trim() || null,
        show_bride_photo: !!form.show_bride_photo,
        show_groom_photo: !!form.show_groom_photo,
        show_couple_photo: !!form.show_couple_photo,
        // Opening animation background
        opening_bg_source: form.opening_bg_source || 'couple',
        opening_photo_url: form.opening_bg_source === 'custom' ? (form.opening_photo_url || null) : null,
        use_couple_photo_as_opening_bg: (form.opening_bg_source || 'couple') === 'couple',
        guest_rooms: (form.guest_rooms || [])
          .filter((r) => (r.guest_name || '').trim())
          .map((r) => ({
            guest_name: (r.guest_name || '').trim(),
            phone: r.phone || null,
            room_number: r.room_number || null,
            building: r.building || null,
            floor: r.floor || null,
            address: r.address || null,
            map_link: r.map_link || null,
            check_in: r.check_in || null,
            check_out: r.check_out || null,
            notes: r.notes || null,
          })),
        pre_wedding_links: (form.pre_wedding_links || [])
          .filter((l) => (l.url || '').trim())
          .map((l) => ({
            label: (l.label || 'Pre-wedding').trim(),
            url: (l.url || '').trim(),
            kind: l.kind || 'auto',
          })),
        gallery_privacy: form.gallery_privacy?.enabled
          ? {
              enabled: true,
              code: form.gallery_privacy.code,
              confirm_code: form.gallery_privacy.confirm_code,
              remember_days: form.gallery_privacy.remember_days || 30,
              public_highlights_enabled: !!form.gallery_privacy.public_highlights_enabled,
              private_full_gallery_enabled: !!form.gallery_privacy.private_full_gallery_enabled,
              ai_face_match_enabled: !!form.gallery_privacy.ai_face_match_enabled,
              allow_downloads: !!form.gallery_privacy.allow_downloads,
              allow_share: !!form.gallery_privacy.allow_share,
              expires_at: form.gallery_privacy.expires_at || null,
            }
          : null,
      };
      const { data } = await axios.post(`${API_URL}/api/users/profiles`, payload, { withCredentials: true });

      // If the user came through the PurchaseOptionsWizard, charge the
      // selected add-ons against this freshly-created profile so they
      // show up as "purchased" in `profile.add_ons`.
      const newProfile = data?.profile;
      // BUG P FIX: collect (instead of silently swallowing) any add-on
      // purchase failures so the success screen can surface a clear
      // "your invitation was created but add-on X could not be activated"
      // banner. Previously every failure was caught with `catch (_e) {}`,
      // leaving users wondering why their paid add-on never appeared.
      const failedAddons = [];
      if (newProfile?.id && purchasedAddonIds.length > 0) {
        for (const addonId of purchasedAddonIds) {
          try {
            await axios.post(
              `${API_URL}/api/users/profiles/${newProfile.id}/buy-addon`,
              { addon_id: addonId },
              { withCredentials: true },
            );
          } catch (e) {
            const detail = e?.response?.data?.detail;
            failedAddons.push({
              id: addonId,
              reason: (typeof detail === 'string'
                ? detail
                : detail?.error || detail?.message)
                || e?.message
                || 'unknown error',
            });
          }
        }
      }
      if (failedAddons.length > 0) {
        setAddonFailures(failedAddons);
      }

      await refresh?.();
      setSuccess(newProfile);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.error === 'Insufficient credits') {
        setError(`Need ${detail.required} credits — your balance is ${detail.balance}. Buy more to continue.`);
        // Auto-open the top-up modal so the user can buy credits without
        // leaving the wizard — wizard state is preserved.
        setTopUpOpen(true);
      } else if (typeof detail === 'string') {
        if (/insufficient/i.test(detail)) setTopUpOpen(true);
        setError(detail);
      } else {
        setError(err?.message || 'Could not create invitation.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !design || !themeRes) {
    return (
      <div className="luxe min-h-screen grid place-items-center">
        <Sparkles className="w-6 h-6 animate-pulse text-gold" />
      </div>
    );
  }

  if (success) {
    const link = success.invitation_link;
    const fullUrl = `${window.location.origin}${link}`;
    return (
      <InvitationSuccessScreen
        fullUrl={fullUrl}
        link={link}
        navigate={navigate}
        addonFailures={addonFailures}
      />
    );
  }

  return (
    <div className="luxe min-h-screen px-5 md:px-12 py-8 md:py-12" data-testid="user-invitation-form">
      <button
        onClick={() => navigate('/user/create-invitation')}
        className="text-[10px] tracking-[0.25em] uppercase mb-5 inline-flex items-center gap-2 hover:opacity-80"
        style={{ color: 'rgba(255,248,220,0.6)' }}
        data-testid="form-back-btn"
      >
        <ArrowLeft className="w-3 h-3" /> Pick a different design
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Live preview */}
        <div className="order-2 lg:order-1">
          <span className="lux-eyebrow block mb-3">◆ Live Preview</span>
          <div className="max-w-md mx-auto" data-testid="form-live-preview">
            <UniversalDesignRenderer
              design={{ ...themeRes.design, image: design.image, id: design.id }}
              theme={themeRes.theme}
              bride={form.bride_name || ''}
              groom={form.groom_name || ''}
              date={form.event_date ? new Date(form.event_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' }) : ''}
              venue={[form.venue, form.city].filter(Boolean).join(' · ')}
              testId="form-preview-render"
            />
          </div>
          {/* Purchased add-ons summary — only shown if the user came
              through the PurchaseOptionsWizard with ?addons=… */}
          <div className="mt-4 p-4 lux-glass flex items-center justify-between">
            <div>
              <div className="text-[10px] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>This Design</div>
              <div className="font-display text-base mt-0.5" style={{ color: '#FFF8DC' }}>{design.title}</div>
            </div>
            <div className="px-3 py-1.5 rounded-full text-[10px] tracking-[0.2em] uppercase inline-flex items-center gap-1"
              style={{ background: 'linear-gradient(135deg,#D4AF37,#B8941F)', color: '#16110C' }}
            >
              <Coins className="w-3 h-3" /> {cost} credit{cost === 1 ? '' : 's'}
            </div>
          </div>
          {(purchasedAddonIds.length > 0 || expiryTierId) && (
            <div className="lux-glass p-4 mt-4" data-testid="purchased-addons">
              <span className="lux-eyebrow block mb-2">◆ Purchased — included</span>
              <ul className="space-y-1.5 text-xs" style={{ color: 'rgba(255,248,220,0.85)' }}>
                {purchasedAddonIds.map((id) => {
                  const meta = addonCatalog.find((a) => a.id === id);
                  return (
                    <li key={id} className="flex items-center gap-2" data-testid={`purchased-addon-${id}`}>
                      <Check className="w-3.5 h-3.5 text-gold shrink-0" />
                      <span className="flex-1">{meta?.label || id}</span>
                      {meta?.credits != null && (
                        <span className="text-[10px] tracking-[0.18em] uppercase opacity-70">
                          {meta.credits} credit{meta.credits === 1 ? '' : 's'}
                        </span>
                      )}
                    </li>
                  );
                })}
                {expiryTierId && (
                  <li className="flex items-center gap-2" data-testid="purchased-expiry">
                    <Check className="w-3.5 h-3.5 text-gold shrink-0" />
                    <span className="flex-1">
                      Link expiry · {expiryTiers.find((t) => t.id === expiryTierId)?.label || expiryTierId}
                    </span>
                    {expiryTiers.find((t) => t.id === expiryTierId)?.credits != null && (
                      <span className="text-[10px] tracking-[0.18em] uppercase opacity-70">
                        {expiryTiers.find((t) => t.id === expiryTierId).credits} credit{expiryTiers.find((t) => t.id === expiryTierId).credits === 1 ? '' : 's'}
                      </span>
                    )}
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>

        {/* Form */}
        <form className="order-1 lg:order-2 lux-glass p-7 space-y-4" onSubmit={submit}>
          <span className="lux-eyebrow block">◆ Your Story</span>
          <h2 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>
            Fill in the <span className="font-script italic text-gold">details.</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Bride's name *" testId="bride">
              <input style={fieldStyle} required value={form.bride_name} onChange={set('bride_name')} data-testid="input-bride-name" />
            </Field>
            <Field label="Groom's name *" testId="groom">
              <input style={fieldStyle} required value={form.groom_name} onChange={set('groom_name')} data-testid="input-groom-name" />
            </Field>
          </div>

          <Field label="Event date *" testId="date">
            <div className="relative">
              <Calendar className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'rgba(255,248,220,0.5)' }} />
              <input type="date" required value={form.event_date} onChange={set('event_date')} style={{ ...fieldStyle, paddingLeft: '2.6rem' }} data-testid="input-event-date" />
            </div>
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Venue" testId="venue">
              <div className="relative">
                <MapPin className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'rgba(255,248,220,0.5)' }} />
                <input style={{ ...fieldStyle, paddingLeft: '2.6rem' }} value={form.venue} onChange={set('venue')} placeholder="e.g. Falaknuma Palace" data-testid="input-venue" />
              </div>
            </Field>
            <Field label="City" testId="city">
              <input style={fieldStyle} value={form.city} onChange={set('city')} placeholder="e.g. Hyderabad" data-testid="input-city" />
            </Field>
          </div>

          <Field label="Invitation message" testId="message" hint="A short note from the couple — appears under the names.">
            <div className="relative">
              <MessageCircle className="w-4 h-4 absolute left-3.5 top-3 pointer-events-none" style={{ color: 'rgba(255,248,220,0.5)' }} />
              <textarea rows={3} style={{ ...fieldStyle, paddingLeft: '2.6rem' }} value={form.invitation_message} onChange={set('invitation_message')} placeholder="Together with our families…" data-testid="input-message" />
            </div>
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Bride's WhatsApp" testId="wa-bride">
              <input style={fieldStyle} value={form.whatsapp_bride} onChange={set('whatsapp_bride')} placeholder="+91 99999 99999" data-testid="input-whatsapp-bride" />
            </Field>
            <Field label="Groom's WhatsApp" testId="wa-groom">
              <input style={fieldStyle} value={form.whatsapp_groom} onChange={set('whatsapp_groom')} placeholder="+91 99999 99999" data-testid="input-whatsapp-groom" />
            </Field>
          </div>

          <Field label="About the couple" testId="about" hint="Optional — appears on the story section.">
            <textarea rows={3} style={fieldStyle} value={form.about_couple} onChange={set('about_couple')} placeholder="A short biography…" data-testid="input-about" />
          </Field>

          {/* Bride / Groom mini-bios — render next to their portraits */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="About the Bride" testId="bride-about" hint="Optional — appears next to her photo.">
              <textarea rows={3} maxLength={500} style={fieldStyle} value={form.bride_about} onChange={set('bride_about')} placeholder="Her work, her passions, what makes her glow…" data-testid="input-bride-about" />
            </Field>
            <Field label="About the Groom" testId="groom-about" hint="Optional — appears next to his photo.">
              <textarea rows={3} maxLength={500} style={fieldStyle} value={form.groom_about} onChange={set('groom_about')} placeholder="His passions, what makes him laugh, his story…" data-testid="input-groom-about" />
            </Field>
          </div>

          {/* Joint couple story + ceremony details — drives the rich preview's
              Together slide and Wedding Details panel. Optional but encouraged. */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <Field label="Couple Story (joint)" testId="couple-about" hint="Optional — one paragraph about both of you together.">
              <textarea rows={3} maxLength={400} style={fieldStyle} value={form.couple_about} onChange={set('couple_about')} placeholder="How you met, fell in love, decided to spend forever…" data-testid="input-couple-about" />
            </Field>
            <div className="grid grid-cols-1 gap-3">
              <Field label="Nakshatram" testId="nakshatram" hint="e.g. Anuradha & Rohini">
                <input type="text" style={fieldStyle} value={form.nakshatram} onChange={set('nakshatram')} placeholder="Bride / Groom nakshatram" data-testid="input-nakshatram" />
              </Field>
              <Field label="Muhurtam Window" testId="muhurtam" hint="Exact window when the wedding moment is auspicious.">
                <input type="text" style={fieldStyle} value={form.muhurtam} onChange={set('muhurtam')} placeholder="e.g. 11:23 AM – 12:08 PM" data-testid="input-muhurtam" />
              </Field>
            </div>
          </div>

          {/* Photo uploads — drag-and-drop, no profile needed (user endpoint).
              Each slot has a per-block enable toggle (Feb 2026) so haldi /
              mehendi link creators can turn off photos they don't need. */}
          {isSinglePersonEvent && (
            <div
              className="p-3 rounded-lg mb-2"
              style={{ background: 'rgba(212,175,55,0.08)', border: '1px solid rgba(212,175,55,0.3)' }}
              data-testid="single-event-notice"
            >
              <div className="lux-eyebrow" style={{ color: '#E8C766' }}>◆ {event} ceremony</div>
              <p className="text-xs mt-1" style={{ color: 'rgba(255,248,220,0.75)' }}>
                We auto-hide the groom + couple photo slots since this is a single-person ceremony. Toggle them back on below if you want to include them.
              </p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4" data-testid="user-photo-uploads">
            <UserPhotoSlot
              enabled={form.show_bride_photo}
              onToggle={(v) => setForm((f) => ({ ...f, show_bride_photo: v }))}
              testid="toggle-show-bride-photo"
            >
              <PhotoUploadField
                label="Bride photo"
                value={form.bride_photo_url}
                onChange={(url) => setForm((f) => ({ ...f, bride_photo_url: url }))}
                mode="user"
                slot="bride"
                testid="upload-bride-photo"
              />
            </UserPhotoSlot>
            <UserPhotoSlot
              enabled={form.show_groom_photo}
              onToggle={(v) => setForm((f) => ({ ...f, show_groom_photo: v }))}
              testid="toggle-show-groom-photo"
            >
              <PhotoUploadField
                label="Groom photo"
                value={form.groom_photo_url}
                onChange={(url) => setForm((f) => ({ ...f, groom_photo_url: url }))}
                mode="user"
                slot="groom"
                testid="upload-groom-photo"
              />
            </UserPhotoSlot>
            <UserPhotoSlot
              enabled={form.show_couple_photo}
              onToggle={(v) => setForm((f) => ({ ...f, show_couple_photo: v }))}
              testid="toggle-show-couple-photo"
            >
              <PhotoUploadField
                label="Couple photo"
                value={form.couple_photo_url}
                onChange={(url) => setForm((f) => ({ ...f, couple_photo_url: url }))}
                mode="user"
                slot="couple"
                testid="upload-couple-photo"
              />
            </UserPhotoSlot>
          </div>

          {/* Opening (link-open) animation background — picker for the user
              wizard so couples can choose which photo backs the wax-seal
              intro. Mirrors the photographer panel. */}
          <div className="pt-2" data-testid="opening-bg-card">
            <span className="lux-eyebrow block mb-2">◆ Opening animation background</span>
            <p className="text-[11px] mb-3 italic" style={{ color: 'rgba(255,248,220,0.5)' }}>
              Pick the photo that sits behind the wax-seal opening animation when guests first open your link.
            </p>
            <div className="rounded-lg p-4" style={{ background: 'rgba(255,248,220,0.03)', border: '1px solid var(--lux-border)' }}>
              <div className="grid grid-cols-5 gap-2 mb-3">
                {[
                  { key: 'couple', label: 'Couple' },
                  { key: 'bride',  label: 'Bride'  },
                  { key: 'groom',  label: 'Groom'  },
                  { key: 'custom', label: 'Custom' },
                  { key: 'none',   label: 'Off'    },
                ].map((opt) => {
                  const active = (form.opening_bg_source || 'couple') === opt.key;
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, opening_bg_source: opt.key }))}
                      className="px-2 py-2 rounded text-xs tracking-[0.15em] uppercase transition-all"
                      style={{
                        background: active ? 'rgba(212,175,55,0.18)' : 'rgba(255,248,220,0.04)',
                        border: `1px solid ${active ? 'rgba(212,175,55,0.7)' : 'rgba(255,248,220,0.15)'}`,
                        color: active ? '#E8C766' : 'rgba(255,248,220,0.7)',
                      }}
                      data-testid={`opening-bg-source-${opt.key}`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
              {form.opening_bg_source === 'custom' && (
                <div className="mt-3">
                  <p className="text-[10px] tracking-[0.25em] uppercase mb-2" style={{ color: 'rgba(255,248,220,0.55)' }}>
                    Custom opening animation background
                  </p>
                  <PhotoUploadField
                    label="Opening Background"
                    value={form.opening_photo_url}
                    onChange={(url) => setForm((f) => ({ ...f, opening_photo_url: url }))}
                    mode="user"
                    slot="opening"
                    testid="upload-opening-background"
                  />
                </div>
              )}
            </div>
          </div>

          <Field label="Love story" testId="story" hint="Optional — your love story in a paragraph.">
            <div className="relative">
              <Heart className="w-4 h-4 absolute left-3.5 top-3 pointer-events-none" style={{ color: 'rgba(255,248,220,0.5)' }} />
              <textarea rows={3} style={{ ...fieldStyle, paddingLeft: '2.6rem' }} value={form.love_story} onChange={set('love_story')} placeholder="How you met…" data-testid="input-love-story" />
            </div>
          </Field>

          {/* Pre-wedding shoot links */}
          <div className="pt-2">
            <span className="lux-eyebrow block mb-2">◆ Pre-wedding film (Google Drive · YouTube · Vimeo)</span>
            <p className="text-[11px] mb-3 italic" style={{ color: 'rgba(255,248,220,0.5)' }}>
              Optional — paste a shareable Drive link to embed your pre-wedding video on the invitation.
            </p>
            <PreWeddingLinksEditor
              links={form.pre_wedding_links}
              onChange={(links) => setForm((f) => ({ ...f, pre_wedding_links: links }))}
            />
          </div>

          {/* Guest room directory */}
          <div className="pt-2">
            <span className="lux-eyebrow block mb-2">◆ Find My Room · Guest accommodation</span>
            <p className="text-[11px] mb-3 italic" style={{ color: 'rgba(255,248,220,0.5)' }}>
              Optional — add one row per guest. They'll search by name on the invitation to see their room + map.
            </p>
            <GuestRoomsEditor
              rooms={form.guest_rooms}
              onChange={(rooms) => setForm((f) => ({ ...f, guest_rooms: rooms }))}
              compact
            />
          </div>

          {/* Photo privacy / gallery access code */}
          <div className="pt-2">
            <span className="lux-eyebrow block mb-2">◆ Photo Privacy · Lock the gallery</span>
            <p className="text-[11px] mb-3 italic" style={{ color: 'rgba(255,248,220,0.5)' }}>
              Optional — protect your wedding photos with an access code so they stay private even if the link or QR is shared.
            </p>
            <GalleryPrivacyEditor
              value={form.gallery_privacy}
              onChange={(v) => setForm((f) => ({ ...f, gallery_privacy: v }))}
              compact
            />
          </div>

          {error && (
            <div className="px-3 py-2 rounded-md text-xs"
              style={{ background: 'rgba(139,0,0,0.18)', border: '1px solid rgba(139,0,0,0.5)', color: '#FFD7C9' }}
              data-testid="form-error">
              {error}
            </div>
          )}

          {/* Feature-pack upsell (normal_user) — picks the cheapest bundle */}
          <UserFeaturePackUpsell pricing={pricing} />

          {/* Mini live preview thumbnail */}
          {theme && event && (
            <a
              href={`/themes/${theme}/events/${encodeURIComponent(event)}/design/0`}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-xl overflow-hidden transition-transform hover:scale-[1.01]"
              style={{ background: 'rgba(245,236,215,0.04)', border: '1px solid rgba(212,175,55,0.32)' }}
              data-testid="user-mini-preview"
            >
              <div className="flex items-stretch gap-3">
                <div style={{ width: 88, height: 110, background: 'rgba(8,5,3,0.45)' }}>
                  {(form.couple_photo_url || form.bride_photo_url || form.groom_photo_url) && (() => {
                    const raw = form.couple_photo_url || form.bride_photo_url || form.groom_photo_url;
                    const src = raw.startsWith('http')
                      ? raw.replace(/(https?:\/\/[^/]+)\/uploads\//i, `$1/api/uploads/`)
                      : `${API_URL}${raw.startsWith('/uploads/') ? '/api' + raw : raw}`;
                    return (
                      <img src={src} alt="Preview" className="w-full h-full object-cover" />
                    );
                  })()}
                </div>
                <div className="flex-1 py-3 pr-3 min-w-0">
                  <div className="text-[9px] tracking-[0.3em] uppercase mb-0.5" style={{ color: '#D4AF37' }}>◆ Mini preview</div>
                  <div className="font-display text-base truncate" style={{ color: '#FFF8DC' }}>
                    {form.bride_name || 'Bride'} <span className="text-gold italic font-script">&amp;</span> {form.groom_name || 'Groom'}
                  </div>
                  <div className="text-[10px] mt-1" style={{ color: 'rgba(255,248,220,0.6)' }}>
                    {(getThemeById(theme)?.name || theme)} · {event}
                  </div>
                  <div className="text-[10px] tracking-[0.2em] uppercase mt-1.5 inline-flex items-center gap-1" style={{ color: '#FFE38A' }}>
                    Open full preview <ExternalLink className="w-3 h-3" />
                  </div>
                </div>
              </div>
            </a>
          )}

          <div className="flex items-center justify-between gap-4 pt-2">
            <div className="text-xs" style={{ color: 'rgba(255,248,220,0.6)' }}>
              Will charge <span className="text-gold font-semibold">{cost}</span> credit{cost === 1 ? '' : 's'} · balance {user?.credits ?? 0}
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="lux-btn justify-center"
              data-testid="form-submit-btn"
            >
              {submitting ? <><Sparkles className="w-4 h-4 animate-pulse" /> Publishing…</> : <>Publish invitation <ArrowRight className="w-4 h-4" /></>}
            </button>
          </div>
        </form>
      </div>

      {/* Auto-opened on insufficient-credits error. Wizard state stays
          mounted so the user can re-publish after a successful top-up. */}
      <PublicCreditsModal
        open={topUpOpen}
        onClose={() => setTopUpOpen(false)}
        user={user}
        onPurchased={() => { refresh?.(); setTopUpOpen(false); setError(''); }}
      />
    </div>
  );
}

/* Cheapest applicable feature-pack upsell for normal-user audience. */
const UserFeaturePackUpsell = ({ pricing }) => {
  const packs = pricing?.featurePacks || [];
  if (!packs.length) return null;
  const best = packs
    .map((p) => ({ ...p }))
    .sort((a, b) => (a.price - b.price))[0];
  if (!best) return null;
  return (
    <div className="rounded-xl p-4 flex flex-wrap items-start gap-4"
         style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.10) 0%, rgba(212,175,55,0.03) 100%)', border: '1px solid rgba(212,175,55,0.32)' }}
         data-testid="user-feature-pack-upsell">
      <div className="shrink-0 w-12 h-12 rounded-full grid place-items-center"
           style={{ background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.4)' }}>
        <Coins className="w-5 h-5" style={{ color: '#D4AF37' }} />
      </div>
      <div className="flex-1 min-w-[200px]">
        <div className="text-[10px] tracking-[0.3em] uppercase mb-1" style={{ color: '#D4AF37' }}>◆ Bundle &amp; save</div>
        <div className="font-display text-lg" style={{ color: '#FFF8DC' }} data-testid="user-upsell-label">{best.label}</div>
        <div className="text-xs" style={{ color: 'rgba(255,248,220,0.65)' }}>
          {best.feature_keys.length} premium features for <span className="text-gold font-display">{best.price}</span> credits. Buy once, apply to every invitation.
        </div>
      </div>
    </div>
  );
};


function InvitationSuccessScreen({ fullUrl, link, navigate, addonFailures = [] }) {
  const [copied, setCopied] = useState(false);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_e) {
      // fallback: prompt
      window.prompt('Copy this link:', fullUrl);
    }
  };

  const shareLink = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Our Wedding Invitation', url: fullUrl });
      } catch (_e) { /* user cancelled */ }
    } else {
      copyLink();
    }
  };

  const downloadQR = () => {
    const canvas = document.querySelector('[data-testid="success-qr-code"] canvas');
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `invitation-${link.replace(/[^a-z0-9]/gi, '-')}.png`;
    a.click();
  };

  return (
    <div className="luxe min-h-screen grid place-items-center px-5 py-10" data-testid="user-invitation-success">
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        className="lux-glass p-8 md:p-10 max-w-2xl w-full text-center"
      >
        <motion.div
          initial={{ scale: 0, rotate: -15 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.15, type: 'spring', stiffness: 200 }}
        >
          <Sparkles className="w-12 h-12 text-gold mx-auto mb-4" />
        </motion.div>
        <h2 className="font-display text-3xl md:text-4xl mb-3" style={{ color: '#FFF8DC' }}>
          Your invitation is <span className="italic font-script text-gold">live.</span>
        </h2>
        <p className="text-sm mb-8" style={{ color: 'rgba(255,248,220,0.7)' }}>
          Share the link or QR with your loved ones.
        </p>

        {/* BUG P FIX: surface any add-on activation failures so users aren't
            wondering why a paid add-on never appeared on their invitation.
            Previously these were silently swallowed. */}
        {addonFailures.length > 0 && (
          <div
            className="mb-7 px-4 py-3 rounded-md text-left text-xs"
            style={{
              background: 'rgba(190, 120, 30, 0.15)',
              border: '1px solid rgba(190, 120, 30, 0.55)',
              color: '#FFE9C9',
            }}
            data-testid="user-invitation-addon-failures"
          >
            <div className="font-medium mb-1">
              Your invitation is live, but {addonFailures.length === 1 ? 'one add-on' : `${addonFailures.length} add-ons`} could not be activated:
            </div>
            <ul className="list-disc pl-5 space-y-0.5">
              {addonFailures.map((f) => (
                <li key={f.id}>
                  <span className="font-mono">{f.id}</span>
                  {f.reason && <span> — {f.reason}</span>}
                </li>
              ))}
            </ul>
            <div className="mt-2 opacity-90">
              Check your credit balance and re-purchase from the dashboard, or contact support if credits were already deducted.
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-7 items-stretch">
          {/* QR Code */}
          <div
            className="flex flex-col items-center justify-center p-5 rounded-md"
            style={{ background: 'rgba(255,248,220,0.96)', border: '1px solid rgba(212,175,55,0.4)' }}
            data-testid="success-qr-block"
          >
            <div data-testid="success-qr-code" className="bg-white p-2 rounded">
              <QRCodeCanvas
                value={fullUrl}
                size={170}
                fgColor="#1a0e00"
                bgColor="#FFFFFF"
                level="M"
                includeMargin={false}
              />
            </div>
            <button
              onClick={downloadQR}
              className="mt-3 inline-flex items-center gap-1.5 text-[10px] tracking-[0.2em] uppercase hover:opacity-70"
              style={{ color: '#5d4a1a' }}
              data-testid="success-qr-download"
            >
              <Download className="w-3 h-3" /> Download QR
            </button>
          </div>

          {/* Link + actions */}
          <div className="flex flex-col justify-center text-left">
            <div className="text-[10px] tracking-[0.25em] uppercase mb-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>
              Invitation Link
            </div>
            <div
              className="p-3 rounded-md text-xs break-all mb-3"
              style={{
                background: 'rgba(212,175,55,0.08)',
                border: '1px solid rgba(212,175,55,0.25)',
                color: '#D4AF37',
                fontFamily: 'monospace',
              }}
              data-testid="success-invitation-link"
            >
              {fullUrl}
            </div>
            <div className="flex gap-2">
              <button
                onClick={copyLink}
                className="lux-btn lux-btn-ghost flex-1 justify-center text-xs"
                data-testid="success-copy-link"
              >
                {copied ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy link</>}
              </button>
              <button
                onClick={shareLink}
                className="lux-btn lux-btn-ghost flex-1 justify-center text-xs"
                data-testid="success-share-link"
              >
                <Share2 className="w-3 h-3" /> Share
              </button>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            className="lux-btn lux-btn-ghost flex-1 justify-center"
            onClick={() => navigate('/user/dashboard')}
            data-testid="success-back-dashboard"
          >
            Back to studio
          </button>
          <button
            className="lux-btn flex-1 justify-center"
            onClick={() => window.open(link, '_blank')}
            data-testid="success-view-invitation"
          >
            View invitation <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
