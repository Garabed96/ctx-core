# Proportional Testing

Tests defend observable contracts. They are not a universal prerequisite for every source edit.

## Choose the seam

Add or change a test when the slice introduces uncovered observable behavior, fixes a contract regression, or the user explicitly requests TDD. Match the repository's existing test level and location. Prefer the highest stable seam that exercises real behavior without reproducing implementation details.

A suitable test covers behavior, boundaries, invariants, transitions, precedence, or real errors. Avoid source-text assertions, plumbing checks, mocks that only verify themselves, and tests for incidental defaults.

When the actual surface is the stronger proof—visual UI, interaction feel, configuration wiring, a throwaway prototype, or generated output—exercise that surface instead. Add a test only if a stable observable contract remains uncovered.

## Red–green–refactor

When using TDD:

1. Write one minimal behavioral test.
2. Run it and confirm it fails for the missing behavior, not broken setup.
3. Implement only enough complete behavior to pass.
4. Run the focused test and affected suite.
5. Refactor only after green, preserving the contract.

For a bug, diagnose first. Use a reproducing test when the discovered contract has a stable test seam; do not force a synthetic test before root cause merely to satisfy ceremony.

Code written before a useful test is not grounds to delete working evidence or restart. The requirement is credible proof, not ritual order.