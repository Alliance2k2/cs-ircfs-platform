"""Field users: creation, phone normalisation, deletion guards, and updates."""


def test_create_field_user_normalises_phone(client):
    response = client.post("/api/v1/field-users", json={"phone_number": "+250 788 111 222", "full_name": "Test Farmer"})
    assert response.status_code == 201
    assert response.json()["phone_number"] == "+250788111222"


def test_duplicate_phone_returns_409(client):
    client.post("/api/v1/field-users", json={"phone_number": "+250788111222"})
    assert client.post("/api/v1/field-users", json={"phone_number": "+250788111222"}).status_code == 409


def test_cannot_delete_field_user_with_reports(client):
    created = client.post("/api/v1/field-users", json={"phone_number": "+250788111222"}).json()
    client.post("/api/v1/citizen-reports", json={"reporter_id": created["id"], "crop_type": "Maize"})
    assert client.delete(f"/api/v1/field-users/{created['id']}").status_code == 409


def test_can_delete_field_user_without_reports(client):
    created = client.post("/api/v1/field-users", json={"phone_number": "+250788111222"}).json()
    assert client.delete(f"/api/v1/field-users/{created['id']}").status_code == 204
    assert all(user["id"] != created["id"] for user in client.get("/api/v1/field-users").json())


def test_update_field_user_cell_and_role(client, district):
    created = client.post("/api/v1/field-users", json={"phone_number": "+250788111222"}).json()
    response = client.patch(
        f"/api/v1/field-users/{created['id']}",
        json={"cell_id": district["cell_id"], "role": "cooperative_leader"},
    )
    assert response.status_code == 200
    assert response.json()["cell_id"] == district["cell_id"]
    assert response.json()["role"] == "cooperative_leader"
