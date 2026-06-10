import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Camera, Heart, Upload, X, Download, Share2, Loader2 } from 'lucide-react';
import '@/styles/luxury.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Persistent guest device id (for favorites)
const getDeviceId = () => {
  let id = localStorage.getItem('mh_device_id');
  if (!id) {
    id = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('mh_device_id', id);
  }
  return id;
};

const fadeUp = {
  hidden: { opacity: 0, y: 18, filter: 'blur(6px)' },
  visible: (i = 0) => ({
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.7, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] },
  }),
};

const LivePhotoWall = () => {
  const { slug } = useParams();
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [total, setTotal] = useState(0);
  const sinceRef = useRef(null);
  const deviceId = useRef(getDeviceId());

  useEffect(() => {
    document.body.classList.add('luxe', 'luxe-grain', 'luxe-vignette');
    return () => document.body.classList.remove('luxe', 'luxe-grain', 'luxe-vignette');
  }, []);

  const fetchPhotos = useCallback(async (initial = false) => {
    try {
      const params = {};
      if (!initial && sinceRef.current) params.since = sinceRef.current;
      const res = await axios.get(`${API_URL}/api/invite/${slug}/live-gallery`, { params });
      const newPhotos = res.data.photos || [];
      setTotal(res.data.total || 0);
      sinceRef.current = res.data.fetched_at;
      if (initial) {
        setPhotos(newPhotos);
      } else if (newPhotos.length > 0) {
        setPhotos((prev) => [...newPhotos, ...prev]);
      }
    } catch (e) {
      console.error('Live gallery error', e);
    } finally {
      if (initial) setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    fetchPhotos(true);
    const interval = setInterval(() => fetchPhotos(false), 8000);
    return () => clearInterval(interval);
  }, [fetchPhotos]);

  const toggleFavorite = async (photo) => {
    try {
      const res = await axios.post(`${API_URL}/api/invite/${slug}/live-gallery/favorite`, {
        photo_id: photo.id, device_id: deviceId.current,
      });
      setPhotos((p) => p.map((x) => x.id === photo.id
        ? { ...x, favorite_count: x.favorite_count + (res.data.favorited ? 1 : -1) }
        : x));
    } catch (e) { /* ignore */ }
  };

  return (
    <div className="luxe min-h-screen" data-testid="live-photo-wall">
      {/* Hero */}
      <motion.div
        initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.07 } } }}
        className="px-6 md:px-12 pt-12 md:pt-16 pb-8 max-w-[1400px] mx-auto"
      >
        <motion.span variants={fadeUp} className="lux-eyebrow block mb-4">◆ Live Photo Wall</motion.span>
        <motion.h1 variants={fadeUp} custom={1}
          className="font-display text-[2.2rem] md:text-[3.6rem] leading-[1.05] tracking-tight"
          style={{ color: '#FFF8DC' }}>
          Moments from the <span className="font-script italic text-gold">celebration</span>
        </motion.h1>
        <motion.p variants={fadeUp} custom={2} className="mt-4 max-w-xl text-[0.98rem]"
          style={{ color: 'rgba(255,248,220,0.62)' }}>
          As our photographer captures the day, the gallery updates here in real time.
          Tap a photo to view it, double-tap to favorite, or upload yours.
        </motion.p>
        <motion.div variants={fadeUp} custom={3} className="mt-6 flex flex-wrap items-center gap-3">
          <div className="px-4 py-1.5 rounded-full inline-flex items-center gap-2"
            style={{ border: '1px solid var(--lux-border-strong)', background: 'rgba(212,175,55,0.06)' }}>
            <Camera className="w-3.5 h-3.5 text-gold" />
            <span className="text-xs tracking-[0.2em] uppercase" style={{ color: 'rgba(255,248,220,0.7)' }}>
              {total} photos
            </span>
          </div>
          <button onClick={() => setUploadOpen(true)} className="lux-btn" data-testid="lpw-upload-btn">
            <Upload className="w-4 h-4" /> Upload your photo
          </button>
        </motion.div>
      </motion.div>

      {/* Grid */}
      <div className="px-6 md:px-12 pb-20 max-w-[1400px] mx-auto">
        {loading ? (
          <div className="grid place-items-center py-32"><div className="lux-mandala" /></div>
        ) : photos.length === 0 ? (
          <div className="lux-glass p-14 text-center">
            <Camera className="w-7 h-7 mx-auto mb-4 text-gold" />
            <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>The wall is awake</h3>
            <p className="text-sm" style={{ color: 'rgba(255,248,220,0.6)' }}>
              Photos will appear here the moment the photographer captures them.
            </p>
          </div>
        ) : (
          <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
            <AnimatePresence>
              {photos.map((p, i) => (
                <motion.div key={p.id}
                  layout
                  initial={{ opacity: 0, scale: 0.96, filter: 'blur(8px)' }}
                  animate={{ opacity: 1, scale: 1, filter: 'blur(0)' }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.55, delay: Math.min(i, 12) * 0.025, ease: [0.22, 1, 0.36, 1] }}
                  className="break-inside-avoid relative group cursor-pointer overflow-hidden rounded-lg"
                  style={{ border: '1px solid var(--lux-border)' }}
                  onClick={() => setLightbox(p)}
                  data-testid={`lpw-photo-${p.id}`}
                >
                  <img src={`${API_URL}${p.thumb_url}`} alt={p.caption || 'wedding moment'}
                    loading="lazy"
                    className="w-full h-auto block transition-transform duration-700 group-hover:scale-[1.04]" />
                  <div className="absolute bottom-0 left-0 right-0 px-3 py-2 flex items-center justify-between"
                    style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.6), transparent)' }}>
                    <span className="text-[10px] tracking-[0.15em] uppercase truncate"
                      style={{ color: 'rgba(255,248,220,0.8)' }}>
                      {p.uploader_name || 'Photographer'}
                    </span>
                    <button onClick={(e) => { e.stopPropagation(); toggleFavorite(p); }}
                      className="inline-flex items-center gap-1 text-xs"
                      style={{ color: '#FFD7C9' }}
                      data-testid={`lpw-fav-${p.id}`}>
                      <Heart className="w-3.5 h-3.5" /> {p.favorite_count || 0}
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <AnimatePresence>
        {lightbox && <Lightbox photo={lightbox} onClose={() => setLightbox(null)} slug={slug} />}
      </AnimatePresence>

      <AnimatePresence>
        {uploadOpen && (
          <GuestUploader slug={slug} onClose={() => setUploadOpen(false)} onUploaded={() => fetchPhotos(false)} />
        )}
      </AnimatePresence>
    </div>
  );
};

