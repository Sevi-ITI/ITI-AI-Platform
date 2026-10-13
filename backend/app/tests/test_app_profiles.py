"""6A.7: app profiles (optional notes) merged with live counts from keys, chats and the request log."""

Q = {"question": "How many vacation days?", "collection": "iti-docs"}
PROFILE = {"display_name": "HR Portal", "company": "ITI / HR", "owner_name": "Juan", "owner_email": "juan@iti.example"}


def test_apps_list_merges_profiles_keys_and_users(client, make_key):
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    hr = make_key("hr-portal")
    make_key("hr-portal")  # a second key for the same app
    old = make_key("hr-portal")  # and a third, revoked: not counted
    client.delete(f"/v1/admin/keys/{old['ITI-Api-Key'].split('_')[2]}", headers=admin)
    for user in ("1042", "2210", "1042"):
        client.post("/v1/chat", headers=hr | {"ITI-User-Id": user}, json=Q)

    written = client.put("/v1/admin/apps/hr-portal", headers=admin, json=PROFILE)
    assert written.status_code == 200 and written.json()["display_name"] == "HR Portal"
    client.put("/v1/admin/apps/payroll", headers=admin, json={"notes": "connects in Q1"})  # before its first key

    apps = {a["app_id"]: a for a in client.get("/v1/admin/apps", headers=admin).json()}
    assert set(apps) == {"hr-portal", "iti-admin", "payroll"}
    hr_app = apps["hr-portal"]
    assert (hr_app["active_keys"], hr_app["users"], hr_app["owner_email"]) == (2, 2, "juan@iti.example")
    assert hr_app["last_used_at"] is not None and hr_app["profile_updated_at"] is not None
    assert (apps["payroll"]["active_keys"], apps["payroll"]["notes"]) == (0, "connects in Q1")
    assert apps["iti-admin"]["profile_updated_at"] is None

    replaced = client.put("/v1/admin/apps/hr-portal", headers=admin, json={"display_name": "HR"}).json()
    assert (replaced["display_name"], replaced["owner_name"]) == ("HR", None)  # PUT replaces the whole profile
    assert client.put("/v1/admin/apps/HR Portal", headers=admin, json={}).status_code == 422
    assert client.put("/v1/admin/apps/hr-portal", headers=admin, json={"owner_email": "not-an-email"}).status_code == 422
