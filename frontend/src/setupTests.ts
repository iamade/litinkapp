// Global test setup for Vitest.
// Registers @testing-library/jest-dom matchers on Vitest's expect so that
// assertions such as toBeInTheDocument() work without per-file wiring.
import "@testing-library/jest-dom/vitest";
