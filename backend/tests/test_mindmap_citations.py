"""Source-cited keyless mindmap: branches + concept leaves carry citations.

Contract: {id, name, children=[], source_id?, pages=[]}.
"""
from __future__ import annotations


TEXT_A = (
    "Photosynthesis converts light energy in chloroplasts. "
    "Chlorophyll captures light energy for photosynthesis. "
    "Chloroplasts store starch energy from photosynthesis reactions."
)

TEXT_B = (
    "Mitosis divides the nucleus in prophase stages. "
    "Chromosomes condense during prophase of mitosis. "
    "The nucleus reforms after mitosis completes division."
)


def test_concepts_point_to_the_actual_pages_without_restemming():
    from core.models import Chunk, Page, Source, utcnow
    from core.study import build_mindmap

    source = Source(
        id="abcdef123456", notebook_id="123456abcdef", kind="pdf", title="Course",
        created_at=utcnow(),
        pages=[Page(number=1, text="Class class class."),
               Page(number=7, text="Mitochondria mitochondria mitochondria.")],
        chunks=[Chunk(seq=0, pages=[1], text="Class class class."),
                Chunk(seq=1, pages=[7], text="Mitochondria mitochondria mitochondria.")],
    )
    concepts = {leaf["name"].lower(): leaf for leaf in build_mindmap("Biology", [source])["children"][0]["children"]}
    assert "class" in concepts
    assert concepts["class"]["pages"] == [1]
    assert concepts["mitochondria"]["pages"] == [7]


def _nb(client, name="Biology Course"):
    res = client.post("/api/notebooks", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()


def _add(client, nb_id, title, text):
    res = client.post(
        f"/api/notebooks/{nb_id}/sources/text",
        json={"title": title, "text": text},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _tree(client, nb_id):
    res = client.get(f"/api/notebooks/{nb_id}/mindmap")
    assert res.status_code == 200, res.text
    return res.json()


def test_branches_carry_source_citations(client):
    nb = _nb(client)
    a = _add(client, nb["id"], "Photosynthesis", TEXT_A)
    b = _add(client, nb["id"], "Mitosis", TEXT_B)
    tree = _tree(client, nb["id"])

    # Existing name/children compatibility.
    assert tree["name"] == "Biology Course"
    assert isinstance(tree["id"], str) and tree["id"]
    by_name = {c["name"]: c for c in tree["children"]}
    assert set(by_name) == {"Photosynthesis", "Mitosis"}
    for title, sid in (("Photosynthesis", a["id"]), ("Mitosis", b["id"])):
        branch = by_name[title]
        assert branch["id"] and isinstance(branch["id"], str)
        assert branch["source_id"] == sid
        assert isinstance(branch["pages"], list) and branch["pages"]
        assert all(isinstance(p, int) for p in branch["pages"])
        assert branch["children"]


def test_leaves_carry_concept_citations(client):
    nb = _nb(client)
    a = _add(client, nb["id"], "Photosynthesis", TEXT_A)
    tree = _tree(client, nb["id"])
    branch = next(c for c in tree["children"] if c["name"] == "Photosynthesis")
    assert len(branch["children"]) >= 1
    for leaf in branch["children"]:
        assert leaf["name"] and isinstance(leaf["name"], str)
        assert leaf["id"] and isinstance(leaf["id"], str)
        assert leaf.get("children", []) == []
        assert leaf["source_id"] == a["id"]
        assert isinstance(leaf["pages"], list) and leaf["pages"]
        assert all(isinstance(p, int) and p >= 1 for p in leaf["pages"])
        # Grounded: leaf concept appears in the cited source text.
        assert leaf["name"].lower() in TEXT_A.lower()


def test_ids_stable_across_calls(client):
    nb = _nb(client)
    _add(client, nb["id"], "Photosynthesis", TEXT_A)
    _add(client, nb["id"], "Mitosis", TEXT_B)
    first = _tree(client, nb["id"])
    second = _tree(client, nb["id"])
    assert first == second

    def _ids(node):
        yield node["id"]
        for child in node.get("children", []):
            yield from _ids(child)

    ids = list(_ids(first))
    assert len(ids) == len(set(ids))  # unique


def test_mindmap_needs_sources(client):
    nb = _nb(client)
    assert client.get(f"/api/notebooks/{nb['id']}/mindmap").status_code == 400
    assert client.get(f"/api/notebooks/{nb['id']}/mindmap/export").status_code == 400


def test_mindmap_owner_and_auth(client):
    from fastapi.testclient import TestClient

    from api.main import app

    nb = _nb(client)
    _add(client, nb["id"], "Photosynthesis", TEXT_A)
    # Unauthenticated.
    with TestClient(app) as anon:
        assert anon.get(f"/api/notebooks/{nb['id']}/mindmap").status_code == 401
        assert anon.get(f"/api/notebooks/{nb['id']}/mindmap/export").status_code == 401
    # Stranger (other account) sees 404, never the tree.
    with TestClient(app) as anon:
        rr = anon.post(
            "/api/auth/register",
            json={"email": "stranger-mm@example.com", "password": "password123"},
        )
        assert rr.status_code == 201
        token2 = rr.json()["token"]
    with TestClient(app, headers={"Authorization": f"Bearer {token2}"}) as other:
        assert other.get(f"/api/notebooks/{nb['id']}/mindmap").status_code == 404
        assert other.get(f"/api/notebooks/{nb['id']}/mindmap/export").status_code == 404
    # Malformed id is indistinguishable from foreign (404 oracle).
    assert client.get("/api/notebooks/notahexid!!/mindmap").status_code == 404


def test_mindmap_markdown_export_keeps_names_and_citations(client):
    nb = _nb(client)
    a = _add(client, nb["id"], "Photosynthesis", TEXT_A)
    res = client.get(f"/api/notebooks/{nb['id']}/mindmap/export")
    assert res.status_code == 200, res.text
    assert "attachment" in res.headers["content-disposition"]
    assert "# Biology Course" in res.text
    assert "- Photosynthesis" in res.text
    # Export carries the citation so readers can open the source.
    assert a["id"] in res.text or "p." in res.text or "page" in res.text.lower()


def test_unicode_course_title_exports_without_header_encoding_failure(client):
    nb = _nb(client, "Café 生物")
    _add(client, nb["id"], "Lecture", TEXT_A)
    response = client.get(f"/api/notebooks/{nb['id']}/mindmap/export")
    assert response.status_code == 200
    assert "# Café 生物" in response.text
    assert response.headers["content-disposition"].isascii()
