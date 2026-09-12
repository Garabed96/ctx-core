---
name: ctx-discuss
description: Explore a decision with the user before implementation. Use when they ask to discuss options, tradeoffs, or direction.
---

# CTX Discuss

Help the user reach a useful decision. Inspect relevant existing evidence, distinguish facts from assumptions, and challenge proposals when the tradeoff matters.

Discussion is read-only unless the user separately authorizes a specific change. Preserve that scope; do not create plans, PRDs, or checkpoints merely to hold a conversation.

Infer routine context from the conversation and existing work. Ask a focused question only when its answer materially changes the decision. Do not require prompt rewrites, formal success criteria, or another skill before discussing the substance.

For UI decisions, use the actual screen or supplied reference when available, plus relevant existing PRODUCT.md, DESIGN.md, and components. Explain the user-visible consequence; include implementation details only when they help choose. Read a specialized design reference only when it resolves a concrete question.

When the user authorizes implementation, continue within that authorization without asking them to enter another mode. Use a managed PRD workflow only when the user requests it or explicitly resumes an existing PRD gate.
