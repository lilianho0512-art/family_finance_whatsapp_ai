# Family Finance WhatsApp AI Assistant

[![CI](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml)

Production-ready WhatsApp AI assistant for family finances:
- WhatsApp Cloud API integration (GET verify + POST receive)
- Send "Hi" for an auto-introduction and feature menu
- Text / image / PDF input with automatic OCR
- AI (Ollama / Gemini) + rule-based parsing with two-tier fallback (WhatsApp providers)
- **Telegram bot** — step-by-step prompts (skips AI, asks every field one at a time)
- Auto A/B/C/D follow-up questions, remembering which record each user is currently filling
- Auto-classifies: expense, savings, income, transfer
- In-WhatsApp queries: this month's expenses / savings / income / savings rate / category / merchant
- Bootstrap Dashboard / Records / Accounts / **Loans** / **Reminders** / Reports / **Settings**
- **Multi-currency** — 12 currencies (MYR, SGD, USD, EUR, GBP, JPY, AUD, IDR, THB, PHP, HKD, CNY) with family default + per-record/loan/bill override
- **Loans & payment plans** — track loans and BNPL/installment plans with monthly payment + balance
- **Payment reminders** — auto-fires day-before + day-of reminders for active loans and recurring bills, sent to every enrolled WhatsApp/Telegram number
- Excel monthly export (Summary / Expenses / Savings / Income / Category / Cashflow / Need Review / **Loans**)
- APScheduler: daily summary 22:00, monthly export day-1 01:00, **payment reminders 09:00**
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

> **Telegram is step-by-step.** When `WHATSAPP_PROVIDER=telegram`, the bot
> ignores any free-text content and walks the user through every field one
> at a time: record type → **amount** → category → payment method → account.
> The original message is saved as `source_text` for context but no fields
> are extracted from it. Pre-set greetings (`Hi`, `Menu`, `/start`), undo
> commands (`undo`, `delete #5`), and queries (`this month spent`,
> `summary`) still work the same as on WhatsApp.

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
| Accounts | http://localhost:8000/accounts |
| Loans / payment plans | http://localhost:8000/loans |
| Reminders | http://localhost:8000/reminders |
| Reports | http://localhost:8000/reports |
| Settings (family default currency) | http://localhost:8000/settings |
| Excel monthly report | http://localhost:8000/export/monthly |
| Health | http://localhost:8000/health |

### 4.1 Loans & payment plans (`/loans`)

Track active loans and BNPL / installment plans alongside your monthly cashflow.
Each row stores:

| Field | Notes |
|---|---|
| `kind` | `loan` (mortgage / car / personal) or `installment` (BNPL, credit-card plan) |
| `lender` | Free text — e.g. `Maybank Home Loan`, `Shopee SPayLater` |
| `principal` | Original loan amount |
| `current_balance` | Defaults to principal; update manually as you pay down |
| `monthly_payment` | This month's scheduled payment |
| `interest_rate` | Annual %, optional |
| `term_months` | Optional |
| `start_date`, `payment_due_day` | Optional |
| `status` | `active` or `closed` |

The list page shows two summary cards: **Total monthly payment (active)** and
**Total outstanding (active)** — quick view of how much your loans cost you each
month and how much principal is left.

The monthly Excel export adds a **Loans** sheet with one row per active loan
plus the same totals.

Family-scoped: each row belongs to one family and never leaks across
`/admin` boundaries.

### 4.2 Payment reminders (`/reminders`)

Auto-reminds every enrolled WhatsApp/Telegram number when a loan or
recurring bill is due. Works alongside `/loans` — loans inherit reminders
automatically from `payment_due_day`; bills (utilities, subscriptions, rent)
get tracked in a separate `recurring_expenses` table you manage on this page.

**Schedule.** APScheduler fires at 09:00 family-local time every day and
sends two reminders per cycle:

| Kind | Fires when | Message |
|---|---|---|
| `day_before` | due_date == today + 1 | "🔔 Payment due TOMORROW (date) Bill/Loan: name Amount: …" |
| `day_of`     | due_date == today     | "🔔 Payment due TODAY (date) Bill/Loan: name Amount: …" |

**Dedup.** A `UNIQUE(family_id, target_type, target_id, due_date, kind)`
constraint on `payment_reminders` prevents double-sending. Manual
`POST /reminders/run-now` and the scheduled 09:00 run share the same
dedup, so you can safely re-trigger.

**Date math.** `compute_next_due` handles month rollovers and short
months — `payment_due_day=31` correctly resolves to Feb 28 / Apr 30 /
the actual last day of any month.

**The page** at `/reminders` has three sections:

1. **Upcoming (next 14 days)** — combined view of loans + recurring bills
   with `Today` / `Tomorrow` / `in N days` badges. Today's items are
   highlighted yellow, tomorrow's blue.
2. **Recurring expenses CRUD** — add/edit/pause/delete recurring bills
   inline. Fields: `name`, `amount`, `payment_due_day` (1–31, clamped),
   `category`, `account`, `notes`, `status` (active / paused).
3. **Reminder history** — last 30 reminders sent with status badges.

**▶ Run now** button at the top of the page manually fires today's pass
for this family — useful for testing without waiting for 09:00.

Failures (no Telegram bot token, network error, etc.) keep the dedup
row but flip its status to `failed` so the audit log surfaces them
instead of silently retrying every 9am.

### 4.3 Multi-currency (`/settings`)

Records, loans, and recurring bills are stored in their **native
currency** — no FX conversion. Each family has a default currency that
new rows inherit, and individual rows can override.

**Supported list (12):** `MYR`, `SGD`, `USD`, `EUR`, `GBP`, `JPY`,
`AUD`, `IDR`, `THB`, `PHP`, `HKD`, `CNY`. Symbols rendered as
`RM`, `S$`, `$`, `€`, `£`, `¥`, `A$`, `Rp`, `฿`, `₱`, `HK$`, `¥`.

**Where it's set.** A new `/settings` page lets the family admin pick
the default. Loan + recurring-expense forms have their own currency
dropdown (defaults to family currency, overridable per row).

**Bot flow.**
- **Telegram (step-by-step):** the bot always asks `ask_currency`
  after `ask_amount`. The 12-letter menu lists every supported code.
- **WhatsApp (Meta / Green API):** parsers detect currency hints in
  free text (`"USD 50"`, `"$50 lunch"`, `"S$25 hawker"`, `"RM88"`).
  If no hint is found, the family default applies. The
  `ask_currency` step is skipped because the record already has one.

**Hint precedence.** Symbols match longest-first so
`"S$50"` → SGD (not USD), `"HK$200"` → HKD (not USD).

**Display.** A `money` Jinja filter turns `(amount, currency)` into a
symbol-prefixed string everywhere — dashboard cards, loans table,
reminders list, records, reports, monthly Excel sheets, and
reminder messages.

**Existing data.** The migration backfills old `Family.default_currency`,
`Loan.currency`, and `RecurringExpense.currency` to `MYR` via
`server_default`, so legacy rows keep rendering as RM.

> Reports and totals do **not** convert across currencies. A family
> with mixed-currency loans will see totals summed in the family's
> default symbol — the breakdown column shows each row's own currency
> so the discrepancy is visible.

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
│   ├── models.py                # FinancialRecord / Conversation / Loan / RecurringExpense / PaymentReminder / BugLog
│   ├── schemas.py
│   ├── routers/
│   │   ├── whatsapp.py          # GET verify + POST receive (Meta / Telegram / Green API)
│   │   ├── dashboard.py
│   │   ├── records.py
│   │   ├── accounts.py
│   │   ├── loans.py             # /loans CRUD
│   │   ├── reminders.py         # /reminders CRUD + run-now
│   │   ├── settings.py          # /settings — family default currency
│   │   ├── reports.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   └── export.py
│   ├── services/
│   │   ├── whatsapp_service.py  # send text + download media + retry
│   │   ├── ai_parser.py         # Ollama → Gemini → rule (skipped on Telegram)
│   │   ├── rule_parser.py       # extracts currency hints from free text
│   │   ├── ocr_service.py
│   │   ├── record_service.py
│   │   ├── account_service.py
│   │   ├── loan_service.py      # Loan CRUD, family-scoped
│   │   ├── recurring_expense_service.py  # Recurring-bill CRUD
│   │   ├── reminder_service.py  # compute_next_due, run_daily_reminders, dedup
│   │   ├── question_engine.py   # A/B/C + ask_amount + ask_currency question bank
│   │   ├── conversation_memory.py
│   │   ├── report_service.py
│   │   ├── excel_export.py      # adds Loans sheet
│   │   ├── scheduler_service.py # 22:00 summary, day-1 01:00 export, 09:00 reminders
│   │   ├── auto_bug_checker.py  # @safe decorator + log_bug
│   │   ├── self_healing_service.py
│   │   └── menu_service.py
│   ├── templates/   (Jinja2 + Bootstrap, "money" filter installed per router)
│   ├── static/
│   └── utils/
│       ├── logger.py
│       ├── json_tools.py
│       ├── date_tools.py
│       ├── money_tools.py       # extract_amount; format_money proxies to currency
│       └── currency.py          # SUPPORTED_CURRENCIES, format_money, parse_currency_hint
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
| `families` | Family accounts (with `default_currency`) |
| `users` | Email + bcrypt password + `family_id` |
| `whatsapp_enrollments` | WhatsApp number → family mapping, globally unique |
| `financial_records.family_id` | Each record belongs to a family |
| `conversations.family_id` | Conversation state isolated by family too |
| `bank_accounts` / `account_balances` | Per-family ledger and balance snapshots |
| `loans.family_id` | Loans / installment plans, family-scoped |
| `recurring_expenses.family_id` | Recurring bills (utilities, subscriptions), family-scoped |
| `payment_reminders` | Audit log of sent reminders, with UNIQUE constraint for dedup |

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
