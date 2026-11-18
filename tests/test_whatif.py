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
