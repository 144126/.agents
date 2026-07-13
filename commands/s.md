---
description: Determine if input is a question or a task. Questions get researched and answered. Tasks get researched for best approach, then executed.
---

$ARGUMENTS

## 1. Classify

Is this a **question** (seeking information/knowledge) or a **task/instruction** (asking me to do something, make something, fix something)?

Answer with one word: QUESTION or TASK. Then proceed to the matching section.

## 2A. If QUESTION — research & answer

You must find a definitive, sourced answer across every relevant angle. Do NOT stop until you have one.

### Loop
```
Loop:
   1. Break the topic into 3-8 sub-queries from different angles (multi-query rewrite, problem decomposition, step-back, perspective shifts, contrarian angles)
   2. Launch ALL in a single parallel batch
   3. Read promising results with WebFetch, extract what you found (or didn't)
   4. Critic: Do you have a fully sourced answer covering all angles with 2+ sources per major claim?
      → Yes: Exit, synthesize with inline [source URL] citations
      → No:  Identify gaps/weak coverage, reformulate with completely different phrasings, loop again
```

## 2B. If TASK — research best approach, then execute

### Research phase
```
Loop:
   1. Break the task into sub-questions: what's the best tool/library/approach, common pitfalls, known solutions, design patterns, alternatives
   2. Launch ALL in a single parallel batch
   3. Read promising results with WebFetch, extract what you found (or didn't)
   4. Critic: Do you have a clear, actionable execution plan with authoritative sources?
      → Yes: Exit research, proceed to execution
      → No:  Identify gaps, reformulate with different angles, loop again
```

### Execution phase
Carry out the task using the researched best approach. Use all available tools (read, edit, write, bash, etc.). Follow the repo's code style and conventions from AGENTS.md.

## Rules (both modes)
- Start broad — 3-8 parallel searches per round, cover every angle
- Read promising results fully (WebFetch), not just snippets
- Each round's phrasings must be substantially different from previous rounds — never repeat yourself
- Actively seek contrarian/critical/skeptical sources
- Note publication dates. Prefer recent sources (last 12-18 months) but include foundational older sources when relevant.
- Score source credibility: official doc > academic > industry > news > blog > forum
- Flag speculation vs fact clearly
- There are NO round limits, NO diminishing returns checks, NO quality thresholds that stop early
- Cite every factual claim inline [source URL] (question mode) or every design decision inline [source URL] (task mode)