const Lightbox = ({ photo, onClose, slug }) => {
  const share = async () => {
    const url = `${window.location.origin}/invite/${slug}/live-gallery`;
    if (navigator.share) {
      try { await navigator.share({ title: 'Live Wedding Gallery', url }); } catch (_) {}
    } else {
      try { await navigator.clipboard.writeText(url); } catch (_) {}
    }
  };
  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      style={{ background: 'rgba(6,4,2,0.92)', backdropFilter: 'blur(10px)' }}
      onClick={onClose}
      data-testid="lpw-lightbox"
    >
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.94, opacity: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        onClick={(e) => e.stopPropagation()}
        className="relative max-w-5xl max-h-[90vh]"
      >
        <img src={`${API_URL}${photo.url}`} alt={photo.caption || ''}
          className="max-w-full max-h-[85vh] rounded-lg" style={{ boxShadow: '0 30px 90px rgba(0,0,0,0.7)' }} />
        <div className="absolute -top-12 right-0 flex items-center gap-2">
          <button onClick={share} className="lux-btn lux-btn-ghost text-xs" data-testid="lpw-share">
            <Share2 className="w-3.5 h-3.5" /> Share
          </button>
          <a href={`${API_URL}${photo.url}`} download className="lux-btn lux-btn-ghost text-xs" data-testid="lpw-download">
            <Download className="w-3.5 h-3.5" /> Download
          </a>
          <button onClick={onClose} className="lux-btn lux-btn-ghost text-xs" data-testid="lpw-lightbox-close">
            <X className="w-3.5 h-3.5" /> Close
          </button>
        </div>
        {photo.caption && (
          <p className="absolute -bottom-10 left-0 right-0 text-center text-sm" style={{ color: 'rgba(255,248,220,0.78)' }}>
            “{photo.caption}” — {photo.uploader_name}
          </p>
        )}
      </motion.div>
    </motion.div>
  );
};

