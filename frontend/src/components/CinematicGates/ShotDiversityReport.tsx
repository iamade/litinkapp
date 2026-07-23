import React, { useCallback, useEffect, useState } from 'react';
import { cinematicGatesApi } from '../../services/cinematicGatesApi';
import type { ShotDiversityReport as ShotDiversityReportType } from '../../types/cinematicGates';

interface ShotDiversityReportProps {
  videoGenerationId: string;
  className?: string;
}

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  analyzing: 'bg-blue-100 text-blue-700 animate-pulse',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

export const ShotDiversityReport: React.FC<ShotDiversityReportProps> = ({
  videoGenerationId,
  className = '',
}) => {
  const [report, setReport] = useState<ShotDiversityReportType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  // Motif marking state
  const [motifShotId, setMotifShotId] = useState<string | null>(null);
  const [motifReason, setMotifReason] = useState('');
  const [markingMotif, setMarkingMotif] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await cinematicGatesApi.getShotDiversityReport(videoGenerationId);
      setReport(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load shot diversity report');
    } finally {
      setLoading(false);
    }
  }, [videoGenerationId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await cinematicGatesApi.analyzeShotDiversity(videoGenerationId);
      setReport(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, [videoGenerationId]);

  const handleMarkMotif = useCallback(async () => {
    if (!report || !motifShotId || !motifReason.trim()) return;
    setMarkingMotif(true);
    setError(null);
    try {
      const updatedEntry = await cinematicGatesApi.markIntentionalMotif(
        report.id,
        motifShotId,
        motifReason.trim()
      );
      setReport(prev =>
        prev
          ? {
              ...prev,
              report_data: prev.report_data.map(e =>
                e.shot_id === updatedEntry.shot_id ? updatedEntry : e
              ),
              intentional_motif_count:
                prev.intentional_motif_count + (updatedEntry.is_intentional_motif ? 1 : 0),
            }
          : prev
      );
      setMotifShotId(null);
      setMotifReason('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to mark motif');
    } finally {
      setMarkingMotif(false);
    }
  }, [report, motifShotId, motifReason]);

  const summary = report
    ? [
        { label: 'Total', value: report.total_shots, color: 'text-gray-800' },
        { label: 'Duplicates', value: report.duplicate_count, color: 'text-red-600' },
        { label: 'Near Duplicates', value: report.near_duplicate_count, color: 'text-orange-600' },
        { label: 'Unique', value: report.unique_count, color: 'text-green-600' },
        { label: 'Motifs', value: report.intentional_motif_count, color: 'text-purple-600' },
      ]
    : [];

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Shot Diversity Report</h3>
        <div className="flex items-center gap-3">
          {report && (
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[report.status] ?? ''}`}>
              {report.status}
            </span>
          )}
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={analyzing || loading}
            className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {analyzing ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
      </div>

      {loading && !report && <p className="text-sm text-gray-500">Loading report…</p>}
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {report && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-5 gap-3 mb-6">
            {summary.map(stat => (
              <div key={stat.label} className="text-center">
                <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Per-shot table */}
          {report.report_data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-3">Shot ID</th>
                    <th className="py-2 pr-3">Hash</th>
                    <th className="py-2 pr-3">Duplicates</th>
                    <th className="py-2 pr-3">Near Duplicates</th>
                    <th className="py-2 pr-3">Motif</th>
                    <th className="py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {report.report_data.map(entry => {
                    const isDup = entry.duplicates.length > 0;
                    const isNearDup = entry.near_duplicates.length > 0;
                    return (
                      <tr
                        key={entry.shot_id}
                        className={`border-b border-gray-50 ${
                          isDup ? 'bg-red-50' : isNearDup ? 'bg-orange-50' : ''
                        }`}
                      >
                        <td className="py-2 pr-3 font-mono text-xs">{entry.shot_id}</td>
                        <td className="py-2 pr-3 font-mono text-xs text-gray-400">{entry.hash.slice(0, 12)}…</td>
                        <td className="py-2 pr-3">
                          {entry.duplicates.length > 0 ? (
                            <span className="text-red-600 font-medium">{entry.duplicates.length}</span>
                          ) : (
                            <span className="text-gray-300">0</span>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {entry.near_duplicates.length > 0 ? (
                            <span className="text-orange-600 font-medium">{entry.near_duplicates.length}</span>
                          ) : (
                            <span className="text-gray-300">0</span>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {entry.is_intentional_motif ? (
                            <span className="text-purple-600 text-xs" title={entry.motif_reason ?? ''}>
                              🎯 {entry.motif_reason ?? 'intentional'}
                            </span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="py-2">
                          {!entry.is_intentional_motif && (
                            <button
                              type="button"
                              onClick={() => setMotifShotId(entry.shot_id)}
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Mark as motif
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No shot-level data available.</p>
          )}

          {/* Motif marking modal */}
          {motifShotId && (
            <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-[90vw]">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                  Mark Shot as Intentional Motif
                </h4>
                <p className="text-xs text-gray-500 mb-3">Shot: <span className="font-mono">{motifShotId}</span></p>
                <textarea
                  value={motifReason}
                  onChange={e => setMotifReason(e.target.value)}
                  placeholder="Reason (e.g. recurring establishing shot)…"
                  rows={3}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 mb-3"
                  autoFocus
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => { setMotifShotId(null); setMotifReason(''); }}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleMarkMotif}
                    disabled={markingMotif || !motifReason.trim()}
                    className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {markingMotif ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ShotDiversityReport;