# Inventory Management API – Background Tasks and Email Notifications

FastAPI + SQLAlchemy 2.0 + MySQL + Alembic, layered architecture (routers → services → repositories → models), JWT auth with RBAC, and an automated email notification system built on FastAPI `BackgroundTasks`.

## Project Structure

```
app/
  core/            config, database, security, exceptions
  models/          User, RefreshToken, Category, Supplier, Product, NotificationLog
  schemas/         Pydantic request/response models
  repositories/    database access
  services/        business logic + email_service.py
  background/      tasks.py (background task logic, separate from routers)
  routers/         auth, products, catalog, notifications
  dependencies.py  DI and role checks
alembic/           migrations
tests/             pytest suite (24 tests)
postman/           Postman collection
```

## Setup

1. Create a virtual environment and install dependencies:
   `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in real values. `.env` is git-ignored; never commit it.
3. Create the MySQL database named in `DATABASE_URL`.
4. Apply migrations: `alembic upgrade head`
5. Start the server: `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/docs`

## Environment Variables

| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy URL, e.g. `mysql+pymysql://user:pass@localhost:3306/inventory_db` |
| SECRET_KEY, ALGORITHM | JWT signing |
| ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS | Token lifetimes |
| SMTP_HOST, SMTP_PORT | SMTP server |
| SMTP_USERNAME, SMTP_PASSWORD | SMTP credentials (leave blank for servers without auth) |
| SMTP_USE_TLS | `true` to use STARTTLS (typical for port 587) |
| SMTP_TIMEOUT_SECONDS | Connection timeout so a dead server cannot hang a worker |
| EMAIL_SENDER | From address |
| ADMIN_NOTIFICATION_EMAIL | Recipient of inventory alerts |
| EMAIL_ENABLED | `false` turns delivery off (messages are logged as `skipped`) |
| ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD | Optional: creates the first admin on startup if it does not exist |

## Testing Email in Development

Use a local SMTP catcher so nothing leaves your machine:

- **MailHog / Mailpit**: run it, then set `SMTP_HOST=localhost`, `SMTP_PORT=1025`, `SMTP_USE_TLS=false`, leave username/password blank. View messages in its web UI.
- **Python debug server**: `python -m smtpd -c DebuggingServer -n localhost:1025` (older Python) or use Mailpit.
- **Mailtrap / Gmail**: put the provider's host, port, username and app password in `.env` with `SMTP_USE_TLS=true`.

After starting the API, log in as an admin and call `POST /notifications/test` to confirm delivery.

## How It Works

**Background tasks.** Routers perform the database work through a service, commit, return the response, and queue a task from `app/background/tasks.py` with `BackgroundTasks.add_task`. The tasks run after the response is sent, so SMTP latency never delays the API. Each task opens its own database session, catches every exception, and writes a row to `notification_logs` with status `sent`, `failed` or `skipped`.

**Email service (`app/services/email_service.py`).**
- `send_email`, `send_to_user`, `send_admin_alert`
- `send_registration_confirmation`, `send_low_stock_alert`, `send_stock_notification`
- SMTP and socket errors are wrapped in `EmailDeliveryError`; header values are sanitised against newline injection.

**Low-stock alerts.** A product has `low_stock_notified`. When a create/update/stock adjustment leaves `stock_quantity <= reorder_level` and the flag is false, the flag is set and one alert is queued. Further updates while the product stays low send nothing. When stock rises above the reorder level the flag resets, so the next drop alerts again. If delivery fails, the task resets the flag so the next update retries; a message that was never delivered is never counted as sent.

**Registration emails.** The user is committed before the task is queued. The email contains only the username and a confirmation message, never a password, hash, secret or token. An email failure cannot roll back or duplicate the account; a repeated registration attempt returns `409` and queues nothing.

**Inventory events.** Stock adjustments and product deletions send an administrator notification that names the user who performed the operation.

## Endpoints

| Method | Path | Access |
|---|---|---|
| POST | /auth/register | public (role: employee) |
| POST | /auth/login | public (OAuth2 form) |
| POST | /auth/refresh, /auth/logout | refresh token |
| GET | /auth/me | authenticated |
| POST/PATCH | /products, /products/{id} | admin, manager |
| GET | /products (filters: name, category_id, supplier_id, low_stock_only) | authenticated |
| POST | /products/{id}/adjust-stock | authenticated |
| DELETE | /products/{id} | admin |
| CRUD | /categories, /suppliers | read: authenticated, write: manager/admin, delete: admin |
| GET | /notifications/logs?status=failed | admin |
| POST | /notifications/test | admin |

## Running Tests

`pytest`

The suite uses a temporary SQLite database and replaces the SMTP delivery step, so no real emails are sent.

## Security Notes

- Credentials live only in `.env`; `.env.example` holds placeholders.
- Passwords are hashed with Argon2; refresh tokens are rotated and revocable.
- Emails never contain secrets.
