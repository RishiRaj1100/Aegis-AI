import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/services/api';

/**
 * RecommendationsWidget - Display personalized task recommendations
 */
export const RecommendationsWidget: React.FC<{ userId: string }> = ({ userId }) => {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [strategy, setStrategy] = useState('hybrid');

  useEffect(() => {
    if (!userId) {
      setRecommendations([]);
      setLoading(false);
      return;
    }
    fetchRecommendations();
  }, [userId, strategy]);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(
        `/api/recommendations/for-user?user_id=${encodeURIComponent(userId)}&strategy=${strategy}&top_k=10`,
        { skipAuth: false }
      );
      setRecommendations(data.recommendations || []);
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Recommended Tasks</h2>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="px-3 py-1 border rounded text-sm"
        >
          <option value="hybrid">Hybrid</option>
          <option value="content">Content-Based</option>
          <option value="historical">Historical</option>
          <option value="collaborative">Collaborative</option>
        </select>
      </div>

      {!userId ? (
        <p className="text-gray-500">Connect an account to view personalized recommendations.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading recommendations...</p>
      ) : recommendations.length === 0 ? (
        <p className="text-gray-500">No recommendations available</p>
      ) : (
        <div className="space-y-3">
          {recommendations.map((rec) => (
            <div
              key={rec.task_id}
              className="p-3 border-l-4 border-blue-500 bg-blue-50 rounded"
            >
              <h3 className="font-semibold">{rec.goal}</h3>
              <p className="text-sm text-gray-600">{rec.domain}</p>
              <p className="text-xs text-gray-500 mt-1">
                Similarity: {Math.round((rec.similarity_score || 0) * 100)}%
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * SearchBar - Hybrid search with autocomplete suggestions
 */
interface SearchBarProps {
  userId: string;
  onSearch: (query: string) => void;
  initialQuery?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  userId,
  onSearch,
  initialQuery = '',
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    if (!initialQuery.trim()) {
      return;
    }

    setQuery(initialQuery);
    void handleSearch(initialQuery);
  }, [initialQuery]);

  const fetchSuggestions = async (value: string) => {
    if (!userId) {
      setSuggestions([]);
      return;
    }
    const data = await apiFetch(
      `/api/search/suggest?user_id=${encodeURIComponent(userId)}&prefix=${encodeURIComponent(value)}`,
      { skipAuth: false }
    );
    setSuggestions(data.suggestions || []);
    setShowSuggestions(true);
  };

  const handleInputChange = async (value: string) => {
    setQuery(value);

    if (value.length > 2) {
      try {
        await fetchSuggestions(value);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
      }
    } else {
      setSuggestions([]);
    }
  };

  const handleSearch = (value: string = query) => {
    const activeQuery = value.trim();
    if (activeQuery) {
      setQuery(activeQuery);
      onSearch(activeQuery);
      setShowSuggestions(false);
    }
  };

  return (
    <div className="relative w-full">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Search tasks..."
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={() => handleSearch()}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Search
        </button>
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-10">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                onSearch(suggestion);
                setShowSuggestions(false);
              }}
              className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
            >
              {suggestion}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * APIKeyManager - API key management UI
 */
export const APIKeyManager: React.FC<{ userId: string }> = ({ userId }) => {
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }
    fetchApiKeys();
  }, [userId]);

  const fetchApiKeys = async () => {
    try {
      const data = await apiFetch(`/api/security/api-keys?user_id=${encodeURIComponent(userId)}`);
      setApiKeys(data.api_keys || []);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
      setApiKeys([]);
    } finally {
      setLoading(false);
    }
  };

  const generateApiKey = async () => {
    if (!newKeyName.trim() || !userId) return;

    try {
      const data = await apiFetch(
        `/api/security/api-keys/create?user_id=${encodeURIComponent(userId)}&name=${encodeURIComponent(newKeyName)}&expires_in_days=90`,
        { method: 'POST' }
      );
      setGeneratedKey(data.api_key);
      setNewKeyName('');
      await fetchApiKeys();
    } catch (error) {
      console.error('Failed to generate API key:', error);
    }
  };

  const revokeApiKey = async (keyName: string) => {
    try {
      await apiFetch(
        `/api/security/api-keys/revoke?user_id=${encodeURIComponent(userId)}&key_name=${encodeURIComponent(keyName)}`,
        { method: 'POST' }
      );
      await fetchApiKeys();
    } catch (error) {
      console.error('Failed to revoke API key:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">API Key Management</h2>
      {!userId ? <p className="text-sm text-gray-500 mb-4">Sign in to manage API keys.</p> : null}

      {generatedKey && (
        <div className="mb-4 p-3 bg-green-100 border border-green-500 rounded">
          <p className="text-sm font-semibold">New API Key Generated:</p>
          <code className="block mt-2 p-2 bg-gray-100 rounded text-xs break-all">
            {generatedKey}
          </code>
          <p className="text-xs text-red-600 mt-2">Save this key securely!</p>
        </div>
      )}

      <div className="mb-6 p-4 bg-gray-50 rounded">
        <h3 className="font-semibold mb-2">Generate New Key</h3>
        <input
          type="text"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          placeholder="Key name (e.g., mobile-app)"
          className="w-full px-3 py-2 border rounded mb-2"
        />
        <button
          onClick={generateApiKey}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Generate Key
        </button>
      </div>

      <div>
        <h3 className="font-semibold mb-2">Active Keys</h3>
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : apiKeys.length === 0 ? (
          <p className="text-gray-500 text-sm">No API keys yet</p>
        ) : (
          <div className="space-y-2">
            {apiKeys.map((key) => (
              <div key={key.name} className="flex justify-between items-center p-2 border rounded">
                <div>
                  <p className="font-semibold text-sm">{key.name}</p>
                  <p className="text-xs text-gray-500">
                    Expires: {new Date(key.expires_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => revokeApiKey(key.name)}
                  className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * MFASetup - Two-factor authentication setup
 */
export const MFASetup: React.FC<{ userId: string }> = ({ userId }) => {
  const [mfaSecret, setMfaSecret] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [showQr, setShowQr] = useState(false);

  const enableMFA = async () => {
    if (!userId) return;
    try {
      const data = await apiFetch(`/api/security/mfa/enable?user_id=${encodeURIComponent(userId)}`, {
        method: 'POST',
      });
      setMfaSecret(data.secret);
      setShowQr(true);
    } catch (error) {
      console.error('Failed to enable MFA:', error);
    }
  };

  const confirmMFA = async () => {
    if (!verificationCode.trim() || !userId) return;

    try {
      await apiFetch(
        `/api/security/mfa/confirm?user_id=${encodeURIComponent(userId)}&code=${encodeURIComponent(verificationCode)}`,
        { method: 'POST' }
      );

      setMfaEnabled(true);
      setShowQr(false);
      setVerificationCode('');
      setMfaSecret('');
    } catch (error) {
      console.error('Failed to confirm MFA:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Two-Factor Authentication</h2>
      {!userId ? <p className="text-sm text-gray-500 mb-4">Sign in to enable two-factor authentication.</p> : null}

      {mfaEnabled ? (
        <div className="p-3 bg-green-100 border border-green-500 rounded">
          <p className="text-green-800">✓ 2FA is enabled on your account</p>
        </div>
      ) : showQr ? (
        <div className="space-y-4">
          <div className="p-3 bg-yellow-100 rounded">
            <p className="text-sm font-semibold mb-2">
              1. Scan with authenticator app
            </p>
            <code className="block p-2 bg-white rounded text-xs">
              {mfaSecret}
            </code>
          </div>

          <div>
            <p className="text-sm font-semibold mb-2">
              2. Enter 6-digit code to confirm
            </p>
            <input
              type="text"
              maxLength={6}
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="000000"
              className="w-20 px-3 py-2 border rounded text-center"
            />
          </div>

          <button
            onClick={confirmMFA}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Confirm 2FA
          </button>
        </div>
      ) : (
        <button
          onClick={enableMFA}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Enable 2FA
        </button>
      )}
    </div>
  );
};

/**
 * BatchImportExport - CSV upload/download
 */
export const BatchImportExport: React.FC<{ userId: string }> = ({ userId }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleImport = async () => {
    if (!file || !userId) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_id', userId);

      const data = await apiFetch('/api/batch/import-csv', {
        method: 'POST',
        body: formData,
      });

      setUploadStatus(`Imported ${data.count} tasks successfully`);
      setFile(null);
    } catch (error) {
      setUploadStatus('Failed to import tasks');
    } finally {
      setUploading(false);
    }
  };

  const handleExport = async () => {
    if (!userId) return;
    try {
      const payload = await apiFetch(`/api/batch/export-csv?user_id=${encodeURIComponent(userId)}`, {
        method: 'POST',
      });
      const csvText = payload?.data || '';
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tasks-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
    } catch (error) {
      console.error('Failed to export tasks:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Batch Import/Export</h2>
      {!userId ? <p className="text-sm text-gray-500 mb-4">Sign in to import or export batches.</p> : null}

      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 border rounded">
          <h3 className="font-semibold mb-2">Import CSV</h3>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="w-full mb-2"
          />
          <button
            onClick={handleImport}
            disabled={!file || uploading}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
          >
            {uploading ? 'Importing...' : 'Import Tasks'}
          </button>
          {uploadStatus && (
            <p className="text-sm mt-2 text-green-600">{uploadStatus}</p>
          )}
        </div>

        <div className="p-4 border rounded">
          <h3 className="font-semibold mb-2">Export CSV</h3>
          <p className="text-sm text-gray-600 mb-3">
            Download all your tasks as CSV
          </p>
          <button
            onClick={handleExport}
            className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            Export Tasks
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * WebhookManager - Webhook configuration UI
 */
export const WebhookManager: React.FC<{ userId: string }> = ({ userId }) => {
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [newUrl, setNewUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const eventTypes = [
    'task.created',
    'task.completed',
    'task.failed',
    'analytics.updated',
    'recommendation.generated',
    'milestone.reached',
    'alert.triggered',
  ];

  useEffect(() => {
    if (!userId) {
      setWebhooks([]);
      setLoading(false);
      return;
    }
    fetchWebhooks();
  }, [userId]);

  const fetchWebhooks = async () => {
    try {
      const data = await apiFetch(`/api/webhooks/?user_id=${encodeURIComponent(userId)}`);
      setWebhooks(data.webhooks || []);
    } catch (error) {
      console.error('Failed to fetch webhooks:', error);
      setWebhooks([]);
    } finally {
      setLoading(false);
    }
  };

  const registerWebhook = async () => {
    if (!newUrl.trim() || selectedEvents.length === 0 || !userId) return;

    try {
      const params = new URLSearchParams();
      params.append('user_id', userId);
      params.append('url', newUrl);
      selectedEvents.forEach((event) => params.append('events', event));
      await apiFetch(`/api/webhooks/register?${params.toString()}`, { method: 'POST' });

      setNewUrl('');
      setSelectedEvents([]);
      await fetchWebhooks();
    } catch (error) {
      console.error('Failed to register webhook:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Webhook Management</h2>

      <div className="mb-6 p-4 bg-gray-50 rounded">
        <h3 className="font-semibold mb-2">Register New Webhook</h3>
        <input
          type="url"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          placeholder="https://example.com/webhook"
          className="w-full px-3 py-2 border rounded mb-2"
        />

        <div className="mb-2">
          <p className="text-sm font-semibold mb-1">Select events:</p>
          <div className="grid grid-cols-2 gap-2">
            {eventTypes.map((event) => (
              <label key={event} className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedEvents.includes(event)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedEvents([...selectedEvents, event]);
                    } else {
                      setSelectedEvents(
                        selectedEvents.filter((e) => e !== event)
                      );
                    }
                  }}
                  className="mr-2"
                />
                <span className="text-sm">{event}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={registerWebhook}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Register Webhook
        </button>
      </div>

      <div>
        <h3 className="font-semibold mb-2">Active Webhooks</h3>
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : webhooks.length === 0 ? (
          <p className="text-gray-500 text-sm">No webhooks registered</p>
        ) : (
          <div className="space-y-2">
            {webhooks.map((webhook) => (
              <div key={webhook.webhook_id} className="p-2 border rounded">
                <p className="font-semibold text-sm">{webhook.url}</p>
                <p className="text-xs text-gray-500">
                  {webhook.events?.join(', ')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
