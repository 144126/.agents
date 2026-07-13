---
name: markitdown
description: Convert any document (PDF, Word, Excel, PowerPoint, images, audio, HTML, EPUB, CSV, JSON, XML, ZIP, YouTube URLs) to clean Markdown using Microsoft's MarkItDown library. Use this whenever someone needs to extract text from files, convert documents for LLM ingestion, prepare files for RAG pipelines, or transcribe audio/video content. This skill knows the exact CLI flags, Python API patterns, and all optional features (LLM image descriptions, Azure Document Intelligence/Content Understanding, OCR plugins, MCP server). If markitdown isn't found, this skill installs it via pipx (or installs pipx first if needed).
---

# MarkItDown Skill

MarkItDown is Microsoft's Python utility for converting files to Markdown — designed specifically for LLM ingestion and text analysis pipelines. It excels at preserving structure (headings, lists, tables, links) while keeping output token-efficient.

## Installation Check

Before using markitdown, check if it's available:

```bash
command -v markitdown >/dev/null 2>&1
```

If not found, install via pipx:

```bash
# Install pipx first if missing (Linux/macOS)
command -v pipx >/dev/null 2>&1 || python3 -m pip install --user pipx

# Install markitdown with all extras via pipx
pipx install 'markitdown[all]'

# Ensure pipx is on PATH
pipx ensurepath
```

After pipx install, the `markitdown` command may need a new shell or `source ~/.bashrc` to be on PATH. If `markitdown` still isn't found after install, try `python3 -m markitdown` or the full pipx bin path (`~/.local/bin/markitdown`).

## Quick Reference

### CLI (Primary Mode)

```bash
# Basic conversion — stdout
markitdown path/to/file.pdf > output.md

# Output to file
markitdown path/to/file.docx -o output.md

# Pipe content
cat path/to/file.xlsx | markitdown

# Pipe with content type hint
cat data.csv | markitdown --mime-type text/csv
```

The CLI auto-detects format from file extension. For piped input, it may need `--mime-type` or `--extension` hints. Use `--zip-auto` to auto-process ZIP contents.

**All supported formats (CLI):** PDF, DOCX, PPTX, XLSX, XLS, images (JPG/PNG/GIF/BMP/TIFF/SVG/WEBP), audio (MP3/WAV/MP4A/OGG/FLAC/M4A), HTML, CSV, JSON, XML, ZIP, EPUB, Outlook MSG, YouTube URLs, Markdown, text files.

### Python API (for Advanced Features)

```python
from markitdown import MarkItDown

# Basic
md = MarkItDown()
result = md.convert("file.pdf")
print(result.text_content)  # or result.markdown
```

## Advanced Features

### LLM-Powered Image Descriptions

When you need meaningful descriptions of images within documents (especially PPTX slides or standalone images), provide an LLM client:

```python
from openai import OpenAI
from markitdown import MarkItDown

client = OpenAI()  # or any OpenAI-compatible provider
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("presentation.pptx")
# Images in the doc now get AI-generated alt-text
print(result.text_content)
```

`llm_prompt` lets you customize the description style: `md = MarkItDown(llm_client=client, llm_model="gpt-4o", llm_prompt="Describe this image in detail for a blind user")`

### Azure Document Intelligence

For complex PDFs with dense tables, forms, or multi-column layouts where built-in extraction falls short:

```bash
markitdown path-to-file.pdf -o document.md -d -e "<endpoint>"
```

The `-d` flag enables Document Intelligence mode; `-e` specifies the endpoint. Requires `pip install 'markitdown[az-doc-intel]'` and Azure credentials.

```python
# Python equivalent
md = MarkItDown(docintel_endpoint="https://your-instance.cognitiveservices.azure.com/")
result = md.convert("complex_invoice.pdf")
```

### Azure Content Understanding

Higher-quality conversion with structured field extraction (YAML front matter), multi-modal support (documents, images, audio, video), and configurable analyzers. Install: `pip install 'markitdown[az-content-understanding]'`

```bash
markitdown path-to-file.pdf --use-cu --cu-endpoint "<endpoint>"
```

