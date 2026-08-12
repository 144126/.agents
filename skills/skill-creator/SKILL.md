---
name: skill-creator
description: Create new skills and iteratively improve them. Use when users want to create a skill from scratch, edit an existing skill, or need help iterating on a skill draft.
---

# Skill Creator

Help the user create or improve a skill. The loop: understand what they want → write/revise the skill → test it → get feedback → repeat.

## Quick Questions

Start by understanding the intent:
1. What should this skill enable Claude to do?
2. When should it trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test prompts to verify it works?

Check available MCPs too — they might help research the domain.

## Write the SKILL.md

Fill in these components:

- **name**: Skill identifier
- **description**: When to trigger, what it does. Include both what the skill does AND specific trigger contexts. Make it slightly "pushy" to avoid undertriggering.
- **the rest**: Instructions for Claude to follow.

### Structure

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── resources (optional)
    ├── scripts/     - Code for deterministic/repetitive tasks
    ├── references/  - Docs loaded into context as needed
    └── assets/      - Templates, icons, fonts
```

### Progressive Disclosure

1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context when skill triggers (<500 lines ideal)
3. **Resources** — As needed (unlimited)

Keep it under 500 lines. If you're approaching that, add another hierarchy level with clear pointers. For large reference files, include a table of contents.

### Writing Tips

- Use imperative form ("Do this", not "You should do this")
- Explain **why** things are important rather than heavy-handed MUSTs
- LLMs have good theory of mind — explain reasoning so the model understands
- Include concrete examples of expected input/output
- Prefer general instructions over narrow, overfitted examples
- If you find yourself writing ALWAYS/NEVER in all caps, reframe — explain the reasoning instead

### Principle

Skills must not contain malware, exploit code, or anything that could compromise security. Don't create misleading or deceptive skills.

## Test & Iterate

After writing the skill:

1. **Draft 2-3 test prompts** — realistic things a user would say. Share them with the user: "Here are a few test cases. Do these look right?"
2. **Run the skill** on each test prompt yourself (or in a subagent if available). See what it produces.
3. **Show the results** to the user. Ask: "How does this look? Anything to change?"
4. **Revise the skill** based on feedback. Keep it lean — remove things that aren't pulling their weight.
5. **Repeat** until the user is satisfied.

### Making Improvements

- **Generalize from feedback** — don't overfit to the specific test prompts. The skill needs to work for many different prompts.
- **Keep it lean** — remove parts that waste time or don't contribute. Read transcripts, not just final outputs.
- **Look for repeated work** — if all test cases independently wrote similar helper scripts, bundle that script into `scripts/` and reference it from the SKILL.md.
- **Explain the why** — transmit your understanding into the instructions rather than piling on rigid rules.

## Package (optional)

If the `present_files` tool is available and the user wants a packaged skill:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Direct the user to the resulting `.skill` file.

### Updating an existing skill

- Preserve the original name (directory name and `name` frontmatter field).
- If the installed path is read-only, copy to `/tmp/skill-name/`, edit there, and package from the copy.
