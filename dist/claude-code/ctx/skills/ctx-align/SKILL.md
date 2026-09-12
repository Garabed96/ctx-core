---
name: ctx-align
description: Review a prompt or skill for unclear intent, conflicting instructions, and unnecessary process when the user requests prompt calibration.
---

# CTX Align

Improve the instruction being reviewed, not the user's way of speaking. Use the surrounding conversation and available evidence to resolve ordinary ambiguity.

Identify wording that can change the outcome: an unclear objective, a material missing constraint, conflicting requirements, an overly broad trigger, or prescribed process without a useful purpose. Recommend the smallest correction and explain its practical effect.

Preserve domain knowledge, safety boundaries, and observable completion criteria. Remove generic coaching, duplicate rules, and mandatory workflows that add no task-specific value. Keep discovery descriptions narrow and load supporting material only when relevant.

Examples, output templates, and structured tags are optional tools, not prerequisites. Add them only when they clarify a real ambiguity. Do not invent a line budget or a required number of examples.

Ask only when an unresolved answer materially changes scope, risk, or the desired result. Otherwise state a reasonable assumption and provide the improved wording. Never require the user to rewrite their request before useful work can continue.

A review authorizes recommendations. Edit the target instructions only when the user authorizes changes; do not activate a planning or implementation workflow merely because the reviewed prompt mentions one.
