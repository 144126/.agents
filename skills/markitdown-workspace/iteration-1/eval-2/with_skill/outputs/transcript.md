# MarkItDown Batch Conversion — Transcript

**Date:** 2026-06-25
**Skill:** markitdown
**Tool:** markitdown CLI

## Input Files

### 1. `sales_data.csv`
- **Path:** `/home/ed/.agents/skills/markitdown/evals/files/sales_data.csv`
- **Type:** CSV
- **Content:** Quarterly sales data for Widget A and Widget B across 4 regions (9 rows, 6 columns)
- **Conversion command:** `markitdown input/sales_data.csv -o outputs/sales_data.md`

### 2. `article.html`
- **Path:** `/home/ed/.agents/skills/markitdown/evals/files/article.html`
- **Type:** HTML
- **Content:** Blog article "The Rise of AI-Powered Code Assistants" with headings, paragraphs, unordered list, table, and ordered list (64 lines)
- **Conversion command:** `markitdown input/article.html -o outputs/article.md`

## Output Directory

`/home/ed/.agents/skills/markitdown-workspace/iteration-1/eval-2/with_skill/outputs/`

## Output Files

### `sales_data.md`
- Result: CSV data preserved as plain text rows (markitdown treats CSV as plain text by default)

### `article.md`
- Result: Properly structured Markdown
  - `<h1>` → `# The Rise of AI-Powered Code Assistants`
  - `<h2>/<h3>` → `##` / `###`
  - `<ul>` → bullet list with `*`
  - `<ol>` → numbered list
  - `<table>` → GitHub-flavored markdown table
  - `<p>`, `<meta>` etc. → stripped/reformatted

## Summary

| Input | Size | Output | Notes |
|-------|------|--------|-------|
| sales_data.csv | 9 lines | sales_data.md (9 lines) | CSV preserved as-is |
| article.html | 64 lines | article.md (37 lines) | HTML fully converted to MD |

Total: 2 files converted successfully using `markitdown` CLI with auto-format detection.
