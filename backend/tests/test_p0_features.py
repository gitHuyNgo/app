"""P0 feature tests for license-vehicle compatibility & hub-manager hub_id validation."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BACKEND_URL") or "https://reverent-noyce-9.preview.emergentagent.com"
API = f"{BASE_URL.rstrip('/')}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module", autouse=True)
def seed(client):
    r = client.post(f"{API}/seed", timeout=30)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def world(client):
    drivers = client.get(f"{API}/drivers").json()
    vehicles = client.get(f"{API}/vehicles").json()
    hubs = client.get(f"{API}/hubs").json()
    # group drivers by license
    by_lic = {}
    for d in drivers:
        by_lic.setdefault(d.get("license_type"), []).append(d)
    by_type = {}
    for v in vehicles:
        by_type.setdefault(v.get("type"), []).append(v)
    return {"drivers": drivers, "vehicles": vehicles, "hubs": hubs, "by_lic": by_lic, "by_type": by_type}


def _free_vehicle(client, vehicles_of_type):
    """Return a vehicle id, unassigning it first to be safe."""
    v = vehicles_of_type[0]
    client.post(f"{API}/vehicles/{v['id']}/unassign")
    return v["id"]


# ─── License × Vehicle compatibility matrix ───
class TestLicenseVehicleMatrix:
    def test_van_rejects_license_A(self, client, world):
        van_id = _free_vehicle(client, world["by_type"]["van"])
        a_driver = world["by_lic"]["A"][0]
        # ensure driver not bound to another vehicle so error is the license one
        if a_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{a_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{van_id}/assign", json={"driver_id": a_driver["id"]})
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "")
        assert "not allowed to operate" in detail.lower() and "van" in detail.lower()
        assert "B" in detail and "C" in detail

    def test_van_accepts_license_B(self, client, world):
        van_id = _free_vehicle(client, world["by_type"]["van"])
        b_driver = world["by_lic"]["B"][0]
        if b_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{b_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{van_id}/assign", json={"driver_id": b_driver["id"]})
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True}

    def test_van_accepts_license_C(self, client, world):
        van_id = _free_vehicle(client, world["by_type"]["van"])
        c_driver = world["by_lic"]["C"][0]
        if c_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{c_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{van_id}/assign", json={"driver_id": c_driver["id"]})
        assert r.status_code == 200, r.text

    def test_motorbike_rejects_license_C(self, client, world):
        mb_id = _free_vehicle(client, world["by_type"]["motorbike"])
        c_driver = world["by_lic"]["C"][0]
        if c_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{c_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{mb_id}/assign", json={"driver_id": c_driver["id"]})
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "")
        assert "A" in detail and "B" in detail
        assert "motorbike" in detail.lower()

    def test_motorbike_accepts_license_A(self, client, world):
        mb_id = _free_vehicle(client, world["by_type"]["motorbike"])
        a_driver = world["by_lic"]["A"][0]
        if a_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{a_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{mb_id}/assign", json={"driver_id": a_driver["id"]})
        assert r.status_code == 200, r.text

    def test_motorbike_accepts_license_B(self, client, world):
        mb_id = _free_vehicle(client, world["by_type"]["motorbike"])
        b_driver = world["by_lic"]["B"][0]
        if b_driver.get("vehicle_id"):
            client.post(f"{API}/vehicles/{b_driver['vehicle_id']}/unassign")
        r = client.post(f"{API}/vehicles/{mb_id}/assign", json={"driver_id": b_driver["id"]})
        assert r.status_code == 200, r.text


# ─── Hub Manager: hub_id resolution & validation ───
class TestHubManagerHubId:
    created_id = None

    def test_seeded_hms_have_hub_id(self, client):
        r = client.get(f"{API}/hub-managers")
        assert r.status_code == 200
        hms = r.json()
        assert len(hms) >= 2
        # at least one HM should have a hub_id populated (per seed)
        with_hub = [h for h in hms if h.get("hub_id")]
        assert len(with_hub) >= 1, f"No HM has hub_id populated after seed: {hms}"

    def test_create_with_valid_hub_id(self, client, world):
        hub = world["hubs"][0]
        payload = {"name": "TEST_HM_NEW", "phone": "+6599990111", "hub_id": hub["id"]}
        r = client.post(f"{API}/hub-managers", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["hub_id"] == hub["id"]
        assert data["hub_name"] == hub["name"]
        TestHubManagerHubId.created_id = data["id"]

        # Verify via GET
        rr = client.get(f"{API}/hub-managers")
        found = next((x for x in rr.json() if x["id"] == data["id"]), None)
        assert found is not None
        assert found["hub_id"] == hub["id"]
        assert found["hub_name"] == hub["name"]

    def test_create_with_invalid_hub_id_returns_400(self, client):
        payload = {"name": "TEST_HM_BAD", "phone": "+6599990222", "hub_id": "non-existent-hub-id-xyz"}
        r = client.post(f"{API}/hub-managers", json=payload)
        assert r.status_code == 400, r.text
        assert r.json().get("detail") == "Selected hub does not exist"

    def test_update_hub_id_updates_hub_name(self, client, world):
        assert TestHubManagerHubId.created_id is not None, "previous create must succeed"
        # find a different hub
        hms = client.get(f"{API}/hub-managers").json()
        cur = next(h for h in hms if h["id"] == TestHubManagerHubId.created_id)
        other_hub = next(h for h in world["hubs"] if h["id"] != cur["hub_id"])
        payload = {"name": cur["name"], "phone": cur["phone"], "hub_id": other_hub["id"]}
        r = client.put(f"{API}/hub-managers/{cur['id']}", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["hub_id"] == other_hub["id"]
        assert data["hub_name"] == other_hub["name"]

        # cleanup
        client.delete(f"{API}/hub-managers/{cur['id']}")


# ─── Regression: existing endpoints still ok ───
class TestRegression:
    def test_stats_ok(self, client):
        r = client.get(f"{API}/stats")
        assert r.status_code == 200

    def test_hubs_ok(self, client):
        r = client.get(f"{API}/hubs")
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_drivers_ok(self, client):
        r = client.get(f"{API}/drivers")
        assert r.status_code == 200

    def test_vehicles_ok(self, client):
        r = client.get(f"{API}/vehicles")
        assert r.status_code == 200

    def test_unassign_idempotent(self, client):
        vehicles = client.get(f"{API}/vehicles").json()
        v = vehicles[0]
        r = client.post(f"{API}/vehicles/{v['id']}/unassign")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
