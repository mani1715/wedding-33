import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Coins, Crown, Sparkles, Eye, ShoppingCart, Check, Info } from 'lucide-react';
import SmartImage from './perf/SmartImage';
import useAbortController from '../hooks/useAbortController';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * DesignCard with Pricing - Shows design preview with credit cost
 */
const DesignCardWithPricing = ({ 
  design, 
  themeId, 
  eventType, 
  onClick, 
  showPurchaseButton = true 
}) => {
  const [credits, setCredits] = useState(null);
  const [userType, setUserType] = useState('user');
  const [loading, setLoading] = useState(true);
  const getSignal = useAbortController();

  useEffect(() => {
    fetchDesignPrice();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [design.design_id, userType]);

  const fetchDesignPrice = async () => {
    try {
      const res = await axios.get(
        `${API_URL}/api/admin/restructured/design-pricing/${userType}?theme=${themeId}`,
        { signal: getSignal() }
      );
      const designData = res.data.designs?.find(d => d.design_id === design.design_id);
      setCredits(designData?.credits || 50); // Default 50 if not found
    } catch (e) {
      if (e?.name !== 'CanceledError' && e?.code !== 'ERR_CANCELED') {
        setCredits(50); // Fallback
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      whileHover={{ y: -8, scale: 1.02 }}
      className="relative group cursor-pointer"
      onClick={onClick}
    >
      {/* Design Preview */}
      <div className="lux-glass rounded-lg overflow-hidden border border-cream/20 hover:border-gold/50 transition-all">
        {/* Preview Image/Placeholder */}
        <div className="aspect-[3/4] bg-gradient-to-br from-dark/50 to-dark/80 flex items-center justify-center relative overflow-hidden">
          {design.preview_image_url ? (
            <SmartImage
              src={design.preview_image_url}
              alt={design.design_name}
              className="w-full h-full"
              style={{ width: '100%', height: '100%' }}
            />
          ) : (
            <Sparkles className="w-16 h-16 text-gold/30" />
          )}
          
          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-all flex items-center justify-center">
            <div className="text-center space-y-2">
              <Eye className="w-8 h-8 text-gold mx-auto" />
              <p className="text-cream text-sm font-semibold">Preview Design</p>
            </div>
          </div>

          {/* Premium Badge */}
          {design.is_premium && (
            <div className="absolute top-3 right-3 bg-gold text-dark px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
              <Crown className="w-3 h-3" />
              PREMIUM
            </div>
          )}
        </div>

        {/* Design Info */}
        <div className="p-4 space-y-3">
          <div>
            <h3 className="text-cream font-semibold text-lg line-clamp-1">
              {design.design_name}
            </h3>
            <p className="text-cream/50 text-xs capitalize">
              {eventType} • {themeId.replace('_', ' ')}
            </p>
          </div>

          {/* Pricing */}
          <div className="flex items-center justify-between pt-2 border-t border-cream/10">
            <div className="flex items-center gap-2">
              <Coins className="w-5 h-5 text-gold" />
              <div>
                <div className="text-2xl font-bold text-gold">
                  {loading ? '...' : credits}
                </div>
                <div className="text-xs text-cream/50">credits</div>
              </div>
            </div>

            {showPurchaseButton && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onClick?.();
                }}
                className="px-4 py-2 rounded bg-gold text-dark font-semibold hover:bg-gold/80 transition-all text-sm flex items-center gap-1"
              >
                <ShoppingCart className="w-4 h-4" />
                Buy
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

/**
 * Credit Value Display - Shows credit to currency conversion
 */
export const CreditValueBanner = () => {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCreditPackages();
  }, []);

  const fetchCreditPackages = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/restructured/plans-pricing/user`);
      setPackages(res.data.plans || []);
    } catch (e) {
      // Set default packages if API fails
      setPackages([
        { name: 'Starter', credits: 50, price: 499, discount_enabled: false },
        { name: 'Pro', credits: 200, price: 1799, discounted_price: 1499, discount_enabled: true },
        { name: 'Premium', credits: 500, price: 3999, discounted_price: 2999, discount_enabled: true }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading || packages.length === 0) return null;

  // Calculate average credit value
  const avgPackage = packages[0];
  const creditValue = avgPackage.discounted_price || avgPackage.price;
  const perCreditCost = (creditValue / avgPackage.credits).toFixed(2);

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="lux-glass p-4 border border-gold/30 mb-8"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
            <Coins className="w-5 h-5 text-gold" />
          </div>
          <div>
            <p className="text-cream font-semibold">Credit Pricing</p>
            <p className="text-xs text-cream/60">
              1 Credit ≈ ₹{perCreditCost} | Best value at higher tiers
            </p>
          </div>
        </div>

        {/* Quick packages */}
        <div className="flex gap-2 flex-wrap">
          {packages.slice(0, 3).map((pkg) => (
            <div
              key={pkg.name}
              className="px-3 py-2 rounded border border-cream/20 bg-dark/30"
            >
              <div className="text-xs text-cream/60 mb-0.5">{pkg.name}</div>
              <div className="flex items-center gap-1">
                <span className="text-gold font-bold">{pkg.credits}</span>
                <span className="text-xs text-cream/50">credits</span>
              </div>
              {pkg.discount_enabled && pkg.discounted_price ? (
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-xs text-cream/40 line-through">₹{pkg.price}</span>
                  <span className="text-sm text-gold font-semibold">₹{pkg.discounted_price}</span>
                </div>
              ) : (
                <div className="text-sm text-cream font-semibold mt-0.5">₹{pkg.price}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

/**
 * Features Showcase - Shows all invitation features with checkmarks
 */
export const FeaturesShowcase = () => {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFeatures();
  }, []);

  const fetchFeatures = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/admin/pricing/features`);
      setFeatures(res.data.features || []);
    } catch (e) {
      // Default features if API fails
      setFeatures([
        { feature_name: 'QR Code for Photos', user_credits: 5, is_free: false },
        { feature_name: 'AI Image Compression', user_credits: 2, is_free: false },
        { feature_name: 'Face Recognition', user_credits: 10, is_free: false },
        { feature_name: 'Digital Shagun (Gifts)', user_credits: 3, is_free: false },
        { feature_name: 'Live Photo Gallery', user_credits: 8, is_free: false },
        { feature_name: 'Guest Photo Upload', user_credits: 4, is_free: false },
        { feature_name: 'RSVP Management', user_credits: 0, is_free: true },
        { feature_name: 'SMS Invitations', user_credits: 15, is_free: false }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return null;

  return (
    <div className="lux-glass p-6 mb-8">
      <div className="flex items-center gap-2 mb-6">
        <Sparkles className="w-6 h-6 text-gold" />
        <h3 className="text-2xl font-display text-cream">All Features Included</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map((feature, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="flex items-start gap-3 p-3 rounded bg-dark/30 border border-cream/10"
          >
            <div className="w-5 h-5 rounded-full bg-gold/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-3 h-3 text-gold" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-cream font-medium text-sm">{feature.feature_name}</p>
              {feature.is_free ? (
                <span className="text-xs text-green-400 font-semibold">FREE</span>
              ) : (
                <span className="text-xs text-gold">+{feature.user_credits} credits</span>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-6 flex items-start gap-2 p-4 bg-blue-500/10 border border-blue-500/30 rounded">
        <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-cream/80">
          <strong>Mix & match features:</strong> Select only the features you need for each event. 
          Credits are consumed only when you purchase the design.
        </p>
      </div>
    </div>
  );
};

/**
 * Link Duration Pricing - Shows expiry options
 */
export const DurationPricingTable = () => {
  const [durations, setDurations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDurations();
  }, []);

  const fetchDurations = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/user/purchase/durations`);
      setDurations(res.data.durations || []);
    } catch (e) {
      setDurations([
        { label: '1 Day', credits: 2 },
        { label: '7 Days', credits: 5 },
        { label: '30 Days (1 Month)', credits: 15 },
        { label: '90 Days (3 Months)', credits: 30 },
        { label: '180 Days (6 Months)', credits: 50 },
        { label: '365 Days (1 Year)', credits: 80 },
        { label: 'Unlimited', credits: 150 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return null;

  return (
    <div className="lux-glass p-6 mb-8">
      <h3 className="text-2xl font-display text-cream mb-4">Link Duration Pricing</h3>
      <p className="text-cream/60 text-sm mb-6">
        Choose how long your invitation link remains active. Longer durations cost more credits.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {durations.map((duration, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.05 }}
            className="p-4 rounded border border-cream/20 bg-dark/30 text-center"
          >
            <div className="text-cream font-semibold mb-1">{duration.label}</div>
            <div className="text-2xl font-bold text-gold">{duration.credits}</div>
            <div className="text-xs text-cream/50">credits</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default DesignCardWithPricing;
