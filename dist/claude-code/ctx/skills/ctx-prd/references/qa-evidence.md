# QA Evidence Campaign

Create a separate Obsidian QA note when gate proof forms an evidence matrix: multiple scenarios, surfaces, devices, screenshots, safety constraints, or meaningful blockers. A single focused command result stays concise in the PRD gate.

Group evidence by coherent campaign, not mechanically by gate. Multiple gates may link one campaign. Start a new note when the surface, environment, release boundary, or test purpose is materially different.

## Naming and placement

Place the note beside its PRD and name the feature plus campaign:

```text
<Feature> — Mobile QA.md
<Feature> — Release QA.md
<Feature> — Accessibility QA.md
```

Use `<Feature> — QA.md` only when the campaign is genuinely the feature's sole QA scope. Never use bare `QA.md`.

## Evidence sheet

```markdown
---
title: <Feature> — <Campaign> QA
type: ctx-qa-evidence
status: in-progress | passed | blocked | failed
date: YYYY-MM-DD
related_prd: "[[<Feature> — PRD]]"
gates: [G2]
---

# <Feature> — <Campaign> QA

> [!info] Evidence boundary
> <Exact runtime, account class, environment, and what this does not prove.>

## Environment
| Surface | Evidence |
|---|---|
| ... | ... |

## Results
| Scenario | Expected contract | Result | Evidence / finding |
|---|---|---|---|
| ... | ... | PASS / FAIL / BLOCKED | ... |

## Findings or repairs verified
<Only material behavior and defects.>

## Automated checks
<Exact focused checks and observed outcomes.>

## Residual risks and next
<Untested paths, blockers, cleanup, or next campaign.>
```

Embed only screenshots that prove distinct states. Keep large galleries under the campaign's attachment folder. Do not persist credentials, tokens, customer data, or unnecessary personal account details.

## Authority

The QA note owns scenario evidence; the PRD owns the gate verdict and lifecycle. After the campaign changes, update every linked gate's concise status/evidence pointer. QA findings do not authorize source fixes unless the original request or a later user instruction authorized them.