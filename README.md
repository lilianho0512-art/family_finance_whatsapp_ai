# Family Finance WhatsApp AI Assistant

[![CI](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml)

Production-ready WhatsApp AI assistant for family finances:
- WhatsApp Cloud API integration (GET verify + POST receive)
- Send "Hi" for an auto-introduction and feature menu
- Text / image / PDF input with automatic OCR
- AI (Ollama / Gemini) + rule-based parsing with two-tier fallback
- Auto A/B/C/D follow-up questions, remembering which record each user is currently filling
- Auto-classifies: expense, savings, income, transfer
- In-WhatsApp queries: this month's expenses / savings / income / savings rate / category / merchant
- Bootstrap Dashboard / Records / Reports
- Excel monthly export (Summary / Expenses / Savings / Income / Category / Cashflow / Need Review)
- APScheduler runs at 22:00 daily and 01:00 on the first of each month
- Self-healing: missing folders auto-created, AI offline → rule_parser, JSON repair, WhatsApp send retried 3x, all errors written to logs + bug_logs

---

## 1. Quick start

### 1.1 Windows one-shot

```bat
run.bat
```

This will: create the venv → install dependencies → run health_check → start uvicorn on port 8000.

### 1.2 Manual

```bash
python -m venv venv
venv\Scripts\activate           # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
python health_check.py
uvicorn app.main:app --reload --port 8000
```

### 1.3 Docker

```bash
docker compose up -d --build
```

### 1.4 OCR dependency (for image / screenshot recognition)

- **Windows**: download from https://github.com/UB-Mannheim/tesseract/wiki, install, then in `.env` set:
  ```
  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```
- **macOS**: `brew install tesseract tesseract-lang`
- **Linux**: `sudo apt install tesseract-ocr`

> The app still runs without Tesseract — images just fall into `need_review` for manual entry.

---

## 2. Connecting WhatsApp (pick one provider)

Set `WHATSAPP_PROVIDER=meta` or `WHATSAPP_PROVIDER=greenapi` in `.env` to switch.

### 2A. Green API (recommended: simple sign-up, scan QR, no Meta console)

1. Sign up at https://green-api.com (email is enough; the free Developer instance works)
2. In the console, create an Instance → grab `idInstance` + `apiTokenInstance`
3. Open WhatsApp on your phone and scan the QR code to attach your account (this number becomes the bot's sender)
4. Fill `.env`:
   ```
   WHATSAPP_PROVIDER=greenapi
   GREENAPI_INSTANCE_ID=<idInstance>
   GREENAPI_TOKEN=<apiTokenInstance>
   ```
5. Start the service: `run.bat` → expose with ngrok: `ngrok http 8000`
6. Register the webhook URL in one shot:
   ```
   python setup_greenapi_webhook.py https://<your-ngrok>.ngrok-free.app
   ```
7. Send "Hi" on WhatsApp to the linked number → you should get the menu back

> Heads up: Green API uses the (unofficial) WhatsApp Web protocol, which violates Meta's ToS — there's a real ban risk. **Use a backup number, not your main one.**

### 2B. Meta WhatsApp Cloud API

1. Go to [Meta for Developers](https://developers.facebook.com/) → create a Business App
2. Add the **WhatsApp** product → open **API Setup**
3. Collect three values:
   - `Phone Number ID` → put in `.env` as `WHATSAPP_PHONE_NUMBER_ID`
   - A `Temporary access token` (24h) or a long-lived System User token → `WHATSAPP_TOKEN`
   - A `WHATSAPP_VERIFY_TOKEN` you make up (any string, e.g. `my_verify_token`)
4. **Add recipient phone number**: add your test phone number to the allowed list
5. **Configuration → Webhook**:
   - Callback URL: `https://<your-public-domain>/webhook`
   - Verify Token: must match `.env`
   - Click **Verify and save** (the app must be running for verification to succeed)
6. **Webhook Fields**: tick `messages`

### 2.1 Expose local port 8000 with ngrok

```bash
ngrok http 8000
```

ngrok gives you a public URL like `https://xxxx-xx-xx.ngrok-free.app`.
Use it as the Meta webhook callback URL:
```
https://xxxx-xx-xx.ngrok-free.app/webhook
```

---

## 3. Test flows

### 3.1 Hi menu
On WhatsApp, send:
```
Hi
```
Expected reply:
```
Hi, I'm your family finance AI assistant 👋
I can record:
A. Family expense
B. Family savings
...
```

### 3.2 Plain text record
Send:
```
Today Tesco RM88
```
Expected:
```
Here's what I picked up:
Merchant: Tesco
Amount: MYR 88.00
Date: YYYY-MM-DD

Pick a record type:
A. Family expense
...
```
Reply `A` → asked for category → `A` → asked for payment method → `D` → confirmed ✅

### 3.3 Savings
```
Today saved RM500
```
→ classified as savings → asks for the savings account → choose `A` (Maybank) → ✅

### 3.4 Income
```
Salary RM3800
```
→ classified as income with source = Salary → ✅ (nothing else needed)

### 3.5 Queries
- `How much did I spend this month?`
- `How much did I save this month?`
- `This month income`
- `Savings rate`
- `Today expense`
- `Baby category`
- `This month Tesco spent`
- `export` → generates the Excel monthly report

### 3.6 Image / PDF
Send a receipt photo on WhatsApp directly — it gets OCR'd, parsed by AI, then asked about.

### 3.7 Simulate the webhook with curl (no WhatsApp needed)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d "{\"entry\":[{\"changes\":[{\"value\":{\"messages\":[{\"from\":\"60123456789\",\"id\":\"test1\",\"type\":\"text\",\"text\":{\"body\":\"Hi\"}}]}}]}]}"
```

---

## 4. Dashboard / reports

Open in the browser after startup:

| Page | URL |
|---|---|
| Dashboard | http://localhost:8000/ |
| Records | http://localhost:8000/records |
| Reports | http://localhost:8000/reports |
| Excel monthly report | http://localhost:8000/export/monthly |
| Health | http://localhost:8000/health |

---

## 5. Self-healing behaviors

| Scenario | What happens |
|---|---|
| AI output wrapped in ` ```json ` markdown | `extract_json` strips the fences |
| AI JSON has trailing commas / single quotes | Auto-cleaned and re-parsed |
| Ollama offline | Falls back to `rule_parser` |
| Gemini not configured | Skipped — Ollama / rule only |
| Tesseract missing or OCR fails | Marked as `need_review` |
| WhatsApp send fails | Backoff retry 3× (2 / 4 / 8 seconds) |
| Webhook parsing throws | Logged to `bug_logs`, still returns 200 to avoid Meta retry storms |
| Folder missing | `ensure_folders()` recreates it on startup |
| Amount detection fails | Follow-up question (A/B/C flow) catches it |
| Date detection fails | Falls back to `today` |
| All errors | Written to `logs/app.log` + the `bug_logs` table |

---

## 6. Project layout

```
family_finance_whatsapp_ai/
├── app/
│   ├── main.py                  # FastAPI entrypoint
│   ├── config.py
│   ├── database.py
│   ├── models.py                # FinancialRecord / Conversation / BugLog
│   ├── schemas.py
│   ├── routers/
│   │   ├── whatsapp.py          # GET verify + POST receive
│   │   ├── dashboard.py
│   │   ├── records.py
│   │   ├── reports.py
│   │   └── export.py
│   ├── services/
│   │   ├── whatsapp_service.py  # send text + download media + retry
│   │   ├── ai_parser.py         # Ollama → Gemini → rule
│   │   ├── rule_parser.py
│   │   ├── ocr_service.py
│   │   ├── record_service.py
│   │   ├── question_engine.py   # A/B/C question bank + answer parsing
│   │   ├── conversation_memory.py
│   │   ├── report_service.py
│   │   ├── excel_export.py
│   │   ├── scheduler_service.py
│   │   ├── auto_bug_checker.py  # @safe decorator + log_bug
│   │   ├── self_healing_service.py
│   │   └── menu_service.py
│   ├── templates/   (Jinja2 + Bootstrap)
│   ├── static/
│   └── utils/
│       ├── logger.py
│       ├── json_tools.py
│       ├── date_tools.py
│       └── money_tools.py
├── tests/test_smoke.py
├── uploads/  output/  logs/  data/
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.bat
├── health_check.py
└── README.md
```

---

## 7. Database + Alembic migrations

### 7.1 SQLite (default / development)

```
DATABASE_URL=sqlite:///./data/family_finance.db
```

No extra steps — `alembic upgrade head` runs automatically on startup.

### 7.2 PostgreSQL (recommended for production)

**1) Run a Postgres instance**

Use the bundled docker-compose profile:

```bash
docker compose --profile postgres up -d db
```

Or install Postgres yourself and create the database:

```sql
CREATE DATABASE family_finance;
CREATE USER family WITH ENCRYPTED PASSWORD 'family_secret';
GRANT ALL PRIVILEGES ON DATABASE family_finance TO family;
```

**2) Switch the URL in `.env`**

```
DATABASE_URL=postgresql+psycopg2://family:family_secret@localhost:5432/family_finance
```
(Container-to-container: replace `localhost` with `db`.)

**3) Run migrations**

