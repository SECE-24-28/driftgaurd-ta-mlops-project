import { useState, useEffect, useCallback } from 'react';
import { getModels } from '../lib/api';

export function useModels() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchModels = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await getModels();
      if (data === null) {
        setError("Cannot connect to DriftGuard API at localhost:8000. Make sure the backend is running.");
        setModels([]);
      } else {
        setModels(data || []);
      }
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Error in useModels:", err);
      setError(err.message || "Failed to load models");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchModels(true);
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchModels]);

  return {
    models,
    loading,
    error,
    lastUpdated,
    refresh: () => fetchModels(false),
    silentRefresh: () => fetchModels(true)
  };
}
