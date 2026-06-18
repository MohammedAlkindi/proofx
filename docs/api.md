# API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

No client authentication is required. The Anthropic API key is server-side only. All request bodies are JSON; all responses are JSON unless noted.

---

## POST /generate

Generate candidate mathematical conjectures for a domain.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stream` | bool | `false` | If `true`, return a Server-Sent Events stream instead of a JSON body |

**Request body**

```json
{
  "domain": "algebraic number theory",
  "n": 5
}
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `domain` | string | 1–200 chars | Mathematical domain to generate conjectures for |
| `n` | integer | 1–20 | Number of conjectures to generate |

**Response (non-streaming)**

```json
{
  "conjectures": [
    {
      "id": "<uuid>",
      "domain": "algebraic number theory",
      "statement": "For all prime p > 2, ...",
      "subfield": "prime distribution",
      "motivation": "Extends the result of ...",
      "confidence_estimate": 0.72,
      "tags": ["primes", "algebraic"]
    }
  ]
}
```

**SSE streaming** (`?stream=true`)

Events are delivered as Server-Sent Events. Event types:

| Event | Data |
|-------|------|
| `conjecture` | JSON-encoded `ConjectureItem` object |
| `done` | `{}` |
| `error` | Error message string |

---

## POST /formalize

Translate a natural-language conjecture to Lean 4 and validate it with `lake build`.

**Request body**

