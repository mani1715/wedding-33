import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  X, Coins, IndianRupee, Sparkles, Loader2, Check, History,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const loadRazorpay = () => new Promise((resolve) => {
  if (window.Razorpay) return resolve(true);
  const s = document.createElement('script');
  s.src = 'https://checkout.razorpay.com/v1/checkout.js';
  s.onload = () => resolve(true);
  s.onerror = () => resolve(false);
  document.body.appendChild(s);
});

/**
 * TopUpCreditsModal — opens inside the dashboard so the user never loses context.
 * Loads credit packs + Razorpay flow. On success, refreshes parent via onSuccess.
 */
const TopUpCreditsModal = ({ open, onClose, onSuccess }) => {
  const [packs, setPacks] = useState([]);
  const [balance, setBalance] = useState({ available_credits: 0, total_credits: 0, used_credits: 0 });
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (type, message, ms = 4000) => {
    setToast({ type, message }); setTimeout(() => setToast(null), ms);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([
        axios.get(`${API_URL}/api/admin/credit-packs`),
        axios.get(`${API_URL}/api/admin/credits`).catch(() => ({ data: balance })),
      ]);
      setPacks(p.data?.packs || []);
      if (c.data) setBalance(c.data);
    } catch (_) { /* silent */ }
    finally { setLoading(false); }
    // eslint-disable-next-line
  }, []);

  useEffect(() => { if (open) load(); }, [open, load]);

  const buy = async (pack) => {
    setWorking(pack.id);
    try {
      const ok = await loadRazorpay();
      if (!ok) throw new Error('Could not load Razorpay');
      const orderRes = await axios.post(`${API_URL}/api/admin/credits/purchase/create-order`, { pack_id: pack.id });
      const order = orderRes.data;
      if (!order.razorpay_key_id || String(order.razorpay_key_id).includes('PLACEHOLDER')) {
        showToast('error', 'Razorpay keys not configured.'); setWorking(null); return;
      }
      const adminEmail = (JSON.parse(localStorage.getItem('admin') || 'null') || {}).email;
      const options = {
        key: order.razorpay_key_id,
        amount: order.amount_paise,
        currency: order.currency || 'INR',
        order_id: order.order_id,
        name: 'Wedding Studio',
        description: `${pack.label} · ${pack.credits} credits`,
        prefill: adminEmail ? { email: adminEmail } : {},
        theme: { color: '#D4AF37' },
        handler: async (resp) => {
          try {
            const verify = await axios.post(`${API_URL}/api/admin/credits/purchase/verify`, {
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
            });
            const v = verify.data;
            setBalance({
              total_credits: v.total_credits, used_credits: v.used_credits, available_credits: v.available_credits,
            });
            showToast('success', `Credited ${v.credits_added} credits · new balance ${v.available_credits}`);
            onSuccess?.(v);
          } catch (e) {
            showToast('error', e.response?.data?.detail || 'Verification failed');
          } finally { setWorking(null); }
        },
        modal: { ondismiss: () => setWorking(null) },
      };
      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', () => { showToast('error', 'Payment failed.'); setWorking(null); });
      rzp.open();
    } catch (e) {
      showToast('error', e.response?.data?.detail || e.message);
      setWorking(null);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center px-4 py-8"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          style={{ background: 'rgba(8,5,3,0.78)', backdropFilter: 'blur(8px)' }}
          onClick={onClose}
          data-testid="topup-modal"
        >
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="lux-glass w-full max-w-3xl p-6 md:p-8 relative max-h-[88vh] overflow-y-auto"
          >
            <button onClick={onClose} className="absolute right-4 top-4 opacity-70 hover:opacity-100"
              data-testid="topup-modal-close">
              <X className="w-5 h-5" style={{ color: '#FFF8DC' }} />
            </button>
            <span className="lux-eyebrow block mb-2">◆ Credits</span>
            <h2 className="font-display text-3xl mb-4" style={{ color: '#FFF8DC' }}>
              Top up <span className="font-script italic text-gold">your credits</span>
            </h2>

            <div className="grid grid-cols-3 gap-3 mb-6">
              <Stat label="Available" value={balance.available_credits} icon={<Coins className="w-3.5 h-3.5" />} big />
              <Stat label="Total ever" value={balance.total_credits} icon={<Sparkles className="w-3.5 h-3.5" />} />
              <Stat label="Used" value={balance.used_credits} icon={<History className="w-3.5 h-3.5" />} />
            </div>

            {loading ? (
              <div className="py-10 grid place-items-center">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#D4AF37' }} />
              </div>
            ) : packs.length === 0 ? (
              <p className="text-sm py-6 text-center" style={{ color: 'rgba(255,248,220,0.6)' }}>
                No packs available right now.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="topup-modal-packs">
                {packs.map((p) => (
                  <div key={p.id}
                    className="lux-glass p-4 flex flex-col"
                    style={p.badge ? { border: '1px solid rgba(212,175,55,0.55)' } : {}}
                    data-testid={`topup-modal-pack-${p.id}`}>
                    {p.badge && (
                      <span className="self-start mb-2 px-2 py-0.5 rounded-full text-[9px] tracking-[0.2em] uppercase"
                        style={{ background: 'linear-gradient(135deg,#D4AF37,#B8941F)', color: '#16110C' }}>
                        {p.badge}
                      </span>
                    )}
                    <div className="text-[10px] tracking-[0.3em] uppercase" style={{ color: 'rgba(255,248,220,0.55)' }}>
                      {p.label}
                    </div>
                    <div className="mt-1 mb-2 flex items-baseline">
                      <IndianRupee className="w-4 h-4 text-gold" />
                      <span className="font-display text-3xl text-gold leading-none">
                        {p.price_inr.toLocaleString('en-IN')}
                      </span>
                    </div>
                    <div className="text-xs mb-3" style={{ color: 'rgba(255,248,220,0.7)' }}>
                      <span className="text-gold font-semibold">{p.credits}</span> credits
                      {p.bonus_credits ? ` (+${p.bonus_credits} bonus)` : ''}
                    </div>
                    <button onClick={() => buy(p)} disabled={working === p.id}
                      className="lux-btn mt-auto text-xs" data-testid={`topup-modal-buy-${p.id}`}>
                      {working === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                      {working === p.id ? 'Processing…' : 'Buy now'}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {toast && (
              <div className="mt-4 text-xs px-3 py-2 rounded"
                style={{
                  background: toast.type === 'success' ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                  color: toast.type === 'success' ? '#22C55E' : '#EF4444',
                  border: `1px solid ${toast.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
                }}
                data-testid="topup-modal-toast">
                {toast.message}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const Stat = ({ icon, label, value, big }) => (
  <div className="lux-glass p-3">
    <div className="flex items-center gap-1.5 text-[9px] tracking-[0.3em] uppercase"
      style={{ color: 'rgba(255,248,220,0.55)' }}>{icon} {label}</div>
    <div className={`font-display ${big ? 'text-3xl' : 'text-xl'} text-gold mt-1 leading-none`}>{value || 0}</div>
  </div>
);

export default TopUpCreditsModal;
