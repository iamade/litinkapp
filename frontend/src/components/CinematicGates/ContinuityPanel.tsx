import React, { useCallback, useEffect, useState } from 'react';
import { cinematicGatesApi } from '../../services/cinematicGatesApi';
import type {
  ContinuityReference,
  ContinuityReferenceType,
} from '../../types/cinematicGates';

interface ContinuityPanelProps {
  videoGenerationId: string;
  className?: string;
}

const REF_TYPE_LABELS: Record<ContinuityReferenceType, string> = {
  character: 'Character',
  world: 'World',
  prop: 'Prop',
  location: 'Location',
};

const REF_TYPE_ICONS: Record<ContinuityReferenceType, string> = {
  character: '👤',
  world: '🌍',
  prop: '📦',
  location: '📍',
};

/** Traffic-light indicator for adjacent-shot QA values. */
const QaIndicator: React.FC<{ value: unknown }> = ({ value }) => {
  // The backend stores QA as a Record<string, unknown>; we try to find
  // a pass/warn/fail-like signal from common keys.
  let level: 'pass' | 'warn' | 'fail' | 'unknown' = 'unknown';

  if (typeof value === 'string') {
    const v = value.toLowerCase();
    if (['pass', 'passed', 'ok', 'true', 'verified'].includes(v)) level = 'pass';
    else if (['warn', 'warning', 'review'].includes(v)) level = 'warn';
    else if (['fail', 'failed', 'error', 'false', 'mismatch'].includes(v)) level = 'fail';
  } else if (typeof value === 'boolean') {
    level = value ? 'pass' : 'fail';
  } else if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const status = String(obj.status ?? obj.result ?? obj.passed ?? '').toLowerCase();
    if (['pass', 'passed', 'ok', 'true', 'verified'].includes(status)) level = 'pass';
    else if (['warn', 'warning', 'review'].includes(status)) level = 'warn';
    else if (['fail', 'failed', 'error', 'false', 'mismatch'].includes(status)) level = 'fail';
  }

  const colors: Record<string, string> = {
    pass: 'bg-green-100 text-green-700',
    warn: 'bg-yellow-100 text-yellow-700',
    fail: 'bg-red-100 text-red-700',
    unknown: 'bg-gray-100 text-gray-500',
  };
  const icons: Record<string, string> = {
    pass: '✅',
    warn: '⚠️',
    fail: '❌',
    unknown: '❓',
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[level]}`}>
      {icons[level]} {level}
    </span>
  );
};

export const ContinuityPanel: React.FC<ContinuityPanelProps> = ({
  videoGenerationId,
  className = '',
}) => {
  const [references, setReferences] = useState<ContinuityReference[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningQA, setRunningQA] = useState(false);
  const [consistency, setConsistency] = useState<{ consistent: boolean; inconsistencies: string[] } | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [refs, cons] = await Promise.all([
        cinematicGatesApi.getContinuityReferences(videoGenerationId),
        cinematicGatesApi.validateTrackConsistency(videoGenerationId).catch(() => null),
      ]);
      setReferences(refs);
      if (cons) setConsistency(cons);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load continuity data');
    } finally {
      setLoading(false);
    }
  }, [videoGenerationId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleRunQA = useCallback(async () => {
    setRunningQA(true);
    setError(null);
    try {
      await cinematicGatesApi.runAdjacentShotQA(videoGenerationId);
      await fetchAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Adjacent-shot QA failed');
    } finally {
      setRunningQA(false);
    }
  }, [videoGenerationId, fetchAll]);

  // Group references by type
  const grouped = references.reduce<Record<string, ContinuityReference[]>>((acc, ref) => {
    (acc[ref.reference_type] ??= []).push(ref);
    return acc;
  }, {});

  const refTypes = Object.keys(grouped) as ContinuityReferenceType[];

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Continuity & Track Consistency</h3>
        <button
          type="button"
          onClick={handleRunQA}
          disabled={runningQA || loading}
          className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {runningQA ? 'Running QA…' : 'Run Adjacent-Shot QA'}
        </button>
      </div>

      {loading && references.length === 0 && <p className="text-sm text-gray-500">Loading…</p>}
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Track consistency summary */}
      {consistency && (
        <div
          className={`mb-4 p-3 rounded-lg border text-sm ${
            consistency.consistent
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-yellow-50 border-yellow-200 text-yellow-800'
          }`}
        >
          <div className="font-medium mb-1">
            {consistency.consistent ? '✅ Track consistency verified' : '⚠️ Track consistency issues'}
          </div>
          {consistency.inconsistencies.length > 0 && (
            <ul className="list-disc list-inside text-xs mt-1 space-y-0.5">
              {consistency.inconsistencies.map((msg, i) => (
                <li key={i}>{msg}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* References grouped by type */}
      {refTypes.length === 0 && !loading && (
        <p className="text-sm text-gray-400">No continuity references created yet.</p>
      )}

      {refTypes.map(refType => (
        <div key={refType} className="mb-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
            <span>{REF_TYPE_ICONS[refType]}</span>
            {REF_TYPE_LABELS[refType]} ({grouped[refType].length})
          </h4>
          <div className="space-y-2">
            {grouped[refType].map(ref => (
              <div key={ref.id} className="border border-gray-200 rounded p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-800">
                    {ref.reference_data?.name ?? ref.reference_data?.title ?? ref.reference_id}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{ref.reference_id}</span>
                </div>

                {/* Shot IDs */}
                {ref.shot_ids.length > 0 && (
                  <div className="mb-2">
                    <span className="text-xs text-gray-500">Shots: </span>
                    {ref.shot_ids.map(shotId => (
                      <span
                        key={shotId}
                        className="inline-block mr-1 mb-1 px-1.5 py-0.5 text-xs font-mono bg-gray-100 text-gray-600 rounded"
                      >
                        {shotId}
                      </span>
                    ))}
                  </div>
                )}

                {/* Adjacent-shot QA */}
                {Object.keys(ref.adjacent_shot_qa).length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs font-medium text-gray-500">Adjacent-Shot QA:</span>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {Object.entries(ref.adjacent_shot_qa).map(([key, value]) => (
                        <div key={key} className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">{key}:</span>
                          <QaIndicator value={value} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ContinuityPanel;