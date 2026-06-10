import React, { useState, useEffect } from 'react';
import { Wallet, TrendingUp, TrendingDown, Clock, Gift, Zap, Calendar } from 'lucide-react';

/**
 * PHASE 35: Credit Wallet Component
 * Displays credit balance and transaction history
 */
const CreditWallet = ({ profileId, onSpendCredits }) => {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSpendModal, setShowSpendModal] = useState(false);

  useEffect(() => {
    fetchWallet();
  }, [profileId]);

  const fetchWallet = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('admin_token');
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001/api';

      const response = await fetch(`${backendUrl}/profiles/${profileId}/credits`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch wallet');

      const data = await response.json();
      setWallet(data);

    } catch (error) {
      console.error('Error fetching wallet:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTransactionIcon = (type) => {
    switch (type) {
      case 'referral_reward':
        return <Gift className="w-5 h-5 text-green-600" />;
      case 'feature_unlock':
        return <Zap className="w-5 h-5 text-purple-600" />;
      case 'plan_extension':
        return <Calendar className="w-5 h-5 text-blue-600" />;
      case 'admin_grant':
        return <TrendingUp className="w-5 h-5 text-green-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-600" />;
    }
  };

  const getTransactionColor = (amount) => {
    return amount > 0 ? 'text-green-600' : 'text-red-600';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-center py-8">
          <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-3 text-gray-600">Loading wallet...</span>
        </div>
      </div>
    );
  }

  if (!wallet) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <p className="text-gray-600">Failed to load wallet</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Balance Card */}
      <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-lg p-6 text-white shadow-lg">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-purple-100 text-sm mb-1">Available Credits</p>
            <h2 className="text-5xl font-bold">{wallet.balance}</h2>
          </div>
          <Wallet className="w-16 h-16 opacity-80" />
        </div>

        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/20">
          <div>
            <p className="text-purple-100 text-xs mb-1">Earned</p>
            <p className="text-xl font-semibold">{wallet.earned_total}</p>
          </div>
          <div>
            <p className="text-purple-100 text-xs mb-1">Spent</p>
            <p className="text-xl font-semibold">{wallet.spent_total}</p>
          </div>
          <div>
            <p className="text-purple-100 text-xs mb-1">Expired</p>
            <p className="text-xl font-semibold">{wallet.expired_total}</p>
          </div>
        </div>

        {wallet.balance >= 50 && (
          <button
            onClick={() => setShowSpendModal(true)}
            className="mt-4 w-full bg-white text-purple-600 py-3 rounded-lg font-semibold hover:bg-purple-50 transition-colors"
          >
            Use Credits
          </button>
        )}
      </div>

      {/* What You Can Do */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What You Can Do With Credits</h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
            <Zap className="w-6 h-6 text-purple-600 flex-shrink-0 mt-1" />
            <div>
              <p className="font-medium text-gray-900">Unlock Premium Features</p>
              <p className="text-sm text-gray-600">100 credits = 7 days of any premium feature</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
            <Calendar className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
            <div>
              <p className="font-medium text-gray-900">Extend Your Plan</p>
              <p className="text-sm text-gray-600">50 credits = 1 extra day of your current plan</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
            <Gift className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
            <div>
              <p className="font-medium text-gray-900">Earn More Credits</p>
              <p className="text-sm text-gray-600">200 credits for each friend who creates an invitation</p>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Transactions</h3>
        
        {wallet.recent_transactions && wallet.recent_transactions.length > 0 ? (
          <div className="space-y-3">
            {wallet.recent_transactions.map((txn) => (
              <div
                key={txn.transaction_id}
                className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex-shrink-0">
                  {getTransactionIcon(txn.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {txn.description}
                  </p>
                  <p className="text-sm text-gray-500">
                    {formatDate(txn.created_at)}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`font-bold text-lg ${getTransactionColor(txn.amount)}`}>
                    {txn.amount > 0 ? '+' : ''}{txn.amount}
                  </p>
                  <p className="text-xs text-gray-500">
                    Balance: {txn.balance_after}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-600">No transactions yet</p>
            <p className="text-sm text-gray-500 mt-1">
              Start referring friends to earn credits!
            </p>
          </div>
        )}
      </div>

      {/* Spend Credits Modal */}
      {showSpendModal && (
        <SpendCreditsModal
          profileId={profileId}
          currentBalance={wallet.balance}
          onClose={() => setShowSpendModal(false)}
          onSuccess={() => {
            setShowSpendModal(false);
            fetchWallet();
            if (onSpendCredits) onSpendCredits();
          }}
        />
      )}
    </div>
  );
};

/**
 * Modal for spending credits
 */
const SpendCreditsModal = ({ profileId, currentBalance, onClose, onSuccess }) => {
  const [spendType, setSpendType] = useState('plan_extension');
  const [extensionDays, setExtensionDays] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const calculateCost = () => {
    if (spendType === 'plan_extension') {
      return 50 * extensionDays;
    }
    return 100; // feature_unlock
  };

  const handleSpend = async () => {
    const cost = calculateCost();
    
    if (cost > currentBalance) {
      setError(`Insufficient credits. You need ${cost} credits but have ${currentBalance}.`);
      return;
    }

    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('admin_token');
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001/api';

      const response = await fetch(`${backendUrl}/profiles/${profileId}/credits/spend`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          profile_id: profileId,
          spend_type: spendType,
          extension_days: spendType === 'plan_extension' ? extensionDays : null
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to spend credits');
      }

      const data = await response.json();
      alert(data.message);
      onSuccess();

    } catch (error) {
      console.error('Error spending credits:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Use Your Credits</h3>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              What do you want to do?
            </label>
            <select
              value={spendType}
              onChange={(e) => setSpendType(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg"
            >
              <option value="plan_extension">Extend Plan Duration</option>
              <option value="feature_unlock" disabled>Unlock Feature (Coming Soon)</option>
            </select>
          </div>

          {spendType === 'plan_extension' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Days
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={extensionDays}
                onChange={(e) => setExtensionDays(parseInt(e.target.value) || 1)}
                className="w-full px-4 py-2 border rounded-lg"
              />
              <p className="text-sm text-gray-600 mt-1">
                50 credits per day
              </p>
            </div>
          )}

          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600">Cost:</span>
              <span className="font-bold text-lg text-purple-600">{calculateCost()} credits</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Balance After:</span>
              <span className="font-bold text-lg text-gray-900">
                {currentBalance - calculateCost()} credits
              </span>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSpend}
            disabled={loading || calculateCost() > currentBalance}
            className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreditWallet;
