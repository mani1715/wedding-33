import React, { useEffect, useState } from 'react';
import { X, Check, Sparkles, AlertCircle, CheckCircle, CreditCard } from 'lucide-react';

/**
 * UpgradeModal — credit-pack picker (Feb 2026 refactor).
 *
 * The legacy FREE/SILVER/GOLD/PLATINUM plan tier system was replaced with
 * a unified credit system. This modal now fetches role-appropriate credit
 * packs from `/api/public/credit-packs` and lets the user buy one via
 * Razorpay. Photographers see photographer packs; normal users see user
 * packs (audience filter is server-side).
 *
 * Props (most are kept for back-compat with old call sites):
 *   isOpen, onClose, onUpgradeSuccess
 */
const UpgradeModal = ({ isOpen, onClose, onUpgradeSuccess }) => {
  const [packs, setPacks] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);          // 'success' | 'failed' | null
  const [error, setError] = useState('');

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  // Load Razorpay script once
  useEffect(() => {
    if (!isOpen) return;
    if (document.getElementById('razorpay-checkout-js')) return;
    const s = document.createElement('script');
    s.id = 'razorpay-checkout-js';
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.async = true;
    document.body.appendChild(s);
  }, [isOpen]);

  // Fetch packs for the current role
  useEffect(() => {
    if (!isOpen) return;
    const token = localStorage.getItem('admin_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    fetch(`${backendUrl}/api/public/credit-packs`, { headers })
      .then((r) => r.json())
      .then((data) => setPacks(Array.isArray(data) ? data : data?.packs || []))
      .catch(() => setPacks([]));
  }, [isOpen, backendUrl]);

  if (!isOpen) return null;

  const handleBuy = async () => {
    if (!selected) return;
    setLoading(true);
    setError('');
    setStatus(null);
    try {
      const token = localStorage.getItem('admin_token');
      const orderRes = await fetch(`${backendUrl}/api/credits/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ pack_id: selected.id }),
      });
      if (!orderRes.ok) throw new Error((await orderRes.json()).detail || 'Order failed');
      const order = await orderRes.json();

      const options = {
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency || 'INR',
        name: 'Wedding Credits',
        description: `${selected.label || selected.name} — ${selected.credits} credits`,
        order_id: order.order_id,
        handler: async (resp) => {
          try {
            const verifyRes = await fetch(`${backendUrl}/api/credits/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                payment_id: order.payment_id,
                razorpay_order_id: resp.razorpay_order_id,
                razorpay_payment_id: resp.razorpay_payment_id,
                razorpay_signature: resp.razorpay_signature,
              }),
            });
            if (!verifyRes.ok) throw new Error('Verification failed');
            const v = await verifyRes.json();
            setStatus('success');
            if (onUpgradeSuccess) onUpgradeSuccess(v);
            setTimeout(onClose, 2200);
          } catch (e) {
            setStatus('failed');
            setError(e.message || 'Verification failed');
          } finally {
            setLoading(false);
          }
        },
        modal: {
          ondismiss: () => {
            setLoading(false);
            setError('Payment cancelled');
          },
        },
        theme: { color: '#D4AF37' },
      };
      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (e) {
      setError(e.message || 'Could not start payment');
      setLoading(false);
    }
  };

  // Success state
  if (status === 'success') {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="upgrade-modal-success">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Credits added!</h3>
          <p className="text-gray-600 mb-4">
            {selected?.credits} credits were added to your account.
          </p>
        </div>
      </div>
    );
  }

  // Failed state
  if (status === 'failed') {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="upgrade-modal-failed">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-10 h-10 text-red-600" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Payment failed</h3>
          <p className="text-gray-600 mb-6">{error || 'Something went wrong'}</p>
          <button
            onClick={() => { setStatus(null); setError(''); }}
            className="px-6 py-2.5 bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition-colors font-medium"
            data-testid="upgrade-modal-retry"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="upgrade-modal">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Buy credits</h2>
            <p className="text-sm text-gray-600 mt-1">Pay-as-you-go for designs and features</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="upgrade-modal-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {packs.length === 0 ? (
            <div className="py-16 text-center text-gray-500">No credit packs available yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {packs.map((p) => {
                const isSel = selected?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelected(p)}
                    data-testid={`credit-pack-${p.id}`}
                    className={`relative border-2 rounded-xl p-5 transition-all cursor-pointer
                      ${isSel ? 'border-amber-500 ring-2 ring-amber-300' : 'border-gray-200 hover:border-amber-300 hover:shadow-lg'}`}
                  >
                    {p.badge && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                        <span className="bg-gradient-to-r from-amber-400 to-rose-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-md">
                          {p.badge}
                        </span>
                      </div>
                    )}
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{p.label || p.name}</h3>
                    <div className="text-3xl font-bold text-gray-900 mb-1">{p.credits} <span className="text-base font-medium text-gray-500">credits</span></div>
                    <div className="text-sm text-gray-700 mb-3">₹{p.price_inr || p.price}</div>
                    {p.description && <p className="text-xs text-gray-500 mb-3">{p.description}</p>}
                    <div className="text-xs text-amber-700 font-medium flex items-center gap-1">
                      <Sparkles className="w-3 h-3" /> Spend on any design or feature
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
            <CreditCard className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-gray-700">
              Credits never expire. Use them anytime across all your weddings.
            </p>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="mt-6 flex items-center justify-between gap-4">
            <button onClick={onClose} className="px-6 py-2.5 text-gray-700 hover:bg-gray-100 rounded-lg font-medium">
              Cancel
            </button>
            <button
              onClick={handleBuy}
              disabled={!selected || loading}
              data-testid="upgrade-modal-buy"
              className={`px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-all
                ${selected && !loading
                  ? 'bg-gradient-to-r from-amber-500 to-rose-600 text-white hover:from-amber-600 hover:to-rose-700 shadow-md hover:shadow-lg'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Processing...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  {selected ? `Pay ₹${selected.price_inr || selected.price}` : 'Select a pack'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UpgradeModal;
