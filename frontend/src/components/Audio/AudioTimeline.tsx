import React, { useRef, useState, useEffect } from 'react';
import { ZoomIn, ZoomOut } from 'lucide-react';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';

interface AudioTimelineProps {
  files: any[];
  duration: number;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onAudioSelect: (audioId: string) => void;
}

const AudioTimeline: React.FC<AudioTimelineProps> = ({
  files,
  duration,
  currentTime,
  onTimeUpdate,
  onAudioSelect
}) => {
  const {
    selectedScriptId,
    selectedChapterId,
    selectedSegmentId,
    versionToken,
    isSwitching,
    selectSegment,
    subscribe,
  } = useScriptSelection();

  const [zoom, setZoom] = useState(1);
  const timelineRef = useRef<HTMLDivElement>(null);

  // React to selection and version changes
  useEffect(() => {
    // Recompute markers and layout when script/chapter changes
    // This effect will trigger re-renders when selection changes
  }, [selectedScriptId, selectedChapterId, versionToken]);

  // Center active segment on change
  useEffect(() => {
    if (selectedSegmentId) {
      // TODO: Implement scroll to active segment
      // This would require having segment data to compute position
    }
  }, [selectedSegmentId]);

  // Subscribe to timeline recalculation requests
  useEffect(() => {
    const unsub = subscribe((evt) => {
      if (evt === 'TIMELINE_RECALC_REQUESTED') {
        // Force re-render to recompute layout
        // This is handled by the existing state and props
      }
    });
    return unsub;
  }, [subscribe]);

  // On marker click handler - use for segment selection
  const onMarkerClick = (id: string) => {
    if (timelineDisabled) return;
    selectSegment(id, { reason: 'user' });
  };

  // Disable interactions during switching
  const timelineDisabled = isSwitching;

  // Render empty state when no script is selected
  if (!selectedScriptId) {
    return (
      <div className="bg-white border rounded-lg p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Audio Timeline</h4>
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg font-medium">No script selected</p>
          <p className="text-sm">Select a script to view the audio timeline</p>
        </div>
      </div>
    );
  }

  const tracks = [
    { name: 'Narration', color: 'bg-gradient-to-r from-emerald-500 to-green-500', files: files?.filter(f => f.type === 'narration') || [] },
    { name: 'Dialogue', color: 'bg-gradient-to-r from-blue-500 to-cyan-500', files: files?.filter(f => f.type === 'dialogue') || [] },
    { name: 'Music', color: 'bg-gradient-to-r from-purple-500 to-pink-500', files: files?.filter(f => f.type === 'music') || [] },
    { name: 'Effects', color: 'bg-gradient-to-r from-orange-500 to-red-500', files: files?.filter(f => f.type === 'effects') || [] },
    { name: 'Ambiance', color: 'bg-gradient-to-r from-teal-500 to-cyan-600', files: files?.filter(f => f.type === 'ambiance') || [] }
  ];

  const handleTimelineClick = (e: React.MouseEvent) => {
    if (!timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    const newTime = percentage * duration;
    
    onTimeUpdate(newTime);
  };

  return (
    <div className="bg-white/20 backdrop-blur-md border border-white/20 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Audio Timeline</h4>
        
        <div className="flex items-center space-x-2 bg-white/40 dark:bg-black/20 rounded-lg p-1">
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
            className="p-1.5 text-gray-700 dark:text-gray-300 hover:bg-white/60 dark:hover:bg-white/10 rounded-md transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
            className="p-1.5 text-gray-700 dark:text-gray-300 hover:bg-white/60 dark:hover:bg-white/10 rounded-md transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Time ruler */}
      <div className="mb-4 ml-24 relative h-6">
        <div className="absolute inset-0">
          {[...Array(Math.ceil(duration / 10))].map((_, i) => (
            <div
              key={i}
              className="absolute top-0 h-full border-l border-gray-400/30"
              style={{ left: `${(i * 10 / duration) * 100}%` }}
            >
              <span className="text-[10px] font-medium text-gray-500 absolute -top-4 -translate-x-1/2">
                {i * 10}s
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline tracks */}
      <div 
        ref={timelineRef}
        className="space-y-3 relative overflow-visible"
        onClick={handleTimelineClick}
        style={{ width: `${zoom * 100}%` }}
      >
        {tracks.map((track) => (
          <div key={track.name} className="relative group">
            <div className="absolute left-0 -ml-0 w-20 flex items-center h-10">
              <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider text-right w-full pr-4">{track.name}</span>
            </div>
            
            <div className="h-10 bg-black/5 rounded-lg relative ml-24 border border-black/5 overflow-hidden backdrop-blur-sm transition-colors group-hover:bg-black/10">
              {track.files.map((file: any) => (
                <div
                  key={file.id}
                  className={`absolute h-8 top-1 ${track.color} rounded-md shadow-sm cursor-pointer hover:brightness-110 active:scale-[0.99] transition-all duration-200 border border-white/20 group`}
                  style={{
                    left: `${(file.startTime / duration) * 100}%`,
                    width: `${Math.max(1, ((file.endTime - file.startTime) / duration) * 100)}%`, // Ensure visibility even if short
                    minWidth: '4px'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onAudioSelect(file.id);
                  }}
                  title={`${file.name || 'Untitled'} (${file.duration}s)`}
                >
                  <div className="w-full h-full relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent" />
                    <span className="absolute inset-0 flex items-center px-2 text-[10px] font-bold text-white shadow-sm truncate opacity-90 group-hover:opacity-100">
                      {file.name}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Playhead */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 pointer-events-none z-20 ml-24"
          style={{ left: `${(currentTime / duration) * 100}%` }}
        >
          <div className="absolute -top-3 -left-1.5 w-3 h-3 bg-red-500 rounded-full shadow-md border-2 border-white" />
        </div>
      </div>
    </div>
  );
};

export default AudioTimeline;
