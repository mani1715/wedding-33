import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import QRCodeDisplay from '@/components/QRCodeDisplay';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * PHASE 28: QR Code Management Page
 * 
 * Admin page for generating and downloading QR codes for:
 * - Full wedding invitation
 * - Individual events
 * 
 * Usage: Print cards, venue banners, digital displays
 */
const QRCodeManagement = () => {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProfile();
  }, [profileId]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('adminToken');
      const response = await axios.get(
        `${API_URL}/api/admin/profiles/${profileId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setProfile(response.data);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
      setError('Failed to load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-pink-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="luxe min-h-screen p-6">
        <div className="max-w-4xl mx-auto">
          <div className="lux-glass p-8 text-center">
            <p className="mb-4" style={{ color: '#F08585' }}>{error || 'Profile not found'}</p>
            <Button onClick={() => navigate('/admin/dashboard')} className="lux-btn">
              Back to Studio
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Get enabled events
  const enabledEvents = profile.events?.filter(e => e.event_enabled) || [];

  return (
    <div className="luxe min-h-screen relative" data-testid="qr-management">
      <div className="lux-orbit" style={{ width: 700, height: 700, top: -200, right: -200 }} />
      <div className="relative z-10 max-w-5xl mx-auto p-6 md:p-12">
        {/* Header */}
        <div className="mb-10">
          <Button
            variant="ghost"
            onClick={() => navigate('/admin/dashboard')}
            className="lux-btn lux-btn-ghost text-xs mb-6"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Studio
          </Button>

          <span className="lux-eyebrow block mb-4">◆ Scan · Share · Celebrate</span>
          <h1 className="font-display text-[2.4rem] md:text-[3.8rem] leading-[1.04]" style={{ color: '#FFF8DC' }}>
            QR <span className="font-script italic text-gold">codes</span> for every guest
          </h1>
          <p className="mt-4 text-base" style={{ color: 'rgba(255,248,220,0.65)' }}>
            {profile.bride_name} &amp; {profile.groom_name}
          </p>
        </div>

        {/* Profile Info */}
        <div className="bg-gradient-to-r from-pink-100 to-purple-100 rounded-lg p-6 mb-8 shadow-md">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            About QR Codes
          </h2>
          <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-700">
            <div>
              <h3 className="font-semibold mb-2">📱 Where to Use:</h3>
              <ul className="space-y-1 ml-4">
                <li>• Print on physical wedding cards</li>
                <li>• Display on venue entrance banners</li>
                <li>• Add to save-the-date cards</li>
                <li>• Place on table cards at reception</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-2">✨ Benefits:</h3>
              <ul className="space-y-1 ml-4">
                <li>• Instant access to digital invitation</li>
                <li>• Guests can RSVP immediately</li>
                <li>• Easy to share with others</li>
                <li>• Works on any smartphone camera</li>
              </ul>
            </div>
          </div>
        </div>

        {/* QR Code Display Component */}
        <QRCodeDisplay
          profileId={profileId}
          slugUrl={profile.slug_url}
          events={enabledEvents}
        />

        {/* Additional Instructions */}
        <div className="mt-8 bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            💡 Pro Tips
          </h3>
          <div className="space-y-3 text-sm text-gray-700">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-pink-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-pink-600 font-bold">1</span>
              </div>
              <div>
                <p className="font-semibold mb-1">Test Before Printing</p>
                <p className="text-gray-600">Download and scan the QR code with your phone to ensure it works correctly before mass printing.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-purple-600 font-bold">2</span>
              </div>
              <div>
                <p className="font-semibold mb-1">Size Matters</p>
                <p className="text-gray-600">For print materials, ensure the QR code is at least 2cm x 2cm (0.8" x 0.8") for easy scanning.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-blue-600 font-bold">3</span>
              </div>
              <div>
                <p className="font-semibold mb-1">High Contrast</p>
                <p className="text-gray-600">Maintain good contrast between QR code and background for reliable scanning in all lighting conditions.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-green-600 font-bold">4</span>
              </div>
              <div>
                <p className="font-semibold mb-1">Event-Specific QR Codes</p>
                <p className="text-gray-600">Generate separate QR codes for each event (Engagement, Haldi, etc.) to direct guests to specific ceremony details.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QRCodeManagement;
