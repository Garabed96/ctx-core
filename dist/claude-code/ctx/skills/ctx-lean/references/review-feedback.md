# Review Feedback

Review comments are technical claims to evaluate, not instructions to accept performatively.

For every comment:

1. Map it to the exact requirement and affected code path.
2. Inspect current code, tests, conventions, and prior product decisions.
3. Classify it as `accept`, `reject`, or `clarify`, with concrete evidence.
4. Resolve every unclear or conflicting item before mutation when the ambiguity could change the shared implementation.
5. Implement accepted items in dependency order through the owning source path.
6. Re-run the affected contract after each coupled group, then verify the integrated result.
7. Reply with the disposition and evidence; use the original inline review thread when one exists.

Reject or escalate feedback that breaks existing behavior, conflicts with an approved product decision, adds unused machinery, assumes a different platform, or misunderstands a compatibility constraint. State the technical reason directly.

Do not add gratitude, praise, or reflexive agreement in place of analysis. When prior analysis was wrong, correct the record briefly and proceed.

A multi-item review is complete only when every comment has a disposition, every accepted change is verified, and rejected items retain evidence-backed reasoning.