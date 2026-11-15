import csv
import hmac
import io
import math
import os
import secrets
import sqlite3
import time
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, redirect,
                   render_template, request, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

DB_PATH = os.environ.get("DB_PATH", "/data/overtime.db")
USERNAME = os.environ.get("APP_USERNAME", "")
PASSWORD_HASH = os.environ.get("APP_PASSWORD_HASH", "")
PASSWORD_PLAIN = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"

MAX_FAILS = 5              # failed logins allowed per IP ...
LOCK_SECONDS = 15 * 60     # ... within this window
MAX_ENTRY_MIN = 24 * 60    # sanity limit per entry

if not SECRET_KEY or not USERNAME or not (PASSWORD_HASH or PASSWORD_PLAIN):
    raise RuntimeError(
        "Set SECRET_KEY, APP_USERNAME and APP_PASSWORD_HASH (or APP_PASSWORD)."
    )

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


# ---------- database ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_date TEXT NOT NULL,
                minutes INTEGER NOT NULL CHECK (minutes > 0),
                action TEXT NOT NULL DEFAULT 'add' CHECK (action IN ('add', 'take')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(work_date);
            CREATE TABLE IF NOT EXISTS login_failures (
                ip TEXT NOT NULL,
                ts REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fail_ip ON login_failures(ip, ts);
        """)
        db.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in db.execute("PRAGMA table_info(entries)")}
        if "action" not in columns:
            db.execute(
                "ALTER TABLE entries ADD COLUMN action TEXT NOT NULL DEFAULT 'add' "
                "CHECK (action IN ('add', 'take'))"
            )
        db.commit()
    finally:
        db.close()


init_db()


# ---------- helpers ----------

def fmt_duration(minutes):
    minutes = int(minutes)
    sign = "-" if minutes < 0 else ""
    h, m = divmod(abs(minutes), 60)
    if h and m:
        return f"{sign}{h}h {m}m"
    if h:
        return f"{sign}{h}h"
    return f"{sign}{m}m"


def fmt_decimal(minutes):
    return f"{minutes / 60:.2f} h"


def fmt_day(iso):
    return date.fromisoformat(iso).strftime("%a %d/%m")


app.jinja_env.filters["dur"] = fmt_duration
app.jinja_env.filters["dec"] = fmt_decimal
app.jinja_env.filters["day"] = fmt_day


def parse_amount(raw, label):
    raw = (raw or "").strip().replace(",", ".")
    if raw == "":
        return 0.0
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} can't be negative.")
    return value


def parse_entry_form(form):
    """Returns (iso_date, total_minutes, action) or raises ValueError."""
    try:
        work_date = date.fromisoformat(form.get("date", "").strip())
    except ValueError:
        raise ValueError("Pick a valid date.")
    hours = parse_amount(form.get("hours"), "Hours")
    minutes = parse_amount(form.get("minutes"), "Minutes")
    total_f = hours * 60 + minutes
    if total_f > MAX_ENTRY_MIN:
        raise ValueError("That's more than 24 hours. Check the numbers.")
    total = math.floor(total_f + 0.5)
    if total <= 0:
        raise ValueError("Enter some time in hours, minutes or both.")
    action = form.get("action", "")
    if action not in ("add", "take"):
        raise ValueError("Choose whether to add or take overtime.")
    return work_date.isoformat(), total, action


def client_ip():
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "unknown"


def is_locked(ip):
    db = get_db()
    db.execute("DELETE FROM login_failures WHERE ts < ?",
               (time.time() - LOCK_SECONDS,))
    n = db.execute("SELECT COUNT(*) FROM login_failures WHERE ip = ?",
                   (ip,)).fetchone()[0]
    db.commit()
    return n >= MAX_FAILS


def check_credentials(username, password):
    user_ok = hmac.compare_digest(username.encode(), USERNAME.encode())
    if PASSWORD_HASH:
        pass_ok = check_password_hash(PASSWORD_HASH, password)
    else:
        pass_ok = hmac.compare_digest(password.encode(), PASSWORD_PLAIN.encode())
    return user_ok and pass_ok


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- request hooks ----------

@app.before_request
def csrf_protect():
    if request.endpoint in ("healthz", "static"):
        return
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not hmac.compare_digest(sent, session.get("csrf", "")):
            abort(400)


@app.context_processor
def inject_csrf():
    return {"csrf_token": session.get("csrf", "")}


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    if request.endpoint != "static":
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------- routes ----------

@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("auth"):
        return redirect(url_for("log"))
    error = None
    status = 200
    if request.method == "POST":
        ip = client_ip()
        if is_locked(ip):
            error = "Too many failed attempts. Try again in 15 minutes."
            status = 429
        elif check_credentials(request.form.get("username", ""),
                               request.form.get("password", "")):
            db = get_db()
            db.execute("DELETE FROM login_failures WHERE ip = ?", (ip,))
            db.commit()
            session.clear()
            session["csrf"] = secrets.token_urlsafe(32)
            session["auth"] = True
            session.permanent = True
            return redirect(url_for("log"))
        else:
            db = get_db()
            db.execute("INSERT INTO login_failures (ip, ts) VALUES (?, ?)",
                       (ip, time.time()))
            db.commit()
            time.sleep(0.6)
            error = "Wrong username or password."
            status = 401
    return render_template("login.html", error=error), status


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def log():
    form = {"date": date.today().isoformat(), "hours": "", "minutes": "", "action": "add"}
    error = None
    if request.method == "POST":
        form = {k: request.form.get(k, "") for k in ("date", "hours", "minutes", "action")}
        try:
            iso, total, action = parse_entry_form(request.form)
        except ValueError as exc:
            error = str(exc)
        else:
            db = get_db()
            db.execute("INSERT INTO entries (work_date, minutes, action) VALUES (?, ?, ?)",
                       (iso, total, action))
            db.commit()
            signed_total = -total if action == "take" else total
            flash(f"Saved {fmt_duration(signed_total)} on {fmt_day(iso)}.")
            return redirect(url_for("log"))
    return render_template("log.html", form=form, error=error, editing=None,
                           autofill_today=(request.method == "GET"))


@app.route("/edit/<int:entry_id>", methods=["GET", "POST"])
@login_required
def edit(entry_id):
    db = get_db()
    row = db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        abort(404)
    error = None
    if request.method == "POST":
        form = {k: request.form.get(k, "") for k in ("date", "hours", "minutes", "action")}
        try:
            iso, total, action = parse_entry_form(request.form)
        except ValueError as exc:
            error = str(exc)
        else:
            db.execute("UPDATE entries SET work_date = ?, minutes = ?, action = ? WHERE id = ?",
                       (iso, total, action, entry_id))
            db.commit()
            signed_total = -total if action == "take" else total
            flash(f"Updated to {fmt_duration(signed_total)} on {fmt_day(iso)}.")
            return redirect(url_for("overview"))
    else:
        h, m = divmod(row["minutes"], 60)
        form = {"date": row["work_date"], "action": row["action"], "hours": str(h) if h else "",
                "minutes": str(m) if m else ""}
    return render_template("log.html", form=form, error=error,
                           editing=entry_id, autofill_today=False)


@app.route("/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete(entry_id):
    db = get_db()
    db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    db.commit()
    flash("Entry deleted.")
    return redirect(url_for("overview"))


@app.route("/overview")
@login_required
def overview():
    rows = get_db().execute(
        "SELECT id, work_date, action, "
        "CASE WHEN action = 'take' THEN -minutes ELSE minutes END AS minutes FROM entries "
        "ORDER BY work_date DESC, id DESC").fetchall()
    months = []
    for row in rows:
        key = row["work_date"][:7]
        if not months or months[-1]["key"] != key:
            year, month = key.split("-")
            months.append({"key": key,
                           "label": f"{MONTHS[int(month) - 1]} {year}",
                           "total": 0, "entries": []})
        months[-1]["entries"].append(row)
        months[-1]["total"] += row["minutes"]
    grand = sum(m["total"] for m in months)
    return render_template("overview.html", months=months, grand=grand)


@app.route("/export.csv")
@login_required
def export_csv():
    rows = get_db().execute(
        "SELECT work_date, CASE WHEN action = 'take' THEN -minutes ELSE minutes END AS minutes "
        "FROM entries "
        "ORDER BY work_date, id").fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "minutes", "hours"])
    for r in rows:
        writer.writerow([r["work_date"], r["minutes"], f"{r['minutes'] / 60:.2f}"])
    return Response(out.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": 'attachment; filename="overtime.csv"'})
