#!/usr/bin/env python3
"""Flask web application for the Adeamus flashcard trainer."""

import os
import secrets
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for

from flashcard_core import SpacedRepetitionEngine, initialize_database

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flashcards.db"
EXCEL_PATH = BASE_DIR / "out/adeamus_flashcards.xlsx"
RECENT_SESSION_KEY = "recent_cards"
CURRENT_CARD_KEY = "current_cards"
SESSION_SECRET_SETTING = "SECRET" + "_KEY"

app = Flask(__name__)
app.config[SESSION_SECRET_SETTING] = os.environ.get("FLASHCARD_SECRET_KEY") or secrets.token_hex(32)

db_manager = initialize_database(base_dir=BASE_DIR, db_path=DB_PATH, excel_path=EXCEL_PATH)


def get_recent_cards_store():
    return session.setdefault(RECENT_SESSION_KEY, {})


def get_current_cards_store():
    return session.setdefault(CURRENT_CARD_KEY, {})


def load_lesson_or_404(lesson):
    lessons = set(db_manager.get_lessons())
    if lesson not in lessons:
        abort(404)
    return lesson


def choose_or_restore_card(lesson):
    current_cards = get_current_cards_store()
    if lesson in current_cards:
        card = db_manager.get_card(current_cards[lesson])
        if card:
            return card
        current_cards.pop(lesson, None)
        session.modified = True

    recent_cards = get_recent_cards_store().get(lesson, [])
    engine = SpacedRepetitionEngine(db_manager, lesson, recent_card_ids=recent_cards)
    card = engine.get_next_card()
    if not card:
        return None

    current_cards[lesson] = card["id"]
    get_recent_cards_store()[lesson] = engine.recent_card_ids()
    session.modified = True
    return card


def lesson_dashboard(lesson):
    return {
        "stats": db_manager.get_lesson_stats(lesson),
        "difficult_words": db_manager.get_difficult_words(limit=5, lektion=lesson),
        "recent_activity": db_manager.get_recent_activity(limit=8, lektion=lesson),
    }


@app.route("/", methods=["GET"])
def home():
    lessons = []
    for lesson in db_manager.get_lessons():
        lessons.append({
            "name": lesson,
            "stats": db_manager.get_lesson_stats(lesson),
        })

    return render_template(
        "index.html",
        lessons=lessons,
        global_stats=db_manager.get_lesson_stats(),
        difficult_words=db_manager.get_difficult_words(limit=8),
        recent_activity=db_manager.get_recent_activity(limit=10),
    )


@app.route("/lesson/<lesson>", methods=["GET"])
def lesson_view(lesson):
    lesson = load_lesson_or_404(lesson)
    card = choose_or_restore_card(lesson)
    return render_template(
        "lesson.html",
        lesson=lesson,
        card=card,
        dashboard=lesson_dashboard(lesson),
    )


@app.post("/lesson/<lesson>/rate")
def rate_card(lesson):
    lesson = load_lesson_or_404(lesson)
    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0

    if rating < 1 or rating > 5:
        abort(400)

    current_cards = get_current_cards_store()
    card_id = current_cards.get(lesson)
    if card_id is None:
        return redirect(url_for("lesson_view", lesson=lesson))

    db_manager.update_rating(card_id, rating)
    current_cards.pop(lesson, None)
    session.modified = True
    return redirect(url_for("lesson_view", lesson=lesson))


@app.post("/lesson/<lesson>/reset-session")
def reset_lesson_session(lesson):
    lesson = load_lesson_or_404(lesson)
    get_current_cards_store().pop(lesson, None)
    get_recent_cards_store().pop(lesson, None)
    session.modified = True
    return redirect(url_for("lesson_view", lesson=lesson))


if __name__ == "__main__":
    app.run(debug=True)
