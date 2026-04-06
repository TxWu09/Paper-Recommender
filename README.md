# Paper Reading Assistant

Hybrid paper tracking bot with user-defined domains, topics, and keyword-driven filtering.

## Project Status

This repository already implements an end-to-end MVP based on the plan:

- Source ingestion from `arXiv`, `OpenReview`, `Semantic Scholar`, and `Papers With Code`
- Deduplication (`paper_id`/URL identity + near-duplicate title similarity)
- Topic tagging from configurable taxonomy (not limited to fixed LLM subfields)
- Multi-signal quality scoring with confidence levels and explainable selection reasons
- Structured summary generation (template mode by default, API mode optional)
- Persistence in SQLite
- Export to `CSV/XLSX`, optional sync to Notion/Obsidian, and markdown digest generation
- Feedback loop (`like/dislike`) that adjusts scoring weights over time

## Architecture

```mermaid
flowchart LR
  sourceConnectors[SourceConnectors] --> ingestStage[IngestAndNormalize]
  ingestStage --> dedupStage[DedupAndTopicTag]
  dedupStage --> qualityEngine[QualityEngine]
  qualityEngine --> summaryEngine[SummaryEngine]
  summaryEngine --> storageLayer[SQLiteStorage]
  storageLayer --> sheetExporter[CSVXLSXExporter]
  storageLayer --> notionExporter[NotionExporterOptional]
  storageLayer --> obsidianExporter[ObsidianExporterOptional]
  storageLayer --> pushDispatcher[MarkdownDigest]
  pushDispatcher --> researcherView[ResearcherView]
  storageLayer --> feedbackStore[FeedbackSignals]
  feedbackStore --> feedbackAdjust[WeightAdjustments]
  feedbackAdjust --> qualityEngine
```

### Runtime Steps

1. Collect paper candidates from enabled sources.
2. Normalize all sources into a shared `Paper` schema.
3. Remove exact and near-duplicate records.
4. Tag papers into `reasoning`, `agent`, `post_training`, `rl`.
5. Score with multi-signal quality metrics and confidence levels.
6. Generate structured summaries and risk notes.
7. Persist all records, export top picks, and produce digest output.
8. Consume user feedback to adjust future scoring weights.

## Custom Domains and Keyword Selection

The bot is no longer limited to fixed LLM subfields.

- You can define any broad domain in `config/bot_config.yaml` under `domain_keyword_catalog`.
- You can define your own topic system under `topics`.
- You can ask the CLI to suggest multi-select keywords for a broad domain.
- You can run the pipeline with selected keywords or selected topics.

Example domain keyword suggestion:

```bash
paper-bot-run --config config/bot_config.yaml suggest-keywords --domain LLM --limit 20
```

Example run with multi-selected keywords:

```bash
paper-bot-run --config config/bot_config.yaml run --selected-keywords "post-training,pre-training,tool use"
```

Example run with explicit selected topics:

```bash
paper-bot-run --config config/bot_config.yaml run --selected-topics "reasoning,agent"
```

## Obsidian Integration

This project supports exporting recommendations directly into your Obsidian vault.

### Features

- One-note-per-paper export as Markdown
- YAML frontmatter for Dataview compatibility
- Auto tags such as `#paper/recommendation` and `#topic/<topic>`
- Daily index note (`paper_digest.md`) inside your configured folder

### Configuration

Edit `config/bot_config.yaml`:

```yaml
export:
  obsidian:
    enabled: true
    vault_path: "D:/Obsidian/MyVault"
    folder: "Papers"
    one_note_per_paper: true
    index_file: "paper_digest.md"
```

**Single Obsidian note (one file path)** — write the digest to an exact note path (e.g. `LLM/Paper Recommender.md` in your vault):

```yaml
export:
  obsidian:
    enabled: true
    output_path: "D:/Obsidian Vault/LLM/Paper Recommender.md"
    one_note_per_paper: false
    vault_path: ""
```

You can leave `vault_path` empty when using only `output_path`.

### Output Structure

- **Single file mode** (`output_path` set): digest written to that `.md` file (parent folders are created if needed).
- **Vault folder mode** (`vault_path` set, no `output_path`): per-paper notes: `<vault_path>/<folder>/<YYYY-MM-DD>/<paper_id>.md`
- **Vault folder mode** index: `<vault_path>/<folder>/paper_digest.md` when `output_path` is not set