```bash
alembic upgrade head
```

Or start app + db together:

```bash
docker compose --profile postgres up -d --build
```

### 7.3 Alembic cheat sheet

```bash
alembic upgrade head                                # upgrade to latest
alembic current                                     # show current version
alembic history --verbose                           # list all migrations
alembic revision --autogenerate -m "add family_id"  # generate after editing models.py
alembic downgrade -1                                # roll back one step
```

Migration files live in `alembic/versions/`. `alembic/env.py` reads `DATABASE_URL` from `.env` automatically — no need to edit `alembic.ini`.

### 7.4 Multi-family SaaS (enabled)

Multi-tenant isolation + JWT login is on:

| Table | Purpose |
|---|---|
| `families` | Family accounts |
| `users` | Email + bcrypt password + `family_id` |
| `whatsapp_enrollments` | WhatsApp number → family mapping, globally unique |
| `financial_records.family_id` | Each record belongs to a family |
| `conversations.family_id` | Conversation state isolated by family too |

**First-time setup:**

1. After startup, hit http://localhost:8000/ — you're redirected to `/register`
2. Fill in family name + email + password + your WhatsApp number (auto-linked to this family)
3. After login you can add more WhatsApp numbers (family members) on the dashboard

**WhatsApp routing logic:**
- Incoming message → look up `whatsapp_enrollments` → resolve `family_id` → all writes/queries are scoped to that family
- An unbound number → onboarding prompt directing them to `/register`

