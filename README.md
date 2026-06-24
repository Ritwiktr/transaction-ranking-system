# Transaction Ranking System

A points-ledger backend with idempotent transactions, safe concurrent updates, and a fair multi-factor ranking leaderboard. Includes a small live frontend that demonstrates the full flow.

## Assumptions

- **Domain**: Users earn positive integer points via transactions (not a payment processor).
- **Identity**: Clients supply a `userId` string; there is no authentication layer.
- **Persistence**: PostgreSQL in production (Render), SQLite for local development.
- **Rate limiting**: In-memory per-user limit (resets on process restart).

## Project Structure

```
backend/     FastAPI application
frontend/    Vanilla HTML/CSS/JS demo UI
render.yaml  Render Blueprint for API + static site + Postgres
```

## Run Locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Optional `.env` in `backend/`:

```env
DATABASE_URL=sqlite:///./local.db
CORS_ORIGINS=*
RATE_LIMIT_PER_MINUTE=30
```

### Frontend

Serve the `frontend/` directory with any static file server and ensure `frontend/js/config.js` points to your API:

```js
window.API_BASE_URL = "http://localhost:8000";
```

Example:

```bash
cd frontend
python3 -m http.server 5500
```

Open http://localhost:5500

## API Reference

### POST `/transaction`

Records a points transaction idempotently.

**Request body**

```json
{
  "userId": "alice",
  "amount": 250,
  "idempotencyKey": "client-uuid-abc123"
}
```

**Validation**

- `userId`: 3–64 chars, alphanumeric plus `-` or `_`
- `amount`: integer from 1 to 10,000
- `idempotencyKey`: 8–128 chars, required

**Responses**

- `201` — new transaction processed
- `200` — duplicate idempotency key (same result returned, balance unchanged)
- `400` — validation error
- `429` — per-user rate limit exceeded (30 requests/minute)

**Example**

```bash
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{"userId":"alice","amount":100,"idempotencyKey":"demo-key-001"}'
```

### GET `/summary/:userId`

Returns aggregate stats and current rank for a user.

**Response**

```json
{
  "userId": "alice",
  "totalPoints": 1250,
  "transactionCount": 8,
  "averageTransactionAmount": 156.25,
  "rank": 2,
  "rankingScore": 1265.63
}
```

- `404` if the user has no transactions.

### GET `/ranking?limit=50`

Returns the ordered leaderboard (`limit` default 50, max 100).

## Database Schema

**`transactions`**

| Column           | Type         | Notes                    |
|------------------|--------------|--------------------------|
| id               | UUID         | primary key              |
| user_id          | VARCHAR(64)  | indexed                  |
| amount           | INTEGER      | 1–10,000                 |
| idempotency_key  | VARCHAR(128) | unique — deduplication   |
| created_at       | TIMESTAMPTZ  | server timestamp         |

**`user_stats`** (denormalized aggregate)

| Column                | Type         | Notes              |
|-----------------------|--------------|--------------------|
| user_id               | VARCHAR(64)  | primary key        |
| total_points          | BIGINT       | running sum        |
| transaction_count     | INTEGER      | running count      |
| first_transaction_at  | TIMESTAMPTZ  | ranking tie-break  |
| updated_at            | TIMESTAMPTZ  | last update        |

Each write runs in a single DB transaction: insert transaction, lock user row with `SELECT ... FOR UPDATE`, increment aggregates, commit.

## How Ranking Is Calculated

Users are sorted by three factors in order:

1. **Total points** (descending) — rewards genuine volume.
2. **Average transaction size** (descending) — discourages spamming many 1-point micro-transactions.
3. **First transaction timestamp** (ascending) — stable tie-breaker for early participants.

Display score (informational):

```
rankingScore = totalPoints + (averageTransactionAmount × 0.1)
```

Sorting uses the three factors directly, not just the scalar score.

## Duplicate Request Prevention

1. Client sends a unique `idempotencyKey` with each intended transaction.
2. Server enforces a **unique constraint** on `idempotency_key`.
3. On insert conflict, the existing transaction is fetched and returned with `"duplicate": true` and HTTP `200`.
4. User balances are **not** incremented again.

This protects against network retries and accidental double-submits.

## Concurrency & Consistency

- **Idempotency**: unique key prevents duplicate processing.
- **Row locking**: `SELECT ... FOR UPDATE` on `user_stats` prevents lost updates when multiple requests hit the same user concurrently.
- **Atomic updates**: transaction insert and stats increment happen in one DB transaction.

## Abuse Prevention

- Per-user rate limit: 30 requests/minute.
- Amount bounds: 1–10,000 per transaction.
- Multi-factor ranking reduces benefit from micro-transaction spam.

## Deploy to Render

1. Push this repo to GitHub.
2. In Render, create a **Blueprint** from `render.yaml`.
3. Set environment variables:
   - `CORS_ORIGINS` on the API service to your static site URL (e.g. `https://txn-ranking-ui.onrender.com`)
   - `API_BASE_URL` on the static site to your API URL (e.g. `https://txn-ranking-api.onrender.com`)
4. Deploy both services and the Postgres database.

## Live Demo

**Local (API + frontend together):**

```bash
./scripts/start.sh
```

Open http://localhost:8000

**Render deployment:**

1. Push this repo to GitHub.
2. In [Render Blueprints](https://dashboard.render.com/blueprints), connect the repo and deploy `render.yaml`.
3. Set `CORS_ORIGINS` on the API to your static site URL.
4. Set `API_BASE_URL` on the static site to your API URL.

The API also serves the frontend at `/` when run as a single service (useful for simpler deployments).

> **Note:** Render deployment requires an active billing plan on your Render workspace and a connected GitHub repository. If services are suspended, reactivate billing in the Render dashboard first.

## Known Limitations

- No authentication or authorization.
- Rate limiting is in-memory and resets when the API process restarts.
- Ranking is computed in application memory on read (fine for demo scale).
