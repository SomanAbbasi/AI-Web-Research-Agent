# AI Understanding & Extraction

## Purpose

Turn natural-language research goals into structured, validated data. Given a
goal ("find product name, price and rating") and a page, the extraction layer
asks an LLM for the values and returns a validated `ExtractedRecord` with
per-field results, missing-field tracking and a confidence score.

## Architecture

```
api/research.py  (POST /research/extract)
   |
   v
services/research.py  (extract_from_url)
   |      +-- HybridPageFetcher / HttpPageFetcher   (fetch page)
   |      +-- HTMLParser                            (page text)
   |      +-- ExtractionService                     (prompt + validate)
   |
   +-- infrastructure/llm.py   (build_llm_provider factory)
   |      +-- OpenAILLMProvider (OpenAI API, JSON mode)
   |      +-- MockLLMProvider   (deterministic, no API key)
   |
   +-- domain/llm.py           (LLMProvider protocol)
   +-- domain/research.py      (ResearchRequest, ExtractedRecord, ...)
```

Dependencies flow inward. Business logic (`ExtractionService`) depends only on
the `LLMProvider` protocol and the domain models; it never touches the OpenAI
SDK. The provider is selected by `LLM_PROVIDER` (default `mock`).

## Data Flow

1. `POST /research/extract` accepts a validated `ExtractRequestSchema` (goal,
   source URL, fields with descriptions).
2. `extract_from_url` fetches the page, rejects non-HTML/error responses, and
   parses it to visible text.
3. `ExtractionService.extract` builds a prompt (system + user with the goal,
   requested fields and truncated page text) and calls
   `LLMProvider.generate_json`.
4. The raw output is parsed with `json.loads` (tolerating markdown code fences)
   and must be a JSON object.
5. Values are coerced to strings; requested fields that are absent or empty are
   reported in `missing_fields`; unrequested keys are dropped.
6. `confidence` is the fraction of requested fields that were found. Malformed
   LLM output raises `ExtractionError` (surfaced as `ResearchError`).

## Key Decisions

- **Never trust raw LLM output.** Every response goes through JSON parsing and
  field-level validation. A provider change cannot silently change behavior.
- **Provider is a small protocol.** Adding Gemini/Anthropic/local providers
  only requires a new implementation of `generate_json` and a factory branch.
- **Confidence is derived, not guessed.** It reflects how many requested fields
  were actually found, which is deterministic and easy to audit.
- **Mock provider by default.** The app works end-to-end without an API key;
  set `LLM_PROVIDER=openai` and `LLM_API_KEY` for real extraction.
- **Text is truncated** to `LLM_MAX_CONTEXT` characters before prompting to
  bound token usage.

## Configuration

| Setting         | Default       | Purpose                     |
| --------------- | ------------- | --------------------------- |
| `LLM_PROVIDER`  | `mock`        | `mock` or `openai`          |
| `LLM_API_KEY`   | (none)        | Required when using openai  |
| `LLM_MODEL`     | `gpt-4o-mini` | Model name for openai       |
| `LLM_MAX_CONTEXT`| `12000`      | Max page characters in prompt |

## Tradeoffs

- **JSON-object mode, not typed schemas.** OpenAI's `json_object` response
  format is simple and provider-portable, at the cost of schema enforcement in
  the SDK. Validation compensates at the application layer.
- **Confidence is coverage-based.** It does not judge answer quality, only
  presence. Per-field reliability metadata is a possible extension.
- **Single page per request.** Batch/research-session extraction over many
  pages arrives in Phase 5 (data management) and Phase 6 (the agent).