**Auth endpoints:**

| Method + path | Purpose |
|---|---|
| `GET /login`, `POST /login` | HTML form login (sets cookie) |
| `GET /register`, `POST /register` | Create family + admin |
| `GET/POST /auth/logout` | Clear cookie |
| `POST /auth/login` (form) | Returns JSON `{access_token}` for API/CLI clients |
| `GET /auth/me` | Current user + family info (cookie or Bearer) |
| `POST /auth/whatsapp` | Add a number to the current family |
| `DELETE /auth/whatsapp/{id}` | Remove a number from the current family (cross-family forbidden) |

**JWT settings (in `.env`):**
```
JWT_SECRET=<32+ char random string>     # MUST change for production!
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080                 # 7 days
```

Generate a strong random secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Two supported credentials:**
- Browser → httponly cookie `ff_token` (set automatically on login)
- API client → `Authorization: Bearer <jwt>` (obtained via `POST /auth/login`)

**Security defenses:**
- Passwords hashed with bcrypt
- WhatsApp numbers globally unique (no shared numbers across families)
- Cross-family operations all return 404/409 (end-to-end tested)
- Webhook always resolves family from `from_number` first → unbound numbers can't write anything

### 7.5 Admin panel (cross-family)

A user with `users.is_superadmin = True` can access `/admin` and see all families, all WhatsApp numbers, and bug logs.
A normal family admin (family admin role) can only see their own family.

**Promote a superadmin (CLI):**

```bash
python make_superadmin.py alice@example.com           # promote
python make_superadmin.py alice@example.com --revoke  # revoke
python make_superadmin.py --list                      # list superadmins
```

**Admin routes:**

| Path | Content |
|---|---|
| `GET /admin` | Overview: family / user / number / record / bug counts + recent errors |
| `GET /admin/family/{id}` | Any family's detail: members, numbers, last 200 records |
| `GET /admin/bugs` | Global bug logs (last 200) |

A non-superadmin hitting `/admin*` gets redirected to `/` if logged in, `/login` otherwise.

---

## 8. Unit tests

```bash
pip install pytest
pytest tests/ -v
```

---

## 9. Common errors

| Error | Fix |
|---|---|
| `Webhook verification failed` | `.env` `WHATSAPP_VERIFY_TOKEN` must match what you put in the Meta console |
| WhatsApp replies don't go out | Check `WHATSAPP_TOKEN` (System User tokens don't expire), `WHATSAPP_PHONE_NUMBER_ID`, and that the recipient is on the allowed list |
| Image OCR returns empty | Tesseract isn't installed, or `TESSERACT_CMD` path is wrong |
| Ollama slow / unavailable | App auto-falls back to rule_parser; no impact on usage |
| No logs visible | Check `logs/app.log`, or query the `bug_logs` table in SQLite |
