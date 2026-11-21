import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

/**
 * KAN-521: behavioural coverage for the mounted ScriptGenerationPanel.
 *
 * kan521ScriptCreditParity.test.ts pins only the CREDIT_COSTS.SCRIPT constant.
 * This file mounts the panel so the rendered label and the client-side credit
 * gate are guarded too.
 *
 * SCOPE LIMIT: this proves the generation callback is never invoked when the
 * client gate is closed. It does NOT prove that no ledger debit occurs - the
 * debit is server-side (require_credits / credit_transaction) and is out of
 * reach of a component test. Do not read these tests as a ledger guarantee.
 *
 * Derived from PSQ's exact-SHA behavioural probe at adf2c05.
 */

const balanceRef = { value: 0 };

vi.mock('../../../hooks/useCreditBalance', () => ({
  useCreditBalance: () => ({ balance: balanceRef.value, loading: false, refreshBalance: vi.fn() }),
}));
vi.mock('../../../lib/api', () => ({
  apiClient: { get: vi.fn(async () => ({})), post: vi.fn(async () => ({})), put: vi.fn(async () => ({})) },
}));
vi.mock('../../../contexts/ScriptSelectionContext', () => ({
  useScriptSelection: () => ({ selectedScript: null, setSelectedScript: vi.fn(), selection: null, setSelection: vi.fn() }),
}));
vi.mock('react-hot-toast', () => ({ toast: { error: vi.fn(), success: vi.fn() }, default: {} }));

import ScriptGenerationPanel from '../ScriptGenerationPanel';

function mount(balance: number) {
  balanceRef.value = balance;
  const onGenerateScript = vi.fn();
  render(
    <MemoryRouter>
      <ScriptGenerationPanel
        chapterId="c1"
        chapterTitle="Chapter 1"
        chapterContent="Some chapter content."
        generatedScripts={[]}
        isLoading={false}
        isGeneratingScript={false}
        onGenerateScript={onGenerateScript}
        onUpdateScript={vi.fn()}
        onDeleteScript={vi.fn()}
        plotOverview={null}
      />
    </MemoryRouter>
  );
  return { onGenerateScript };
}

const generateButton = () => screen.getByRole('button', { name: /Generate Script/i });

describe('KAN-521 ScriptGenerationPanel credit label and gate', () => {
  beforeEach(() => {
    balanceRef.value = 0;
  });
  afterEach(() => cleanup());

  it('(a) displays a cost of 2 on the button and on the estimate line', () => {
    mount(10);
    expect(generateButton().textContent).toContain('Generate Script (2 credits)');
    expect(generateButton().textContent).not.toContain('(3 credits)');
    expect(screen.getByText(/Estimated cost: 2 credits/)).toBeTruthy();
  });

  it('(b1) balance 2 opens the gate: callback fires exactly once, no insufficient-credits text', () => {
    const { onGenerateScript } = mount(2);
    fireEvent.click(generateButton());
    expect(onGenerateScript).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/insufficient/i)).toBeNull();
  });

  it('(b2) balance 1 closes the gate: callback not called, Insufficient Credits modal shown', () => {
    const { onGenerateScript } = mount(1);
    fireEvent.click(generateButton());
    expect(onGenerateScript).toHaveBeenCalledTimes(0);
    expect(screen.getByText(/insufficient credits/i)).toBeTruthy();
  });

  it('(b3) balance 0 closes the gate: callback not called', () => {
    const { onGenerateScript } = mount(0);
    fireEvent.click(generateButton());
    expect(onGenerateScript).toHaveBeenCalledTimes(0);
  });
});
