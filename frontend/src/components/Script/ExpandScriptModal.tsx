import React, { useState } from 'react';
import { Wand2, X, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { userService } from '../../services/userService';
import toast from 'react-hot-toast';

interface ExpandScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
  content: string;
  onExpansionAccepted: (expandedContent: string) => void;
  artifactId?: string;
  scriptId?: string;
}

interface ExpansionResult {
  expanded_content: string;
  original_length: number;
  expanded_length: number;
  expansion_ratio: number;
  saved: boolean;
  message: string;
}

const ExpandScriptModal: React.FC<ExpandScriptModalProps> = ({
  isOpen,
  onClose,
  content,
  onExpansionAccepted,
  artifactId,
  scriptId,
}) => {
  const [expansionPrompt, setExpansionPrompt] = useState('');
  const [targetIncrease, setTargetIncrease] = useState(1.5);
  const [focusAreas, setFocusAreas] = useState<string[]>([]);
  const [isExpanding, setIsExpanding] = useState(false);
  const [expansionResult, setExpansionResult] = useState<ExpansionResult | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const focusOptions = [
    { id: 'dialogue', label: 'Dialogue & Conversations' },
    { id: 'action', label: 'Action & Movement' },
    { id: 'description', label: 'Visual Descriptions' },
    { id: 'emotion', label: 'Emotional Depth' },
    { id: 'worldbuilding', label: 'World Building' },
  ];

  const toggleFocusArea = (area: string) => {
    setFocusAreas(prev =>
      prev.includes(area)
        ? prev.filter(a => a !== area)
        : [...prev, area]
    );
  };

  const handleExpand = async () => {
    if (!content) return;

    setIsExpanding(true);
    try {
      const response = await userService.expandScript({
        content,
        expansion_prompt: expansionPrompt || undefined,
        target_length_increase: targetIncrease,
        focus_areas: focusAreas.length > 0 ? focusAreas : undefined,
        artifact_id: artifactId,
        script_id: scriptId,
      });

      setExpansionResult(response);
      toast.success('Content expanded successfully!');
    } catch (error) {
      console.error('Error expanding script:', error);
      toast.error('Failed to expand content. Please try again.');
    } finally {
      setIsExpanding(false);
    }
  };

  const handleAccept = () => {
    if (expansionResult) {
      onExpansionAccepted(expansionResult.expanded_content);
      onClose();
    }
  };

  const handleRegenerate = () => {
    setExpansionResult(null);
    handleExpand();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Wand2 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Expand Story Content
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Use AI to enrich and expand your script content
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!expansionResult ? (
            <>
              {/* Expansion Prompt */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Expansion Guidance (Optional)
                </label>
                <textarea
                  value={expansionPrompt}
                  onChange={(e) => setExpansionPrompt(e.target.value)}
                  placeholder="E.g., 'Add more tension to the confrontation scene' or 'Expand the character's backstory'"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                           focus:ring-2 focus:ring-purple-500 focus:border-transparent
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           placeholder-gray-400 dark:placeholder-gray-500 resize-none"
                  rows={3}
                />
              </div>

              {/* Focus Areas */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Focus Areas
                </label>
                <div className="flex flex-wrap gap-2">
                  {focusOptions.map(option => (
                    <button
                      key={option.id}
                      onClick={() => toggleFocusArea(option.id)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors
                        ${focusAreas.includes(option.id)
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Advanced Options */}
              <div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                >
                  {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  Advanced Options
                </button>
                
                {showAdvanced && (
                  <div className="mt-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Target Length Increase: {Math.round((targetIncrease - 1) * 100)}%
                    </label>
                    <input
                      type="range"
                      min="1.2"
                      max="3"
                      step="0.1"
                      value={targetIncrease}
                      onChange={(e) => setTargetIncrease(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>20%</span>
                      <span>100%</span>
                      <span>200%</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Original Content Preview */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Original Content Preview
                </label>
                <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg max-h-40 overflow-y-auto">
                  <pre className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                    {content.slice(0, 500)}{content.length > 500 && '...'}
                  </pre>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {content.length.toLocaleString()} characters
                </p>
              </div>
            </>
          ) : (
            <>
              {/* Expansion Result */}
              <div className="space-y-4">
                {/* Stats */}
                <div className="flex gap-4">
                  <div className="flex-1 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <p className="text-xs text-green-600 dark:text-green-400 font-medium">Original</p>
                    <p className="text-lg font-bold text-green-700 dark:text-green-300">
                      {expansionResult.original_length.toLocaleString()}
                    </p>
                    <p className="text-xs text-green-600 dark:text-green-400">characters</p>
                  </div>
                  <div className="flex-1 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">Expanded</p>
                    <p className="text-lg font-bold text-purple-700 dark:text-purple-300">
                      {expansionResult.expanded_length.toLocaleString()}
                    </p>
                    <p className="text-xs text-purple-600 dark:text-purple-400">characters</p>
                  </div>
                  <div className="flex-1 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">Increase</p>
                    <p className="text-lg font-bold text-blue-700 dark:text-blue-300">
                      {Math.round((expansionResult.expansion_ratio - 1) * 100)}%
                    </p>
                    <p className="text-xs text-blue-600 dark:text-blue-400">growth</p>
                  </div>
                </div>

                {/* Expanded Content Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Expanded Content
                  </label>
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg max-h-96 overflow-y-auto">
                    <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                      {expansionResult.expanded_content}
                    </pre>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
          {!expansionResult ? (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 
                         dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExpand}
                disabled={isExpanding || !content}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg
                         transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center gap-2"
              >
                {isExpanding ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Expanding...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4" />
                    Expand Content
                  </>
                )}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setExpansionResult(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 
                         dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleRegenerate}
                disabled={isExpanding}
                className="px-4 py-2 border border-purple-600 text-purple-600 dark:text-purple-400
                         hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors
                         disabled:opacity-50"
              >
                Regenerate
              </button>
              <button
                onClick={handleAccept}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg
                         transition-colors flex items-center gap-2"
              >
                Accept & Apply
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExpandScriptModal;
