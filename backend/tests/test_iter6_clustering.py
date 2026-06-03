"""Iter-6 tests for the new zone+hub clustering & routing flow."""
from __future__ import annotations

import os
from collections import Counter

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def seeded(session):
    r = session.post(f"{API}/seed")
    assert r.status_code == 200, r.text
    return r.json()


def _get(session, path):
    r = session.get(f"{API}{path}")
    assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"
    return r.json()


# ---------- Clustering ----------
class TestClustering:
    def test_cluster_returns_zone_and_hub_keys(self, session, seeded):
        r = session.post(f"{API}/orders/cluster", json={})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "unassigned" in data
        assert isinstance(data.get("clusters"), list)
        # Should have at least 2 clusters (Central CBD + North-West)
        assert data["count"] >= 2
        for c in data["clusters"]:
            assert c["zone_id"]
            assert c["zone_name"]
            assert c["hub_id"]
            assert c["hub_name"]

    def test_cluster_correctness_central_and_northwest(self, session, seeded):
        session.post(f"{API}/orders/cluster", json={})
        clusters = _get(session, "/clusters")
        orders = _get(session, "/orders")
        orders_by_code = {o["code"]: o for o in orders}
        clusters_by_id = {c["id"]: c for c in clusters}

        # ORD-00001 / 00005 / 00006 → Central CBD / Central Hub · Queenstown
        for code in ("ORD-00001", "ORD-00005", "ORD-00006"):
            o = orders_by_code[code]
            assert o.get("cluster_id"), f"{code} not clustered"
            c = clusters_by_id[o["cluster_id"]]
            assert c["zone_name"] == "Central CBD", f"{code} zone={c['zone_name']}"
            assert c["hub_name"] == "Central Hub · Queenstown", f"{code} hub={c['hub_name']}"

        # ORD-00010 → North-West / West Hub · Jurong
        o = orders_by_code["ORD-00010"]
        assert o.get("cluster_id")
        c = clusters_by_id[o["cluster_id"]]
        assert c["zone_name"] == "North-West"
        assert c["hub_name"] == "West Hub · Jurong"

    def test_unassigned_count_for_out_of_zone_orders(self, session, seeded):
        r = session.post(f"{API}/orders/cluster", json={}).json()
        # Of 15 seeded orders only 4 fall inside zones
        assert r["unassigned"] >= 8  # most orders outside


# ---------- Re-clustering preservation ----------
class TestReClusterPreserve:
    def test_in_flight_clusters_preserved(self, session, seeded):
        # 1) seed already done
        # 2) cluster
        session.post(f"{API}/orders/cluster", json={})
        # 3) assign-auto -> moves orders to "assigned"
        r = session.post(f"{API}/orders/assign-auto")
        assert r.status_code == 200, r.text
        first_clusters = _get(session, "/clusters")
        first_ids = {c["id"] for c in first_clusters}
        assert first_ids, "expected at least one cluster after first round"

        # 4) cluster again — clusters with non-pending orders must persist
        session.post(f"{API}/orders/cluster", json={})
        second_clusters = _get(session, "/clusters")
        second_ids = {c["id"] for c in second_clusters}
        # The clusters that had assigned orders must still be there.
        preserved = first_ids & second_ids
        assert preserved, f"expected preserved cluster ids, first={first_ids}, second={second_ids}"


# ---------- Assignment: strict zone match ----------
class TestStrictZoneAssign:
    def test_strict_zone_assignment(self, session, seeded):
        # Re-seed because the prior class assigned orders -> no pending left
        session.post(f"{API}/seed")
        session.post(f"{API}/orders/cluster", json={})
        r = session.post(f"{API}/orders/assign-auto")
        assert r.status_code == 200
        data = r.json()
        assignments = data.get("assignments", [])
        skipped = data.get("skipped", [])

        drivers = _get(session, "/drivers")
        d_by_name = {d["name"]: d for d in drivers}
        clusters = _get(session, "/clusters")
        c_by_id = {c["id"]: c for c in clusters}
        zones = {z["id"]: z for z in _get(session, "/zones")}

        # Every assignment must have driver.zone_id == cluster.zone_id
        for a in assignments:
            c = c_by_id[a["cluster_id"]]
            # find the driver by id
            drv = next(d for d in drivers if d["id"] == a["driver_id"])
            assert drv.get("zone_id") == c.get("zone_id"), (
                f"zone mismatch — driver {drv['name']} zone={drv.get('zone_id')} cluster zone={c.get('zone_id')}"
            )

        # Skipped entries must carry zone_id and hub_id keys
        for s in skipped:
            assert "zone_id" in s
            assert "hub_id" in s

        # Kumar Das (Central CBD zone) should have at least one Central CBD assignment
        kumar = d_by_name["Kumar Das"]
        siti = d_by_name["Siti Nurhaliza"]
        central_zone_id = kumar.get("zone_id")
        north_zone_id = siti.get("zone_id")
        assert zones[central_zone_id]["name"] == "Central CBD"
        assert zones[north_zone_id]["name"] == "North-West"

        kumar_clusters = [a for a in assignments if a["driver_id"] == kumar["id"]]
        siti_clusters = [a for a in assignments if a["driver_id"] == siti["id"]]
        # At least the Central CBD cluster goes to a Central CBD driver
        central_assigned = [a for a in assignments if c_by_id[a["cluster_id"]]["zone_id"] == central_zone_id]
        north_assigned = [a for a in assignments if c_by_id[a["cluster_id"]]["zone_id"] == north_zone_id]
        assert central_assigned, "expected Central CBD cluster to be assigned"
        assert north_assigned, "expected North-West cluster to be assigned"
        # And those assignments are to Central/North drivers respectively
        for a in central_assigned:
            drv = next(d for d in drivers if d["id"] == a["driver_id"])
            assert drv["zone_id"] == central_zone_id
        for a in north_assigned:
            drv = next(d for d in drivers if d["id"] == a["driver_id"])
            assert drv["zone_id"] == north_zone_id