Run as usual:

```bash
paper-bot-run --config config/bot_config.yaml run
```

## Data Schema

### `papers` table (SQLite)

| Field | Type | Description |
|---|---|---|
| `paper_id` | `TEXT (PK)` | Stable identity key for upsert and dedup. |
| `source` | `TEXT` | Source name (`arxiv`, `openreview`, etc.). |
| `title` | `TEXT` | Paper title. |
| `abstract` | `TEXT` | Paper abstract/body snippet used by scoring/summary. |
| `url` | `TEXT` | Canonical paper URL. |
| `published_at` | `TEXT` | ISO timestamp when available. |
| `authors_json` | `TEXT` | JSON array of authors. |
| `orgs_json` | `TEXT` | JSON array of institutions/organizations. |
| `venue` | `TEXT` | Venue string for venue-quality signal. |
| `topics_json` | `TEXT` | JSON array of matched topics. |
| `code_url` | `TEXT` | Code repository URL if available. |
| `citation_count` | `INTEGER` | Citation-based impact signal. |
| `social_signal` | `REAL` | Early attention signal (normalized score). |
| `metadata_json` | `TEXT` | Raw extra source metadata. |
| `final_score` | `REAL` | Combined quality score in `[0, 1]`. |
| `confidence` | `TEXT` | Confidence bucket (`A`, `B`, `C`). |
| `score_breakdown_json` | `TEXT` | JSON detail of each score dimension. |
| `why_selected` | `TEXT` | Human-readable recommendation rationale. |
| `risk_flags_json` | `TEXT` | JSON list of risk flags. |
| `summary` | `TEXT` | Structured summary content. |
| `pushed` | `INTEGER` | Delivery state (`0` not pushed, `1` pushed). |

### `feedback` table (SQLite)

| Field | Type | Description |
|---|---|---|
| `id` | `INTEGER (PK)` | Auto-increment feedback row ID. |
| `paper_id` | `TEXT` | Target paper identifier. |
| `signal` | `TEXT` | Feedback channel (`topic_like`, `venue_like`, etc.). |
| `value` | `INTEGER` | Feedback value in `{-1, 0, 1}`. |
| `created_at` | `TEXT` | Feedback timestamp (UTC ISO string). |

### Recommendation Output Schema (`CSV/XLSX` and Notion mapping)

| Field | Description |
|---|---|
| `title` | Paper title |
| `url` | Paper link |
| `date` | Publication date |
| `topics` | Matched topic tags |
| `venue` | Venue/journal/conference |
| `authors` | Author list |
| `org` | Organization list |
| `score` | Final score |
| `confidence` | Confidence tier |
| `summary` | Structured summary |
| `risks` | Risk flags |
| `code_url` | Code repository URL |
| `read_status` | Manual reading state (default `new`) |
| `why_selected` | Explainable recommendation reason |

## What We Built

### 1) Source Connectors and Ingestion Pipeline

Implemented connectors:

- `src/paper_bot/connectors/arxiv.py`
- `src/paper_bot/connectors/openreview.py`
- `src/paper_bot/connectors/semantic_scholar.py`
- `src/paper_bot/connectors/papers_with_code.py`
- `src/paper_bot/connectors/registry.py` (orchestrates all connectors)

Pipeline flow:

1. Fetch candidate papers from enabled sources
2. Normalize metadata into a shared `Paper` model
3. Deduplicate by identity key and title similarity
4. Tag topics based on configured taxonomy

Relevant files:

- `src/paper_bot/models/paper.py`
- `src/paper_bot/pipeline/ingest.py`
- `src/paper_bot/topic_taxonomy.py`
- `src/paper_bot/utils/text.py`

### 2) Quality Engine (Beyond Semantic Similarity)

Implemented in `src/paper_bot/pipeline/quality.py`.

Scoring dimensions:

- `topic_fit`
- `venue_signal`
- `author_org_signal`
- `impact_signal`
- `method_novelty`
- `evidence_strength`

Outputs per paper:

- `final_score` in `[0, 1]`
- `confidence` (`A/B/C`)
- `risk_flags` (e.g., weak evidence or hype mismatch)
- `why_selected` (human-readable explanation)

### 3) Summary Engine and Risk-Aware Reporting

Implemented in `src/paper_bot/pipeline/summary.py`.

