from whatif.render import chunks, word_times


def test_word_times_cover_duration():
    words = word_times("You wake up in Canada. The year is 1535.", 4.0)
    assert words[0][1] == 0.0
    assert abs(words[-1][2] - 4.0) < 1e-6
    assert all(a[2] <= b[1] + 1e-9 for a, b in zip(words, words[1:]))


def test_chunks_break_at_punctuation_and_length():
    words = word_times("Salt meat. Dried meat. No fruit, no vegetables at all today.", 5.0)
    groups = [" ".join(w[0] for w in g) for g in chunks(words)]
    assert groups[0] == "Salt meat."
    assert all(len(g) <= 20 for g in groups)


def test_trend_ranking_prefers_hypotheticals():
    from whatif import trends

    assert trends.parse_traffic("200K+") == 200000
    assert trends.parse_traffic("1M+") == 1000000
    items = [
        {"source": "r/AskReddit", "title": "What if you only had 2 days to live?", "score": 500},
        {"source": "r/AskReddit", "title": "Favourite soup?", "score": 5000},
        {"source": "google-CA", "title": "hockey score", "score": 100000},
    ]
    ranked = trends.rank(items)
    assert ranked[0]["title"].startswith("What if")
    md = trends.to_markdown(ranked, ["wikipedia: blocked"], trends.dt.datetime(2026, 11, 19))
    assert "Questions people are asking" in md and "wikipedia: blocked" in md


def test_inherit_and_landscape_layout():
    from whatif import render as R

    shots = [{"text": "a", "scene": "clinic", "cast": [], "clock": "48:00:00"}, {"text": "b"}, {"text": "c", "clock": None}]
    R.inherit(shots)
    assert shots[1]["scene"] == "clinic" and shots[1]["clock"] == "48:00:00" and "clock" not in shots[2]
    R.set_format("landscape")
    assert (R.W, R.H) == (1920, 1080)
    R.set_format("vertical")
    assert (R.W, R.H) == (1080, 1920)
