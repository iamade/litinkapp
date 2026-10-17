import { describe, expect, it } from 'vitest';
import { shouldMountConsultationTab } from '../ProjectView';
describe('KAN-469 consultation tab eligibility', () => {
  it('mounts when pipeline steps include consultation', () => expect(shouldMountConsultationTab(['plot', 'consultation'], false)).toBe(true));
  it('mounts when saved data exists without a pipeline step', () => expect(shouldMountConsultationTab(['plot', 'chapters', 'script'], true)).toBe(true));
  it('does not mount without either condition', () => expect(shouldMountConsultationTab(['plot', 'chapters', 'script'], false)).toBe(false));
});
