import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../lib/api';
import { isExplorerModeEnabled } from '../lib/explorerMode';

export type UserMode = 'explorer' | 'creator';

/**
 * KAN-216: previously every useUserMode mount (Navbar, Profile,
 * BookViewForEntertainment) issued its own GET /users/me, even though
 * AuthContext already loads the same payload at startup and the User type
 * carries preferred_mode. Now the auth user is the source of truth; the
 * network call only happens when preferred_mode is genuinely absent, and
 * concurrent mounts share one in-flight request.
 */
let modeInflight: Promise<UserMode | null> | null = null;

async function fetchPreferredMode(): Promise<UserMode | null> {
  if (modeInflight) return modeInflight;
  modeInflight = apiClient
    .get<{ preferred_mode: UserMode }>('/users/me')
    .then((profile) => profile.preferred_mode || null)
    .catch(() => null)
    .finally(() => {
      modeInflight = null;
    });
  return modeInflight;
}

export const useUserMode = () => {
  const { user } = useAuth();
  const [mode, setMode] = useState<UserMode>('creator');
  const [isLoading, setIsLoading] = useState(true);

  const authMode = user?.preferred_mode;

  useEffect(() => {
    let cancelled = false;

    const loadUserMode = async () => {
      if (!user) {
        setMode('creator');
        setIsLoading(false);
        return;
      }

      if (!isExplorerModeEnabled()) {
        setMode('creator');
        setIsLoading(false);
        return;
      }

      // precise role based enforcement
      const hasCreator = user.roles?.includes('creator');
      const hasExplorer = user.roles?.includes('explorer');

      if (hasCreator && !hasExplorer) {
        setMode('creator');
        setIsLoading(false);
        return;
      }

      if (!hasCreator && hasExplorer) {
        setMode('explorer');
        setIsLoading(false);
        return;
      }

      // Both roles (or neither): preferred_mode decides. Reuse what
      // AuthContext already fetched instead of re-requesting /users/me.
      if (authMode === 'creator' || authMode === 'explorer') {
        setMode(authMode);
        setIsLoading(false);
        return;
      }

      try {
        const fetched = await fetchPreferredMode();
        if (cancelled) return;
        setMode(fetched || 'creator');
      } catch (error) {
        if (cancelled) return;
        console.error('Failed to load user mode:', error);
        setMode('creator');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    loadUserMode();
    return () => {
      cancelled = true;
    };
  }, [user, authMode]);

  const switchMode = async (newMode: UserMode) => {
    if (!user) return;
    if (newMode === 'explorer' && !isExplorerModeEnabled()) return false;

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
  const canAccessExplorerMode = isExplorerModeEnabled() && (user?.roles?.includes('explorer') ?? false);

  return {
    mode,
    switchMode,
    isLoading,
    canAccessCreatorMode,
    canAccessExplorerMode,
  };
};
