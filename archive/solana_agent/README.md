# Solana Agent MVP

Execution + Payment Infrastructure for AI Agents on Solana.

**Flow:** Accept task → Run AI agent → Verify result → Send SOL → Return result + tx hash.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Solana CLI (for wallet setup)
- OpenAI API key

### 2. Install

```bash
cd solana_agent
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/solana_agent
OPENAI_API_KEY=sk-...
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PAYER_PRIVATE_KEY=<base58 private key>
SOLANA_RECIPIENT_ADDRESS=<recipient public key>
```

### 4. Set up a devnet wallet (payer)

```bash
# Generate a new keypair
solana-keygen new --outfile payer.json

# Fund it with devnet SOL (free)
solana airdrop 2 --keypair payer.json --url devnet

# Export to base58 for .env
python -c "
import json, base58
key = json.load(open('payer.json'))
print(base58.b58encode(bytes(key)).decode())
"
```

### 5. Run

```bash
uvicorn main:app --reload
```

---

## API

### Health check
```
GET /health
```
```json
{
  "status": "ok",
  "solana": "ok",
  "payer_balance_sol": 2.0
}
```

---

### Run a task (async — returns immediately)
```
POST /agents/run
Content-Type: application/json

{
  "task": "What is the capital of France?",
  "payment_amount": 0.001
}
```
```json
{
  "task_id": "uuid",
  "status": "pending"
}
```

Poll for result:
```
GET /agents/{task_id}
```
```json
{
  "task_id": "uuid",
  "status": "completed",
  "result": "Paris",
  "tx_signature": "5xK3...",
  "explorer_url": "https://explorer.solana.com/tx/5xK3...?cluster=devnet",
  "error": null
}
```

---

### Run a task (sync — waits for full result)
```
POST /agents/run/sync
Content-Type: application/json

{
  "task": "Summarise the benefits of blockchain in 2 sentences.",
  "payment_amount": 0.001
}
```
Returns the full `TaskStatusResponse` in one shot — perfect for demos.

---

## Project Structure

```
solana_agent/
├── main.py
├── requirements.txt
├── .env.example
└── app/
    ├── api/
    │   ├── health.py          GET /health
    │   └── agents.py          POST /agents/run, POST /agents/run/sync, GET /agents/{id}
    ├── core/
    │   ├── config.py          Settings from .env
    │   ├── database.py        SQLAlchemy async engine
    │   └── orchestrator.py    Task lifecycle: run → verify → pay
    ├── models/
    │   └── task.py            Task ORM model
    ├── services/
    │   ├── agent_runner.py    OpenAI gpt-4o-mini call
    │   ├── task_service.py    DB CRUD
    │   └── solana_client.py   Send SOL, get balance
    └── utils/
        ├── verifier.py        Result verification gate
        ├── retry.py           Exponential backoff (tenacity)
        ├── idempotency.py     No double payment guard
        └── error_handler.py   Global 500 handler
```

---

## Task Status Flow

```
pending → running → completed  (agent OK + payment sent)
                 → failed      (agent failed, verification failed, or payment failed)
```

Completed tasks always have `tx_signature` + `explorer_url`.
Failed tasks always have `error` describing which step broke.
