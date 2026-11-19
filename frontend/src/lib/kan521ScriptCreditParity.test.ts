import { existsSync, readFileSync } from 'node:fs';
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
 * Tests 1 and 3 assert against the backend constant read from source. Both carry
 * the same skipIf, so in a frontend-only checkout they skip visibly (reported as
 * "N passed / M skipped", never as a full pass). Skipping beats a collection-time
 * ENOENT, which would kill the file and take the backend-free assertions with it.
 *
 * Test 4 is a PINNED LITERAL, not a parity check: it keeps a backend-free guard
 * on the agreed price. Update it alongside the ledger when KAN-521's price is
 * finally ruled on.
 */

const BACKEND_CONSTANTS = resolve(
  __dirname,
  '../../../backend/app/credits/constants.py'
);

const hasBackendSource = existsSync(BACKEND_CONSTANTS);

function readLedgerScriptGen(): number {
  const source = readFileSync(BACKEND_CONSTANTS, 'utf8');
  const match = source.match(/^SCRIPT_GEN\s*=\s*(\d+)/m);
  if (!match) throw new Error('SCRIPT_GEN not found in backend credit constants');
  return Number(match[1]);
}

describe('KAN-521 script credit display/ledger parity', () => {
  it.skipIf(!hasBackendSource)(
    'display constant equals the backend ledger debit',
    () => {
      const ledger = readLedgerScriptGen();
      expect(ledger).toBe(2);
      expect(CREDIT_COSTS.SCRIPT).toBe(ledger);
    }
  );

  it('reports the flat ledger price, not the unused book-pipeline token rate', () => {
    // The old label came from estimateScriptCredits(), which returns the
    // per-1k-token rate (3) and is what produced the over-statement.
    expect(estimateScriptCredits()).toBe(3);
    expect(CREDIT_COSTS.SCRIPT).toBe(2);
    expect(CREDIT_COSTS.SCRIPT).not.toBe(estimateScriptCredits());
  });

  // Dynamic compare against the ledger, so a DOWNWARD drift fails too. A literal
  // `<= 2` would pass when the ledger drops to 1 while the label still quotes 2,
  // which is the exact KAN-521 defect class (label quotes more than the debit).
  it.skipIf(!hasBackendSource)(
    'label never exceeds the debit (under-charge direction is closed)',
    () => {
      const ledger = readLedgerScriptGen();
      expect(CREDIT_COSTS.SCRIPT).toBeLessThanOrEqual(ledger);
    }
  );

  // Backend-free coverage. PINNED LITERAL — not a parity check. Update alongside
  // backend SCRIPT_GEN whenever the price ruling lands.
  it('pins the display constant to 2 for backend-free checkouts', () => {
    expect(CREDIT_COSTS.SCRIPT).toBe(2);
  });
});
