from fastapi.testclient import TestClient
from app.access import AccessStore

def test_employee_access_and_admin_controls(tmp_path, monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "ACCESS", AccessStore(tmp_path / "access.sqlite"))
    with TestClient(main_module.app) as client:
        assert client.get("/api/reviews").status_code == 401
        assert client.post("/api/access/login", json={"employee_id": "missing"}).status_code == 404
        assert client.post("/api/access/login", json={"employee_id": "2"}).json()["role"] == "user"
        assert client.get("/api/admin/employees").status_code == 403
        assert client.post("/api/access/login", json={"employee_id": "1"}).json()["role"] == "admin"
        assert client.get("/api/admin/employees").status_code == 403
        assert client.post("/api/admin/unlock", json={"password": "wrong"}).status_code == 403
        assert client.post("/api/admin/unlock", json={"password": "1"}).json()["admin_unlocked"]
        created = client.post("/api/admin/employees", json={"employee_id": "3", "role": "user"})
        employees = client.get("/api/admin/employees")
        updated = client.put("/api/admin/employees/3", json={"role": "admin"})
        deleted = client.delete("/api/admin/employees/3")
    assert created.status_code == 200
    assert any(item["employee_id"] == "3" for item in employees.json())
    assert updated.json()["role"] == "admin"
    assert deleted.status_code == 200


def test_login_page_and_console_redirects_are_server_enforced():
    import app.main as main_module

    with TestClient(main_module.app) as client:
        redirect = client.get("/", follow_redirects=False)
        login_page = client.get("/login")
        assert client.post("/api/access/login", json={"employee_id": "1"}).status_code == 200
        response = client.get("/", follow_redirects=False)
        authenticated_login_redirect = client.get("/login", follow_redirects=False)
        script = client.get("/static/app.js")
        login_script = client.get("/static/login.js")

    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/login"
    assert login_page.status_code == 200
    assert '<form id="login-form">' in login_page.text
    assert '<script src="/static/login.js?v=0.5.5"></script>' in login_page.text
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert script.headers["cache-control"] == "no-store"
    assert login_script.headers["cache-control"] == "no-store"
    assert 'access-gate' not in response.text
    assert '<script src="/static/app.js?v=0.5.5"></script>' in response.text
    assert 'window.location.replace("/login")' in script.text
    assert authenticated_login_redirect.status_code == 303
    assert authenticated_login_redirect.headers["location"] == "/"
