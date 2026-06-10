import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, FileText, ExternalLink, Info } from 'lucide-react';

const ParkingConfig = ({ value, onChange }) => {
  const [parkingEnabled, setParkingEnabled] = useState(value?.parking_enabled || false);
  const [parkingType, setParkingType] = useState(value?.parking_type || 'description');
  const [description, setDescription] = useState(value?.parking_description || '');
  const [mapLink, setMapLink] = useState(value?.parking_map_link || '');

  const handleChange = () => {
    onChange({
      parking_enabled: parkingEnabled,
      parking_type: parkingType,
      parking_description: parkingType === 'description' ? description : '',
      parking_map_link: parkingType === 'map_link' ? mapLink : ''
    });
  };

  React.useEffect(() => {
    handleChange();
  }, [parkingEnabled, parkingType, description, mapLink]);

  return (
    <div className="space-y-4">
      {/* Enable Parking Info */}
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="parking-enabled"
          checked={parkingEnabled}
          onChange={(e) => setParkingEnabled(e.target.checked)}
          className="w-4 h-4 rounded border-cream/30 text-gold focus:ring-gold"
        />
        <label htmlFor="parking-enabled" className="text-cream font-medium cursor-pointer">
          Include Parking Information
        </label>
      </div>

      {parkingEnabled && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="lux-glass p-4 space-y-4"
        >
          {/* Info Banner */}
          <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded">
            <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-cream/80">
              Help your guests find parking easily. Choose between providing a text description or a Google Maps link to the parking area.
            </p>
          </div>

          {/* Parking Type Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-cream/80">Parking Information Type</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setParkingType('description')}
                className={`p-4 rounded border-2 transition-all ${
                  parkingType === 'description'
                    ? 'border-gold bg-gold/10'
                    : 'border-cream/20 bg-dark/30 hover:border-gold/50'
                }`}
              >
                <FileText className={`w-5 h-5 mb-2 ${
                  parkingType === 'description' ? 'text-gold' : 'text-cream/60'
                }`} />
                <div className="text-sm font-semibold text-cream mb-1">Description</div>
                <div className="text-xs text-cream/60">Nearby parking info</div>
              </button>

              <button
                type="button"
                onClick={() => setParkingType('map_link')}
                className={`p-4 rounded border-2 transition-all ${
                  parkingType === 'map_link'
                    ? 'border-gold bg-gold/10'
                    : 'border-cream/20 bg-dark/30 hover:border-gold/50'
                }`}
              >
                <MapPin className={`w-5 h-5 mb-2 ${
                  parkingType === 'map_link' ? 'text-gold' : 'text-cream/60'
                }`} />
                <div className="text-sm font-semibold text-cream mb-1">Map Link</div>
                <div className="text-xs text-cream/60">Google Maps URL</div>
              </button>
            </div>
          </div>

          {/* Description Input */}
          {parkingType === 'description' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-2"
            >
              <label className="text-sm font-medium text-cream/80">
                Parking Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., Parking available at the basement of the function hall. Additional parking on the street behind the venue."
                rows="4"
                className="w-full px-4 py-3 rounded bg-dark/50 border border-cream/20 text-cream text-sm placeholder:text-cream/30 focus:border-gold/50 focus:outline-none"
              />
              <p className="text-xs text-cream/50">
                Describe where guests can park or provide directions to nearby parking.
              </p>
            </motion.div>
          )}

          {/* Map Link Input */}
          {parkingType === 'map_link' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-2"
            >
              <label className="text-sm font-medium text-cream/80">
                Google Maps Link
              </label>
              <div className="relative">
                <input
                  type="url"
                  value={mapLink}
                  onChange={(e) => setMapLink(e.target.value)}
                  placeholder="https://maps.google.com/..."
                  className="w-full pl-4 pr-10 py-3 rounded bg-dark/50 border border-cream/20 text-cream text-sm placeholder:text-cream/30 focus:border-gold/50 focus:outline-none"
                />
                {mapLink && (
                  <a
                    href={mapLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gold hover:text-gold/80"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
              <p className="text-xs text-cream/50">
                Paste the Google Maps link to the parking location. Guests can tap to open directions.
              </p>
              
              {/* How to get link */}
              <details className="text-xs text-cream/60 bg-dark/30 p-3 rounded">
                <summary className="cursor-pointer font-medium text-cream/80 hover:text-gold">
                  How to get Google Maps link?
                </summary>
                <ol className="mt-2 space-y-1 list-decimal list-inside">
                  <li>Open Google Maps in your browser</li>
                  <li>Search for the parking location</li>
                  <li>Click "Share" button</li>
                  <li>Copy the link and paste it here</li>
                </ol>
              </details>
            </motion.div>
          )}

          {/* Preview */}
          {parkingEnabled && ((parkingType === 'description' && description) || (parkingType === 'map_link' && mapLink)) && (
            <div className="border-t border-cream/10 pt-4">
              <p className="text-xs font-semibold text-cream/60 mb-2">Preview:</p>
              <div className="bg-dark/50 p-3 rounded border border-cream/10">
                <div className="flex items-start gap-2">
                  <MapPin className="w-4 h-4 text-gold flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-cream mb-1">Parking Information</p>
                    {parkingType === 'description' ? (
                      <p className="text-xs text-cream/70">{description}</p>
                    ) : (
                      <a href={mapLink} className="text-xs text-gold hover:underline flex items-center gap-1">
                        Open in Google Maps
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
};

export default ParkingConfig;
