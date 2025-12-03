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
    { name: 'Narration', color: 'bg-green-500', files: files?.filter(f => f.type === 'narration') || [] },
    { name: 'Music', color: 'bg-purple-500', files: files?.filter(f => f.type === 'music') || [] },
    { name: 'Effects', color: 'bg-orange-500', files: files?.filter(f => f.type === 'effects') || [] },
    { name: 'Ambiance', color: 'bg-teal-500', files: files?.filter(f => f.type === 'ambiance') || [] }
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
    <div className="bg-white border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-semibold text-gray-900">Audio Timeline</h4>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-600">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Time ruler */}
      <div className="mb-2">
        <div className="h-6 bg-gray-100 rounded relative">
          {[...Array(Math.ceil(duration / 10))].map((_, i) => (
            <div
              key={i}
              className="absolute top-0 h-full border-l border-gray-300"
              style={{ left: `${(i * 10 / duration) * 100}%` }}
            >
              <span className="text-xs text-gray-500 absolute -top-5">
                {i * 10}s
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline tracks */}
      <div 
        ref={timelineRef}
        className="space-y-2 relative"
        onClick={handleTimelineClick}
        style={{ width: `${zoom * 100}%` }}
      >
        {tracks.map((track, trackIndex) => (
          <div key={track.name} className="relative">
            <div className="absolute left-0 -ml-20 mt-3 text-sm font-medium text-gray-700">
              {track.name}
            </div>
            
            <div className="h-12 bg-gray-100 rounded relative ml-24">
              {track.files.map((file: any) => (
                <div
                  key={file.id}
                  className={`absolute h-10 ${track.color} bg-opacity-75 rounded cursor-pointer hover:bg-opacity-100`}
                  style={{
                    left: `${(file.startTime / duration) * 100}%`,
                    width: `${((file.endTime - file.startTime) / duration) * 100}%`,
                    top: '1px'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onAudioSelect(file.id);
                  }}
                >
                  <span className="text-xs text-white px-1 truncate">
                    {file.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Playhead */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 pointer-events-none"
          style={{ left: `${(currentTime / duration) * 100}%` }}
        >
          <div className="absolute -top-2 -left-2 w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-red-500" />
        </div>
      </div>
    </div>
  );
};

export default AudioTimeline;
