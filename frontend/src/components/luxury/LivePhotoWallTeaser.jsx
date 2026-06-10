import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, X, ChevronLeft, ChevronRight, ZoomIn, Wifi } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * PROMPT 05 + 13 — Real-time Live Photo Wall (public invitation)
 * Native WebSocket connection (no socket.io) with auto-reconnect.
 * New photos animate in. Click any photo for cinematic full-screen lightbox.
 */
const LivePhotoWallTeaser = ({ slug }) => {
  const [photos, setPhotos] = useState([]);
  const [connected, setConnected] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const isUnmountingRef = useRef(false);

  // Fetch initial photos
  const fetchPhotos = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/public/gallery/${slug}/photos?limit=200`);
      const j = await r.json();
      setPhotos(j.photos || []);
    } catch (_) {
      // ignore
    }
  }, [slug]);

  // WebSocket connection with auto-reconnect
  const connectWs = useCallback(() => {
    if (isUnmountingRef.current) return;
    try {
      const wsBase = API_URL.replace(/^https?:/, API_URL.startsWith('https') ? 'wss:' : 'ws:');
      const ws = new WebSocket(`${wsBase}/api/ws/gallery/${slug}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'photo_added' && msg.photo) {
            setPhotos((prev) => {
              if (prev.some((p) => p.id === msg.photo.id)) return prev;
              return [msg.photo, ...prev];
            });
          } else if (msg.type === 'photo_deleted' && msg.photo_id) {
            setPhotos((prev) => prev.filter((p) => p.id !== msg.photo_id));
          }
        } catch (_) { /* ignore */ }
      };
      ws.onerror = () => { setConnected(false); };
      ws.onclose = () => {
        setConnected(false);
        if (!isUnmountingRef.current) {
          reconnectTimerRef.current = setTimeout(connectWs, 3000);
        }
      };
    } catch (_) {
      reconnectTimerRef.current = setTimeout(connectWs, 3000);
    }
  }, [slug]);

  useEffect(() => {
    isUnmountingRef.current = false;
    fetchPhotos();
    connectWs();
    return () => {
      isUnmountingRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      try { wsRef.current?.close(); } catch (_) {}
    };
  }, [fetchPhotos, connectWs]);

  const openLightbox = (i) => setLightboxIndex(i);
  const closeLightbox = () => setLightboxIndex(null);
  const prev = useCallback(() => setLightboxIndex((i) => (i > 0 ? i - 1 : photos.length - 1)), [photos.length]);
  const next = useCallback(() => setLightboxIndex((i) => (i < photos.length - 1 ? i + 1 : 0)), [photos.length]);

  useEffect(() => {
    if (lightboxIndex === null) return;
    const onKey = (e) => {
      if (e.key === 'Escape') closeLightbox();
      else if (e.key === 'ArrowLeft') prev();
      else if (e.key === 'ArrowRight') next();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxIndex, prev, next]);

  return (
    <section className="px-4 md:px-12 py-20 md:py-24 relative" data-testid="public-live-wall">
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-start justify-between gap-4 mb-10">
          <div className="flex-1">
            <motion.span initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, amount: 0.1 }}
              className="lux-eyebrow block mb-3">◆ Live Photo Wall</motion.span>
            <motion.h2 initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }}
              className="font-display text-[2rem] md:text-[3.2rem] leading-[1.05]" style={{ color: '#FFF8DC' }}>
              Moments unfold <span className="font-script italic text-gold">in real time</span>
            </motion.h2>
            <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, amount: 0.1 }} transition={{ delay: 0.2 }}
              className="mt-3 max-w-xl text-sm md:text-base italic" style={{ color: 'rgba(255,248,220,0.7)' }}>
              As the photographer captures the day, the gallery refreshes live. Tap a photo to view full.
            </motion.p>
          </div>
          <LivePill connected={connected} count={photos.length} />
        </div>

        {photos.length === 0 ? (
          <div className="lux-glass p-10 md:p-14 text-center" data-testid="live-wall-empty">
            <Camera className="w-7 h-7 mx-auto mb-3" style={{ color: '#D4AF37' }} />
            <p className="text-sm md:text-base" style={{ color: 'rgba(255,248,220,0.7)' }}>
              No photos yet. The gallery comes alive as the day unfolds.
            </p>
          </div>
        ) : (
          <div className="masonry-cols" data-testid="live-wall-grid">
            <AnimatePresence initial={false}>
              {photos.map((p, i) => (
                <motion.div
                  key={p.id}
                  layout
                  initial={{ scale: 0.8, opacity: 0, y: 20 }}
                  animate={{ scale: 1, opacity: 1, y: 0 }}
                  exit={{ scale: 0.85, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 22, delay: i < 8 ? i * 0.04 : 0 }}
                  className="break-inside-avoid mb-3 md:mb-4 relative group cursor-pointer rounded-lg overflow-hidden"
                  style={{ border: '1px solid var(--lux-border, rgba(212,175,55,0.18))' }}
                  onClick={() => openLightbox(i)}
                  data-testid={`live-wall-photo-${i}`}
                >
                  <img
                    src={`${API_URL}${p.thumb_url}`}
                    alt={p.caption || ''}
                    loading="lazy"
                    className="w-full h-auto block transition-transform duration-700 group-hover:scale-[1.04]"
                    style={{ background: '#1a140e' }}
                  />
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    style={{ background: 'linear-gradient(to top, rgba(10,10,15,0.85), transparent 60%)' }}>
                    <div className="absolute bottom-2 left-3 right-10">
                      {p.guest_name && (
                        <div className="font-script text-base md:text-lg text-gold italic truncate">{p.guest_name}</div>
                      )}
                      {p.caption && (
                        <div className="text-xs md:text-sm truncate" style={{ color: 'rgba(255,248,220,0.85)' }}>{p.caption}</div>
                      )}
                    </div>
                    <ZoomIn className="absolute bottom-2 right-2 w-4 h-4" style={{ color: '#D4AF37' }} />
                  </div>
                  {p.source === 'guest' && (
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full text-[9px] tracking-widest uppercase"
                      style={{ background: 'rgba(232,196,184,0.18)', color: '#E8C4B8', backdropFilter: 'blur(8px)' }}>
                      Guest
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <AnimatePresence>
        {lightboxIndex !== null && photos[lightboxIndex] && (
          <Lightbox
            photo={photos[lightboxIndex]}
            index={lightboxIndex}
            total={photos.length}
            onClose={closeLightbox}
            onPrev={prev}
            onNext={next}
          />
        )}
      </AnimatePresence>

      <style>{`
        .masonry-cols { column-count: 1; column-gap: 1rem; }
        @media (min-width: 640px) { .masonry-cols { column-count: 2; } }
        @media (min-width: 1024px) { .masonry-cols { column-count: 3; column-gap: 1.25rem; } }
        @media (min-width: 1400px) { .masonry-cols { column-count: 4; } }
        .break-inside-avoid { break-inside: avoid; -webkit-column-break-inside: avoid; }
        @keyframes livepulse { 0%,100% { opacity:1 } 50% { opacity: 0.55 } }
        .live-dot { animation: livepulse 1.4s ease-in-out infinite; }
      `}</style>
    </section>
  );
};

const LivePill = ({ connected, count }) => (
  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] tracking-[0.25em] uppercase whitespace-nowrap shrink-0"
    style={{
      background: connected ? 'rgba(220, 38, 38, 0.18)' : 'rgba(255,248,220,0.08)',
      border: `1px solid ${connected ? 'rgba(220,38,38,0.45)' : 'rgba(255,248,220,0.2)'}`,
      color: connected ? '#fca5a5' : 'rgba(255,248,220,0.55)',
    }}
    data-testid="live-pill"
  >
    {connected ? (
      <>
        <span className="w-2 h-2 rounded-full live-dot" style={{ background: '#ef4444' }} />
        Live · {count}
      </>
    ) : (
      <>
        <Wifi className="w-3 h-3 opacity-70" />
        Connecting…
      </>
    )}
  </div>
);

const Lightbox = ({ photo, index, total, onClose, onPrev, onNext }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-[120] flex items-center justify-center"
    style={{ background: 'rgba(5,4,3,0.96)', backdropFilter: 'blur(12px)' }}
    onClick={onClose}
    data-testid="lightbox"
  >
    <button className="absolute top-5 right-5 w-11 h-11 rounded-full grid place-items-center"
      style={{ background: 'rgba(255,248,220,0.08)', color: '#FFF8DC', border: '1px solid rgba(212,175,55,0.35)' }}
      onClick={(e) => { e.stopPropagation(); onClose(); }} data-testid="lightbox-close">
      <X className="w-5 h-5" />
    </button>
    <button className="absolute left-3 md:left-8 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full grid place-items-center"
      style={{ background: 'rgba(255,248,220,0.08)', color: '#FFF8DC' }}
      onClick={(e) => { e.stopPropagation(); onPrev(); }} data-testid="lightbox-prev">
      <ChevronLeft className="w-6 h-6" />
    </button>
    <button className="absolute right-3 md:right-8 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full grid place-items-center"
      style={{ background: 'rgba(255,248,220,0.08)', color: '#FFF8DC' }}
      onClick={(e) => { e.stopPropagation(); onNext(); }} data-testid="lightbox-next">
      <ChevronRight className="w-6 h-6" />
    </button>
    <motion.div
      key={photo.id}
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.97, opacity: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="max-w-[95vw] max-h-[90vh] flex flex-col items-center gap-3"
      onClick={(e) => e.stopPropagation()}
    >
      <img
        src={`${API_URL}${photo.url || photo.thumb_url}`}
        alt={photo.caption || ''}
        className="max-w-[95vw] max-h-[80vh] object-contain rounded-lg"
        style={{ boxShadow: '0 28px 80px rgba(0,0,0,0.7)' }}
      />
      <div className="text-center max-w-2xl">
        {photo.guest_name && (
          <div className="font-script text-2xl text-gold italic">{photo.guest_name}</div>
        )}
        {photo.caption && (
          <div className="text-sm md:text-base mt-1 italic" style={{ color: 'rgba(255,248,220,0.8)' }}>“{photo.caption}”</div>
        )}
        <div className="text-[10px] tracking-[0.3em] uppercase mt-2" style={{ color: 'rgba(255,248,220,0.5)' }}>
          {index + 1} / {total}
        </div>
      </div>
    </motion.div>
  </motion.div>
);

export default React.memo(LivePhotoWallTeaser);
