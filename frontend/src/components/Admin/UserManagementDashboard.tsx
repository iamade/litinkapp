import React, { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import { toast } from 'react-hot-toast';
import {
  Users,
  Search,
  Trash2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Filter,
  RefreshCw,
  Download,
  UserX,
  Mail,
  Calendar,
  Shield
} from 'lucide-react';
import ConfirmUserDeletionModal from './ConfirmUserDeletionModal';

interface User {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

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
  is_active: boolean;
  content_counts: ContentCounts;
  can_delete: boolean;
  warnings: string[];
}

export default function UserManagementDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(0);
  const [totalUsers, setTotalUsers] = useState(0);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState<string | null>(null);
  const [deletionPreview, setDeletionPreview] = useState<DeletionPreview | null>(null);
  const [isBatchDelete, setIsBatchDelete] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    verified: 0,
    unverified: 0,
    creators: 0
  });

  const limit = 20;

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [currentPage, roleFilter]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (currentPage === 0) {
        fetchUsers();
      } else {
        setCurrentPage(0);
      }
    }, 500);

    return () => clearTimeout(delayDebounce);
  }, [searchTerm]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: (currentPage * limit).toString(),
      });

      if (searchTerm) params.append('search', searchTerm);
      if (roleFilter) params.append('role_filter', roleFilter);

      const response = await apiClient.get<{
        users: User[];
        total: number;
        limit: number;
        offset: number;
      }>(`/admin/users/list?${params}`);

      setUsers(response.users);
      setTotalUsers(response.total);
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await apiClient.get<{
        total_users: number;
        verified_users: number;
        unverified_users: number;
      }>('/admin/users/verification-stats');

      const creatorsResponse = await apiClient.get<{
        users: User[];
        total: number;
      }>('/admin/users/list?role_filter=creator&limit=1');

      setStats({
        total: response.total_users,
        verified: response.verified_users,
        unverified: response.unverified_users,
        creators: creatorsResponse.total
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      const preview = await apiClient.get<DeletionPreview>(
        `/admin/users/${userId}/deletion-preview`
      );
      setDeletionPreview(preview);
      setUserToDelete(userId);
      setIsBatchDelete(false);
      setShowDeleteModal(true);
    } catch (error: any) {
      toast.error(error.message || 'Failed to get deletion preview');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedUsers.size === 0) {
      toast.error('No users selected');
      return;
    }

    setIsBatchDelete(true);
    setShowDeleteModal(true);
  };

  const confirmDelete = async (reason?: string) => {
    try {
      if (isBatchDelete) {
        const response = await apiClient.post<{
          success: boolean;
          message: string;
          results: {
            total: number;
            successful: any[];
            failed: any[];
          };
        }>('/admin/users/batch-delete', {
          user_ids: Array.from(selectedUsers),
          reason
        });

        if (response.success) {
          toast.success(response.message);
          setSelectedUsers(new Set());
        } else {
          toast.error(`Batch deletion completed with errors: ${response.results.failed.length} failed`);
        }
      } else if (userToDelete) {
        await apiClient.delete(`/admin/users/${userToDelete}`, {
          reason
        });
        toast.success('User deleted successfully');
      }

      setShowDeleteModal(false);
      setUserToDelete(null);
      setDeletionPreview(null);
      fetchUsers();
      fetchStats();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete user(s)');
    }
  };

  const toggleUserSelection = (userId: string) => {
    const newSelection = new Set(selectedUsers);
    if (newSelection.has(userId)) {
      newSelection.delete(userId);
    } else {
      newSelection.add(userId);
    }
    setSelectedUsers(newSelection);
  };

  const selectTestUsers = () => {
    const testUsers = users.filter(u =>
      u.email.includes('test') ||
      u.email.includes('temp') ||
      u.email.includes('demo')
    );
    setSelectedUsers(new Set(testUsers.map(u => u.id)));
    toast.success(`Selected ${testUsers.length} test users`);
  };

  const totalPages = Math.ceil(totalUsers / limit);

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{stats.total}</p>
            </div>
            <Users className="w-10 h-10 text-blue-600 dark:text-blue-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Verified</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">{stats.verified}</p>
            </div>
            <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Unverified</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 mt-1">{stats.unverified}</p>
            </div>
            <XCircle className="w-10 h-10 text-orange-600 dark:text-orange-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Content Creators</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{stats.creators}</p>
            </div>
            <Shield className="w-10 h-10 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="flex flex-col md:flex-row gap-4 flex-1">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500 w-5 h-5" />
              <input
                type="text"
                placeholder="Search by email or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
              />
            </div>

            {/* Role Filter */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500 w-5 h-5" />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="pl-10 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All Roles</option>
                <option value="explorer">Explorer</option>
                <option value="creator">Creator</option>
                <option value="admin">Admin</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>

            <button
              onClick={fetchUsers}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Batch Actions */}
          {selectedUsers.size > 0 && (
            <div className="flex gap-2">
              <button
                onClick={handleBatchDelete}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Delete Selected ({selectedUsers.size})
              </button>
            </div>
          )}
        </div>

        {users.length > 0 && (
          <div className="mt-4">
            <button
              onClick={selectTestUsers}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline"
            >
              Select all test users
            </button>
          </div>
        )}
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedUsers.size === users.length && users.length > 0}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedUsers(new Set(users.map(u => u.id)));
                      } else {
                        setSelectedUsers(new Set());
                      }
                    }}
                    className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:bg-gray-600"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Roles
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex justify-center">
                      <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
                    </div>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                    <UserX className="w-12 h-12 mx-auto mb-2 text-gray-400 dark:text-gray-500" />
                    <p>No users found</p>
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedUsers.has(user.id)}
                        onChange={() => toggleUserSelection(user.id)}
                        className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:bg-gray-600"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {user.display_name || 'No name'}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                            <Mail className="w-3 h-3" />
                            {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((role) => (
                          <span
                            key={role}
                            className={`px-2 py-1 text-xs rounded-full ${
                              role === 'superadmin'
                                ? 'bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300'
                                : role === 'author'
                                ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300'
                                : 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300'
                            }`}
                          >
                            {role}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_active ? (
                        <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                          <CheckCircle className="w-4 h-4" />
                          Verified
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-sm text-orange-600 dark:text-orange-400">
                          <XCircle className="w-4 h-4" />
                          Unverified
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(user.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-gray-50 dark:bg-gray-700/50 px-6 py-4 flex items-center justify-between border-t border-gray-200 dark:border-gray-600">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              Showing {currentPage * limit + 1} to {Math.min((currentPage + 1) * limit, totalUsers)} of {totalUsers} users
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                disabled={currentPage === 0}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                disabled={currentPage >= totalPages - 1}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <ConfirmUserDeletionModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setUserToDelete(null);
            setDeletionPreview(null);
          }}
          onConfirm={confirmDelete}
          deletionPreview={deletionPreview}
          isBatchDelete={isBatchDelete}
          batchCount={selectedUsers.size}
        />
      )}
    </div>
  );
}
