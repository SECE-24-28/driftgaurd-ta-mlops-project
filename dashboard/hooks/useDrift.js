import { useState, useEffect, useCallback } from 'react';
import { getModel, getDrift, getRetrainingHistory, getAuditLog, getModelVersions } from '../lib/api';

export function useDrift(modelId) {
  const [model, setModel] = useState(null);
  const [driftData, setDriftData] = useState([]);
  const [retrainHistory, setRetrainHistory] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [versions, setVersions] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchAll = useCallback(async (silent = false) => {
    if (!modelId) return;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const [modelRes, driftRes, retrainRes, auditRes, versionsRes] = await Promise.all([
        getModel(modelId),
        getDrift(modelId),
        getRetrainingHistory(modelId),
        getAuditLog(modelId),
        getModelVersions(modelId)
      ]);

      if (modelRes === null) {
        setError("Cannot connect to DriftGuard API at localhost:8000. Make sure the backend is running.");
        setModel(null);
        setDriftData([]);
        setRetrainHistory([]);
        setAuditLog([]);
        setVersions([]);
      } else {
        setModel(modelRes);
        setDriftData(driftRes || []);
        setRetrainHistory(retrainRes || []);
        setAuditLog(auditRes || []);
        setVersions(versionsRes || []);
      }
      setLastUpdated(new Date());
    } catch (err) {
      console.error(`Error fetching detailed data for ${modelId}:`, err);
      setError(err.message || "Failed to load model details");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [modelId]);

  useEffect(() => {
    if (modelId) {
      fetchAll();

      // Poll every 30 seconds
      const interval = setInterval(() => {
        fetchAll(true);
      }, 30000);

      return () => clearInterval(interval);
    }
  }, [modelId, fetchAll]);

  return {
    model,
    driftData,
    retrainHistory,
    auditLog,
    versions,
    loading,
    error,
    lastUpdated,
    refresh: () => fetchAll(false),
    silentRefresh: () => fetchAll(true)
  };
}
