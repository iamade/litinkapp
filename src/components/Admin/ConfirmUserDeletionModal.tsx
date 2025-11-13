import React, { useState } from 'react';
import { AlertTriangle, X, Trash2, CheckCircle, XCircle } from 'lucide-react';

interface ContentCounts {
  books: number;
  chapters: number;
  characters: number;
  scripts: number;
  plot_overviews: number;
  image_generations: number;
  audio_generations: number;
  video_generations: number;
  subscriptions: number;
  usage_logs: number;
}

interface DeletionPreview {
  user_id: string;
  email: string;
  display_name: string;
  roles: string[];
  created_at: string;
  email_verified: boolean;
  content_counts: ContentCounts;
  can_delete: boolean;
  warnings: string[];
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason?: string) => Promise<void>;
  deletionPreview: DeletionPreview | null;
  isBatchDelete: boolean;
  batchCount: number;
}

export default function ConfirmUserDeletionModal({
  isOpen,
  onClose,
  onConfirm,
  deletionPreview,
  isBatchDelete,
  batchCount
}: Props) {
  const [step, setStep] = useState(1);
  const [confirmText, setConfirmText] = useState('');
  const [reason, setReason] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsDeleting(true);
    try {
      await onConfirm(reason || undefined);
      handleClose();
    } catch (error) {
      console.error('Deletion error:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    setStep(1);
    setConfirmText('');
    setReason('');
    setAgreed(false);
    setIsDeleting(false);
    onClose();
  };

  const getTotalContentCount = () => {
    if (!deletionPreview) return 0;
    const counts = deletionPreview.content_counts;
    return (
      counts.books +
      counts.chapters +
      counts.characters +
      counts.scripts +
      counts.plot_overviews +
      counts.image_generations +
      counts.audio_generations +
      counts.video_generations
    );
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return true;
      case 2:
        return true;
      case 3:
        if (isBatchDelete) {
          return true;
        }
        return confirmText.toLowerCase() === deletionPreview?.email.toLowerCase();
      case 4:
        return agreed;
      default:
        return false;
    }
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
              <div>
                <h4 className="font-semibold text-red-900">
                  Warning: Permanent Deletion
                </h4>
                <p className="text-sm text-red-700 mt-1">
                  This action cannot be undone. All user data will be permanently removed.
                </p>
              </div>
            </div>

            {isBatchDelete ? (
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">
                  Batch Delete: {batchCount} Users
                </h4>
                <p className="text-gray-600">
                  You are about to delete {batchCount} users and all their associated content.
                  Each user's data will be archived before deletion for compliance purposes.
                </p>
              </div>
            ) : deletionPreview && (
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">User Information</h4>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Email:</span>
                    <span className="font-medium">{deletionPreview.email}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Display Name:</span>
                    <span className="font-medium">
                      {deletionPreview.display_name || 'Not set'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Roles:</span>
                    <span className="font-medium">
                      {deletionPreview.roles.join(', ')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`font-medium ${
                      deletionPreview.email_verified ? 'text-green-600' : 'text-orange-600'
                    }`}>
                      {deletionPreview.email_verified ? 'Verified' : 'Unverified'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Created:</span>
                    <span className="font-medium">
                      {new Date(deletionPreview.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {deletionPreview.warnings.length > 0 && (
                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm font-medium text-yellow-900 mb-2">Warnings:</p>
                    <ul className="list-disc list-inside text-sm text-yellow-800">
                      {deletionPreview.warnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <h4 className="font-semibold text-gray-900">Content to be Deleted</h4>

            {isBatchDelete ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                  Deleting {batchCount} users will also delete all their associated content.
                  A detailed breakdown will be shown for each user during the deletion process.
                </p>
              </div>
            ) : deletionPreview && (
              <>
                <p className="text-sm text-gray-600">
                  The following content will be permanently deleted:
                </p>

                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(deletionPreview.content_counts).map(([key, count]) => (
                    <div
                      key={key}
                      className="flex justify-between items-center p-3 bg-gray-50 rounded-lg"
                    >
                      <span className="text-sm text-gray-700 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className={`font-semibold ${
                        count > 0 ? 'text-red-600' : 'text-gray-400'
                      }`}>
                        {count}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-medium text-blue-900">
                    Total items to delete: {getTotalContentCount()}
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    All data will be archived in the audit log before deletion
                  </p>
                </div>
              </>
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <h4 className="font-semibold text-gray-900">Confirm Deletion</h4>

            {isBatchDelete ? (
              <div>
                <p className="text-sm text-gray-600 mb-4">
                  This will delete {batchCount} users and all their content. This action is irreversible.
                </p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reason for deletion (optional)
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g., Test accounts cleanup, spam users, etc."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                  />
                </div>
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-600 mb-4">
                  To confirm, please type the user's email address:{' '}
                  <span className="font-semibold text-gray-900">
                    {deletionPreview?.email}
                  </span>
                </p>
                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Enter email address to confirm"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent mb-4"
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reason for deletion (optional)
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g., User requested deletion, policy violation, etc."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                  />
                </div>
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <h4 className="font-semibold text-gray-900">Final Confirmation</h4>

            <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-red-900 mb-2">
                    This is your last chance to cancel
                  </p>
                  <p className="text-sm text-red-800">
                    {isBatchDelete
                      ? `${batchCount} users and all their content will be permanently deleted. This cannot be undone.`
                      : `${deletionPreview?.email} and all their content will be permanently deleted. This cannot be undone.`}
                  </p>
                </div>
              </div>
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-1 rounded border-gray-300 text-red-600 focus:ring-red-500"
              />
              <span className="text-sm text-gray-700">
                I understand this action is permanent and cannot be undone. All user data and
                content will be deleted from both the profiles table and authentication system.
              </span>
            </label>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Trash2 className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">
                {isBatchDelete ? 'Batch Delete Users' : 'Delete User'}
              </h3>
              <p className="text-sm text-gray-500">
                Step {step} of 4
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isDeleting}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Progress */}
        <div className="px-6 pt-4">
          <div className="flex gap-2">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`flex-1 h-2 rounded-full transition-colors ${
                  s <= step ? 'bg-red-600' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderStep()}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={() => {
              if (step === 1) {
                handleClose();
              } else {
                setStep(step - 1);
              }
            }}
            disabled={isDeleting}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors disabled:opacity-50"
          >
            {step === 1 ? 'Cancel' : 'Back'}
          </button>

          {step < 4 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canProceed() || isDeleting}
              className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleConfirm}
              disabled={!canProceed() || isDeleting}
              className="flex items-center gap-2 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDeleting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  Delete Permanently
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
