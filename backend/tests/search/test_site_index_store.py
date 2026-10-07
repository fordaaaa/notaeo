"""Site-index Store isolation/cap/revision/composite-FK (TDD)."""
from __future__ import annotations


def _store(tmp_path, email="u@example.com"):
    from core.store import Store

    store = Store(root=tmp_path / "data")
    user = store.create_user(email, "password123")
    return store, user


def _pages(n=1, base="https://example.edu/book"):
    now = "2026-10-07T00:00:00+00:00"
    return [{"url": f"{base}/p{i}", "title": f"T{i}", "text": f"cells content {i}"} for i in range(n)]


def test_add_idempotent_and_cap20(tmp_path):
    from core.store import Store  # noqa: F401

    store, user = _store(tmp_path)
    first = store.create_index_site(user.id, "https://example.edu/book")
    again = store.create_index_site(user.id, "https://example.edu/book")
    assert first["id"] == again["id"]
    assert first["revision"] == again["revision"]
    for i in range(19):
        store.create_index_site(user.id, f"https://example.edu/book{i}")
    import pytest

    with pytest.raises(ValueError):
        store.create_index_site(user.id, "https://example.edu/over-cap")
    assert len(store.list_index_sites(user.id)) == 20


def test_user_isolated_list_and_pages(tmp_path):
    store, user = _store(tmp_path, "a@example.com")
    store2_user = store.create_user("b@example.com", "password123")
    site = store.create_index_site(user.id, "https://example.edu/book")
    store.replace_index_pages(user.id, site["id"], site["revision"], _pages(1), "2026-10-07T00:00:00+00:00", "complete")
    assert len(store.list_index_sites(user.id)) == 1
    assert store.list_index_sites(store2_user.id) == []
    assert len(store.list_index_pages(user.id)) == 1
    assert store.list_index_pages(store2_user.id) == []
    assert store.get_index_site(store2_user.id, site["id"]) is None


def test_composite_fk_rejects_foreign_site_id(tmp_path):
    store, user = _store(tmp_path)
    other = store.create_user("other@example.com", "password123")
    site = store.create_index_site(user.id, "https://example.edu/book")
    # direct SQL with mismatched owner must violate composite FK
    with store._connect() as con:
        import pytest

        import sqlite3

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            con.execute(
                "INSERT INTO web_index_pages (site_id, user_id, url, title, text, indexed_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (site["id"], other.id, "https://example.edu/book/x", "T", "cells", "2026-10-07T00:00:00+00:00"),
            )


def test_claim_revision_cas409_no_resurrect(tmp_path):
    store, user = _store(tmp_path)
    site = store.create_index_site(user.id, "https://example.edu/book")
    claimed = store.claim_index_refresh(user.id, site["id"])
    assert claimed == site["revision"] + 1
    # stale expected revision conflicts
    import pytest

    with pytest.raises(store.IndexConflict):
        store.replace_index_pages(user.id, site["id"], site["revision"], _pages(1), "2026-10-07T00:00:00+00:00", "complete")
    # correct revision replaces
    updated = store.replace_index_pages(user.id, site["id"], claimed, _pages(2), "2026-10-07T00:00:01+00:00", "complete")
    assert updated["page_count"] == 2
    # delete then replace cannot resurrect
    assert store.delete_index_site(user.id, site["id"]) is True
    with pytest.raises(KeyError):
        store.replace_index_pages(user.id, site["id"], updated["revision"], _pages(1), "2026-10-07T00:00:02+00:00", "complete")
    assert store.list_index_sites(user.id) == []
    assert store.list_index_pages(user.id) == []


def test_failed_refresh_preserves_pages_and_indexed_at(tmp_path):
    store, user = _store(tmp_path)
    site = store.create_index_site(user.id, "https://example.edu/book")
    store.replace_index_pages(user.id, site["id"], site["revision"], _pages(1), "2026-10-07T00:00:00+00:00", "complete")
    before = store.get_index_site(user.id, site["id"])
    claimed = store.claim_index_refresh(user.id, site["id"])
    # simulate failed crawl: no replace call; data preserved, revision bumped
    after = store.get_index_site(user.id, site["id"])
    assert after["page_count"] == before["page_count"]
    assert after["indexed_at"] == before["indexed_at"]
    assert after["revision"] == claimed
    assert len(store.list_index_pages(user.id)) == 1


def test_delete_cascades_pages(tmp_path):
    store, user = _store(tmp_path)
    site = store.create_index_site(user.id, "https://example.edu/book")
    store.replace_index_pages(user.id, site["id"], site["revision"], _pages(2), "2026-10-07T00:00:00+00:00", "complete")
    assert len(store.list_index_pages(user.id)) == 2
    assert store.delete_index_site(user.id, site["id"]) is True
    assert store.list_index_pages(user.id) == []


def test_cached_search_stable_ranking_fulltext(tmp_path):
    from core import siteindex as si

    store, user = _store(tmp_path)
    site = store.create_index_site(user.id, "https://example.edu/book")
    long_text = "\n\n".join(
        [
            "Intro filler about schedules. " * 10,
            "Background filler about rooms. " * 10,
            "The mitochondria powerhouse zymurgy discovery matters. " * 3,
        ]
    )
    store.replace_index_pages(
        user.id, site["id"], site["revision"],
        [{"url": "https://example.edu/book/a", "title": "Cells", "text": long_text}],
        "2026-10-07T00:00:00+00:00", "complete",
    )
    pages = store.list_index_pages(user.id)
    hits = si.search_cached_pages(pages, "mitochondria zymurgy", limit=10, domain=None, file_type="all", academic=False)
    assert len(hits) == 1
    assert "zymurgy" in hits[0]["snippet"].lower()
    # stable ties: same score sorts by title then url
    hits2 = si.search_cached_pages(pages, "mitochondria zymurgy", limit=10, domain=None, file_type="all", academic=False)
    assert hits == hits2
