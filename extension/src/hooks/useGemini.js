import { useState } from 'react';

export function useGemini(messageType) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function generate(payload) {
    setLoading(true);
    setError(null);
    try {
      const response = await chrome.runtime.sendMessage({ type: messageType, ...payload });
      if (response?.error === 'NO_API_KEY') {
        setError('NO_API_KEY');
        return null;
      }
      if (response?.error) {
        setError(response.error);
        return null;
      }
      setResult(response);
      return response;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { generate, loading, error, result };
}
