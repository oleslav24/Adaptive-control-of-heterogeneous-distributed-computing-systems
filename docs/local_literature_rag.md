# Local Literature RAG MVP

This workflow builds a local retrieval index from downloaded Google Scholar Alert PDFs.
It does not depend on Gmail and only uses files under `data/literature`.

## Inputs

- `data/literature/google_scholar_articles_clean.jsonl`
- `data/literature/google_scholar_pdf_downloads.jsonl`
- `data/literature/pdfs/*.pdf`

## Build

```bash
python -m project.literature_rag build
```

Outputs:

- `data/literature/rag/document_manifest.jsonl`
- `data/literature/rag/pages.jsonl`
- `data/literature/rag/chunks.jsonl`
- `data/literature/rag/tfidf_index.joblib`
- `data/literature/rag/rag_report.json`
- `data/literature/texts/*.txt`

## Search

```bash
python -m project.literature_rag search "task offloading resource allocation mobile edge computing" --top-k 5
```

The search command returns ranked chunks with score, article id, title, page, PDF path,
and a text snippet.

## Extractive Answer

```bash
python -m project.literature_rag answer "What methods are used for UAV task offloading in mobile edge computing?" --top-k 6
```

The answer command is intentionally extractive: it only uses retrieved local chunks and
prints local PDF sources. If retrieval confidence is low, it reports insufficient context.

## Report

```bash
python -m project.literature_rag report
```

Current MVP coverage:

- 44 readable PDFs
- 751 extracted pages
- 2,921 indexed chunks
- TF-IDF local index over extracted PDF text

Known limitations:

- It indexes only already downloaded PDFs, not the full clean article list.
- It uses TF-IDF retrieval, not embeddings.
- The answer command is extractive and does not perform LLM-based synthesis.
- Publisher-locked PDFs remain outside the local text corpus until downloaded separately.
