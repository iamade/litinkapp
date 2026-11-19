import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { CREDIT_COSTS, estimateScriptCredits } from './creditCosts';

/**
 * KAN-521: the UI label said 3 credits while the ledger debited 2 for a script
 * generation. The ledger is authoritative: the backend charges a flat
 * SCRIPT_GEN = 2 (backend/app/credits/constants.py), reserved and committed with
 * no token scaling, and the endpoint has no path that consumes the book-pipeline
 * per-1k-token rate.
 *
 * These tests pin the display constant to the ledger constant and fail if either
 * side drifts, so the label cannot silently disagree with the debit again.
 */

const BACKEND_CONSTANTS = resolve(
  __dirname,
  '../../../backend/app/credits/constants.py'
);

function readLedgerScriptGen(): number {
  const source = readFileSync(BACKEND_CONSTANTS, 'utf8');
  const match = source.match(/^SCRIPT_GEN\s*=\s*(\d+)/m);
  if (!match) throw new Error('SCRIPT_GEN not found in backend credit constants');
  return Number(match[1]);
}

describe('KAN-521 script credit display/ledger parity', () => {
  it('display constant equals the backend ledger debit', () => {
    const ledger = readLedgerScriptGen();
    expect(ledger).toBe(2);
    expect(CREDIT_COSTS.SCRIPT).toBe(ledger);
  });

  it('reports the flat ledger price, not the unused book-pipeline token rate', () => {
    // The old label came from estimateScriptCredits(), which returns the
    // per-1k-token rate (3) and is what produced the over-statement.
    expect(estimateScriptCredits()).toBe(3);
    expect(CREDIT_COSTS.SCRIPT).toBe(2);
    expect(CREDIT_COSTS.SCRIPT).not.toBe(estimateScriptCredits());
  });

  it('under-charge direction is closed: label never exceeds the debit', () => {
    const ledger = readLedgerScriptGen();
    // Ticket KAN-521 was filed as under-charging (debit 2 < label 3). After the
    // fix the label is the debit, so the user is never quoted more than charged.
    expect(CREDIT_COSTS.SCRIPT).toBeLessThanOrEqual(ledger);
  });
});
