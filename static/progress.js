// Learning progress is stored only in this browser's localStorage and survives restarts.
(function () {
  const STORAGE_KEY = "adeamus-progress-v1";
  const memoryFallback = { cards: {}, lessons: {} };

  function load() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return { cards: {}, lessons: {} };
      const data = JSON.parse(raw);
      return {
        cards: data && typeof data.cards === "object" && data.cards ? data.cards : {},
        lessons: data && typeof data.lessons === "object" && data.lessons ? data.lessons : {},
      };
    } catch (err) {
      return memoryFallback;
    }
  }

  function save(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (err) {
      memoryFallback.cards = state.cards;
      memoryFallback.lessons = state.lessons;
      return false;
    }
  }

  function storageAvailable() {
    try {
      const probe = "__adeamus_probe__";
      window.localStorage.setItem(probe, "1");
      window.localStorage.removeItem(probe);
      return true;
    } catch (err) {
      return false;
    }
  }

  if (navigator.storage && navigator.storage.persist) {
    navigator.storage.persist().catch(() => {});
  }

  function cardKey(card) {
    return card.lektion + "\u001f" + card.latin;
  }

  function progressFor(state, card) {
    return state.cards[cardKey(card)] || { rating: 0, review_count: 0, last_reviewed: null };
  }

  function withProgress(state, cards) {
    return cards.map((card) => Object.assign({}, card, progressFor(state, card)));
  }

  function stats(state, cards) {
    let learned = 0;
    let ratedSum = 0;
    let ratedCount = 0;
    cards.forEach((card) => {
      const p = progressFor(state, card);
      if (p.rating >= 3) learned += 1;
      if (p.rating > 0) {
        ratedSum += p.rating;
        ratedCount += 1;
      }
    });
    const total = cards.length;
    return {
      total: total,
      learned: learned,
      avg_rating: ratedCount ? Math.round((ratedSum / ratedCount) * 100) / 100 : 0,
      progress_pct: total ? Math.round((learned / total) * 1000) / 10 : 0,
    };
  }

  function difficultWords(state, cards, limit) {
    return withProgress(state, cards)
      .filter((c) => c.rating > 0 && c.rating < 3)
      .sort((a, b) => a.rating - b.rating || b.review_count - a.review_count)
      .slice(0, limit);
  }

  function recentActivity(state, cards, limit) {
    return withProgress(state, cards)
      .filter((c) => c.last_reviewed)
      .sort((a, b) => (a.last_reviewed < b.last_reviewed ? 1 : -1))
      .slice(0, limit);
  }

  function weightForRating(rating) {
    switch (rating) {
      case 0:
      case 1: return 10.0;
      case 2: return 5.0;
      case 3: return 2.0;
      case 4: return 0.5;
      case 5: return 0.1;
      default: return 1.0;
    }
  }

  function lessonState(state, lesson) {
    if (!state.lessons[lesson]) state.lessons[lesson] = { current: null, recent: [] };
    return state.lessons[lesson];
  }

  // Returns the card currently being studied (restored after restart) or picks a new weighted one.
  function currentOrNextCard(state, lesson, cards) {
    if (!cards.length) return null;
    const ls = lessonState(state, lesson);
    if (ls.current) {
      const existing = cards.find((c) => cardKey(c) === ls.current);
      if (existing) return existing;
    }

    const recencySize = Math.max(0, Math.min(4, Math.floor(cards.length / 2)));
    const recent = new Set((ls.recent || []).slice(-recencySize));
    let weights = cards.map((c) => (recent.has(cardKey(c)) ? 0 : weightForRating(progressFor(state, c).rating)));
    let sum = weights.reduce((a, b) => a + b, 0);
    if (sum === 0) {
      weights = cards.map(() => 1);
      sum = cards.length;
    }

    let threshold = Math.random() * sum;
    let selected = cards[cards.length - 1];
    for (let i = 0; i < cards.length; i += 1) {
      threshold -= weights[i];
      if (threshold < 0) {
        selected = cards[i];
        break;
      }
    }

    const key = cardKey(selected);
    ls.current = key;
    ls.recent = recencySize ? (ls.recent || []).concat(key).slice(-recencySize) : [];
    save(state);
    return selected;
  }

  function rate(state, lesson, card, rating) {
    const p = progressFor(state, card);
    state.cards[cardKey(card)] = {
      rating: rating,
      review_count: (p.review_count || 0) + 1,
      last_reviewed: new Date().toISOString(),
    };
    lessonState(state, lesson).current = null;
    return save(state);
  }

  function resetLessonRound(state, lesson) {
    state.lessons[lesson] = { current: null, recent: [] };
    save(state);
  }

  function renderWordList(listEl, items, emptyText, formatMeta, showLesson) {
    listEl.replaceChildren();
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "empty-state";
      li.textContent = emptyText;
      listEl.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      const strong = document.createElement("strong");
      strong.textContent = showLesson ? "L" + item.lektion + " · " + item.latin : item.latin;
      const span = document.createElement("span");
      span.textContent = item.german;
      const small = document.createElement("small");
      small.textContent = formatMeta(item);
      li.append(strong, span, small);
      listEl.appendChild(li);
    });
  }

  function readJson(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  window.AdeamusProgress = {
    load: load,
    save: save,
    storageAvailable: storageAvailable,
    cardKey: cardKey,
    progressFor: progressFor,
    stats: stats,
    difficultWords: difficultWords,
    recentActivity: recentActivity,
    currentOrNextCard: currentOrNextCard,
    rate: rate,
    resetLessonRound: resetLessonRound,
    renderWordList: renderWordList,
    readJson: readJson,
  };
})();
