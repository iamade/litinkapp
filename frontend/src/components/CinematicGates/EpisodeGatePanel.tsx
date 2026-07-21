import React, { useCallback, useEffect, useState } from 'react';
import { cinematicGatesApi } from '../../services/cinematicGatesApi';
import type { EpisodeGateStatus } from '../../types/cinematicGates';

interface GateItem {
  key: string;
  label: string;
  passed: boolean;
  pending: boolean;
  detail?: React.ReactNode;
}

interface EpisodeGatePanelProps {
  videoGenerationId: string;
  className?: string;
}

const GateIcon: React.FC<{ passed: boolean; pending: boolean }> = ({ passed, pending }) => {
  if (pending) return <span className="text-gray-400 text-lg">⏸️</span>;
  if (passed) return <span className="text-green-500 text-lg">✅</span>;
  return <span className="text-red-500 text-lg">❌</span>;
};

const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}> = ({ title, icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg mb-2">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-gray-800">
          {icon}
          {title}
        </span>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-4 pb-3 text-sm text-gray-600">{children}</div>}
    </div>
  );
};

export const EpisodeGatePanel: React.FC<EpisodeGatePanelProps> = ({
  videoGenerationId,
  className = '',
}) => {
  const [status, setStatus] = useState<EpisodeGateStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningAnalysis, setRunningAnalysis] = useState(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await cinematicGatesApi.getEpisodeGateStatus(videoGenerationId);
      setStatus(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load gate status');
    } finally {
      setLoading(false);
    }
  }, [videoGenerationId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleRunAnalysis = useCallback(async () => {
    setRunningAnalysis(true);
    setError(null);
    try {
      await cinematicGatesApi.analyzeShotDiversity(videoGenerationId);
      await cinematicGatesApi.runAdjacentShotQA(videoGenerationId);
      await fetchStatus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setRunningAnalysis(false);
    }
  }, [videoGenerationId, fetchStatus]);

  const gates: GateItem[] = status
    ? [
        {
          key: 'sequence_units',
          label: 'Sequence Units Valid',
          passed: status.sequence_units_valid,
          pending: false,
          detail:
            status.missing_units.length > 0
              ? `Missing: ${status.missing_units.join(', ')}`
              : 'All required sequence units present.',
        },
        {
          key: 'line_tracking',
          label: 'Line Tracking Complete',
          passed: status.line_tracking_complete,
          pending: false,
          detail:
            status.untracked_lines > 0
              ? `${status.untracked_lines} untracked line(s).`
              : 'All lines tracked.',
        },
        {
          key: 'shot_diversity',
          label: 'Shot Diversity Analyzed',
          passed: status.shot_diversity_status === 'completed',
          pending: status.shot_diversity_status === 'pending' || status.shot_diversity_status === 'analyzing',
          detail: status.shot_diversity_summary
            ? `Total: ${status.shot_diversity_summary.total} | Dup: ${status.shot_diversity_summary.duplicates} | Near: ${status.shot_diversity_summary.near_duplicates} | Unique: ${status.shot_diversity_summary.unique} | Motifs: ${status.shot_diversity_summary.motifs}`
            : `Status: ${status.shot_diversity_status}`,
        },
        {
          key: 'continuity',
          label: 'Continuity Verified',
          passed: status.continuity_verified,
          pending: false,
          detail: status.continuity_verified ? 'Continuity checks passed.' : 'Continuity issues detected.',
        },
        {
          key: 'track_consistency',
          label: 'Track Consistency',
          passed: status.track_consistency.consistent,
          pending: false,
          detail:
            status.track_consistency.inconsistencies.length > 0
              ? `Issues: ${status.track_consistency.inconsistencies.join('; ')}`
              : 'All tracks consistent.',
        },
      ]
    : [];

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Episode Gate Status</h3>
        <div className="flex items-center gap-3">
          {status?.all_gates_passed && (
            <span className="text-sm font-medium text-green-600">All gates passed 🎉</span>
          )}
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={runningAnalysis || loading}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {runningAnalysis ? 'Analyzing…' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {loading && !status && <p className="text-sm text-gray-500">Loading gate status…</p>}
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {status && (
        <>
          {/* Overall banner */}
          <div
            className={`mb-4 p-3 rounded-lg border text-sm font-medium ${
              status.all_gates_passed
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-yellow-50 border-yellow-200 text-yellow-800'
            }`}
          >
            {status.all_gates_passed
              ? 'All episode gates have passed. Ready for final render.'
              : 'Some gates have not passed yet. Resolve issues below.'}
          </div>

          {/* Gate checklist */}
          <div>
            {gates.map(gate => (
              <CollapsibleSection
                key={gate.key}
                title={gate.label}
                icon={<GateIcon passed={gate.passed} pending={gate.pending} />}
              >
                {gate.detail}
              </CollapsibleSection>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default EpisodeGatePanel;