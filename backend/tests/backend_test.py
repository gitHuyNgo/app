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


# ───── NEW: Hubs CRUD + default enforcement ─────
class TestHubs:
    def test_list_seeded_hubs(self, client):
        r = client.get(f"{API}/hubs")
        assert r.status_code == 200
        hubs = r.json()
        assert len(hubs) >= 3
        defaults = [h for h in hubs if h.get("is_default")]
        assert len(defaults) == 1, f"Expected exactly one default hub, got {len(defaults)}"

    def test_create_hub_and_persist(self, client):
        payload = {"name": "TEST_Hub_North", "address": "TEST addr", "lat": 1.44, "lng": 103.80, "is_default": False}
        r = client.post(f"{API}/hubs", json=payload)
        assert r.status_code == 200, r.text
        h = r.json()
        assert h["name"] == payload["name"]
        assert h["lat"] == 1.44 and h["lng"] == 103.80
        hid = h["id"]
        # GET verify persisted
        all_hubs = client.get(f"{API}/hubs").json()
        assert any(x["id"] == hid for x in all_hubs)
        # cleanup
        client.delete(f"{API}/hubs/{hid}")

    def test_default_enforcement_on_create(self, client):
        # create a hub with is_default=true, previous default should be unset
        before = client.get(f"{API}/hubs").json()
        old_default = next((h for h in before if h.get("is_default")), None)
        payload = {"name": "TEST_Hub_Default", "address": "x", "lat": 1.30, "lng": 103.80, "is_default": True}
        r = client.post(f"{API}/hubs", json=payload)
        assert r.status_code == 200
        new_hub = r.json()
        assert new_hub["is_default"] is True
        after = client.get(f"{API}/hubs").json()
        defaults = [h for h in after if h.get("is_default")]
        assert len(defaults) == 1 and defaults[0]["id"] == new_hub["id"]
        # restore old default & delete test hub
        if old_default:
            client.put(f"{API}/hubs/{old_default['id']}", json={**old_default, "is_default": True})
        client.delete(f"{API}/hubs/{new_hub['id']}")

    def test_update_hub(self, client):
        hubs = client.get(f"{API}/hubs").json()
        target = next(h for h in hubs if not h.get("is_default"))
        body = {**{k: target[k] for k in ("name", "address", "lat", "lng", "is_default", "notes")}, "notes": "TEST_updated"}
        r = client.put(f"{API}/hubs/{target['id']}", json=body)
        assert r.status_code == 200
        assert r.json()["notes"] == "TEST_updated"
        # GET verify
        got = [h for h in client.get(f"{API}/hubs").json() if h["id"] == target["id"]][0]
        assert got["notes"] == "TEST_updated"

    def test_delete_default_promotes_another(self, client):
        # create two hubs: one default, then delete it, expect promotion
        h1 = client.post(f"{API}/hubs", json={"name": "TEST_DD1", "lat": 1.3, "lng": 103.8, "is_default": False}).json()
        h2 = client.post(f"{API}/hubs", json={"name": "TEST_DD2", "lat": 1.31, "lng": 103.81, "is_default": True}).json()
        # delete default h2
        r = client.delete(f"{API}/hubs/{h2['id']}")
        assert r.status_code == 200
        after = client.get(f"{API}/hubs").json()
        defaults = [h for h in after if h.get("is_default")]
        assert len(defaults) == 1, f"Expected promotion, got {len(defaults)} defaults"
        # cleanup
        client.delete(f"{API}/hubs/{h1['id']}")
        # re-establish original default (first seeded hub)
        seeded = client.get(f"{API}/hubs").json()
        if seeded and not any(h.get("is_default") for h in seeded):
            first = seeded[0]
            client.put(f"{API}/hubs/{first['id']}", json={**{k: first[k] for k in ("name","address","lat","lng","notes")}, "is_default": True})


# ───── NEW: Geocode graceful fallback ─────
class TestGeocode:
    def test_geocode_returns_json_no_500(self, client):
        r = client.get(f"{API}/geocode", params={"q": "Marina Bay Sands"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "results" in body
        # Either results present or graceful error string, but never 500
        assert isinstance(body["results"], list)

    def test_geocode_validation(self, client):
        r = client.get(f"{API}/geocode", params={"q": "ab"})
        assert r.status_code == 422  # pydantic min_length=3


# ───── NEW: Routing with explicit hub_id ─────
class TestRoutingWithHub:
    def test_plan_with_non_default_hub(self, client):
        client.post(f"{API}/orders/cluster", json={"max_distance_m": 3000})
        client.post(f"{API}/orders/assign-auto")
        orders = client.get(f"{API}/orders").json()
        assigned = [o for o in orders if o.get("driver_id") and o["status"] == "assigned"]
        if not assigned:
            pytest.skip("No assigned orders")
        did = assigned[0]["driver_id"]
        hubs = client.get(f"{API}/hubs").json()
        non_default = [h for h in hubs if not h.get("is_default")]
        if not non_default:
            pytest.skip("No non-default hub")
        hub = non_default[0]
        r = client.post(f"{API}/routing/plan", json={"driver_id": did, "mode": "eco", "hub_id": hub["id"]}, timeout=30)
        assert r.status_code == 200, r.text
        route = r.json()
        assert len(route["waypoints"]) >= 2
        start = route["waypoints"][0]
        # first waypoint should be the chosen hub
        assert abs(start[0] - hub["lat"]) < 1e-4 and abs(start[1] - hub["lng"]) < 1e-4

    def test_plan_without_hub_uses_default(self, client):
        orders = client.get(f"{API}/orders").json()
        assigned = [o for o in orders if o.get("driver_id") and o["status"] in ("assigned", "delivering")]
        if not assigned:
            pytest.skip("No assigned orders")
        did = assigned[0]["driver_id"]
        hubs = client.get(f"{API}/hubs").json()
        default = next((h for h in hubs if h.get("is_default")), None)
        assert default is not None
        r = client.post(f"{API}/routing/plan", json={"driver_id": did, "mode": "time"}, timeout=30)
        assert r.status_code == 200
        start = r.json()["waypoints"][0]
        assert abs(start[0] - default["lat"]) < 1e-4 and abs(start[1] - default["lng"]) < 1e-4
