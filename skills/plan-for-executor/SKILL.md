# Plan-for-Executor Skill

When using a powerful frontier SOTA model to plan and a less powerful smaller model to execute, the plan IS the interface. Every ambiguity in the plan forces the weaker model to reason — and reasoning is exactly what it's weak at. This skill defines exactly what the plan must contain, how it must be structured, and at what granularity.

## The Plan Specification

### 1. Decision-Complete

The executor must NEVER make planning-level decisions. If the executor has to choose between approaches, infer intent, or resolve ambiguity, the plan is insufficient. The plan must specify:

- **What** to do (the exact action)
- **With what inputs** (concrete values, not references to resolve)
- **In what order** (sequential or parallel; explicit dependencies)
- **What output to produce** (exact format, file path, data structure)
- **How to verify success** (test command, assertion, or acceptance criterion)

A search step of `"search for relevant sources"` is too vague. `"search Google Scholar for papers on climate feedback loops published after 2020, return top 5 paper titles and URLs"` is appropriately specific.

### 2. Structured Format (Not Free-Form Prose)

Free-form natural language plans leave too much to interpretation. Use structured formats proven by research (SCoT, IR, DSL):

```
## Plan

### Step 1: [Action verb] [object]
- Input: [concrete value]
- Tool: [tool name]
- Dependencies: [step IDs that must complete first]
- Output: [what this step produces]
- Verify: [how to check success]

### Step 2: ...
```

For code generation, use program structures explicitly:
- **Sequence**: steps that run one after another
- **Branch**: `if/then/else` conditions the executor can evaluate deterministically
- **Loop**: `for each` / `while` with clear iteration bounds

Prefer typed schemas (JSON, DSL) over prose when possible — they constrain the executor's output space and eliminate hallucination at the translation boundary.

### 3. Atomic Granularity

Each step must be directly executable by the weaker model in a single action (one tool call, one code block, one function). Criteria for atomic:
- Can be implemented in 5-15 lines of code
- Requires one tool call (search, read, write, bash)
- Does not require sub-decomposition

Decomposing too deeply (hundreds of trivial steps) creates coordination overhead. Decomposing too shallowly leaves the executor unable to act.

If a step requires the executor to make a judgment call, split it into smaller steps until each judgment is a deterministic check.

### 4. Explicit Dependency Graph

```
Dependencies:
  Step 1: no dependencies (starts immediately)
  Step 2: no dependencies (starts immediately, parallel with 1)
  Step 3: depends on Step 1, Step 2 (waits for both)
  Step 4: depends on Step 3 (sequential)
```

Parallel steps reduce wall-clock time. Mark them explicitly so the executor can batch independent work.

For each dependency, specify the **data contract**: exactly what value passes from producer to consumer (variable name, file path, return value structure).

### 5. Verification Every Step

Each step must carry a verification criterion the executor can check deterministically:

- File exists at path
- Command returns exit code 0
- Output contains expected string
- Test passes

Without verification, the executor cannot detect when a step failed silently — and a weaker model is more likely to produce plausible-but-wrong outputs that a stronger model would catch.

### 6. Plan Quality Is Non-Negotiable

Research (CodePLAN, 2024) proves that low-quality plans degrade performance **below** the no-plan baseline. A bad plan is worse than no plan. The frontier planner must:

1. **Generate multiple candidate plans** and select the best (plan sampling)
2. **Use backward reasoning** when possible: trace from the desired outcome back to the starting state
3. **Self-critique the plan** before releasing it: check for missing steps, ambiguous wording, untestable outcomes
4. **Include step-level error recovery**: what the executor should do if a step fails (retry, use alternative, abort)

### 7. Plan as Intermediate Representation

The most robust pattern is **plan-as-compiler**: the frontier model emits a structured plan (typed JSON, DSL, DAG), then a **deterministic non-LLM compiler** translates it to executable actions. This eliminates the executor model's ability to hallucinate at the translation boundary entirely.

When this isn't possible (executor must interpret flexibly), the plan should use a constrained vocabulary of action verbs and output formats the executor has been primed to handle.

### 8. Recovery and Adaptation

Include in the plan:
- **Per-step fallback**: what to do if this specific step fails
- **Replanning trigger**: conditions under which the executor should request a new plan (not try to fix it)
- **Partial success handling**: what to do when some steps succeed and others fail

The executor should NEVER replan. It should either follow the fallback or escalate to the planner.

## Plan Template

```
## Goal
[one-sentence statement of what success looks like]

## Plan
### Step 1: [Action] [Object]
- Input: [concrete value]
- Tool/Command: [exact command or tool]
- Dependencies: []
- Output: [exact output specification]
- Verify: [deterministic check]

### Step N: ...
[repeat for each atomic step]

## Dependencies
[explicit dependency graph or list]

## Recovery
- If Step 1 fails: [specific fallback]
- If Step 3 fails more than 2 times: escalate to planner
- Partial success: [what constitutes acceptable partial completion]
```

## When to Use This Pattern

| Use | Don't Use |
|-----|-----------|
| Multi-step tasks with clear decomposition | Single-step queries |
| Tasks needing audit trail | Tasks needing <500ms response |
| High-cost execution (many tool calls) | Exploratory/creative work |
| Repetitive workflows (plan caching) | Rapidly changing tool APIs |
| Tasks where failure is expensive | Tasks where planning costs exceed execution |