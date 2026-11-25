# Secure Rental System

## Demo login credentials

These accounts are for local/demo use only. Change or remove them before
deploying the application to a shared or production environment.

| Role | Email | Password |
| --- | --- | --- |
| Landlord | `landlord@mwangaza.co.ke` | `AdminPass2026!` |
| Caretaker | `caretaker@mwangaza.co.ke` | `Caretaker2026!` |
| Tenant | `tenant101@mwangaza.co.ke` | `TenantPass2026!` |
| Landlord | `landlord2@mwangaza.co.ke` | `LandlordDemo2026!` |
| Caretaker | `caretaker2@mwangaza.co.ke` | `CaretakerDemo2026!` |
| Tenant | `tenant102@mwangaza.co.ke` | `Tenant102Demo2026!` |
| Tenant | `tenant103@mwangaza.co.ke` | `Tenant103Demo2026!` |
| Tenant | `tenant104@mwangaza.co.ke` | `Tenant104Demo2026!` |
| Tenant | `tenant105@mwangaza.co.ke` | `Tenant105Demo2026!` |

Passwords are stored as bcrypt hashes, not plaintext, in the database.

The additional tenant accounts have demo leases, rent charges, and sample
payments across units A02, B01, B02, and C01. The extra landlord and
caretaker accounts are useful for testing role-based access.

## Running locally

The Docker Compose setup starts MySQL and the Flask application:

```powershell
docker compose up --build
```

Open <http://127.0.0.1:5000/> and use one of the demo accounts above.

For a local SQLite-only run, set `DATABASE_URL=sqlite:///dev.db` before
starting Flask. SQLite is suitable for a local demo, not production.

The canonical SQL seed data is in [`db/seed_data.sql`](db/seed_data.sql).

## IntaSend M-Pesa payments

The tenant statement includes an STK Push payment form. Configure these
environment variables before enabling it:

```text
INTASEND_SECRET_KEY=your_sandbox_or_live_secret_key
INTASEND_WEBHOOK_CHALLENGE=challenge_value_from_intasend
INTASEND_BASE_URL=https://api.intasend.com/api/v1
```

The collection webhook endpoint is:

```text
POST /finance/payments/intasend/webhook
```

Expose the Flask application through HTTPS and register that public webhook
URL in the IntaSend dashboard. Use sandbox credentials and test phone numbers
before production. Never commit secret keys.
