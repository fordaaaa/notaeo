"""Classes, assignments, and the calendar endpoint."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import classes as classes_api
from api.main import app

def _other_user(email: str) -> TestClient:
    """Register a second user and return an authed client for them."""
    with TestClient(app) as anon:
        token = anon.post(
            "/api/auth/register", json={"email": email, "password": "password123"}
    ).json()["token"]
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})




def _class(client: TestClient, name: str = "Biology", color: str = "sea") -> str:
    return client.post("/api/classes", json={"name": name, "color": color}).json()["id"]


def test_class_crud_round_trip(client: TestClient):
    class_id = _class(client, "Chemistry", "ocean")
    listed = client.get("/api/classes").json()
    assert [c["name"] for c in listed] == ["Chemistry"]

    renamed = client.patch(f"/api/classes/{class_id}", json={"name": "Organic Chem"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Organic Chem"

    assert client.delete(f"/api/classes/{class_id}").status_code == 204
    assert client.get("/api/classes").json() == []


def test_assignment_crud_and_calendar_buckets(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(classes_api, "utcnow", lambda: datetime(2026, 10, 14, 12, tzinfo=timezone.utc))
    class_id = _class(client, "Biology", "sea")
    created = client.post(
        "/api/assignments",
        json={"title": "Lab report", "class_id": class_id, "details": "ch. 4",
              "due_at": "2026-10-15T23:59:00+00:00"},
    )
    assert created.status_code == 201
    assignment = created.json()
    assert assignment["class_name"] == "Biology"
    assert assignment["done"] is False

    calendar = client.get("/api/me/calendar?days=35").json()
    bucket = next(day for day in calendar if day["day"] == "2026-10-15")
    assert [a["title"] for a in bucket["assignments"]] == ["Lab report"]
    assert bucket["assignments"][0]["class_name"] == "Biology"

    done = client.patch(f"/api/assignments/{assignment['id']}", json={"done": True})
    assert done.json()["done"] is True

    assert client.delete(f"/api/assignments/{assignment['id']}").status_code == 204
    calendar = client.get("/api/me/calendar?days=35").json()
    assert all(not day["assignments"] for day in calendar)


def test_assignment_without_class_is_allowed(client: TestClient):
    created = client.post("/api/assignments", json={"title": "Read chapter 5"})
    assert created.status_code == 201
    assert created.json()["class_id"] is None
    listed = client.get("/api/assignments").json()
    assert [a["title"] for a in listed] == ["Read chapter 5"]


def test_foreign_resources_are_404(client: TestClient):
    class_id = _class(client)
    assignment_id = client.post(
        "/api/assignments", json={"title": "essay", "class_id": class_id}
    ).json()["id"]
    other = _other_user("other-classes@example.com")
    assert other.get(f"/api/classes/{class_id}").status_code == 404
    assert other.patch(f"/api/classes/{class_id}", json={"name": "Changed"}).status_code == 404
    assert other.delete(f"/api/classes/{class_id}").status_code == 404
    assert other.patch(
        f"/api/assignments/{assignment_id}", json={"done": True}
    ).status_code == 404
    assert other.delete(f"/api/assignments/{assignment_id}").status_code == 404
    # the other user's calendar is empty of assignments and card dues
    for day in other.get("/api/me/calendar").json():
        assert day["assignments"] == [] and day["card_due"] == []


def test_assignment_class_validation(client: TestClient):
    assert client.post(
        "/api/assignments", json={"title": "x", "class_id": "0" * 12}
    ).status_code == 404
    assert client.post("/api/assignments", json={"title": "  "}).status_code == 422
    assert client.patch(
        f"/api/assignments/{'a' * 12}", json={"done": True}
    ).status_code == 404


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("link_kind", ["foreign", "missing", "malformed"])
def test_assignment_rejects_unowned_notebook_links_without_writes(
    client: TestClient, operation: str, link_kind: str,
) -> None:
    own_notebook = client.post("/api/notebooks", json={"title": "My notes"}).json()["id"]
    assignment = client.post(
        "/api/assignments", json={"title": "My essay", "notebook_id": own_notebook},
    ).json()
    other = _other_user("notebook-owner@example.test")
    foreign = other.post("/api/notebooks", json={"title": "Private notes"}).json()["id"]
    notebook_id = {"foreign": foreign, "missing": "0" * 12, "malformed": "invalid"}[link_kind]
    response = (
        client.post("/api/assignments", json={"title": "Unexpected task", "notebook_id": notebook_id})
        if operation == "create" else
        client.patch(f"/api/assignments/{assignment['id']}", json={"notebook_id": notebook_id, "done": True})
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "notebook not found"}
    assert client.get("/api/assignments").json() == [assignment]
    assert other.get("/api/assignments").json() == []


def test_assignment_owned_notebook_can_be_changed_and_unlinked(client: TestClient) -> None:
    first = client.post("/api/notebooks", json={"title": "Lecture"}).json()["id"]
    second = client.post("/api/notebooks", json={"title": "Reading"}).json()["id"]
    created = client.post("/api/assignments", json={"title": "Essay", "notebook_id": first})
    assert created.status_code == 201
    assignment_id = created.json()["id"]
    changed = client.patch(f"/api/assignments/{assignment_id}", json={"notebook_id": second})
    assert changed.status_code == 200
    assert changed.json()["notebook_id"] == second
    unlinked = client.patch(f"/api/assignments/{assignment_id}", json={"notebook_id": None})
    assert unlinked.status_code == 200
    assert unlinked.json()["notebook_id"] is None


def test_foreign_assignment_is_hidden_before_notebook_validation(client: TestClient) -> None:
    assignment_id = client.post("/api/assignments", json={"title": "Private task"}).json()["id"]
    other = _other_user("foreign-task@example.test")
    for task_id in (assignment_id, "0" * 12):
        response = other.patch(f"/api/assignments/{task_id}", json={"notebook_id": "invalid"})
        assert response.status_code == 404
        assert response.json() == {"detail": "assignment not found"}


def test_assignment_course_link_can_only_use_owned_classes(client: TestClient) -> None:
    course_id = _class(client)
    task = client.post("/api/assignments", json={"title": "Essay"}).json()
    route = f"/api/assignments/{task['id']}"
    linked = client.patch(route, json={"class_id": course_id})
    assert linked.status_code == 200
    assert linked.json()["class_name"] == "Biology"
    other = _other_user("foreign-class-owner@example.test")
    foreign_id = _class(other, "Private class")
    for rejected_id in (foreign_id, "0" * 12):
        rejected = client.patch(route, json={"class_id": rejected_id, "done": True})
        assert rejected.status_code == 404
        assert rejected.json() == {"detail": "class not found"}
    assert client.get("/api/assignments").json() == [linked.json()]
    unlinked = client.patch(route, json={"class_id": None})
    assert unlinked.status_code == 200
    assert unlinked.json()["class_id"] is None
