---
description: Todo loop — read current directory's `todo` file, mark first item in progress, implement it, delete it, repeat until empty.
---

## /t — Todo Loop

Find the `todo` file in the current directory (no extension, plain text). Parse it into items separated by blank lines. Loop: pick first pending item → mark `[*]` in progress → implement → delete → repeat until empty.

## Todo File Format

File: `todo` in current working directory. Items separated by blank lines. Indented lines below an item are sub-points of that item.

```
item one description
    sub-detail about item one
    another sub-detail

item two description

section header
    sub-item under header
    another sub-item
```

Rules:
- **Pending**: any non-blank, non-comment, non-done line at the top-level of an item group
- **Done**: lines starting with `x `, `done `, `- [x]`, or `[*]` (already in progress)
- **Comments**: lines starting with `#` — skipped
- **Sections**: lines containing only `---` — skipped (they are just visual separators)
- **Items**: consecutive non-blank lines form one item; the first line is the title, indented lines below are sub-points

## Algorithm

```
loop:
  1. Read todo file from CWD
  2. If file doesn't exist:
       If $ARGUMENTS is non-empty → create file with $ARGUMENTS as first item
       If $ARGUMENTS is empty → report "no todo file" and exit
  3. Parse into items (blank-line separated groups)
  4. Find first pending item (not done/commented/separator)
  5. If no pending item found → report "All todos done!" and exit
  6. Mark it: prepend `[*] ` to the item's first line, save file
  7. Report: "Implementing: [item title]"
  8. IMPLEMENT the item using all available tools (read, edit, write, bash, etc.)
     - Follow the repo's code style and conventions from AGENTS.md
     - For complex items, decompose into sub-steps
  9. Delete the entire item (all its lines including the [*] marker) from the file, save
  10. Report: "Done: [item title]"
  11. goto loop
```

## Rules

- **One item at a time**: mark in progress → implement fully → delete → repeat
- **Item title is the first non-blank line** of the item group; indented sub-lines are context/details about what to do
- **Implement fully**: do not skip, simplify, or defer parts of an item
- **After completing an item**, immediately check if the todo file exists and has more items before looping
- **If implementation fails** or hits a blocker you cannot resolve, prepend `# BLOCKED: ` to the item's first line (replacing `[*]`), save the file, report the blocker, and move to the next item
- **If $ARGUMENTS is provided** (e.g. `/t add some task`), append the argument text as a new item at the end of the todo file before starting the loop. Create the file if it doesn't exist.
- **Be concise in status reports**: just "Implementing: {title}" and "Done: {title}" per item, plus final "All todos done!" when empty.
