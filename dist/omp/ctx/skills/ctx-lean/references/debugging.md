# Proportional Debugging

A bug starts in diagnosis mode, not planning mode. Scale evidence to uncertainty and risk; do not impose phases that add no information.

## Evidence loop

1. **Observe** — capture the reported symptom and exact boundary. Treat user-reported observations as true; do not rerun merely to confirm them.
2. **Reproduce** — when needed to inspect or later prove the fix, exercise the smallest scenario that triggers the symptom.
3. **Trace** — follow the actual data/control path to the first incorrect state, not merely the final exception or UI symptom.
4. **Hypothesize** — state one falsifiable cause and the observation that would disprove it.
5. **Test once** — run the narrowest check that distinguishes that cause from alternatives.
6. **Fix source** — correct the owning source-of-truth path; do not suppress the symptom or special-case the reported input.
7. **Confirm** — exercise the original reproduction after the fix.

If the hypothesis fails, update it from the new evidence. Do not stack speculative fixes.

## Tests

Add a regression test only when it protects an observable contract through a stable test seam. The original runtime reproduction remains required when a test cannot represent the reported surface faithfully.

Do not write an implementation task plan before root cause is supported. Technical complexity remains Lean work. Escalate to PRD only when the correct fix depends on an unresolved product decision.