_counter = {"n": 0}


def register(client, role="student", **extra):
    _counter["n"] += 1
    body = {"email": f"user{_counter['n']}@test.com", "password": "secret123",
            "full_name": f"User {_counter['n']}", "role": role, **extra}
    r = client.post("/auth/register", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"id": data["user_id"], "token": data["access_token"], "email": body["email"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}}