const GuestUploader = ({ slug, onClose, onUploaded }) => {
  const [name, setName] = useState('');
  const [caption, setCaption] = useState('');
  const [eventType, setEventType] = useState('');
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) { setError('Image too large. Max 8MB.'); return; }
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result);
    reader.readAsDataURL(f);
  };

  const submit = async () => {
    setError('');
    if (!name.trim() || !preview) { setError('Please add your name and select a photo.'); return; }
    setBusy(true);
    try {
      await axios.post(`${API_URL}/api/invite/${slug}/live-gallery/guest-upload`, {
        guest_name: name.trim(),
        caption: caption.trim() || null,
        event_type: eventType || null,
        image_base64: preview,
      });
      onUploaded?.();
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[65] flex items-center justify-center p-4"
      style={{ background: 'rgba(6,4,2,0.85)', backdropFilter: 'blur(10px)' }}
      onClick={onClose}
      data-testid="lpw-uploader"
    >
      <motion.div
        initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 30, opacity: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        onClick={(e) => e.stopPropagation()}
        className="lux-glass relative w-full max-w-lg p-7 md:p-9"
        style={{ background: 'rgba(14,10,6,0.96)' }}
      >
        <button onClick={onClose} className="absolute top-3 right-3 w-9 h-9 rounded-full grid place-items-center"
          style={{ color: 'rgba(255,248,220,0.6)', border: '1px solid var(--lux-border)' }}
          data-testid="lpw-uploader-close">
          <X className="w-4 h-4" />
        </button>
        <span className="lux-eyebrow block mb-3">◆ Share a moment</span>
        <h3 className="font-display text-3xl mb-2" style={{ color: '#FFF8DC' }}>
          Upload your <span className="text-gold italic font-script">memory</span>
        </h3>
        <p className="text-sm mb-5" style={{ color: 'rgba(255,248,220,0.6)' }}>
          Your photo joins the live gallery the moment it's approved.
        </p>

        <div className="grid grid-cols-1 gap-3 mb-4">
          <label className="block">
            <span className="text-[10px] tracking-[0.3em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>Your name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Priya Sharma"
              className="w-full px-3 py-2.5 rounded-lg bg-transparent outline-none text-sm"
              style={{ color: '#FFF8DC', border: '1px solid var(--lux-border)' }}
              data-testid="lpw-uploader-name" />
          </label>
          <label className="block">
            <span className="text-[10px] tracking-[0.3em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>Caption (optional)</span>
            <input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="A little message…"
              className="w-full px-3 py-2.5 rounded-lg bg-transparent outline-none text-sm"
              style={{ color: '#FFF8DC', border: '1px solid var(--lux-border)' }}
              data-testid="lpw-uploader-caption" />
          </label>
          <label className="block">
            <span className="text-[10px] tracking-[0.3em] uppercase block mb-1.5" style={{ color: 'rgba(255,248,220,0.55)' }}>Photo</span>
            <input type="file" accept="image/*" onChange={onFile}
              className="w-full text-sm" style={{ color: 'rgba(255,248,220,0.85)' }}
              data-testid="lpw-uploader-file" />
          </label>
          {preview && (
            <img src={preview} alt="preview" className="w-full h-48 object-cover rounded-lg"
              style={{ border: '1px solid var(--lux-border)' }} />
          )}
        </div>
        {error && (
          <div className="mb-4 px-3 py-2 rounded text-sm" style={{ background: 'rgba(139,0,0,0.18)', color: '#FFD7C9' }}>{error}</div>
        )}
        <button onClick={submit} disabled={busy} className="lux-btn w-full" data-testid="lpw-uploader-submit">
          {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</> : <><Upload className="w-4 h-4" /> Share to wall</>}
        </button>
      </motion.div>
    </motion.div>
  );
};

export default LivePhotoWall;
