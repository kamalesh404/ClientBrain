# Deploy ClientBrain (Phase 2)

## Option A — local (fastest demo)
```bash
cp .env.example .env
# MASTER_API_KEY=cb_admin_change-me  (change it)
docker compose up --build
# web http://localhost:3000  api http://localhost:8000/docs
```

## Option B — Render (recommended freelance hosting)
1. Push to GitHub (done).
2. Render → New → Blueprint → select this repo (uses `render.yaml` if present,
   else create 2 services manually):
   - `clientbrain-db`: PostgreSQL 16 (enables pgvector via `CREATE EXTENSION vector`)
   - `clientbrain-api`: Docker → `apps/api`, env `DATABASE_URL` from DB,
     `MASTER_API_KEY`, `OPENAI_API_KEY`, Razorpay/Stripe keys.
   - `clientbrain-web`: Node → `apps/web`, env `NEXT_PUBLIC_API_URL=<api url>`.
3. After deploy, create a client key:
```bash
curl -X POST $API/v1/admin/keys -H "X-API-Key: $MASTER_API_KEY" \
  -H "Content-Type: application/json" -d '{"workspace":"client1","plan":"pro"}'
```

## Option C — VPS (₹500/mo, max margin)
```bash
docker compose -f docker-compose.yml up -d --build
```

## Razorpay live checklist
- Dashboard → Settings → API keys → put in `.env`
- Webhooks → Add `https://<api>/v1/billing/webhook/razorpay`, secret → `.env`
- Test with ₹1 plan, then switch `BILLING_ENABLED=true`.

## Stripe live checklist
- Developers → API keys → `.env`, Webhook endpoint
  `https://<api>/v1/billing/webhook/stripe` → `.env`.
