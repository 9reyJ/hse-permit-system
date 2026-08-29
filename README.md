#### Video Demo: https://youtu.be/dcjksQJeB5o

# HSE Permit System

A web application for managing Health, Safety & Environment (HSE) work permits.
Employees ("requesters") submit permits for high-risk work, EHS staff approve or
reject them, and admins manage roles. Built with Flask + SQLAlchemy + SQLite.

---

## 1. What this project does

A work-permit workflow is basically:

- A **requester** fills in the type of hazardous work, where it happens, and
  when it is valid, then **submits** it.
- An **EHS** officer **approves** or **rejects** it.
- The requester later **closes** the permit once the work is done.

Every transition is recorded so there is an auditable trail of who did what and
when, that audit trail is the whole point of an HSE system.

### Roles

| Role       | What they can do                                            |
|------------|-------------------------------------------------------------|
| `requester`| Submit permits, view their own permits, close their permits |
| `ehs`      | See all permits, approve / reject them                      |
| `admin`    | Promote/demote user roles                                   |

---

## 2. Tech stack & why

| Layer      | Choice                 | Why                                                                                                   |
|------------|------------------------|-------------------------------------------------------------------------------------------------------|
| Web        | **Flask**              | Small, single-file-able, and has first-party session/redirect helpers the auth decorators rely on.     |
| ORM        | **SQLAlchemy** (2.0)   | Declarative models that map cleanly to the tables above and give DB-agnostic queries.                  |
| DB         | **SQLite** (`permits.db`) | Zero-config, file-based, ideal for a single-site internal tool.    |
| Sessions   | **Flask-Session** (filesystem) | Sessions stored on the server instead of signed cookies       |

---

## 3. Project layout

```
hse-permit-system/
├── app.py            # All Flask routes + app config (the whole web layer)
├── auth.py           # login_required / role_required decorators
├── models.py         # SQLAlchemy models: Employee, Permit, PermitAction
├── database.py       # Engine, session factory, init_db()
├── init_db.py        # Script that creates tables (run once)
├── seed.py           # Script that inserts demo data
├── requirements.txt  # Python dependencies
├── permits.db        # SQLite database (gitignored)
├── static/           # CSS, JS, favicon, image assets
└── templates/        # Jinja2 HTML templates
```

---

## 4. Sessions & caching

**Server-side sessions.** The app uses `SESSION_TYPE = "filesystem"` from
Flask-Session. Why not the default signed cookie?

- Signed cookies are client-readable. For an HSE/approval workflow you do not
  want role or workflow state living on the user's browser where it can be
  inspected or tampered with.
- Filesystem sessions keep the data on the server. (Production would use a
  real store — Redis or DB — but filesystem is fine for a single box.)

**Secrets.** `SECRET_KEY` comes from `.env` (which is gitignored).

---

## 5. Auth model

`auth.py` provides two decorators that wrap routes (from the flask CS50x lectures):

- `@login_required` — redirects to `/login` if `session["user_id"]` is missing.
- `@role_required("requester", "ehs", ...)` — redirects to `/` if the logged-in
  user's role isn't in the allowed list.

They are stacked on routes like this:

```python
@app.route("/")
@role_required("requester", "ehs")   # runs first: checks role
@login_required                      # runs second: checks logged in
def index(): ...
```

### Registration behavior

New accounts are created with `role = "requester"` (the least-privileged role).
Elevation to `ehs` / `admin` happens only via the admin role-management page.
This is least-privilege-by-default: nobody signs up with admin rights.

---

## 6. Permit lifecycle & data integrity

### Statuses (on the `Permit` model)
`draft` → `submitted` → `approved` | `rejected` → `closed`

- Creating a permit sets status to `submitted` and immediately writes a
  `submitted` `PermitAction` ("Initial Submission").
- EHS approve/reject sets the permit status and logs the matching action.
- The requester can `close` the permit, logging a `closed` action.

### Actions (on the `PermitAction` model)
Every status change also creates a `PermitAction` row recording `permit_id`,
`actor_id` (who did it), `action`, optional `comment`, and timestamp. This is
the immutable audit log.

### DB-level guarantees (CHECK constraints in `models.py`)

These are enforced by SQLite, not just the UI, so bad data can't slip in:

- `role IN ('requester','ehs','admin')`
- `status IN ('draft','submitted','approved','rejected','closed')`
- `type IN ('hot_work','confined_space','electrical','work_at_height','excavation','cold_work','lifting')`
- `valid_until > valid_from` — a permit's validity window must be sane
- `action IN ('submitted','approved','rejected','closed')`

Foreign keys are turned **on** via a connection PRAGMA in `database.py`:

```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor.execute("PRAGMA foreign_keys=ON")
```

---

## 7. Setup & running

> Prereq: Python 3.10+ (uses `str | None` union syntax).

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the .env file (required — app reads SECRET_KEY from here)
#    .env is gitignored; generate a key, e.g.:
#      python -c "import secrets; print(secrets.token_hex(32))"
#    then put it in .env as:  SECRET_KEY=<the generated hex>

# 4. Initialize the database (creates tables in permits.db)
python init_db.py

# 5. (Optional) seed demo data — note: seed.py hardcodes a username "aissa",
#    so register that user first, then run it.
python seed.py

# 6. Run the app
flask run                # or: python app.py
```

Then open http://127.0.0.1:5000 in a browser. Register an account (you start as
`requester`). To test EHS/admin behavior, either promote your own user via the
admin page, or flip the role directly in the DB for local testing.

---

## 8. Known notes / rough edges (read before you copy this)

Be honest with yourself when you use this project as a reference — these are
real quirks in the current code:

- **`seed.py` uses space-separated types** (`"hot work"`, `"confined space"`)
  which do NOT match the model's CHECK constraint values (`"hot_work"`,
  `"confined_space"`, underscore-separated). The seeds will fail the
  constraint. If you use it, fix the values first.
- **`requirements.txt` has typos / duplicates** (`ask-Session` instead of
  `Flask-Session`; `pytz`, `requests` repeated). Clean it before installing.
- **`/permits/<id>/action` reads `request.form` at the top**, so a `GET` to
  that route will fail; it's effectively POST-only despite allowing GET.
- **No permission check** on the "close" path — any logged-in user who reaches
  it can close any permit (the code only checks that a role is in
  `("ehs","requester")`, not that the permit belongs to them).
- **`permits.db` is gitignored**, so a fresh clone starts empty; run
  `init_db.py` first.
- **`_heart_validator.png` / `favicon.ico`** are static assets, referenced by
  templates.

---

## 9. Moving to production

This is explicitly a dev/demo setup. Before real use:

1. **Database** — swap SQLite for PostgreSQL/MySQL (SQLAlchemy makes this mostly
   a connection-string change, but CHECK constraints / types need review).
2. **Sessions** — filesystem sessions don't survive multi-instance or restart;
   use Redis or the DB via Flask-Session config.
3. **HTTPS + secrets** — serve behind a real web server (gunicorn + nginx) with
   TLS, and rotate `SECRET_KEY`.
4. **Authorization tightening** — add ownership checks (a requester should only
   see/close their own permits) rather than role-only checks.

---
