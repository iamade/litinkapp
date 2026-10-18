// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiClient: { get: vi.fn() },
}));

import { apiClient } from '../../lib/api';
import { shouldMountConsultationTab, useSavedConsultationFlag } from '../ProjectView';

const getSavedConsultation = vi.mocked(apiClient.get);
const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
};

describe('KAN-469 consultation tab eligibility', () => {
  beforeEach(() => vi.clearAllMocks());

  it('mounts when pipeline steps include consultation', () => expect(shouldMountConsultationTab(['plot', 'consultation'], false)).toBe(true));
  it('mounts when saved data exists without a pipeline step', () => expect(shouldMountConsultationTab(['plot', 'chapters', 'script'], true)).toBe(true));
  it('does not mount without either condition', () => expect(shouldMountConsultationTab(['plot', 'chapters', 'script'], false)).toBe(false));

  it('resets on an A-to-B project switch and remains false for B null data', async () => {
    getSavedConsultation
      .mockResolvedValueOnce({ status: 'success', consultation: { id: 'saved-a' } })
      .mockResolvedValueOnce({ status: 'success', consultation: null });
    const { result, rerender } = renderHook(({ projectId }) => useSavedConsultationFlag(projectId), { initialProps: { projectId: 'A' } });
    await waitFor(() => expect(result.current).toBe(true));

    rerender({ projectId: 'B' });
    expect(result.current).toBe(false);
    await waitFor(() => expect(getSavedConsultation).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current).toBe(false));
    expect(shouldMountConsultationTab(['plot', 'chapters', 'script'], result.current)).toBe(false);
  });

  it('does not let a late A response flip B true', async () => {
    const savedA = deferred<{ status: string; consultation: unknown }>();
    const pendingB = deferred<{ status: string; consultation: unknown }>();
    getSavedConsultation.mockReturnValueOnce(savedA.promise).mockReturnValueOnce(pendingB.promise);
    const { result, rerender } = renderHook(({ projectId }) => useSavedConsultationFlag(projectId), { initialProps: { projectId: 'A' } });

    rerender({ projectId: 'B' });
    expect(result.current).toBe(false);
    savedA.resolve({ status: 'success', consultation: { id: 'late-a' } });
    await Promise.resolve();
    expect(result.current).toBe(false);
  });
});
