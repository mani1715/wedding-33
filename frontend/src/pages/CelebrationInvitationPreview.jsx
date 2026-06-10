/**
 * CelebrationInvitationPreview
 * -----------------------------------------------------------------------------
 * Full live-invitation preview for non-wedding categories (baby_birthday,
 * half_saree, puberty, dhoti).
 *
 * Mirrors what `/preview/theme/:themeId` does for wedding themes — renders the
 * actual `CelebrationPublicView` invitation page with rich sample/mock data so
 * a homepage visitor can SEE exactly what the final invitation will look like
 * without logging in or buying credits.
 *
 *   • Cinematic opening curtain + watermark + mock RSVP + demo blessings are
 *     provided by `CelebrationPublicView` itself when `previewMode=true`. This
 *     wrapper only supplies sample data + the exit URL for the sticky CTA.
 *
 * Route: /preview/celebration/:category   or
 *        /preview/celebration/:category/:designId
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import CelebrationPublicView from '@/components/luxury/CelebrationPublicView';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/* Royalty-free CDN images used as default cover/gallery photos for each
   category. They're hot-linked here — same pattern the wedding sampleData
   uses for couple/bride photos. */
const CDN = (file) => `https://images.unsplash.com/${file}?w=900&q=70&fit=crop`;

const inOneMonth = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  d.setHours(17, 30, 0, 0);
  return d.toISOString();
};

/* Per-category mock data — written so the live preview tells a complete,
   moving story. */
const SAMPLE_DATA = {
  baby_birthday: {
    profile: {
      invitation_category: 'baby_birthday',
      event_date: inOneMonth(),
      venue: 'The Royal Banquet Hall',
      city: 'Hyderabad',
      couple_photo_url: 'photo-1519689680058-324335c77eba',
      celebrant_info: {
        celebrant_name: 'Manvi Sharma',
        nickname: 'Mini',
        nickname_visible: true,
        father_name: 'Aakash Sharma',
        mother_name: 'Priya Sharma',
        age_turning: 1,
        story:
          'A year ago, our world was transformed by a tiny pair of footsteps and the brightest of smiles. ' +
          'Manvi has grown into our little sunshine — from her first giggle, to her first tooth, to her first ' +
          'wobbly step. Come help us celebrate one full year of joy, laughter, and unconditional love.',
        extra_photos: [
          'photo-1519689680058-324335c77eba',
          'photo-1607113256158-56a934936ef1',
          'photo-1543342384-1f1350e27861',
          'photo-1576675784201-0e142b423952',
          'photo-1530577197743-7adf14294584',
          'photo-1556767576-5ec41e3239ea',
        ],
        closing_message: 'Your blessings are her greatest gift. We can\'t wait to celebrate with you!',
      },
      map_settings: { map_link: 'https://www.google.com/maps/search/?api=1&query=Banquet+Hall+Hyderabad' },
    },
  },
  half_saree: {
    profile: {
      invitation_category: 'half_saree',
      event_date: inOneMonth(),
      venue: 'Sri Krishna Kalyana Mandapam',
      city: 'Chennai',
      couple_photo_url: 'photo-1581368087033-1d29f31a8b5f',
      celebrant_info: {
        celebrant_name: 'Meera Karthik',
        father_name: 'Karthik Iyer',
        mother_name: 'Lakshmi Iyer',
        story:
          'Today our little girl steps into a new chapter — draped in her first half-saree, blessed by ' +
          'family, music and tradition. From plaits of jasmine to silk and gold, every detail tells a story ' +
          'of love. We invite you to share this sacred moment with us.',
        extra_photos: [
          'photo-1581368087033-1d29f31a8b5f',
          'photo-1492288991661-058aa541ff43',
          'photo-1583394293214-28ded15ee548',
          'photo-1631049551717-1a2d5c52ca7d',
          'photo-1610030469983-98e550d6193c',
        ],
        closing_message: 'Bless our Meera with your love, presence and prayers.',
      },
      map_settings: { map_link: 'https://www.google.com/maps/search/?api=1&query=Sri+Krishna+Kalyana+Mandapam+Chennai' },
    },
  },
  puberty: {
    profile: {
      invitation_category: 'puberty',
      event_date: inOneMonth(),
      venue: 'Sri Meenakshi Mandapam',
      city: 'Coimbatore',
      couple_photo_url: 'photo-1604608672516-f1b9b0c83b62',
      celebrant_info: {
        celebrant_name: 'Anika Sundar',
        father_name: 'Sundar Murali',
        mother_name: 'Priya Sundar',
        story:
          'Our daughter has reached a sacred milestone. Surrounded by turmeric, blessings and family, ' +
          'we mark this beautiful coming-of-age — a threshold between childhood and grace. Join us in ' +
          'showering Anika with your warmest wishes.',
        extra_photos: [
          'photo-1604608672516-f1b9b0c83b62',
          'photo-1581368087033-1d29f31a8b5f',
          'photo-1583394293214-28ded15ee548',
          'photo-1631049551717-1a2d5c52ca7d',
        ],
        closing_message: 'Your blessings light the path ahead.',
      },
      map_settings: { map_link: 'https://www.google.com/maps/search/?api=1&query=Sri+Meenakshi+Mandapam+Coimbatore' },
    },
  },
  dhoti: {
    profile: {
      invitation_category: 'dhoti',
      event_date: inOneMonth(),
      venue: 'Anjaneyar Temple Mandapam',
      city: 'Madurai',
      couple_photo_url: 'photo-1503301360699-d3e2003af3bf',
      celebrant_info: {
        celebrant_name: 'Arjun Vasanth',
        father_name: 'Vasanth Krishnan',
        mother_name: 'Geetha Vasanth',
        story:
          'Today our young man dons the dhoti for the first time — a proud moment of tradition, family ' +
          'and growing up. From childhood\'s small steps to standing tall in our heritage, we celebrate ' +
          'every chapter of Arjun\'s journey. Be with us as he begins this new one.',
        extra_photos: [
          'photo-1503301360699-d3e2003af3bf',
          'photo-1604608672516-f1b9b0c83b62',
          'photo-1581368087033-1d29f31a8b5f',
          'photo-1631049551717-1a2d5c52ca7d',
        ],
        closing_message: 'Your presence is our pride.',
      },
      map_settings: { map_link: 'https://www.google.com/maps/search/?api=1&query=Anjaneyar+Temple+Madurai' },
    },
  },
};

