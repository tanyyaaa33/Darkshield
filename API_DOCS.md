# DarkShield API documentation

Base URL defaults to `http://127.0.0.1:5000` for the internal Flask app. CORS is enabled for `/api/*`.

## Rate limits (public v1)

Routes under `/api/v1/*` are limited to **100 requests per hour per client IP** (Flask-Limiter, in-memory storage). Restarting the server resets counters.

## Internal API

### `POST /api/classify`

Classify UI text snippets (batch).

**Body (JSON)**

| Field | Type | Description |
|-------|------|-------------|
| `texts` | `string[]` | Required. Non-empty list of strings. |
| `url` | `string` | Optional page URL for logging. |
| `include_compliance` | `boolean` | If `true`, each non-`none` result includes a `compliance` object (regulatory mapper). |

**Query**

- `include_compliance=true` — same effect as the JSON field.

**Response:** JSON array of `{ text, label, confidence, explanation [, compliance] }`.

```bash
curl -s -X POST http://127.0.0.1:5000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"texts":["Only 2 left — ends in 00:15:00"],"include_compliance":true}'
```

### `GET /api/compliance-report?domain=<host>`

Aggregates stored SQLite detections for a domain into regulation-keyed lists (educational, not legal advice).

**Response:** `{ domain, violations_by_regulation, highest_severity_pattern, recommended_action }`.

```bash
curl -s "http://127.0.0.1:5000/api/compliance-report?domain=amazon.in"
```

### `GET /api/site-score?domain=<host>`

Transparency DB manipulation score and pattern breakdown.

### `GET /api/leaderboard?vertical=&limit=`

Ranked sites; `vertical` optional filter.

### `POST /api/report`

Submit a user report (`domain`, `text`, `label`, `confirmed`).

### `GET /api/stats`

Global DB stats plus optional evaluation metadata.

### `GET /api/health`

`{ "status": "ok" }`.

---

## Public API v1

### `GET /api/v1/score?domain=<host>`

```json
{
  "domain": "amazon.in",
  "manipulation_score": 67.4,
  "risk_level": "HIGH",
  "top_patterns": ["fake_urgency"],
  "pages_analyzed": 142,
  "last_updated": "...",
  "compliance_flags": ["CCPA_2023", "EU_Dark_Patterns"]
}
```

### `GET /api/v1/leaderboard?vertical=&limit=10`

JSON array of site rows.

### `GET /api/v1/categories`

DarkShield label schema (includes `none`).

### `GET /api/v1/stats`

Aggregate counts for landing page tickers.

```bash
curl -s "http://127.0.0.1:5000/api/v1/score?domain=amazon.in"
```

Optional future extension: accept `X-API-KEY` for elevated quotas (not enforced in the default build).
