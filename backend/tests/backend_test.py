"""LionCity AI-Logistics backend tests — FR-01..FR-20."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BACKEND_URL") or "https://reverent-noyce-9.preview.emergentagent.com"
API = f"{BASE_URL.rstrip('/')}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session", autouse=True)
def seed(client):
    # Reseed at session start so clusters/routes fixtures are clean
    r = client.post(f"{API}/seed", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ───── Core / stats ─────
class TestHealth:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("service") == "LionCity AI-Logistics"

    def test_stats(self, client):
        r = client.get(f"{API}/stats")
        assert r.status_code == 200
        d = r.json()
        assert d["hub_managers"] >= 2
        assert d["drivers"] >= 6
        assert d["vehicles"] >= 6
        assert d["zones"] >= 3
        assert d["orders_pending"] >= 15 or (d["orders_pending"] + d["orders_assigned"]) >= 15


# ───── FR-01/02 Hub Managers ─────
class TestHubManagers:
    created_id = None

    def test_list_seeded(self, client):
        r = client.get(f"{API}/hub-managers")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_create(self, client):
        payload = {"name": "TEST_HM", "phone": "+6599990001", "hub_name": "TestHub"}
        r = client.post(f"{API}/hub-managers", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["phone"] == payload["phone"]
        TestHubManagers.created_id = data["id"]

    def test_duplicate_phone(self, client):
        payload = {"name": "TEST_HM_DUP", "phone": "+6599990001"}
        r = client.post(f"{API}/hub-managers", json=payload)
        assert r.status_code == 400
        assert "Phone" in r.json().get("detail", "")

    def test_update(self, client):
        hid = TestHubManagers.created_id
        r = client.put(f"{API}/hub-managers/{hid}", json={
            "name": "TEST_HM_UPD", "phone": "+6599990001", "hub_name": "X"
        })
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_HM_UPD"

    def test_delete(self, client):
        hid = TestHubManagers.created_id
        r = client.delete(f"{API}/hub-managers/{hid}")
        assert r.status_code == 200


# ───── FR-03..FR-05 Drivers ─────
class TestDrivers:
    created_id = None

    def test_list(self, client):
        r = client.get(f"{API}/drivers")
        assert r.status_code == 200
        assert len(r.json()) >= 6

    def test_create_and_status(self, client):
        r = client.post(f"{API}/drivers", json={
            "name": "TEST_Driver", "phone": "+6599880001", "license_type": "B"
        })
        assert r.status_code == 200
        d = r.json()
        TestDrivers.created_id = d["id"]

        # duplicate phone
        r2 = client.post(f"{API}/drivers", json={
            "name": "TEST_Driver2", "phone": "+6599880001", "license_type": "B"
        })
        assert r2.status_code == 400

        # status update
        rs = client.put(f"{API}/drivers/{d['id']}/status", json={"status": "off_duty"})
        assert rs.status_code == 200
        assert rs.json()["status"] == "off_duty"

    def test_location_update(self, client):
        did = TestDrivers.created_id
        r = client.put(f"{API}/drivers/{did}/location", json={"lat": 1.30, "lng": 103.85})
        assert r.status_code == 200
        assert r.json()["location"]["lat"] == 1.30

    def test_delete(self, client):
        r = client.delete(f"{API}/drivers/{TestDrivers.created_id}")
        assert r.status_code == 200


# ───── FR-06..FR-08 Vehicles ─────
class TestVehicles:
    created_id = None

    def test_list(self, client):
        r = client.get(f"{API}/vehicles")
        assert r.status_code == 200
        assert len(r.json()) >= 6

    def test_create(self, client):
        r = client.post(f"{API}/vehicles", json={
            "plate": "TEST 9999 X", "type": "van", "fuel_type": "ev", "capacity_kg": 500
        })
        assert r.status_code == 200
        TestVehicles.created_id = r.json()["id"]

    def test_assign_swap(self, client):
        # Pick two vehicles + a driver, assign v1→drv, then v2→drv, verify v1 unassigned
        drivers = client.get(f"{API}/drivers").json()
        vehicles = client.get(f"{API}/vehicles").json()
        drv = drivers[0]
        # unassign current linkage on driver + free two vehicles
        if drv.get("vehicle_id"):
            client.post(f"{API}/vehicles/{drv['vehicle_id']}/unassign")
        # forcibly free two vehicles for the swap test
        for v in vehicles[:2]:
            client.post(f"{API}/vehicles/{v['id']}/unassign")
        vehicles = client.get(f"{API}/vehicles").json()
        v_free = [v for v in vehicles if not v.get("assigned_driver_id")]
        assert len(v_free) >= 2
        v1, v2 = v_free[0], v_free[1]
        r1 = client.post(f"{API}/vehicles/{v1['id']}/assign", json={"driver_id": drv["id"]})
        assert r1.status_code == 200
        r2 = client.post(f"{API}/vehicles/{v2['id']}/assign", json={"driver_id": drv["id"]})
        assert r2.status_code == 200
        # verify
        v1_now = client.get(f"{API}/vehicles").json()
        v1_new = next(v for v in v1_now if v["id"] == v1["id"])
        v2_new = next(v for v in v1_now if v["id"] == v2["id"])
        assert v1_new["assigned_driver_id"] is None
        assert v2_new["assigned_driver_id"] == drv["id"]

    def test_delete(self, client):
        r = client.delete(f"{API}/vehicles/{TestVehicles.created_id}")
        assert r.status_code == 200


# ───── FR-09..FR-11 Zones ─────
class TestZones:
    created_id = None

    def test_list(self, client):
        r = client.get(f"{API}/zones")
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_crud_and_driver_assign(self, client):
        r = client.post(f"{API}/zones", json={
            "name": "TEST_Zone",
            "polygon": [[1.4, 103.8], [1.4, 103.85], [1.38, 103.85], [1.38, 103.8]],
            "color": "#123456",
        })
        assert r.status_code == 200
        z = r.json()
        assert z["center"] and len(z["center"]) == 2
        TestZones.created_id = z["id"]

        drivers = client.get(f"{API}/drivers").json()
        drv = drivers[0]
        r1 = client.post(f"{API}/zones/{z['id']}/assign-driver", json={"driver_id": drv["id"]})
        assert r1.status_code == 200
        zones_now = client.get(f"{API}/zones").json()
        z_upd = next(x for x in zones_now if x["id"] == z["id"])
        assert drv["id"] in z_upd["driver_ids"]
        r2 = client.post(f"{API}/zones/{z['id']}/unassign-driver", json={"driver_id": drv["id"]})
        assert r2.status_code == 200

    def test_delete(self, client):
        r = client.delete(f"{API}/zones/{TestZones.created_id}")
        assert r.status_code == 200


# ───── FR-12..FR-16 Orders, Cluster, Assign ─────
class TestOrdersFlow:
    def test_create_order(self, client):
        r = client.post(f"{API}/orders", json={
            "address": "TEST addr", "postal_code": "018956",
            "lat": 1.2837, "lng": 103.8591, "weight_kg": 2.0,
            "required_by": "2026-02-01T10:00:00Z",
        })
        assert r.status_code == 200
        assert r.json()["code"].startswith("ORD-")

    def test_cluster(self, client):
        r = client.post(f"{API}/orders/cluster", json={"max_distance_m": 2500})
        assert r.status_code == 200
        d = r.json()
        assert d.get("count", 0) >= 1
        assert len(d["clusters"]) >= 1
        assert all("order_ids" in c and "centroid" in c for c in d["clusters"])

    def test_assign_auto(self, client):
        r = client.post(f"{API}/orders/assign-auto")
        assert r.status_code == 200
        d = r.json()
        assert d.get("count", 0) >= 1
        # verify orders now have driver_id + assigned status
        orders = client.get(f"{API}/orders?status=assigned").json()
        assert len(orders) > 0

    def test_assign_manual_and_status_update(self, client):
        # pick a pending order (cluster ran, some may remain if drivers < clusters)
        pending = client.get(f"{API}/orders?status=pending").json()
        drivers = client.get(f"{API}/drivers").json()
        if pending:
            oids = [o["id"] for o in pending[:2]]
            r = client.post(f"{API}/orders/assign-manual", json={
                "driver_id": drivers[0]["id"], "order_ids": oids,
            })
            assert r.status_code == 200
            assert r.json()["assigned"] == len(oids)

        # FR-14 delivered + proof
        assigned = client.get(f"{API}/orders?status=assigned").json()
        assert assigned, "Should have assigned orders"
        target = assigned[0]
        r = client.put(f"{API}/orders/{target['id']}/status", json={
            "status": "delivered",
            "proof_photo": "data:image/png;base64,iVBORw0KGgo=",
            "proof_signature": "John Doe",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"
        assert r.json()["proof_photo"] is not None


# ───── FR-17 Routing (with OSRM fallback) ─────
class TestRouting:
    @pytest.mark.parametrize("mode", ["time", "eco", "avoid_erp"])
    def test_plan_route(self, client, mode):
        # find a driver with assigned orders
        drivers = client.get(f"{API}/drivers").json()
        target = None
        for d in drivers:
            orders = client.get(f"{API}/orders", params={"driver_id": d["id"], "status": "assigned"}).json()
            if orders:
                target = d
                break
        assert target, "Need at least one driver with assigned orders"
        r = client.post(f"{API}/routing/plan", json={"driver_id": target["id"], "mode": mode}, timeout=30)
        assert r.status_code == 200, r.text
        rt = r.json()
        assert rt["mode"] == mode
        assert rt["distance_m"] > 0
        assert rt["duration_s"] > 0
        assert len(rt["geometry"]) > 2
        assert len(rt["ordered_order_ids"]) > 0

    def test_simulate_step_and_shipper(self, client):
        drivers = client.get(f"{API}/drivers").json()
        # Pick a driver with route
        for d in drivers:
            rr = client.get(f"{API}/routing/{d['id']}")
            if rr.status_code == 200:
                r = client.post(f"{API}/drivers/{d['id']}/simulate-step", json={"step_m": 300})
                assert r.status_code == 200
                assert "location" in r.json()
                # FR-19 shipper inbox
                s = client.get(f"{API}/shipper/{d['id']}/orders")
                assert s.status_code == 200
                body = s.json()
                assert "orders" in body and "route" in body
                return
        pytest.skip("No driver with route for simulate step")


# ───── LTA passthrough ─────
class TestLTA:
    def test_incidents(self, client):
        r = client.get(f"{API}/lta/incidents", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_speed_bands(self, client):
        r = client.get(f"{API}/lta/speed-bands", timeout=45)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_erp_rates(self, client):
        r = client.get(f"{API}/lta/erp-rates", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
