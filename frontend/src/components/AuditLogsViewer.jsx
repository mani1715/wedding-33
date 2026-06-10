import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Eye, Users, Clock, TrendingUp, Calendar } from 'lucide-react';
import MandalaLoader from './luxury/MandalaLoader';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const AuditLogsViewer = ({ profileId }) => {
  const [loading, setLoading] = useState(true);
  const [auditData, setAuditData] = useState(null);

  useEffect(() => {
    if (profileId) {
      fetchAuditLogs();
    }
  }, [profileId]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_URL}/api/admin/profiles/${profileId}/audit-logs`);
      setAuditData(res.data);
    } catch (e) {
      console.error('Failed to fetch audit logs:', e);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="lux-glass p-6">
        <div className="grid place-items-center py-8">
          <MandalaLoader />
        </div>
      </div>
    );
  }

  if (!auditData) {
    return (
      <div className="lux-glass p-6 text-center text-cream/60">
        No audit data available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Views */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lux-glass p-5 border border-gold/20"
        >
          <div className="flex items-start justify-between mb-3">
            <Eye className="w-6 h-6 text-gold" />
            <TrendingUp className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-3xl font-bold text-cream mb-1">
            {auditData.view_count || 0}
          </div>
          <div className="text-sm text-cream/60">Total Views</div>
        </motion.div>

        {/* Unique Visitors */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lux-glass p-5 border border-gold/20"
        >
          <div className="flex items-start justify-between mb-3">
            <Users className="w-6 h-6 text-gold" />
          </div>
          <div className="text-3xl font-bold text-cream mb-1">
            {auditData.unique_visitors || 0}
          </div>
          <div className="text-sm text-cream/60">Unique Visitors</div>
          <div className="text-xs text-cream/40 mt-1">
            {auditData.view_count && auditData.unique_visitors
              ? `Avg ${(auditData.view_count / auditData.unique_visitors).toFixed(1)} views per visitor`
              : ''}
          </div>
        </motion.div>

        {/* Last Viewed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lux-glass p-5 border border-gold/20"
        >
          <div className="flex items-start justify-between mb-3">
            <Clock className="w-6 h-6 text-gold" />
          </div>
          <div className="text-lg font-semibold text-cream mb-1">
            {formatDate(auditData.last_viewed_at)}
          </div>
          <div className="text-sm text-cream/60">Last Viewed</div>
        </motion.div>
      </div>

      {/* Recent Visitors */}
      {auditData.recent_visitors && auditData.recent_visitors.length > 0 && (
        <div className="lux-glass p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-gold" />
            <h3 className="text-lg font-semibold text-cream">Recent Visitors</h3>
          </div>

          <div className="space-y-2">
            {auditData.recent_visitors.slice(0, 10).map((visitor, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between p-3 rounded bg-dark/30 border border-cream/10"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center">
                    <Users className="w-4 h-4 text-gold" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-cream/80">
                      Visitor {index + 1}
                    </div>
                    <div className="text-xs text-cream/50">
                      IP: {visitor.client_ip?.substring(0, 12)}...
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-cream/60 mb-0.5">
                    First: {formatDate(visitor.first_visit)}
                  </div>
                  <div className="text-xs text-gold">
                    Last: {formatDate(visitor.last_visit)}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {auditData.recent_visitors.length > 10 && (
            <div className="text-center mt-4">
              <button className="text-xs text-gold hover:underline">
                View All {auditData.recent_visitors.length} Visitors
              </button>
            </div>
          )}
        </div>
      )}

      {/* No Visitors Yet */}
      {(!auditData.recent_visitors || auditData.recent_visitors.length === 0) && (
        <div className="lux-glass p-10 text-center">
          <Calendar className="w-12 h-12 text-cream/30 mx-auto mb-3" />
          <p className="text-cream/60">No visitors yet</p>
          <p className="text-sm text-cream/40 mt-1">
            Share your invitation link to start tracking visitors
          </p>
        </div>
      )}

      {/* Engagement Indicator */}
      {auditData.view_count > 0 && auditData.unique_visitors > 0 && (
        <div className="lux-glass p-4 border border-gold/20">
          <div className="flex items-center justify-between">
            <span className="text-sm text-cream/80">Engagement Rate</span>
            <div className="flex items-center gap-2">
              <div className="w-32 h-2 bg-dark/50 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ 
                    width: `${Math.min(100, (auditData.unique_visitors / auditData.view_count) * 100 * 3)}%` 
                  }}
                  className="h-full bg-gradient-to-r from-gold to-yellow-400"
                />
              </div>
              <span className="text-sm font-bold text-gold">
                {((auditData.unique_visitors / auditData.view_count) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <p className="text-xs text-cream/50 mt-2">
            {auditData.unique_visitors} unique visitors out of {auditData.view_count} total views
          </p>
        </div>
      )}
    </div>
  );
};

export default AuditLogsViewer;
