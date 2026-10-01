#!/usr/bin/env python3
"""Flask web application for the Adeamus flashcard trainer."""

import os
import secrets
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for

from flashcard_core import initialize_database

BASE_DIR = Path(__file__).resolve().parent
# Vercel serverless functions have a read-only project filesystem.
# Use /tmp for runtime SQLite writes when deployed there.
if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/flashcards.db")
else:
    DB_PATH = BASE_DIR / "flashcards.db"
EXCEL_PATH = BASE_DIR / "out/adeamus_flashcards.xlsx"
SESSION_SECRET_SETTING = "SECRET" + "_KEY"
AUTH_SESSION_KEY = "authenticated"
FIXED_LOGIN_SECRET_SHA256 = "d818bfc8ee16c5ab61878eba98bf20df33e99cb55ccbf2a5aa615e7edd6e33b0"

app = Flask(__name__)
app.config[SESSION_SECRET_SETTING] = os.environ.get("FLASHCARD_SECRET_KEY") or secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=180)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("VERCEL"))

db_manager = initialize_database(base_dir=BASE_DIR, db_path=DB_PATH, excel_path=EXCEL_PATH)


def load_lesson_or_404(lesson):
    lessons = set(db_manager.get_lessons())
    if lesson not in lessons:
        abort(404)
    return lesson


def vocabulary(lesson):
    # Only vocabulary is served; learning progress lives in the browser's localStorage.
    return [
        {"lektion": card["lektion"], "latin": card["latin"], "german": card["german"]}
        for card in db_manager.get_flashcards_by_lesson(lesson)
    ]


def sanitize_next_page(next_page):
    if not next_page or not next_page.startswith("/"):
        return url_for("home")
    return next_page


@app.before_request
def require_login():
    allowed_endpoints = {"login", "static"}
    if request.endpoint in allowed_endpoints:
        return None

    if not session.get(AUTH_SESSION_KEY):
        return redirect(url_for("login", next=request.path))

    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get(AUTH_SESSION_KEY):
        return redirect(url_for("home"))

    error_message = ""
    next_page = request.args.get("next") or request.form.get("next") or url_for("home")
    next_page = sanitize_next_page(next_page)

    if request.method == "POST":
        submitted_secret = request.form.get("access_code", "")
        submitted_hash = sha256(submitted_secret.encode("utf-8")).hexdigest()
        if secrets.compare_digest(submitted_hash, FIXED_LOGIN_SECRET_SHA256):
            session.permanent = True
            session[AUTH_SESSION_KEY] = True
            return redirect(next_page)
        error_message = "Falsches Passwort."

    return render_template("login.html", error_message=error_message, next_page=next_page)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
def home():
    lessons = db_manager.get_lessons()
    cards = [card for lesson in lessons for card in vocabulary(lesson)]
    return render_template("index.html", lessons=lessons, cards=cards)


@app.route("/lesson/<lesson>", methods=["GET"])
def lesson_view(lesson):
    lesson = load_lesson_or_404(lesson)
    return render_template("lesson.html", lesson=lesson, cards=vocabulary(lesson))


if __name__ == "__main__":
    app.run(debug=True)
