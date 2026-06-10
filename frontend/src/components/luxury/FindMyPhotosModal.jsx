import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  Camera, X, Upload, Download, Loader2, Check, AlertCircle, Sparkles,
  Heart, ExternalLink, Image as ImageIcon, Shield,
} from 'lucide-react';
import { useGalleryAccess, authHeader } from '../../hooks/useGalleryAccess';
import GalleryLockScreen from './GalleryLockScreen';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * FindMyPhotosModal — guest-facing AI face-search modal.
 * Triggered from the public invitation by a "📸 Find My Photos" button.
 */
const FindMyPhotosModal = ({ slug, open, onClose }) => {
  const [step, setStep] = useState('intro'); // intro | analyzing | results | error
  const [selfie, setSelfie] = useState(null); // dataURL preview
  const [result, setResult] = useState(null);
  const [err, setErr] = useState('');
  const fileRef = useRef(null);
  const cameraRef = useRef(null);
  const access = useGalleryAccess(slug);

  useEffect(() => {
    if (!open) {
      setStep('intro'); setSelfie(null); setResult(null); setErr('');
    }
  }, [open]);

  const onSelfie = async (file) => {
    if (!file) return;
    setErr('');
    setSelfie(URL.createObjectURL(file));
    setStep('analyzing');
    try {
      const fd = new FormData();
      fd.append('selfie', file);
      const r = await axios.post(
        `${API_URL}/api/public/gallery/${slug}/face-search`, fd,
        { headers: { 'Content-Type': 'multipart/form-data', ...authHeader(access.deviceToken) } });
      setResult(r.data);
      setStep('results');
    } catch (e) {
      const status = e.response?.status;
      if (status === 401) {
        // Token rejected mid-flight — kick back to lock
        access.logout();
        setErr('Your access has expired. Please re-enter the code.');
      } else {
        setErr(e.response?.data?.detail || 'Face search failed. Please try again with a clearer selfie.');
      }
      setStep('error');
    }
  };

  const downloadZip = () => {
    if (!result?.session_id) return;
    const tokenParam = access.deviceToken ? `&device_token=${encodeURIComponent(access.deviceToken)}` : '';
    const url = `${API_URL}/api/public/gallery/${slug}/download-zip?session_id=${result.session_id}${tokenParam}`;
    window.open(url, '_blank');
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center p-3 md:p-6"
        style={{ background: 'rgba(10,8,5,0.92)' }}
        data-testid="find-photos-modal"
        onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <motion.div initial={{ y: 30, scale: 0.97 }} animate={{ y: 0, scale: 1 }} exit={{ y: 30, scale: 0.97 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="lux-glass w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl relative"
          style={{ background: 'rgba(20,15,11,0.98)', border: '1px solid var(--lux-border-strong)' }}>

          <button onClick={onClose} aria-label="Close"
            className="absolute top-4 right-4 z-10 w-9 h-9 rounded-full grid place-items-center hover:bg-white/10"
            style={{ color: '#FFF8DC' }} data-testid="close-find-photos">
            <X className="w-5 h-5" />
          </button>

          <div className="p-6 md:p-10">
            {/* Gate: if the gallery is privacy-protected and the device isn't unlocked yet,
                show the lock screen before the AI flow. */}
            {access.isProtected && !access.isUnlocked && (
              <div className="py-2">
                <GalleryLockScreen
                  testid="find-photos-lock"
                  title="Private Gallery"
                  subtitle="Enter the access code from the couple to find your photos."
                  onUnlock={(code, remember) => access.unlock(code, remember)}
                />
              </div>
            )}

            {/* AI feature disabled by couple */}
            {access.isProtected && access.isUnlocked && access.privacy && !access.privacy.ai_face_match_enabled && (
              <div className="py-10 text-center" data-testid="ai-disabled-message">
                <Shield className="w-10 h-10 mx-auto mb-3 text-gold" />
                <h3 className="font-display text-2xl mb-2" style={{ color: '#FFF8DC' }}>AI photo search is disabled</h3>
                <p className="text-sm" style={{ color: 'rgba(255,248,220,0.65)' }}>
                  The couple has turned off AI face matching for this gallery.
                </p>
              </div>
            )}

            {(!access.isProtected || access.isUnlocked) && (!access.privacy || access.privacy.ai_face_match_enabled !== false) && (
              <>
                {step === 'intro' && (
                  <IntroStep onPickCamera={() => cameraRef.current?.click()}
                              onPickGallery={() => fileRef.current?.click()} />
                )}
                {step === 'analyzing' && <AnalyzingStep selfie={selfie} />}
                {step === 'results' && (
                  <ResultsStep
                    result={result}
                    onZip={downloadZip}
                    onRetry={() => setStep('intro')}
                    allowDownloads={!access.privacy || access.privacy.allow_downloads !== false}
                    allowShare={!access.privacy || access.privacy.allow_share !== false}
                  />
                )}
                {step === 'error' && (
                  <ErrorStep err={err} onRetry={() => { setStep('intro'); setSelfie(null); setErr(''); }} />
                )}
              </>
            )}

            <input ref={cameraRef} type="file" accept="image/*" capture="user"
              style={{ display: 'none' }} onChange={(e) => onSelfie(e.target.files?.[0])}
              data-testid="selfie-camera-input" />
            <input ref={fileRef} type="file" accept="image/*"
              style={{ display: 'none' }} onChange={(e) => onSelfie(e.target.files?.[0])}
              data-testid="selfie-gallery-input" />
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

const IntroStep = ({ onPickCamera, onPickGallery }) => (
  <div className="text-center space-y-6 py-4">
    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full"
      style={{ background: 'rgba(212,175,55,0.12)' }}>
      <Sparkles className="w-7 h-7 text-gold" />
    </div>
    <div>
      <span className="lux-eyebrow inline-block mb-2">◆ AI-powered</span>
      <h2 className="font-display text-3xl md:text-5xl mb-3" style={{ color: '#FFF8DC' }}>
        Find <span className="font-script italic text-gold">your photos</span>
      </h2>
      <p className="text-sm md:text-base max-w-md mx-auto" style={{ color: 'rgba(255,248,220,0.7)' }}>
        Upload a clear selfie and our AI will pull every photo of you from the wedding gallery.
      </p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-md mx-auto">
      <button onClick={onPickCamera} data-testid="find-take-selfie"
        className="p-5 rounded-2xl flex flex-col items-center gap-2 transition-all hover:scale-[1.02]"
        style={{ background: '#D4AF37', color: '#16110C' }}>
        <Camera className="w-7 h-7" />
        <span className="text-sm tracking-[0.15em] uppercase font-medium">Take Selfie</span>
      </button>
      <button onClick={onPickGallery} data-testid="find-choose-photo"
        className="p-5 rounded-2xl flex flex-col items-center gap-2 transition-all hover:scale-[1.02]"
        style={{ background: 'rgba(255,248,220,0.04)', border: '1px solid var(--lux-border)', color: '#FFF8DC' }}>
        <Upload className="w-7 h-7 text-gold" />
        <span className="text-sm tracking-[0.15em] uppercase">Choose Photo</span>
      </button>
    </div>
    <div className="text-xs inline-flex items-center gap-2 px-3 py-2 rounded-full"
      style={{ background: 'rgba(255,248,220,0.04)', color: 'rgba(255,248,220,0.7)' }}>
      <Shield className="w-3 h-3 text-gold" />
      Your selfie is auto-deleted within 24 hours. Only used for face matching.
    </div>
  </div>
);

const AnalyzingStep = ({ selfie }) => (
  <div className="text-center py-10 space-y-5">
    {selfie && (
      <img src={selfie} alt="Your selfie"
        className="w-32 h-32 rounded-full object-cover mx-auto"
        style={{ border: '3px solid #D4AF37' }} />
    )}
    <Loader2 className="w-8 h-8 text-gold animate-spin mx-auto" />
    <div>
      <h3 className="font-display text-2xl mb-1" style={{ color: '#FFF8DC' }}>Searching the gallery…</h3>
      <p className="text-xs" style={{ color: 'rgba(255,248,220,0.6)' }}>
        AI is comparing your face to every photo. Takes 5–10 seconds.
      </p>
    </div>
  </div>
);

const ResultsStep = ({ result, onZip, onRetry, allowDownloads = true, allowShare = true }) => {
  const count = result?.match_count || 0;
  if (count === 0) {
    return (
      <div className="text-center py-10 space-y-4">
        <ImageIcon className="w-12 h-12 text-gold opacity-50 mx-auto" />
        <h3 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>No photos found</h3>
        <p className="text-sm max-w-md mx-auto" style={{ color: 'rgba(255,248,220,0.65)' }}>
          We couldn't find you in the gallery yet. The photographer may still be uploading — try again in a bit, or use a clearer selfie.
        </p>
        <button onClick={onRetry} className="lux-btn inline-flex items-center gap-2" data-testid="retry-search">
          <Camera className="w-4 h-4" /> Try a different selfie
        </button>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <div className="text-center">
        <span className="lux-eyebrow inline-block mb-2">◆ AI match</span>
        <h3 className="font-display text-3xl md:text-4xl" style={{ color: '#FFF8DC' }}>
          Found <span className="text-gold">{count}</span> photo{count > 1 ? 's' : ''} of you <span className="font-script italic text-gold">🎉</span>
        </h3>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          {allowDownloads && (
            <button onClick={onZip} className="lux-btn inline-flex items-center gap-2" data-testid="download-zip">
              <Download className="w-4 h-4" /> Download all as ZIP
            </button>
          )}
          <button onClick={onRetry} className="lux-btn-ghost inline-flex items-center gap-2 text-xs" data-testid="retry-different">
            <Camera className="w-3.5 h-3.5" /> Try another selfie
          </button>
        </div>
        {!allowDownloads && (
          <p className="text-[11px] italic mt-3" style={{ color: 'rgba(255,248,220,0.5)' }}>
            Downloads are disabled for this gallery by the couple.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {(result.photos || []).map((p, i) => (
          <motion.div key={p.id}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="relative group rounded-lg overflow-hidden"
            style={{ background: 'rgba(0,0,0,0.4)' }}
            data-testid={`match-photo-${i}`}>
            <img src={p.thumb_url} alt="" className="w-full h-44 object-cover" loading="lazy" />
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2">
              <a href={p.original_url} target="_blank" rel="noopener noreferrer"
                className="text-xs tracking-widest uppercase inline-flex items-center gap-1 text-gold"
                data-testid={`view-${i}`}>
                <ExternalLink className="w-3 h-3" /> View
              </a>
              {allowDownloads && (
                <a href={p.original_url} download className="text-xs tracking-widest uppercase inline-flex items-center gap-1"
                  style={{ color: '#FFF8DC' }} data-testid={`dl-${i}`}>
                  <Download className="w-3 h-3" /> Download
                </a>
              )}
            </div>
            <span className="absolute top-2 left-2 text-[10px] tracking-[0.1em] uppercase px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(212,175,55,0.95)', color: '#16110C' }}>
              {Math.round(p.similarity)}%
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

const ErrorStep = ({ err, onRetry }) => (
  <div className="text-center py-10 space-y-4">
    <AlertCircle className="w-10 h-10 text-red-300 mx-auto" />
    <h3 className="font-display text-2xl" style={{ color: '#FFF8DC' }}>Something went wrong</h3>
    <p className="text-sm max-w-md mx-auto" style={{ color: 'rgba(255,248,220,0.7)' }}>{err}</p>
    <button onClick={onRetry} className="lux-btn inline-flex items-center gap-2" data-testid="retry-from-error">
      <Camera className="w-4 h-4" /> Try again
    </button>
  </div>
);

export default FindMyPhotosModal;
