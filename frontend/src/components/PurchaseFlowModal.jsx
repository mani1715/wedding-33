import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { X, Check, Info, Clock, Sparkles, AlertCircle } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const PurchaseFlowModal = ({ design, eventType, onClose, onPurchaseComplete }) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [features, setFeatures] = useState([]);
  const [durations, setDurations] = useState([]);
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const [selectedDuration, setSelectedDuration] = useState(null);
  const [calculation, setCalculation] = useState(null);
  const [calculating, setCalculating] = useState(false);

  useEffect(() => {
    fetchOptions();
  }, []);

  useEffect(() => {
    if (selectedDuration && step === 2) {
      calculatePrice();
    }
  }, [selectedFeatures, selectedDuration]);

  const fetchOptions = async () => {
    try {
      setLoading(true);
      const [featuresRes, durationsRes] = await Promise.all([
        axios.get(`${API_URL}/api/user/purchase/features/${eventType}`),
        axios.get(`${API_URL}/api/user/purchase/durations`)
      ]);
      
      setFeatures(featuresRes.data.features || []);
      setDurations(durationsRes.data.durations || []);
    } catch (e) {
      console.error('Failed to fetch options:', e);
    } finally {
      setLoading(false);
    }
  };

  const calculatePrice = async () => {
    try {
      setCalculating(true);
      const res = await axios.post(`${API_URL}/api/user/purchase/calculate`, {
        design_id: design.design_id,
        event_type: eventType,
        selected_features: selectedFeatures,
        duration_id: selectedDuration,
        is_mixed_theme: false
      });
      setCalculation(res.data.calculation);
    } catch (e) {
      console.error('Failed to calculate:', e);
    } finally {
      setCalculating(false);
    }
  };

  const handlePurchase = async () => {
    try {
      setLoading(true);
      const res = await axios.post(`${API_URL}/api/user/purchase/confirm`, {
        design_id: design.design_id,
        event_type: eventType,
        selected_features: selectedFeatures,
        duration_id: selectedDuration,
        is_mixed_theme: false
      });
      
      if (res.data.success) {
        onPurchaseComplete(res.data);
      }
    } catch (e) {
      alert(e.response?.data?.detail || 'Purchase failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleFeature = (featureId) => {
    setSelectedFeatures(prev =>
      prev.includes(featureId)
        ? prev.filter(id => id !== featureId)
        : [...prev, featureId]
    );
  };

  const getFeatureIcon = (featureType) => {
    // Return appropriate icon based on feature type
    return <Sparkles className="w-4 h-4" />;
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="lux-glass max-w-3xl w-full my-8 relative"
        >
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full hover:bg-cream/10 transition-all z-10"
          >
            <X className="w-5 h-5 text-cream" />
          </button>

          <div className="p-6 md:p-8">
            {/* Header */}
            <div className="mb-6">
              <h2 className="text-2xl md:text-3xl font-display text-cream mb-2">
                Purchase Design
              </h2>
              <p className="text-cream/60">{design.design_name}</p>
            </div>

            {/* Progress Steps */}
            <div className="flex items-center justify-center mb-8 gap-4">
              <div className={`flex items-center gap-2 ${step >= 1 ? 'text-gold' : 'text-cream/30'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                  step >= 1 ? 'border-gold bg-gold/20' : 'border-cream/30'
                }`}>
                  {step > 1 ? <Check className="w-4 h-4" /> : '1'}
                </div>
                <span className="text-sm font-medium">Duration</span>
              </div>
              <div className="w-12 h-0.5 bg-cream/20" />
              <div className={`flex items-center gap-2 ${step >= 2 ? 'text-gold' : 'text-cream/30'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                  step >= 2 ? 'border-gold bg-gold/20' : 'border-cream/30'
                }`}>
                  {step > 2 ? <Check className="w-4 h-4" /> : '2'}
                </div>
                <span className="text-sm font-medium">Features</span>
              </div>
              <div className="w-12 h-0.5 bg-cream/20" />
              <div className={`flex items-center gap-2 ${step >= 3 ? 'text-gold' : 'text-cream/30'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                  step >= 3 ? 'border-gold bg-gold/20' : 'border-cream/30'
                }`}>
                  3
                </div>
                <span className="text-sm font-medium">Confirm</span>
              </div>
            </div>

            {/* Step 1: Duration Selection */}
            {step === 1 && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-gold" />
                  <h3 className="text-lg font-semibold text-cream">Select Link Duration</h3>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {durations.map((duration) => (
                    <motion.button
                      key={duration.duration_id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        setSelectedDuration(duration.duration_id);
                        setStep(2);
                      }}
                      className={`p-4 rounded border-2 transition-all text-left ${
                        selectedDuration === duration.duration_id
                          ? 'border-gold bg-gold/10'
                          : 'border-cream/20 bg-dark/30 hover:border-gold/50'
                      }`}
                    >
                      <div className="text-cream font-semibold mb-1">{duration.label}</div>
                      <div className="text-gold text-xl font-bold">{duration.credits}</div>
                      <div className="text-xs text-cream/50">credits</div>
                    </motion.button>
                  ))}
                </div>

                <div className="flex items-start gap-2 p-4 bg-blue-500/10 border border-blue-500/30 rounded">
                  <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-cream/80">
                    <p className="font-semibold mb-1">What happens after expiry?</p>
                    <p className="text-cream/60">Your invitation link will stop working and all uploaded photos will be deleted from our servers.</p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Step 2: Feature Selection */}
            {step === 2 && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-gold" />
                  <h3 className="text-lg font-semibold text-cream">Select Features</h3>
                </div>

                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                  {features.map((feature) => (
                    <motion.div
                      key={feature.feature_id}
                      whileHover={{ x: 2 }}
                      onClick={() => !feature.is_free && feature.enabled_by_default && toggleFeature(feature.feature_id)}
                      className={`p-4 rounded border-2 transition-all cursor-pointer ${
                        selectedFeatures.includes(feature.feature_id)
                          ? 'border-gold bg-gold/10'
                          : 'border-cream/20 bg-dark/30 hover:border-gold/50'
                      } ${!feature.enabled_by_default ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1">
                          <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-1 ${
                            selectedFeatures.includes(feature.feature_id)
                              ? 'border-gold bg-gold'
                              : 'border-cream/30'
                          }`}>
                            {selectedFeatures.includes(feature.feature_id) && (
                              <Check className="w-3 h-3 text-dark" />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-cream font-semibold">{feature.feature_name}</h4>
                              {feature.is_free && (
                                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full font-semibold">
                                  FREE
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-cream/60 mb-2">{feature.description}</p>
                            {feature.info_text && (
                              <p className="text-xs text-cream/50 italic">{feature.info_text}</p>
                            )}
                            {feature.tutorial_video_url && (
                              <a
                                href={feature.tutorial_video_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-gold hover:underline mt-1 inline-block"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Watch Tutorial →
                              </a>
                            )}
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          {feature.is_free ? (
                            <span className="text-green-400 font-bold">FREE</span>
                          ) : (
                            <>
                              <div className="text-gold text-xl font-bold">+{feature.credits}</div>
                              <div className="text-xs text-cream/50">credits</div>
                            </>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setStep(1)}
                    className="px-6 py-2 rounded bg-dark/50 text-cream border border-cream/20 hover:bg-dark/70 transition-all"
                  >
                    Back
                  </button>
                  <button
                    onClick={() => setStep(3)}
                    className="flex-1 px-6 py-2 rounded bg-gold text-dark font-semibold hover:bg-gold/80 transition-all"
                  >
                    Continue to Summary
                  </button>
                </div>
              </motion.div>
            )}

            {/* Step 3: Confirmation */}
            {step === 3 && calculation && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                <h3 className="text-lg font-semibold text-cream mb-4">Purchase Summary</h3>

                {/* Breakdown */}
                <div className="lux-glass p-4 space-y-2">
                  {calculation.breakdown.map((item, index) => (
                    <div key={index} className="flex justify-between items-center py-2 border-b border-cream/10 last:border-0">
                      <span className="text-cream/80">{item.item}</span>
                      <span className="text-gold font-semibold">{item.credits} credits</span>
                    </div>
                  ))}
                </div>

                {/* Total */}
                <div className="lux-glass p-6 border-2 border-gold/30">
                  <div className="flex justify-between items-center">
                    <span className="text-xl font-semibold text-cream">Total Credits</span>
                    <span className="text-4xl font-bold text-gold">{calculation.total_credits}</span>
                  </div>
                </div>

                {/* Warning */}
                <div className="flex items-start gap-2 p-4 bg-orange-500/10 border border-orange-500/30 rounded">
                  <AlertCircle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-cream/80">
                    This purchase is final. Credits will be deducted immediately and cannot be refunded.
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setStep(2)}
                    className="px-6 py-2 rounded bg-dark/50 text-cream border border-cream/20 hover:bg-dark/70 transition-all"
                  >
                    Back
                  </button>
                  <button
                    onClick={handlePurchase}
                    disabled={loading}
                    className="flex-1 px-6 py-3 rounded bg-gold text-dark font-bold text-lg hover:bg-gold/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Processing...' : `Confirm Purchase (${calculation.total_credits} credits)`}
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default PurchaseFlowModal;
