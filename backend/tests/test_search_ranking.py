"""BM25-style ranking: focused notes beat long repetitive passages.

Covers strict search (core.search + Store.search) and opt-in related_search:
- TF saturation: 12x repetitions must not score ~12x a single mention.
- Length normalization: same TF, short focused chunk outranks diluted chunk.
- End-to-end: Store.search ranks focused above verbose repetitive.
- Related: same-confidence exact hits prefer focused; exact still beats expanded.
- Guards: AND semantics, literal quoted phrases, deterministic pagination.
"""
from __future__ import annotations

from pathlib import Path

from core import search
from core.models import Chunk, Page, Source, utcnow
from core.store import Store, new_id


def _store(tmp_path: Path) -> Store:
    store = Store(root=tmp_path / "data")
    store._test_uid = store.create_user(f"u{new_id()}@example.com", "password123").id
    return store


def _put(store: Store, nb_id: str, title: str, text: str) -> None:
    store.create_source(
        Source(
            id=new_id(),
            notebook_id=nb_id,
            kind="paste",
            title=title,
            tags=[],
            created_at=utcnow(),
            pages=[Page(number=1, text=text)],
            chunks=[Chunk(seq=0, pages=[1], text=text)],
        )
    )


def test_tf_saturates_repetition_not_linear():
    # BM25 path (avg_len given): 6 mentions must help vs 1 but far below 6x.
    q = search.parse_query("photosynthesis")
    df = {"photosynthesi": 1}
    single = "photosynthesis captures light."
    verbose = "photosynthesis " * 6 + "captures light."
    avg = (len(search.stemmed_words(single)) + len(search.stemmed_words(verbose))) / 2
    _, s1, _ = search.score_chunk(single, q, df=df, n_docs=2, avg_len=avg)
    _, s6, _ = search.score_chunk(verbose, q, df=df, n_docs=2, avg_len=avg)
    assert s6 > s1  # repetition still helps a little
    assert s6 < 2.5 * s1, f"tf should saturate, got {s1=} {s6=}"


def test_length_normalization_short_beats_diluted_same_tf():
    # Same tf (1 mention each); BM25 length norm must prefer the focused chunk.
    q = search.parse_query("photosynthesis")
    df = {"photosynthesi": 1}
    short = "photosynthesis captures sunlight in leaves."
    long = "photosynthesis captures sunlight in leaves " + "filler lorem ipsum dolor " * 40
    avg = (len(search.stemmed_words(short)) + len(search.stemmed_words(long))) / 2
    _, s_short, _ = search.score_chunk(short, q, df=df, n_docs=2, avg_len=avg)
    _, s_long, _ = search.score_chunk(long, q, df=df, n_docs=2, avg_len=avg)
    assert s_short > s_long, f"focused should win, got {s_short=} {s_long=}"


def test_store_search_focused_beats_verbose_repetitive(tmp_path):
    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "Rank")
    _put(store, nb.id, "Focused", "Photosynthesis captures sunlight in leaves.")
    # 5 mentions stuffed into a ~165-word diluted passage vs 1 in a 5-word note.
    verbose = "photosynthesis " * 5 + "filler lorem ipsum dolor " * 40
    _put(store, nb.id, "Verbose", verbose)
    hits = store.search(nb.id, "photosynthesis")
    assert len(hits) == 2
    assert hits[0].source_title == "Focused", [ (h.source_title, h.score) for h in hits ]


def test_and_semantics_preserved(tmp_path):
    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "And")
    _put(store, nb.id, "Partial", "alpha only here")
    _put(store, nb.id, "Full", "alpha and beta together")
    hits = store.search(nb.id, "alpha beta")
    assert [h.source_title for h in hits] == ["Full"]


def test_quoted_phrase_stays_literal(tmp_path):
    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "Phrase")
    _put(store, nb.id, "Lecture", "Mitochondria produce energy.")
    _put(store, nb.id, "Phrase", "The powerhouse of the cell produces energy.")
    hits, total = store.search_with_total(nb.id, '"powerhouse of the cell"')
    assert total == 1 and hits[0].source_title == "Phrase"


def test_pagination_deterministic(tmp_path):
    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "Paging")
    for i in range(5):
        _put(store, nb.id, f"src{i}", f"shared term elephant {i}")
    full, total = store.search_with_total(nb.id, "elephant", limit=100)
    page, total2 = store.search_with_total(nb.id, "elephant", limit=2, offset=2)
    assert total == total2 == 5
    assert page == full[2:4]
    again, _ = store.search_with_total(nb.id, "elephant", limit=100)
    assert [h.source_id for h in again] == [h.source_id for h in full]


def test_related_focused_beats_verbose_same_confidence(tmp_path):
    from core.related import related_search

    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "RelatedRank")
    _put(store, nb.id, "Focused", "Mitochondria produce energy for cells.")
    _put(store, nb.id, "Verbose", "mitochondria " * 10 + "filler lorem ipsum dolor " * 40)
    hits, total = related_search(store, nb.id, "mitochondria")
    assert total == 2
    assert hits[0].source_title == "Focused", [(h.source_title, h.score) for h in hits]


def test_related_exact_still_beats_expansion(tmp_path):
    from core.related import related_search

    store = _store(tmp_path)
    nb = store.create_notebook(store._test_uid, "Rank")
    _put(store, nb.id, "Exact", "Mitochondria produce energy.")
    _put(store, nb.id, "Expanded", "The powerhouse produces energy.")
    hits, total = related_search(store, nb.id, "mitochondria")
    assert total == 2
    assert hits[0].source_title == "Exact"
    assert hits[0].score > hits[1].score
    assert "mitochondria" in hits[0].matched_terms
    assert "mitochondria" not in hits[1].matched_terms