Two modes:

- `local_template` (default): no API key required
- `api`: model-based summarization via OpenAI-compatible endpoint

Summary structure is aligned with research use:

- Problem
- Core idea / method
- Key result signal
- Relation to your target research tracks
- Reviewer-style risk notes
- Reproducibility suggestion

### 4) Storage, Export, and Push

Storage:

- `src/paper_bot/storage/sqlite_store.py`
- SQLite tables for `papers` and `feedback`

Export:

- `src/paper_bot/exporters/sheet_exporter.py` -> `data/recommendations.csv` + `data/recommendations.xlsx`
- `src/paper_bot/exporters/notion_exporter.py` -> optional Notion database sync
- `src/paper_bot/exporters/obsidian_exporter.py` -> optional Obsidian vault notes

Push:

- `src/paper_bot/pipeline/push.py` -> `data/daily_digest.md`

### 5) Feedback Loop and Iteration

Feedback and weight adaptation are implemented:

- `src/paper_bot/pipeline/feedback.py`
- `topic_like`, `venue_like`, `author_org_like`, etc. are aggregated from SQLite feedback
- Small, stable weight adjustments are applied in subsequent scoring runs

### 6) End-to-End Bot Orchestration and CLI

Main orchestrator:

- `src/paper_bot/pipeline/bot.py`

CLI entry:

- `src/paper_bot/cli.py`

Supported commands:

- Run one full cycle: fetch -> dedup -> score -> summarize -> persist -> export -> push
- Submit feedback for online iteration
- Suggest keywords by broad domain for user multi-selection

## Quickstart

1. Install:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

2. Configure:

- Edit `config/bot_config.yaml`
- Optional: set `OPENAI_API_KEY` and `NOTION_API_KEY`
- Optional: enable `export.notion.enabled` and fill `database_id`
- Optional: enable `export.obsidian.enabled` and set `vault_path`

3. Run one full cycle:

```bash
paper-bot-run --config config/bot_config.yaml run
```

4. Submit feedback (for iterative quality tuning):

```bash
paper-bot-run --config config/bot_config.yaml feedback --paper-id "<id>" --signal topic_like --value 1
```

## Runtime Outputs

- `data/papers.db`: persistent paper store + score + summary + push state + feedback
- `data/recommendations.csv`: tabular recommendations for spreadsheet workflows
- `data/recommendations.xlsx`: Excel workbook for local/offline use
- `data/daily_digest.md`: generated digest for daily push/report

## Outputs

- `data/papers.db`: full storage with scores/summaries.
- `data/recommendations.csv`: recommendation sheet.
- `data/recommendations.xlsx`: recommendation workbook.
- `data/daily_digest.md`: daily push digest.

## Configuration Highlights

- `config/bot_config.yaml` controls:
  - source enable/disable and limits
  - topic taxonomy aliases (fully customizable)
  - broad-domain keyword catalog for suggestion
  - default selected topics (`app.selected_topics`)
  - scoring weights
  - summary provider/model
  - export destinations
  - push settings

### LLM API (OpenAI or DeepSeek)

Summaries use an OpenAI-compatible `POST .../v1/chat/completions` endpoint.

**DeepSeek** (example):

1. Set your key in the shell (PowerShell):

```powershell
$env:DEEPSEEK_API_KEY="paste-your-key-here"
```

2. In `config/bot_config.yaml`:

```yaml
summary:
  provider: "api"
  api_provider: "deepseek"
  base_url: "https://api.deepseek.com/v1/chat/completions"
  api_key_env: "DEEPSEEK_API_KEY"
  model: "deepseek-chat"
```

**OpenAI**: keep `base_url` default or set `api_key_env` to `OPENAI_API_KEY` and use an OpenAI model name.

## Current Known Limitations

- External APIs may return `403`/`429` depending on rate limit or access policy.
- Some connectors may need source-specific retry/backoff/auth tuning for production.
- Quality signals are currently heuristic-based and should be calibrated with user feedback.

## Next Recommended Improvements

- Add robust retry/backoff and source-specific throttling in connectors.
- Add weekly thematic digest (`reasoning/agent/post-training/rl` balanced picks).
- Add stronger venue/author authority tables and citation velocity tracking.
- Add richer observability (ingest counts, dedup ratio, recommendation hit-rate).