```json
{
  "conjecture": "For all integers n, n^2 + n is even.",
  "subfield": "elementary number theory"
}
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `conjecture` | string | 1–5000 chars | Natural-language conjecture statement |
| `subfield` | string | 0–200 chars | Optional subfield tag (used for RAG context) |

**Response**

```json
{
  "lean_code": "theorem conjecture (n : ℤ) : 2 ∣ n^2 + n := by\n  ...",
  "is_valid": true,
  "error_log": ""
}
```

| Field | Description |
|-------|-------------|
| `lean_code` | Generated Lean 4 source |
| `is_valid` | `true` only if `lake build` passed on this code |
| `error_log` | Compiler output when `is_valid` is `false` |

---

## POST /verify

Attempt automated proof of a Lean 4 theorem statement.

**Request body**

```json
{
  "lean_code": "theorem conjecture (n : ℤ) : 2 ∣ n^2 + n := by\n  sorry",
  "strategy": "claude_standard"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lean_code` | string | *(required)* | Lean 4 source to prove |
| `strategy` | string | `"claude_standard"` | One of `quick_tactics`, `claude_standard`, `extended_thinking`, `human_review` |

**Response**

```json
{
  "proved": true,
  "attempts": [
    {
      "attempt": "auto:omega",
      "lean_code": "theorem conjecture (n : ℤ) : 2 ∣ n^2 + n := by omega",
      "error": "",
      "success": true
    }
  ],
  "final_proof": "theorem conjecture (n : ℤ) : 2 ∣ n^2 + n := by omega",
  "failure_reason": null
}
```

---

## POST /pipeline

Submit a full async pipeline run: generate → formalize → verify → counterexample search → snapshot.

Returns immediately with a job ID. Poll `/jobs/{id}` or stream `/jobs/{id}/stream` for status.

**Request body**

```json
{
  "domain": "algebraic number theory",
  "n": 1
}
```

| Field | Constraints |
|-------|-------------|
| `domain` | 1–200 chars |
| `n` | 1–5 |

**Response** — `202 Accepted`

```json
{
  "job_id": "<uuid>",
  "status": "submitted",
  "message": "Pipeline job submitted"
}
```

If Celery is unavailable, the pipeline runs synchronously and returns `200 OK` with the full result directly.

---

## GET /jobs/{job_id}

Poll the status of an async pipeline job.

**Response**

```json
{
  "job_id": "<uuid>",
  "status": "success",
  "result": { ... },
  "error": null,
  "total_duration_ms": 45320
}
```

Status values: `pending`, `running`, `success`, `failure`.

---

## GET /jobs/{job_id}/stream

Stream job progress events as Server-Sent Events. The connection stays open until the job completes.

Event types vary by pipeline stage. Each event carries a `data` field with a JSON-encoded progress payload. The stream closes with a `done` event on completion or an `error` event on failure.

---

## GET /experiments

List all experiments.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `domain` | string | Filter by domain (substring match) |
| `proved` | bool | Filter by proof status |
| `limit` | integer | Max results (default: 50) |
| `offset` | integer | Pagination offset |

**Response**

```json
{
  "experiments": [
    {
      "id": "<uuid>",
      "timestamp": "2024-01-01T00:00:00Z",
      "domain": "algebraic number theory",
      "conjecture": "...",
      "is_valid": true,
      "proved": false,
      "model_used": "claude-sonnet-4-20250514",
      "duration_ms": 12340,
      "novelty_score": 0.95,
      "proof_strategy": "claude_standard",
      "counterexample_checked": true,
      "counterexample_found": false
    }
  ]
}
```

---

## GET /experiments/{id}

Get full detail for one experiment.

**Response**

```json
{
  "id": "<uuid>",
  "timestamp": "2024-01-01T00:00:00Z",
  "domain": "...",
  "conjecture": "...",
  "lean_code": "...",
  "is_valid": true,
  "proved": false,
  "final_proof": null,
  "model_used": "claude-sonnet-4-20250514",
  "duration_ms": 12340,
  "extra": { ... }
}
```

The `extra` field contains the full counterexample ensemble result (all three method results, consensus, disagreement), arXiv papers used for generation, and any other pipeline metadata.

---

## GET /experiments/{id}/export

Export an experiment as Lean source or LaTeX.

**Query parameters**

| Parameter | Values | Default |
|-----------|--------|---------|
| `format` | `lean`, `latex` | `lean` |

**Response**: `text/plain` — the Lean 4 source or LaTeX document.

---

## GET /experiments/{id}/lineage

Get the lineage graph for an experiment: its parent (if it was derived) and its children (experiments derived from it).

**Response**

```json
{
  "experiment_id": "<uuid>",
  "parent": {
    "id": "<uuid>",
    "conjecture": "...",
    "domain": "...",
    "proved": false,
    "is_valid": true
  },
  "children": [
    {
      "id": "<uuid>",
      "conjecture": "...",
      "domain": "...",
      "proved": true,
      "is_valid": true
    }
  ]
}
```

`parent` is `null` if the experiment was not derived from another.

---

## POST /experiments/{id}/derive

Derive new conjectures from an existing experiment and submit them as a new pipeline job.

**Request body**

```json
{
  "n": 3,
  "relation": "generalization"
}
```

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `n` | 1–10 | `3` | Number of derived conjectures to generate |
| `relation` | `generalization`, `special_case`, `analogue` | `generalization` | Relationship to explore |

**Response** — `202 Accepted`

```json
{
  "parent_experiment_id": "<uuid>",
  "job_id": "<uuid>",
  "status": "submitted",
  "message": "Derive job submitted"
}
```

---

## POST /experiments/{id}/annotate

Attach a human annotation to an experiment.

**Request body**

```json
{
  "interesting": true,
  "notes": "This relates to Goldbach's conjecture because ...",
  "correct_proof": null,
  "annotator": "human"
}
```

**Response**

```json
{
  "annotation_id": "<uuid>",
  "experiment_id": "<uuid>",
  "message": "Annotation saved"
}
```

---

## GET /stats

Aggregate pipeline statistics and failure registry contents.

**Response**

```json
{
  "total_experiments": 142,
  "proved_count": 23,
  "valid_count": 98,
  "failure_registry": {
    "algebraic topology": {
      "formalize": 7,
      "verify": 3
    }
  }
}
```

The `failure_registry` field maps subfield names to per-stage failure counts. Subfields with 5+ formalization failures generate avoidance hints in subsequent generation prompts.

---

## Error responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|------|---------|
| `400 Bad Request` | Invalid request body (validation error) |
| `404 Not Found` | Experiment or job not found |
| `502 Bad Gateway` | Claude API call or Lean build failed |
| `503 Service Unavailable` | Lean sandbox not initialized |

Error bodies follow FastAPI's default format:
```json
{
  "detail": "error description"
}
```
