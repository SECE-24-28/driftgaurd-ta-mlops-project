import React from 'react';
import Head from 'next/head';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import ModelCard from '../components/ModelCard';
import { useModels } from '../hooks/useModels';
import { withAuth } from '../hooks/useAuth';
import { Terminal } from 'lucide-react';

function Dashboard() {
  const { models, loading, error, lastUpdated, refresh } = useModels();

  // Stats calculation
  const totalModels = models ? models.length : 0;
  const healthyModels = models ? models.filter(m => m.status === 'healthy').length : 0;
  const degradedModels = models ? models.filter(m => m.status === 'degraded').length : 0;
  const retrainingModels = models ? models.filter(m => m.status === 'retraining').length : 0;

  return (
    <Layout onRefresh={refresh} lastUpdated={lastUpdated} isRefreshing={loading} error={error}>
      <Head>
        <title>DriftGuard Fleet Dashboard</title>
      </Head>

      <div className="space-y-8">
        {/* Fleet Stat Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Fleet Monitored" value={totalModels} color="text" />
          <StatCard label="Stable Champion Models" value={healthyModels} color="green" />
          <StatCard label="Drifting (SLA Breach)" value={degradedModels} color="amber" />
          <StatCard label="Active Retraining Loops" value={retrainingModels} color="blue" />
        </div>

        {/* Monitored Models Fleet Area */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-[#e6edf3]">Model Observability Fleet</h2>
              <p className="text-xs text-[#7d8590]">Select a model deployment to inspect sliding-window telemetry reports and version audit logs.</p>
            </div>
          </div>

          {/* Grid Area with states */}
          {loading && (!models || models.length === 0) ? (
            /* Skeleton Loading State */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, idx) => (
                <div key={idx} className="bg-[#1c2128] border border-[#30363d] p-5 rounded-lg h-[210px] space-y-4 animate-pulse">
                  <div className="flex justify-between items-center">
                    <div className="h-4 bg-[#30363d] rounded w-2/3" />
                    <div className="h-4 bg-[#30363d] rounded w-1/4" />
                  </div>
                  <div className="space-y-2">
                    <div className="h-3 bg-[#30363d] rounded w-1/2" />
                    <div className="h-6 bg-[#30363d] rounded w-full" />
                  </div>
                  <div className="h-8 bg-[#30363d] rounded w-full pt-4" />
                </div>
              ))}
            </div>
          ) : !models || models.length === 0 ? (
            /* Empty State Guide */
            <div className="bg-[#1c2128] border border-[#30363d] rounded-lg p-8 md:p-10 shadow-lg text-center max-w-2xl mx-auto space-y-6">
              <div className="space-y-2">
                <span className="p-3 bg-[#21262d] border border-[#30363d] rounded-xl inline-block text-[#58a6ff]">
                  <Terminal className="w-6 h-6" />
                </span>
                <h3 className="text-base font-bold text-[#e6edf3]">No Monitored Models Detected</h3>
                <p className="text-xs text-[#7d8590] leading-relaxed max-w-md mx-auto">
                  Ensure your machine learning deployment is integrated with the DriftGuard SDK to track inputs and outputs.
                </p>
              </div>

              {/* Quick start code block */}
              <div className="text-left bg-[#0d1117] border border-[#30363d] rounded-lg overflow-hidden font-mono text-[11px] text-[#e6edf3] p-4 space-y-2">
                <p className="text-[#7d8590]">// 1. Initialize DriftGuard Tracker</p>
                <p>from driftguard import DriftGuard</p>
                <p>dg = DriftGuard(model_id="my-model", api_url="http://localhost:8000")</p>
                <p className="text-[#7d8590]">// 2. Wrap model seamlessly and predict normal</p>
                <p>model = dg.wrap(trained_sklearn_model)</p>
                <p>predictions = model.predict(features)</p>
              </div>
            </div>
          ) : (
            /* Real Models Grid */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {models.map(model => (
                <ModelCard key={model.model_id} model={model} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default withAuth(Dashboard);
