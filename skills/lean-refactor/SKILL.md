---
name: lean-refactor
description: Behavior-preserving cleanup of a codebase — remove dead code, simplify control flow, reduce API surface area, and make code leaner without changing external behavior. Trigger when the user asks to "clean up", "refactor for simplicity", "remove dead code", "simplify", "reduce complexity", "reduce surface area", "streamline", "declutter", "prune", or "make the code leaner". Not for adding features or behavior changes.
---

# Lean Refactor

When invoked, refactor the target code for simplicity and leanness WITHOUT changing external behavior.

## Goals (in priority order)
1. Remove dead code: unreachable branches, unused functions, variables, imports, exports, files, and feature flags that are always on/off.
2. Simplify control flow: collapse redundant conditionals, use guard clauses / early returns, eliminate unnecessary nesting and duplicate code paths.
3. Reduce surface area: shrink public APIs, remove unused parameters/options, consolidate overlapping helpers, delete speculative "just in case" generality.
4. Improve efficiency only where it's a clear win and doesn't add complexity.

## Constraints
- Behavior-preserving. No new features. Do not change public contracts unless the user approves it first.
- Make small, isolated, reviewable changes; keep structural (refactor) changes separate from any behavior changes.
- After each change, run the existing tests/build/linter and confirm they pass. If tests are missing for something you touch, tell the user before proceeding.
- Do not delete anything you cannot prove is unused (check call sites, dynamic references, reflection, string-based lookups, and public exports first).

## Deliverables
- A short list of what you found (dead code, complexity hotspots, redundant paths).
- The refactor applied in small commits/diffs, each with a one-line rationale.
- A summary of what shrank (files/functions/LOC removed, APIs narrowed) and any risks or items you flagged instead of changing.

## Process
Start by auditing and reporting BEFORE making any changes. Then apply the refactor incrementally, verifying after each step.
