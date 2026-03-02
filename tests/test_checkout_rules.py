from fastapi.testclient import TestClient

from app.main import app


def test_cannot_checkout_retired_asset():
    client = TestClient(app)

    create = client.post(
        "/api/assets",
        json={"asset_tag": "RET-1", "serial_number": "retired-serial", "status": "retired"},
    )
    assert create.status_code == 200
    asset_id = create.json()["id"]

    # use seeded employee account lookup from users endpoint page content is enough for smoke; API rejects by status anyway.
    checkout = client.post(
        "/api/checkout",
        json={
            "asset_id": asset_id,
            "user_id": "employee-id-placeholder",
            "initiated_by_user_id": None,
            "policy_version": "v1",
        },
    )
    assert checkout.status_code == 400
    assert "cannot be checked out" in checkout.text.lower()


def test_asset_serial_is_normalized_and_unique():
    client = TestClient(app)
    first = client.post("/api/assets", json={"asset_tag": "NORM-1", "serial_number": " abc123 "})
    assert first.status_code == 200

    second = client.post("/api/assets", json={"asset_tag": "NORM-2", "serial_number": "ABC123"})
    assert second.status_code == 400