Python — zero-config auto-selects analyzer per file type:

```python
md = MarkItDown(cu_endpoint="<endpoint>")
result = md.convert("report.pdf")
result = md.convert("meeting.mp4")  # video
result = md.convert("call.wav")     # audio
```

With custom analyzer for domain-specific field extraction (invoice amounts, dates, etc):

```python
md = MarkItDown(
    cu_endpoint="<endpoint>",
    cu_analyzer_id="my-invoice-analyzer",
)
result = md.convert("invoice.pdf")
# Output includes YAML front matter with extracted fields
```

Use `cu_file_types` to restrict which formats route to CU (save costs):

```python
from markitdown.converters import ContentUnderstandingFileType
md = MarkItDown(
    cu_endpoint="<endpoint>",
    cu_file_types=[ContentUnderstandingFileType.PDF],
)
```

**Cost note:** Each CU-routed `convert()` call is a billable Azure API call.

### Plugins

List installed plugins: `markitdown --list-plugins`
Use plugins: `markitdown --use-plugins path-to-file.pdf`

The `markitdown-ocr` plugin adds OCR to PDF/DOCX/PPTX/XLSX using LLM Vision (same `llm_client`/`llm_model` pattern). Install: `pip install markitdown-ocr`. If no `llm_client` provided, OCR is silently skipped.

### Audio & YouTube Transcription

```bash
# Audio file (requires markitdown[audio-transcription])
markitdown recording.mp3 > transcript.md

# YouTube URL (requires markitdown[youtube-transcription])
markitdown "https://youtube.com/watch?v=..." > video_summary.md
```

Python — MarkItDown uses OpenAI Whisper under the hood for audio:

```python
md = MarkItDown()
result = md.convert("meeting_recording.wav")
print(result.text_content)
```

### MCP Server

MCP server for AI assistants: `pip install markitdown-mcp`

Configure in the AI client's MCP settings to expose on-demand file conversion.

## Security Considerations

This matters because MarkItDown accesses whatever the current process can reach — files, network URIs, internal services.

**Prefer narrow conversion methods** when you know the input type. Instead of the generic `convert()`:
- `convert_local("path/to/file.pdf")` — local files only, no network access
- `convert_stream(io.BytesIO(data), "file.pdf")` — binary stream with filename hint
- `convert_response(requests.get("https://example.com/doc.pdf"))` — HTTP response objects
- `convert_uri("https://example.com/doc.pdf")` — explicit URI conversion

For untrusted input, always validate file paths, limit URI schemes, and block access to private/loopback/metadata-service addresses.

## Common Patterns

### Batch convert all files in a directory

```bash
for f in ~/documents/*.pdf; do
    markitdown "$f" -o "${f%.pdf}.md"
done
```

### Convert with format hints for piped input

```bash
cat unknown_file | markitdown --extension .pdf
cat data | markitdown --mime-type application/json
```

### Help flags

```bash
markitdown --help           # CLI help
markitdown --list-plugins   # Show installed plugins
```

### In-memory conversion (no temp files)

```python
from markitdown import MarkItDown
import io

with open("file.pdf", "rb") as f:
    data = f.read()

md = MarkItDown()
result = md.convert_stream(io.BytesIO(data), "file.pdf")
print(result.text_content)
```

## Troubleshooting

- **"markitdown: command not found"** — Install via pipx: `pipx install 'markitdown[all]' && pipx ensurepath`. If pipx is missing: `python3 -m pip install --user pipx && pipx install 'markitdown[all]'`. After install, `source ~/.bashrc` or use the full path `~/.local/bin/markitdown`.
- **"No module named 'markitdown'"** in a script — Wrong Python env. Check which Python you're using, ensure markitdown is installed there.
- **Piped input fails** — Add `--mime-type` or `--extension` to help auto-detection
- **Empty output for images/audio** — You need `llm_client`/`llm_model` for image descriptions, or appropriate optional extras for audio transcription
- **Plugins not loading** — Use `--use-plugins` flag (disabled by default)
- **Docker usage** — `docker build -t markitdown:latest . && docker run --rm -i markitdown:latest < ~/file.pdf > output.md`
