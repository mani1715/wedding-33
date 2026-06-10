import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Music, Play, Pause, ExternalLink, Search, Volume2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const MusicSelector = ({ selectedSong, onSelect }) => {
  const [songs, setSongs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [customUrl, setCustomUrl] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [playingPreview, setPlayingPreview] = useState(null);

  useEffect(() => {
    fetchMusic();
  }, [selectedCategory]);

  const fetchMusic = async () => {
    try {
      setLoading(true);
      const params = selectedCategory !== 'all' ? `?category=${selectedCategory}` : '';
      const res = await axios.get(`${API_URL}/api/music/library${params}`);
      setSongs(res.data.songs || []);
      setCategories(res.data.categories || []);
    } catch (e) {
      console.error('Failed to fetch music:', e);
    } finally {
      setLoading(false);
    }
  };

  const filteredSongs = songs.filter(song =>
    song.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    song.mood.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectSong = (song) => {
    onSelect(song);
    setShowCustomInput(false);
  };

  const handleCustomUrl = () => {
    if (customUrl.trim()) {
      onSelect({
        id: 'custom',
        title: 'Custom URL',
        url: customUrl.trim(),
        category: 'custom',
        mood: 'custom'
      });
      setCustomUrl('');
      setShowCustomInput(false);
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      devotional: 'from-orange-500/20 to-red-500/20 border-orange-500/30',
      classical: 'from-purple-500/20 to-pink-500/20 border-purple-500/30',
      pleasant: 'from-green-500/20 to-teal-500/20 border-green-500/30',
      romantic: 'from-red-500/20 to-pink-500/20 border-red-500/30',
      cinematic: 'from-blue-500/20 to-indigo-500/20 border-blue-500/30'
    };
    return colors[category] || 'from-gray-500/20 to-gray-600/20 border-gray-500/30';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Music className="w-5 h-5 text-gold" />
          <h3 className="text-lg font-semibold text-cream">Select Background Music</h3>
        </div>
        <button
          onClick={() => setShowCustomInput(!showCustomInput)}
          className="text-xs px-3 py-1 rounded-full border border-gold/30 text-gold hover:bg-gold/10 transition-all"
        >
          {showCustomInput ? 'Browse Library' : 'Custom URL'}
        </button>
      </div>

      {/* Custom URL Input */}
      <AnimatePresence>
        {showCustomInput && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lux-glass p-4 space-y-3"
          >
            <p className="text-sm text-cream/60">Paste a music URL (YouTube, SoundCloud, etc.)</p>
            <div className="flex gap-2">
              <input
                type="url"
                placeholder="https://..."
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                className="flex-1 px-4 py-2 rounded bg-dark/50 border border-cream/20 text-cream text-sm"
              />
              <button
                onClick={handleCustomUrl}
                disabled={!customUrl.trim()}
                className="px-4 py-2 rounded bg-gold text-dark font-semibold hover:bg-gold/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Use This URL
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search & Category Filter */}
      {!showCustomInput && (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream/40" />
            <input
              type="text"
              placeholder="Search by title or mood..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded bg-dark/50 border border-cream/20 text-cream text-sm"
            />
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-3 py-1 rounded-full text-xs transition-all ${
                selectedCategory === 'all'
                  ? 'bg-gold text-dark font-semibold'
                  : 'bg-dark/30 text-cream/60 border border-cream/20'
              }`}
            >
              All ({songs.length})
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full text-xs capitalize transition-all ${
                  selectedCategory === cat
                    ? 'bg-gold text-dark font-semibold'
                    : 'bg-dark/30 text-cream/60 border border-cream/20'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </>
      )}

      {/* Song List */}
      {!showCustomInput && (
        <div className="max-h-[400px] overflow-y-auto space-y-2 pr-2">
          {loading ? (
            <div className="text-center py-8 text-cream/50">Loading music...</div>
          ) : filteredSongs.length === 0 ? (
            <div className="text-center py-8 text-cream/50">No songs found</div>
          ) : (
            filteredSongs.map((song) => (
              <motion.div
                key={song.id}
                whileHover={{ x: 4 }}
                className={`p-4 rounded border bg-gradient-to-r ${getCategoryColor(song.category)} cursor-pointer transition-all ${
                  selectedSong?.id === song.id ? 'ring-2 ring-gold' : ''
                }`}
                onClick={() => handleSelectSong(song)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-semibold text-cream truncate">{song.title}</h4>
                      {selectedSong?.id === song.id && (
                        <span className="text-xs bg-gold text-dark px-2 py-0.5 rounded-full font-semibold">
                          Selected
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-cream/60">
                      <span className="capitalize">{song.category}</span>
                      <span>•</span>
                      <span className="capitalize">{song.mood}</span>
                      <span>•</span>
                      <span>{Math.floor(song.duration_sec / 60)}:{(song.duration_sec % 60).toString().padStart(2, '0')}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (playingPreview === song.id) {
                          setPlayingPreview(null);
                        } else {
                          setPlayingPreview(song.id);
                        }
                      }}
                      className="p-2 rounded bg-gold/20 text-gold hover:bg-gold/30 transition-all"
                      title="Preview"
                    >
                      {playingPreview === song.id ? (
                        <Pause className="w-3 h-3" />
                      ) : (
                        <Play className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      )}

      {/* Selected Song Display */}
      {selectedSong && (
        <div className="lux-glass p-4 border border-gold/30">
          <div className="flex items-center gap-2 mb-2">
            <Volume2 className="w-4 h-4 text-gold" />
            <span className="text-sm font-semibold text-gold">Selected Music</span>
          </div>
          <p className="text-cream font-medium">{selectedSong.title}</p>
          {selectedSong.url && selectedSong.id !== 'custom' && (
            <a
              href={selectedSong.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-cream/60 hover:text-gold flex items-center gap-1 mt-1"
            >
              <ExternalLink className="w-3 h-3" />
              Preview URL
            </a>
          )}
        </div>
      )}

      {/* Info */}
      <div className="text-xs text-cream/50 space-y-1">
        <p>• Select from our curated collection of 60 songs</p>
        <p>• Or paste your own music URL from YouTube, SoundCloud, etc.</p>
        <p>• Songs are categorized by mood and occasion</p>
      </div>
    </div>
  );
};

export default MusicSelector;
