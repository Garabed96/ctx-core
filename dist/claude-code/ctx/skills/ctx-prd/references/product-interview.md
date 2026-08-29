# Product Interview

Use only when a missing answer can change user behavior, scope, visual direction, safety, or acceptance.

## One consequential question

Call `AskOne` with one question, 2–5 distinct options, and one recommendation. Explain tradeoffs in option descriptions. Never batch unrelated decisions or hide multiple seams inside one option.

Prefer questions in this order, skipping every settled axis:

1. **Outcome** — what becomes observably true for the user?
2. **Boundary** — what adjacent behavior is explicitly excluded?
3. **Invariant** — what must remain safe or unchanged?
4. **Direction** — which product or visual choice requires human judgment?
5. **Gate** — what vertical evidence would make progress reviewable?
6. **Verifier** — can evidence decide objectively, or must a human decide?

A technical choice is not a product question unless its consequences alter the product contract. Resolve ordinary implementation choices from repository conventions and evidence.

## Stop condition

Stop interviewing when:

- the outcome and non-goals are explicit;
- material decisions include a brief rationale;
- 1–5 meaningful gates cover the product contract without padding;
- every gate has one named verifier;
- no remaining question can materially alter those fields.

Do not continue for completeness theater. Unknown implementation details belong to execution, not the PRD.