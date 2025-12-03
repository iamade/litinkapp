import React, { useState } from 'react';
import { useAuth, hasRole } from '../../contexts/AuthContext';
import { UserCircle, Sparkles, Compass, Plus, Trash2, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import UpgradeToCreatorModal from './UpgradeToCreatorModal';
import CreatorOnboardingModal from './CreatorOnboardingModal';

interface RoleManagementProps {
  onRoleAdded?: (role: 'creator' | 'explorer') => void;
}

export default function RoleManagement({ onRoleAdded }: RoleManagementProps) {
  const { user, addRole, removeRole } = useAuth();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState<'creator' | 'explorer' | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!user) return null;

  const hasCreatorRole = hasRole(user, 'creator');
  const hasExplorerRole = hasRole(user, 'explorer');

  const handleAddCreatorRole = () => {
    setShowUpgradeModal(true);
  };

  const handleConfirmUpgrade = async () => {
    setIsLoading(true);
    try {
      await addRole('creator');
      toast.success('Creator role added successfully!');
      setShowUpgradeModal(false);
      setShowOnboarding(true);
      onRoleAdded?.('creator');
    } catch (error) {
      toast.error('Failed to add creator role. Please try again.');
      console.error('Error adding creator role:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddExplorerRole = async () => {
    setIsLoading(true);
    try {
      await addRole('explorer');
      toast.success('Explorer role added successfully!');
      onRoleAdded?.('explorer');
    } catch (error) {
      toast.error('Failed to add explorer role. Please try again.');
      console.error('Error adding explorer role:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveRole = async (role: 'creator' | 'explorer') => {
    setIsLoading(true);
    try {
      await removeRole(role);
      toast.success(`${role === 'creator' ? 'Creator' : 'Explorer'} role removed successfully!`);
      setShowRemoveConfirm(null);
    } catch (error: any) {
      const errorMessage = error?.message || 'Failed to remove role. Please try again.';
      toast.error(errorMessage);
      console.error('Error removing role:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
          <UserCircle className="h-6 w-6 text-blue-600 mr-2" />
          Role Management
        </h2>

        <div className="space-y-4">
          {/* Explorer Role */}
          <div className={`p-4 rounded-xl border-2 transition-all ${
            hasExplorerRole
              ? 'border-green-300 bg-green-50'
              : 'border-gray-200 bg-gray-50'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  hasExplorerRole ? 'bg-green-100' : 'bg-gray-200'
                }`}>
                  <Compass className={`h-6 w-6 ${hasExplorerRole ? 'text-green-600' : 'text-gray-500'}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 flex items-center">
                    Explorer Mode
                    {hasExplorerRole && (
                      <span className="ml-2 px-2 py-0.5 bg-green-500 text-white text-xs rounded-full">
                        Active
                      </span>
                    )}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Discover and interact with curated content
                  </p>
                </div>
              </div>
              <div>
                {hasExplorerRole ? (
                  <button
                    onClick={() => setShowRemoveConfirm('explorer')}
                    disabled={isLoading}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Remove explorer role"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                ) : (
                  <button
                    onClick={handleAddExplorerRole}
                    disabled={isLoading}
                    className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Role</span>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Creator Role */}
          <div className={`p-4 rounded-xl border-2 transition-all ${
            hasCreatorRole
              ? 'border-blue-300 bg-blue-50'
              : 'border-gray-200 bg-gray-50'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  hasCreatorRole ? 'bg-blue-100' : 'bg-gray-200'
                }`}>
                  <Sparkles className={`h-6 w-6 ${hasCreatorRole ? 'text-blue-600' : 'text-gray-500'}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 flex items-center">
                    Creator Mode
                    {hasCreatorRole && (
                      <span className="ml-2 px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full">
                        Active
                      </span>
                    )}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Create books, scripts, and videos with AI
                  </p>
                </div>
              </div>
              <div>
                {hasCreatorRole ? (
                  <button
                    onClick={() => setShowRemoveConfirm('creator')}
                    disabled={isLoading}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Remove creator role"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                ) : (
                  <button
                    onClick={handleAddCreatorRole}
                    disabled={isLoading}
                    className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all transform hover:scale-105 disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Upgrade</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">Role Information</p>
              <p>
                You can have both roles simultaneously. Switch between Explorer and Creator modes
                using the toggle in the navigation bar. You must keep at least one role active.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Role Removal */}
      {showRemoveConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">
              Remove {showRemoveConfirm === 'creator' ? 'Creator' : 'Explorer'} Role?
            </h3>
            <p className="text-gray-600 mb-6">
              {showRemoveConfirm === 'creator'
                ? 'You will lose access to all creator features including AI content generation, the Author Panel, and creator tools.'
                : 'You will lose access to explorer features including curated content discovery and learning materials.'}
            </p>
            <p className="text-sm text-amber-600 mb-6 font-medium">
              Note: You must keep at least one role. This action can be reversed by adding the role again.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowRemoveConfirm(null)}
                disabled={isLoading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRemoveRole(showRemoveConfirm)}
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Removing...' : 'Remove Role'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upgrade to Creator Modal */}
      <UpgradeToCreatorModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        onConfirm={handleConfirmUpgrade}
        isLoading={isLoading}
      />

      {/* Creator Onboarding Modal */}
      <CreatorOnboardingModal
        isOpen={showOnboarding}
        onClose={() => setShowOnboarding(false)}
      />
    </>
  );
}
