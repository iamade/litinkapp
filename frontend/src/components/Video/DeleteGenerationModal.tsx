import { X, Trash2, AlertTriangle } from 'lucide-react';

interface DeleteGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export default function DeleteGenerationModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting = false,
}: DeleteGenerationModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full border border-gray-700">
        {/* Header */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              Delete Generation?
            </h2>
            <button
              onClick={onClose}
              disabled={isDeleting}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <p className="text-red-200 text-sm">
              This action cannot be undone. This video generation will be permanently removed.
            </p>
          </div>

          <p className="text-gray-300 text-sm">
            Are you sure you want to delete this failed generation? This will free up storage space and remove it from your history.
          </p>
        </div>

        {/* Actions */}
        <div className="p-6 border-t border-gray-700 flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Generation'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
