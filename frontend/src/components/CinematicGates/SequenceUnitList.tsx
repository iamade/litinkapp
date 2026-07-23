import React, { useCallback, useEffect, useState } from 'react';
import { cinematicGatesApi } from '../../services/cinematicGatesApi';
import type {
  SequenceUnit,
  SequenceUnitType,
  SequenceUnitStatus,
  LineTracking,
  LineTrackingStage,
} from '../../types/cinematicGates';

interface SequenceUnitListProps {
  videoGenerationId: string;
  className?: string;
}

const UNIT_TYPE_LABELS: Record<SequenceUnitType, string> = {
  ident_title: 'Ident / Title',
  prologue: 'Prologue',
  dialogue_act: 'Dialogue Act',
  climax_resolution: 'Climax / Resolution',
  closing_bookend: 'Closing Bookend',
  end_title_credits: 'End Title / Credits',
};

const UNIT_TYPE_ICONS: Record<SequenceUnitType, string> = {
  ident_title: '🏷️',
  prologue: '📖',
  dialogue_act: '🎭',
  climax_resolution: '⚡',
  closing_bookend: '🔖',
  end_title_credits: '🎬',
};

const STATUS_COLORS: Record<SequenceUnitStatus, string> = {
  pending: 'bg-gray-100 text-gray-600',
  active: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  skipped: 'bg-yellow-100 text-yellow-700',
};

const STATUS_ICONS: Record<SequenceUnitStatus, string> = {
  pending: '⏸️',
  active: '▶️',
  completed: '✅',
  skipped: '⏭️',
};

const LINE_STAGE_LABELS: Record<LineTrackingStage, string> = {
  unassigned: 'Unassigned',
  character_assigned: 'Character Assigned',
  voice_assigned: 'Voice Assigned',
  scene_assigned: 'Scene Assigned',
  shot_assigned: 'Shot Assigned',
  audio_generated: 'Audio Generated',
  lipsync_queued: 'Lip Sync Queued',
  lipsync_complete: 'Lip Sync Complete',
  placed: 'Placed',
};

const SequenceUnitCard: React.FC<{
  unit: SequenceUnit;
  lines: LineTracking[];
  onUpdate: (unitId: string, data: Partial<SequenceUnit>) => void;
}> = ({ unit, lines, onUpdate }) => {
  const [expanded, setExpanded] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(unit.title);
  const [editingScript, setEditingScript] = useState(false);
  const [scriptDraft, setScriptDraft] = useState(unit.script_content ?? '');

  const handleTitleBlur = () => {
    setEditingTitle(false);
    if (titleDraft !== unit.title) {
      onUpdate(unit.id, { title: titleDraft });
    }
  };

  const handleScriptBlur = () => {
    setEditingScript(false);
    if (scriptDraft !== (unit.script_content ?? '')) {
      onUpdate(unit.id, { script_content: scriptDraft });
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg mb-2">
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => setExpanded(v => !v)}
          className="text-gray-400 text-xs hover:text-gray-600"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? '▲' : '▼'}
        </button>
        <span className="text-lg">{UNIT_TYPE_ICONS[unit.unit_type]}</span>
        <span className="text-xs font-mono text-gray-400">#{unit.unit_order}</span>

        {editingTitle ? (
          <input
            type="text"
            value={titleDraft}
            onChange={e => setTitleDraft(e.target.value)}
            onBlur={handleTitleBlur}
            onKeyDown={e => { if (e.key === 'Enter') handleTitleBlur(); }}
            className="flex-1 px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
            autoFocus
          />
        ) : (
          <span
            className="flex-1 text-sm font-medium text-gray-800 cursor-text"
            onClick={() => setEditingTitle(true)}
            title="Click to edit title"
          >
            {unit.title || '(untitled)'}
          </span>
        )}

        {unit.duration_seconds != null && (
          <span className="text-xs text-gray-500">{unit.duration_seconds}s</span>
        )}

        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[unit.status]}`}>
          {STATUS_ICONS[unit.status]} {unit.status}
        </span>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">
          {/* Unit type label */}
          <div className="mb-2 text-xs text-gray-500">
            Type: <span className="font-medium text-gray-700">{UNIT_TYPE_LABELS[unit.unit_type]}</span>
          </div>

          {/* Script content */}
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">Script Content</label>
            {editingScript ? (
              <textarea
                value={scriptDraft}
                onChange={e => setScriptDraft(e.target.value)}
                onBlur={handleScriptBlur}
                rows={5}
                className="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                autoFocus
              />
            ) : (
              <pre
                className="w-full p-2 text-sm text-gray-700 bg-gray-50 rounded cursor-text whitespace-pre-wrap min-h-[2.5rem]"
                onClick={() => setEditingScript(true)}
                title="Click to edit"
              >
                {unit.script_content || '(no script content — click to add)'}
              </pre>
            )}
          </div>

          {/* Line tracking */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Line Tracking ({lines.length})
            </label>
            {lines.length === 0 ? (
              <p className="text-xs text-gray-400">No tracked lines for this unit.</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-100">
                    <th className="py-1 pr-2">Line</th>
                    <th className="py-1 pr-2">Character</th>
                    <th className="py-1 pr-2">Stage</th>
                    <th className="py-1">Timeline</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map(line => (
                    <tr key={line.id} className="border-b border-gray-50">
                      <td className="py-1 pr-2 max-w-xs truncate" title={line.line_text}>
                        {line.line_text}
                      </td>
                      <td className="py-1 pr-2">{line.character_name ?? '—'}</td>
                      <td className="py-1 pr-2">
                        <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                          {LINE_STAGE_LABELS[line.status]}
                        </span>
                      </td>
                      <td className="py-1 text-gray-400">
                        {line.timeline_position_ms != null
                          ? `${(line.timeline_position_ms / 1000).toFixed(1)}s`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const SequenceUnitList: React.FC<SequenceUnitListProps> = ({
  videoGenerationId,
  className = '',
}) => {
  const [units, setUnits] = useState<SequenceUnit[]>([]);
  const [lines, setLines] = useState<LineTracking[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [unitsRes, linesRes] = await Promise.all([
        cinematicGatesApi.getSequenceUnits(videoGenerationId),
        cinematicGatesApi.getLineTracking(videoGenerationId),
      ]);
      setUnits(unitsRes);
      setLines(linesRes);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load sequence units');
    } finally {
      setLoading(false);
    }
  }, [videoGenerationId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleUpdate = useCallback(
    async (unitId: string, data: Partial<SequenceUnit>) => {
      try {
        const updated = await cinematicGatesApi.updateSequenceUnit(unitId, data);
        setUnits(prev => prev.map(u => (u.id === unitId ? updated : u)));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to update unit');
      }
    },
    []
  );

  // Sort by unit_order
  const sortedUnits = [...units].sort((a, b) => a.unit_order - b.unit_order);

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Sequence Units</h3>

      {loading && units.length === 0 && <p className="text-sm text-gray-500">Loading…</p>}
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {sortedUnits.length === 0 && !loading && (
        <p className="text-sm text-gray-400">No sequence units created yet.</p>
      )}

      {sortedUnits.map(unit => {
        const unitLines = lines.filter(l => l.sequence_unit_id === unit.id);
        return (
          <SequenceUnitCard
            key={unit.id}
            unit={unit}
            lines={unitLines}
            onUpdate={handleUpdate}
          />
        );
      })}
    </div>
  );
};

export default SequenceUnitList;