/** Convert raw unsplash IDs to fully-resolved CDN URLs in the sample data
 *  shape so CelebrationPublicView's `resolveUrl()` leaves them alone. */
const hydrateSample = (sample) => {
  if (!sample) return null;
  const p = { ...sample.profile };
  if (p.couple_photo_url && !p.couple_photo_url.startsWith('http')) {
    p.couple_photo_url = CDN(p.couple_photo_url);
  }
  if (p.celebrant_info?.extra_photos) {
    p.celebrant_info = {
      ...p.celebrant_info,
      extra_photos: p.celebrant_info.extra_photos.map((u) =>
        u && !u.startsWith('http') ? CDN(u) : u,
      ),
    };
  }
  return p;
};

const CelebrationInvitationPreview = () => {
  const { category, designId } = useParams();
  const [designMeta, setDesignMeta] = useState(null);

  // OPTIONAL — pull the design's cover image so the hero/cover uses the
  // chosen design's artwork rather than the generic CDN photo. Best-effort.
  useEffect(() => {
    if (!category || !designId) return;
    let alive = true;
    (async () => {
      try {
        const res = await axios.get(`${API_URL}/api/event-categories/${category}/designs`);
        if (!alive) return;
        const match = (res?.data?.designs || []).find((d) => d.design_id === designId);
        if (match) setDesignMeta(match);
      } catch (_) { /* swallow */ }
    })();
    return () => { alive = false; };
  }, [category, designId]);

  const sample = SAMPLE_DATA[category] || SAMPLE_DATA.baby_birthday;
  const profile = useMemo(() => {
    const base = hydrateSample(sample);
    if (designMeta?.preview_image) {
      const cover = designMeta.preview_image.startsWith('http')
        ? designMeta.preview_image
        : `${API_URL}${designMeta.preview_image}`;
      return { ...base, couple_photo_url: cover };
    }
    return base;
  }, [sample, designMeta]);

  const exitTo = designId
    ? `/user/buy-celebration/${category}/${encodeURIComponent(designId)}`
    : null;

  if (!sample) {
    return (
      <div className="min-h-screen grid place-items-center bg-black text-white">
        <p>{`No preview available for "${category}".`}</p>
      </div>
    );
  }

  return (
    <div className="relative" data-testid="celebration-invitation-preview-page"
      data-category={category}>
      <CelebrationPublicView
        data={profile}
        previewMode={true}
        previewExitTo={exitTo}
      />
    </div>
  );
};

export default CelebrationInvitationPreview;
