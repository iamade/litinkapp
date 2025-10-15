import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../lib/api';

export type UserMode = 'explorer' | 'creator';

export const useUserMode = () => {
  const { user } = useAuth();
  const [mode, setMode] = useState<UserMode>('explorer');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadUserMode = async () => {
      if (!user) {
        setMode('explorer');
        setIsLoading(false);
        return;
      }

      try {
        const profile = await apiClient.get<{ preferred_mode: UserMode }>('/users/me');
        setMode(profile.preferred_mode || 'explorer');
      } catch (error) {
        console.error('Failed to load user mode:', error);
        setMode('explorer');
      } finally {
        setIsLoading(false);
      }
    };

    loadUserMode();
  }, [user]);

  const switchMode = async (newMode: UserMode) => {
    if (!user) return;

    try {
      await apiClient.put('/users/me', { preferred_mode: newMode });
      setMode(newMode);
      return true;
    } catch (error) {
      console.error('Failed to switch mode:', error);
      return false;
    }
  };

  const canAccessCreatorMode = user?.roles?.includes('creator') ?? false;
  const canAccessExplorerMode = user?.roles?.includes('explorer') ?? false;

  return {
    mode,
    switchMode,
    isLoading,
    canAccessCreatorMode,
    canAccessExplorerMode,
  };
};
