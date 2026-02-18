import React from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface AudioGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  sceneCount: number;
}

export const AudioGenerationModal: React.FC<AudioGenerationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  sceneCount
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-yellow-500" />
            <h2 className="text-xl font-bold text-gray-900">Confirm Audio Generation</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-700 text-center">
            {sceneCount === 1 
              ? "Generate audio for this scene? This may take a moment."
              : `Generate audio for all ${sceneCount} scenes? This may take several minutes.`}
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
};