import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(autouse=True)
def setup_database():
    from main import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_project_crud_and_isolation():
    with TestClient(app) as client:
        # Create User A
        reg_a = client.post("/users/register", json={"email": "usera@driftguard.com", "name": "User A"})
        key_a = reg_a.json()["api_key"]
        headers_a = {"X-API-Key": key_a}

        # Create User B
        reg_b = client.post("/users/register", json={"email": "userb@driftguard.com", "name": "User B"})
        key_b = reg_b.json()["api_key"]
        headers_b = {"X-API-Key": key_b}

        # 1. User A creates Project A
        proj_a = client.post("/projects", json={"name": "Project Alpha"}, headers=headers_a)
        assert proj_a.status_code == 200
        proj_a_id = proj_a.json()["id"]

        # 2. User B creates Project B
        proj_b = client.post("/projects", json={"name": "Project Beta"}, headers=headers_b)
        assert proj_b.status_code == 200
        proj_b_id = proj_b.json()["id"]

        # 3. User A lists projects (should only see Project A)
        list_a = client.get("/projects", headers=headers_a)
        assert list_a.status_code == 200
        items_a = list_a.json()
        assert len(items_a) == 1
        assert items_a[0]["name"] == "Project Alpha"

        # 4. User A gets Project A details
        get_a = client.get(f"/projects/{proj_a_id}", headers=headers_a)
        assert get_a.status_code == 200
        assert get_a.json()["name"] == "Project Alpha"

        # 5. User A tries to get Project B details (should return 403 Forbidden)
        get_b_by_a = client.get(f"/projects/{proj_b_id}", headers=headers_a)
        assert get_b_by_a.status_code == 403
