import React, { useState, useEffect } from 'react';

/**
 * PHASE 28: QRCodeDisplay Component
 * 
 * Admin component to display and download QR codes for wedding invitations.
 * Generates QR codes for full wedding or individual events.
 * 
 * Props:
 * - profileId: Profile ID
 * - slugUrl: Profile slug URL
 * - events: Array of events (optional, for event-specific QR codes)
 */
const QRCodeDisplay = ({ profileId, slugUrl, events = [] }) => {
  const [selectedType, setSelectedType] = useState('full'); // 'full' or event_id
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  // Generate QR code
  const generateQRCode = async (type, eventId = null) => {
    setLoading(true);
    setError(null);

    try {
      let url;
      if (type === 'full') {
        url = `${backendUrl}/api/profiles/${slugUrl}/qr-code?size=500`;
      } else {
        url = `${backendUrl}/api/events/${eventId}/qr-code?size=500`;
      }

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to generate QR code');
      }

      const data = await response.json();
      setQrData(data);
    } catch (err) {
      console.error('QR code generation error:', err);
      setError('Failed to generate QR code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Generate on mount and when selection changes
  useEffect(() => {
    if (selectedType === 'full') {
      generateQRCode('full');
    } else {
      generateQRCode('event', selectedType);
    }
  }, [selectedType, slugUrl]);

  // Download QR code
  const handleDownload = () => {
    if (!qrData) return;

    const link = document.createElement('a');
    link.href = `data:image/png;base64,${qrData.qr_code_base64}`;
    link.download = qrData.download_filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Copy URL
  const handleCopyUrl = () => {
    if (!qrData) return;
    
    navigator.clipboard.writeText(qrData.url);
    alert('URL copied to clipboard!');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        QR Code Generator
      </h2>
      
      <p className="text-gray-600 mb-6">
        Generate QR codes for print cards, venue banners, or digital displays. 
        Guests can scan to instantly view your invitation.
      </p>

      {/* Selection Dropdown */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select what to generate QR for:
        </label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
        >
          <option value="full">Full Wedding Invitation</option>
          {events.map((event) => (
            <option key={event.event_id} value={event.event_id}>
              {event.event_type?.charAt(0).toUpperCase() + event.event_type?.slice(1)} Event
            </option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* QR Code Display */}
      {!loading && !error && qrData && (
        <div className="space-y-6">
          {/* QR Code Image */}
          <div className="flex justify-center bg-gray-50 rounded-lg p-8">
            <div className="bg-white p-4 rounded-lg shadow-md">
              <img
                src={`data:image/png;base64,${qrData.qr_code_base64}`}
                alt="QR Code"
                className="w-64 h-64"
              />
            </div>
          </div>

          {/* URL Display */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-2">QR Code links to:</p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={qrData.url}
                readOnly
                className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded text-sm"
              />
              <button
                onClick={handleCopyUrl}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Copy
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleDownload}
              className="flex-1 min-w-[200px] flex items-center justify-center gap-2 px-6 py-3 bg-pink-500 hover:bg-pink-600 text-white rounded-lg font-medium transition-colors shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download QR Code
            </button>

            <button
              onClick={() => generateQRCode(selectedType === 'full' ? 'full' : 'event', selectedType !== 'full' ? selectedType : null)}
              className="flex-1 min-w-[200px] flex items-center justify-center gap-2 px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Regenerate
            </button>
          </div>

          {/* Usage Tips */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">💡 Usage Tips:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Print on wedding cards and save-the-dates</li>
              <li>• Display on venue entrance banners</li>
              <li>• Add to digital invitations and WhatsApp forwards</li>
              <li>• Place on table cards for easy RSVP access</li>
              <li>• High error correction ensures scanning works even if partially damaged</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default QRCodeDisplay;