# ---------- Routing /plan derives hub from cluster ----------
class TestRoutingDerivesHub:
    def test_plan_route_uses_cluster_hub(self, session, seeded):
        session.post(f"{API}/seed")
        session.post(f"{API}/orders/cluster", json={})
        session.post(f"{API}/orders/assign-auto")
        drivers = _get(session, "/drivers")
        kumar = next(d for d in drivers if d["name"] == "Kumar Das")
        # Verify kumar has active orders
        kumar_orders = [o for o in _get(session, "/orders")
                        if o.get("driver_id") == kumar["id"] and o.get("status") in ("assigned", "delivering")]
        assert kumar_orders, "Kumar Das has no assigned orders — assignment step did not work"

        r = session.post(f"{API}/routing/plan", json={"driver_id": kumar["id"], "mode": "time"})
        assert r.status_code == 200, r.text
        route = r.json()
        # First waypoint must equal Central Hub · Queenstown coordinates 1.3053, 103.8198
        first_wp = route["waypoints"][0]
        assert abs(first_wp[0] - 1.3053) < 1e-4, f"lat={first_wp[0]}"
        assert abs(first_wp[1] - 103.8198) < 1e-4, f"lng={first_wp[1]}"

    def test_plan_route_ignores_extra_hub_id(self, session, seeded):
        session.post(f"{API}/orders/cluster", json={})
        session.post(f"{API}/orders/assign-auto")
        drivers = _get(session, "/drivers")
        kumar = next(d for d in drivers if d["name"] == "Kumar Das")
        # Pydantic should ignore unknown fields (default model_config) — won't raise
        r = session.post(
            f"{API}/routing/plan",
            json={"driver_id": kumar["id"], "mode": "time", "hub_id": "bogus-hub-id"},
        )
        assert r.status_code == 200, f"Pydantic must ignore extra field; got {r.status_code} {r.text}"


# ---------- Regression endpoints ----------
class TestRegression:
    def test_get_clusters(self, session, seeded):
        r = session.get(f"{API}/clusters")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_stats(self, session, seeded):
        r = session.get(f"{API}/stats")
        assert r.status_code == 200

    def test_vehicle_license_mismatch_still_400(self, session, seeded):
        vehicles = _get(session, "/vehicles")
        drivers = _get(session, "/drivers")
        # Find a motorbike and a C-license driver — mismatch
        moto = next(v for v in vehicles if v["type"] == "motorbike")
        # unassign first if assigned
        if moto.get("assigned_driver_id"):
            session.post(f"{API}/vehicles/{moto['id']}/unassign")
        c_drv = next(d for d in drivers if d["license_type"] == "C")
        r = session.post(f"{API}/vehicles/{moto['id']}/assign", json={"driver_id": c_drv["id"]})
        assert r.status_code == 400, f"expected 400 license mismatch, got {r.status_code} {r.text}"

    def test_hub_manager_bad_hub_id_400(self, session, seeded):
        r = session.post(
            f"{API}/hub-managers",
            json={"name": "TEST_HM_bad", "phone": "+6599999999", "hub_id": "nonexistent-hub-id"},
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_drivers_zones_hubs_crud_listing(self, session, seeded):
        for path in ("/drivers", "/zones", "/hubs"):
            r = session.get(f"{API}{path}")
            assert r.status_code == 200, path
            assert isinstance(r.json(), list)
