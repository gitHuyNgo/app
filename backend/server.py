"""
LionCity AI-Logistics — Hub & Delivery Coordination Backend
Implements FR-01 .. FR-20 against MongoDB with LTA DataMall + OSRM routing.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import math
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Tuple
from datetime import datetime, timezone
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
LTA_KEY = os.environ.get('LTA_ACCOUNT_KEY', '')
OSRM_BASE = os.environ.get('OSRM_BASE_URL', 'https://router.project-osrm.org')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="LionCity AI-Logistics")
api = APIRouter(prefix="/api")

logger = logging.getLogger("lioncity")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s — %(message)s')


# ───────────────────────────── Models ─────────────────────────────
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HubManager(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    status: Literal["available", "off_duty"] = "available"
    hub_name: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class HubManagerIn(BaseModel):
    name: str
    phone: str
    status: Optional[Literal["available", "off_duty"]] = "available"
    hub_name: Optional[str] = None


class Driver(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    license_type: Literal["A", "B", "C"] = "B"  # A=motorbike B=car C=van
    status: Literal["available", "delivering", "off_duty"] = "available"
    vehicle_id: Optional[str] = None
    zone_id: Optional[str] = None
    location: Optional[dict] = None  # {lat, lng, updated_at}
    hub_manager_id: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class DriverIn(BaseModel):
    name: str
    phone: str
    license_type: Literal["A", "B", "C"] = "B"
    hub_manager_id: Optional[str] = None


class Vehicle(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plate: str
    type: Literal["motorbike", "van"]
    fuel_type: Literal["ev", "diesel"]
    capacity_kg: float
    assigned_driver_id: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class VehicleIn(BaseModel):
    plate: str
    type: Literal["motorbike", "van"]
    fuel_type: Literal["ev", "diesel"]
    capacity_kg: float


class Zone(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    polygon: List[List[float]]  # [[lat, lng], ...]
    center: List[float]  # [lat, lng]
    driver_ids: List[str] = []
    color: str = "#0ea5a4"
    created_at: str = Field(default_factory=now_iso)


class ZoneIn(BaseModel):
    name: str
    polygon: List[List[float]]
    color: Optional[str] = "#0ea5a4"


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    address: str
    postal_code: str
    lat: float
    lng: float
    weight_kg: float
    required_by: str  # ISO
    status: Literal["pending", "assigned", "delivering", "delivered", "failed"] = "pending"
    cluster_id: Optional[str] = None
    driver_id: Optional[str] = None
    sequence: Optional[int] = None
    proof_photo: Optional[str] = None
    proof_signature: Optional[str] = None
    fail_reason: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class OrderIn(BaseModel):
    address: str
    postal_code: str
    lat: float
    lng: float
    weight_kg: float
    required_by: str


class Cluster(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    order_ids: List[str]
    centroid: List[float]
    created_at: str = Field(default_factory=now_iso)


class RouteRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    driver_id: str
    mode: Literal["time", "eco", "avoid_erp"]
    waypoints: List[List[float]]  # [[lat,lng],...]
    ordered_order_ids: List[str]
    distance_m: float
    duration_s: float
    geometry: List[List[float]]  # [[lat,lng],...]
    created_at: str = Field(default_factory=now_iso)


# ───────────────────────────── Helpers ─────────────────────────────
def haversine(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    R = 6371000.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


async def find_list(coll, q=None):
    q = q or {}
    return await db[coll].find(q, {"_id": 0}).to_list(10000)


async def find_one(coll, q):
    return await db[coll].find_one(q, {"_id": 0})


async def unique_phone(coll, phone, exclude_id=None):
    q = {"phone": phone}
    if exclude_id:
        q["id"] = {"$ne": exclude_id}
    exists = await db[coll].find_one(q, {"_id": 0})
    return exists is None


# ───────────────────────────── Root ─────────────────────────────
HUB_LOCATION = {"lat": 1.3521, "lng": 103.8198, "name": "Central Singapore Hub"}


@api.get("/")
async def root():
    return {"service": "LionCity AI-Logistics", "hub": HUB_LOCATION}


# ───────────────────────────── FR-01 / FR-02 Hub Managers ─────────────────────────────
@api.post("/hub-managers", response_model=HubManager)
async def create_hub_manager(data: HubManagerIn):
    if not await unique_phone("hub_managers", data.phone):
        raise HTTPException(400, "Phone already exists")
    hm = HubManager(**data.model_dump())
    await db.hub_managers.insert_one(hm.model_dump())
    return hm


@api.get("/hub-managers", response_model=List[HubManager])
async def list_hub_managers():
    return await find_list("hub_managers")


@api.put("/hub-managers/{hm_id}", response_model=HubManager)
async def update_hub_manager(hm_id: str, data: HubManagerIn):
    if not await unique_phone("hub_managers", data.phone, exclude_id=hm_id):
        raise HTTPException(400, "Phone already exists")
    upd = {k: v for k, v in data.model_dump().items() if v is not None}
    res = await db.hub_managers.find_one_and_update(
        {"id": hm_id}, {"$set": upd}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


@api.delete("/hub-managers/{hm_id}")
async def delete_hub_manager(hm_id: str):
    await db.hub_managers.delete_one({"id": hm_id})
    return {"ok": True}


# ───────────────────────────── FR-03 / FR-04 / FR-05 Drivers ─────────────────────────────
@api.post("/drivers", response_model=Driver)
async def create_driver(data: DriverIn):
    if not await unique_phone("drivers", data.phone):
        raise HTTPException(400, "Phone already exists")
    d = Driver(**data.model_dump())
    await db.drivers.insert_one(d.model_dump())
    return d


@api.get("/drivers", response_model=List[Driver])
async def list_drivers():
    return await find_list("drivers")


@api.put("/drivers/{did}", response_model=Driver)
async def update_driver(did: str, data: DriverIn):
    if not await unique_phone("drivers", data.phone, exclude_id=did):
        raise HTTPException(400, "Phone already exists")
    res = await db.drivers.find_one_and_update(
        {"id": did}, {"$set": data.model_dump()}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


@api.delete("/drivers/{did}")
async def delete_driver(did: str):
    # unassign vehicle
    await db.vehicles.update_many({"assigned_driver_id": did}, {"$set": {"assigned_driver_id": None}})
    await db.zones.update_many({}, {"$pull": {"driver_ids": did}})
    await db.drivers.delete_one({"id": did})
    return {"ok": True}


class DriverStatusIn(BaseModel):
    status: Literal["available", "delivering", "off_duty"]


@api.put("/drivers/{did}/status")
async def update_driver_status(did: str, body: DriverStatusIn):
    res = await db.drivers.find_one_and_update(
        {"id": did}, {"$set": {"status": body.status}}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


class LocationIn(BaseModel):
    lat: float
    lng: float


# FR-18 real-time GPS push
@api.put("/drivers/{did}/location")
async def update_driver_location(did: str, body: LocationIn):
    loc = {"lat": body.lat, "lng": body.lng, "updated_at": now_iso()}
    res = await db.drivers.find_one_and_update(
        {"id": did}, {"$set": {"location": loc}}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


@api.get("/drivers/locations")
async def drivers_locations():
    drivers = await find_list("drivers")
    return [
        {"id": d["id"], "name": d["name"], "status": d["status"], "location": d.get("location"),
         "vehicle_id": d.get("vehicle_id"), "zone_id": d.get("zone_id")}
        for d in drivers if d.get("location")
    ]


# ───────────────────────────── FR-06 / FR-07 / FR-08 Vehicles ─────────────────────────────
@api.post("/vehicles", response_model=Vehicle)
async def create_vehicle(data: VehicleIn):
    v = Vehicle(**data.model_dump())
    await db.vehicles.insert_one(v.model_dump())
    return v


@api.get("/vehicles", response_model=List[Vehicle])
async def list_vehicles():
    return await find_list("vehicles")


@api.delete("/vehicles/{vid}")
async def delete_vehicle(vid: str):
    # unassign from driver
    v = await find_one("vehicles", {"id": vid})
    if v and v.get("assigned_driver_id"):
        await db.drivers.update_one({"id": v["assigned_driver_id"]}, {"$set": {"vehicle_id": None}})
    await db.vehicles.delete_one({"id": vid})
    return {"ok": True}


class AssignVehicleIn(BaseModel):
    driver_id: str


@api.post("/vehicles/{vid}/assign")
async def assign_vehicle(vid: str, body: AssignVehicleIn):
    vehicle = await find_one("vehicles", {"id": vid})
    driver = await find_one("drivers", {"id": body.driver_id})
    if not vehicle or not driver:
        raise HTTPException(404, "Vehicle or driver not found")
    # driver can have only 1 vehicle → unassign previous
    if driver.get("vehicle_id"):
        await db.vehicles.update_one({"id": driver["vehicle_id"]}, {"$set": {"assigned_driver_id": None}})
    # vehicle had previous driver → unassign
    if vehicle.get("assigned_driver_id"):
        await db.drivers.update_one({"id": vehicle["assigned_driver_id"]}, {"$set": {"vehicle_id": None}})
    await db.vehicles.update_one({"id": vid}, {"$set": {"assigned_driver_id": body.driver_id}})
    await db.drivers.update_one({"id": body.driver_id}, {"$set": {"vehicle_id": vid}})
    return {"ok": True}


@api.post("/vehicles/{vid}/unassign")
async def unassign_vehicle(vid: str):
    vehicle = await find_one("vehicles", {"id": vid})
    if vehicle and vehicle.get("assigned_driver_id"):
        await db.drivers.update_one({"id": vehicle["assigned_driver_id"]}, {"$set": {"vehicle_id": None}})
    await db.vehicles.update_one({"id": vid}, {"$set": {"assigned_driver_id": None}})
    return {"ok": True}


# ───────────────────────────── FR-09 / FR-10 / FR-11 Zones ─────────────────────────────
def polygon_centroid(poly: List[List[float]]) -> List[float]:
    if not poly:
        return [1.3521, 103.8198]
    lat = sum(p[0] for p in poly) / len(poly)
    lng = sum(p[1] for p in poly) / len(poly)
    return [lat, lng]


@api.post("/zones", response_model=Zone)
async def create_zone(data: ZoneIn):
    z = Zone(center=polygon_centroid(data.polygon), **data.model_dump())
    await db.zones.insert_one(z.model_dump())
    return z


@api.get("/zones", response_model=List[Zone])
async def list_zones():
    return await find_list("zones")


@api.put("/zones/{zid}", response_model=Zone)
async def update_zone(zid: str, data: ZoneIn):
    upd = data.model_dump()
    upd["center"] = polygon_centroid(data.polygon)
    res = await db.zones.find_one_and_update(
        {"id": zid}, {"$set": upd}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


@api.delete("/zones/{zid}")
async def delete_zone(zid: str):
    await db.drivers.update_many({"zone_id": zid}, {"$set": {"zone_id": None}})
    await db.zones.delete_one({"id": zid})
    return {"ok": True}


class AssignDriverZoneIn(BaseModel):
    driver_id: str


@api.post("/zones/{zid}/assign-driver")
async def assign_driver_to_zone(zid: str, body: AssignDriverZoneIn):
    zone = await find_one("zones", {"id": zid})
    if not zone:
        raise HTTPException(404, "Zone not found")
    # remove from previous zone
    await db.zones.update_many({}, {"$pull": {"driver_ids": body.driver_id}})
    await db.zones.update_one({"id": zid}, {"$addToSet": {"driver_ids": body.driver_id}})
    await db.drivers.update_one({"id": body.driver_id}, {"$set": {"zone_id": zid}})
    return {"ok": True}


@api.post("/zones/{zid}/unassign-driver")
async def unassign_driver_from_zone(zid: str, body: AssignDriverZoneIn):
    await db.zones.update_one({"id": zid}, {"$pull": {"driver_ids": body.driver_id}})
    await db.drivers.update_one({"id": body.driver_id}, {"$set": {"zone_id": None}})
    return {"ok": True}


# ───────────────────────────── FR-12 Warehouse Entry ─────────────────────────────
@api.post("/orders", response_model=Order)
async def create_order(data: OrderIn):
    count = await db.orders.count_documents({})
    code = f"ORD-{count+1:05d}"
    o = Order(code=code, **data.model_dump())
    await db.orders.insert_one(o.model_dump())
    return o


@api.get("/orders", response_model=List[Order])
async def list_orders(status: Optional[str] = None, driver_id: Optional[str] = None):
    q = {}
    if status:
        q["status"] = status
    if driver_id:
        q["driver_id"] = driver_id
    return await find_list("orders", q)


@api.delete("/orders/{oid}")
async def delete_order(oid: str):
    await db.orders.delete_one({"id": oid})
    return {"ok": True}


# ───────────────────────────── FR-13 Clustering ─────────────────────────────
class ClusterIn(BaseModel):
    max_distance_m: float = 2500.0


@api.post("/orders/cluster")
async def cluster_orders(body: ClusterIn):
    # clear previous clusters for pending orders
    await db.clusters.delete_many({})
    await db.orders.update_many({"status": "pending"}, {"$set": {"cluster_id": None}})

    pending = await find_list("orders", {"status": "pending"})
    if not pending:
        return {"clusters": [], "message": "No pending orders"}

    # group by postal-code sector (first 2 digits) then split by distance
    sectors = {}
    for o in pending:
        sec = (o.get("postal_code") or "00")[:2]
        sectors.setdefault(sec, []).append(o)

    clusters_out = []
    cluster_index = 1
    for sec, items in sectors.items():
        remaining = items.copy()
        while remaining:
            seed = remaining.pop(0)
            group = [seed]
            new_remaining = []
            for o in remaining:
                d = haversine((seed["lat"], seed["lng"]), (o["lat"], o["lng"]))
                if d <= body.max_distance_m:
                    group.append(o)
                else:
                    new_remaining.append(o)
            remaining = new_remaining
            centroid = [
                sum(g["lat"] for g in group) / len(group),
                sum(g["lng"] for g in group) / len(group),
            ]
            cl = Cluster(
                label=f"C{cluster_index:03d}-{sec}",
                order_ids=[g["id"] for g in group],
                centroid=centroid,
            )
            await db.clusters.insert_one(cl.model_dump())
            await db.orders.update_many(
                {"id": {"$in": cl.order_ids}}, {"$set": {"cluster_id": cl.id}}
            )
            clusters_out.append(cl.model_dump())
            cluster_index += 1
    return {"clusters": clusters_out, "count": len(clusters_out)}


@api.get("/clusters")
async def list_clusters():
    clusters = await find_list("clusters")
    # enrich with order count
    for c in clusters:
        c["order_count"] = len(c.get("order_ids", []))
    return clusters


# ───────────────────────────── FR-14 Update Order Status ─────────────────────────────
class OrderStatusIn(BaseModel):
    status: Literal["pending", "assigned", "delivering", "delivered", "failed"]
    fail_reason: Optional[str] = None
    proof_photo: Optional[str] = None
    proof_signature: Optional[str] = None


@api.put("/orders/{oid}/status")
async def update_order_status(oid: str, body: OrderStatusIn):
    upd = {"status": body.status}
    if body.fail_reason:
        upd["fail_reason"] = body.fail_reason
    if body.proof_photo:
        upd["proof_photo"] = body.proof_photo
    if body.proof_signature:
        upd["proof_signature"] = body.proof_signature
    res = await db.orders.find_one_and_update(
        {"id": oid}, {"$set": upd}, return_document=True, projection={"_id": 0}
    )
    if not res:
        raise HTTPException(404, "Not found")
    return res


# ───────────────────────────── FR-15 / FR-16 Assignment ─────────────────────────────
@api.post("/orders/assign-auto")
async def assign_auto():
    """Distribute pending clusters to available drivers (closest cluster centroid → driver zone center).
    If driver has no zone, use hub as fallback.
    """
    clusters = await find_list("clusters")
    # only clusters whose orders are still pending
    pending_clusters = []
    for c in clusters:
        orders_in = await find_list("orders", {"id": {"$in": c["order_ids"]}, "status": "pending"})
        if orders_in:
            pending_clusters.append({"cluster": c, "orders": orders_in})

    drivers = await find_list("drivers", {"status": "available"})
    # prefer drivers with a vehicle
    drivers.sort(key=lambda d: (d.get("vehicle_id") is None, d.get("name", "")))

    assignments = []
    used_drivers = set()
    for pc in pending_clusters:
        c = pc["cluster"]
        best = None
        best_d = float("inf")
        for drv in drivers:
            if drv["id"] in used_drivers:
                continue
            # reference point: zone center → else hub
            zone = None
            if drv.get("zone_id"):
                zone = await find_one("zones", {"id": drv["zone_id"]})
            ref = (zone["center"][0], zone["center"][1]) if zone else (HUB_LOCATION["lat"], HUB_LOCATION["lng"])
            dist = haversine(ref, (c["centroid"][0], c["centroid"][1]))
            if dist < best_d:
                best_d = dist
                best = drv
        if not best:
            continue
        used_drivers.add(best["id"])
        # assign all orders of cluster to driver
        await db.orders.update_many(
            {"id": {"$in": c["order_ids"]}},
            {"$set": {"driver_id": best["id"], "status": "assigned"}},
        )
        # driver status → delivering (will set when route starts; keep "available" until they start)
        assignments.append({
            "cluster_id": c["id"],
            "cluster_label": c["label"],
            "driver_id": best["id"],
            "driver_name": best["name"],
            "order_count": len(c["order_ids"]),
            "distance_to_cluster_m": round(best_d),
        })
    return {"assignments": assignments, "count": len(assignments)}


class ManualAssignIn(BaseModel):
    driver_id: str
    order_ids: List[str]


@api.post("/orders/assign-manual")
async def assign_manual(body: ManualAssignIn):
    drv = await find_one("drivers", {"id": body.driver_id})
    if not drv:
        raise HTTPException(404, "Driver not found")
    await db.orders.update_many(
        {"id": {"$in": body.order_ids}},
        {"$set": {"driver_id": body.driver_id, "status": "assigned"}},
    )
    return {"ok": True, "assigned": len(body.order_ids)}


# ───────────────────────────── FR-17 Routing (OSRM + LTA) ─────────────────────────────
async def fetch_lta(path: str, params: dict = None) -> list:
    if not LTA_KEY:
        return []
    headers = {"AccountKey": LTA_KEY, "accept": "application/json"}
    url = f"https://datamall2.mytransport.sg/ltaodataservice/{path}"
    results = []
    skip = 0
    async with httpx.AsyncClient(timeout=20) as client_http:
        # LTA returns max 500 per call with $skip
        while True:
            q = dict(params or {})
            q["$skip"] = skip
            try:
                r = await client_http.get(url, headers=headers, params=q)
                if r.status_code != 200:
                    logger.warning("LTA %s → %s", path, r.status_code)
                    break
                data = r.json().get("value", [])
            except Exception as e:
                logger.warning("LTA fetch error: %s", e)
                break
            if not data:
                break
            results.extend(data)
            if len(data) < 500:
                break
            skip += 500
            if skip >= 5000:  # safety cap
                break
    return results


async def osrm_route(coords: List[Tuple[float, float]], alternatives: bool = False) -> dict:
    """coords = list of (lat, lng). Returns OSRM JSON or None on failure."""
    if len(coords) < 2:
        raise HTTPException(400, "Need at least 2 points")
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in coords)
    params = {"overview": "full", "geometries": "geojson", "alternatives": str(alternatives).lower(), "steps": "false"}
    url = f"{OSRM_BASE}/route/v1/driving/{coord_str}"
    try:
        async with httpx.AsyncClient(timeout=6) as client_http:
            r = await client_http.get(url, params=params)
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as e:
        logger.info("OSRM unavailable, using fallback: %s", e)
        return None


async def osrm_trip(coords: List[Tuple[float, float]]) -> dict:
    """Solve TSP-like via OSRM /trip with fixed start (hub), optimized order of stops."""
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in coords)
    params = {
        "source": "first", "destination": "last", "roundtrip": "false",
        "overview": "full", "geometries": "geojson", "steps": "false",
    }
    url = f"{OSRM_BASE}/trip/v1/driving/{coord_str}"
    try:
        async with httpx.AsyncClient(timeout=6) as client_http:
            r = await client_http.get(url, params=params)
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as e:
        logger.info("OSRM /trip unavailable, using fallback: %s", e)
        return None


# ERP / CBD bbox used in avoid_erp detour
CBD_BBOX = {"min_lat": 1.270, "max_lat": 1.305, "min_lng": 103.830, "max_lng": 103.870}


def _in_cbd(lat: float, lng: float) -> bool:
    return (CBD_BBOX["min_lat"] <= lat <= CBD_BBOX["max_lat"] and
            CBD_BBOX["min_lng"] <= lng <= CBD_BBOX["max_lng"])


def _interpolate(a: Tuple[float, float], b: Tuple[float, float], n: int = 12) -> List[List[float]]:
    return [[a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n] for i in range(n)]


def _fallback_route(ordered_points: List[Tuple[float, float]], avoid_cbd: bool = False, eco: bool = False) -> dict:
    """Build a naive geometry by connecting ordered points.
    If avoid_cbd and a segment crosses CBD, add a detour via the nearest CBD corner."""
    geom: List[List[float]] = []
    total_dist = 0.0
    for i in range(len(ordered_points) - 1):
        a = ordered_points[i]
        b = ordered_points[i + 1]
        # Detour if avoid_cbd and both endpoints or midpoint fall inside CBD
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if avoid_cbd and _in_cbd(*mid):
            # route via north-east corner of CBD (outside)
            detour = (CBD_BBOX["max_lat"] + 0.01, CBD_BBOX["max_lng"] + 0.01)
            seg1 = _interpolate(a, detour, 10)
            seg2 = _interpolate(detour, b, 10)
            pts = seg1 + seg2
            total_dist += haversine(a, detour) + haversine(detour, b)
        else:
            pts = _interpolate(a, b, 12)
            total_dist += haversine(a, b)
        geom.extend(pts)
    geom.append(list(ordered_points[-1]))
    # Urban speed — eco (EV) ~25 km/h, time ~35 km/h, avoid_erp ~28 km/h
    speed_mps = 9.7 if eco else 8.5
    duration = total_dist / speed_mps
    # emulate OSRM shape minimally
    return {
        "routes": [{
            "distance": total_dist,
            "duration": duration,
            "geometry": {"coordinates": [[p[1], p[0]] for p in geom]},
        }]
    }


class RoutePlanIn(BaseModel):
    driver_id: str
    mode: Literal["time", "eco", "avoid_erp"] = "time"


@api.post("/routing/plan")
async def routing_plan(body: RoutePlanIn):
    driver = await find_one("drivers", {"id": body.driver_id})
    if not driver:
        raise HTTPException(404, "Driver not found")
    # collect driver's assigned orders not yet delivered/failed
    orders = await find_list("orders", {
        "driver_id": body.driver_id,
        "status": {"$in": ["assigned", "delivering"]},
    })
    if not orders:
        raise HTTPException(400, "No active orders for this driver")

    start = (HUB_LOCATION["lat"], HUB_LOCATION["lng"])
    stops = [(o["lat"], o["lng"]) for o in orders]

    # Always compute nearest-neighbor ordering (anchor on hub)
    def nn_order(origin: Tuple[float, float], items: List[dict]) -> List[dict]:
        remaining = items.copy()
        current = origin
        ordered = []
        while remaining:
            remaining.sort(key=lambda o: haversine(current, (o["lat"], o["lng"])))
            nxt = remaining.pop(0)
            ordered.append(nxt)
            current = (nxt["lat"], nxt["lng"])
        return ordered

    sequence_order_ids: List[str] = []
    osrm = None

    if body.mode == "eco":
        ordered = nn_order(start, orders)
        sequence_order_ids = [o["id"] for o in ordered]
        coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
        osrm = await osrm_route(coords, alternatives=False)
        if not osrm:
            osrm = _fallback_route(coords, avoid_cbd=False, eco=True)
    elif body.mode == "avoid_erp":
        ordered = nn_order(start, orders)
        sequence_order_ids = [o["id"] for o in ordered]
        coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
        osrm_try = await osrm_route(coords, alternatives=True)
        if osrm_try and osrm_try.get("routes"):
            routes = osrm_try["routes"]
            cbd = (1.2839, 103.8507)
            def route_cbd_penalty(rt):
                geom = rt["geometry"]["coordinates"]
                mid = geom[len(geom) // 2]
                return haversine(cbd, (mid[1], mid[0]))
            routes.sort(key=route_cbd_penalty, reverse=True)
            osrm = {"routes": [routes[0]]}
        else:
            osrm = _fallback_route(coords, avoid_cbd=True, eco=False)
    else:  # "time"
        trip = await osrm_trip([start] + stops)
        if trip and trip.get("trips"):
            waypoints = trip.get("waypoints", [])
            order_sequence = sorted(
                range(1, len(waypoints)),
                key=lambda i: waypoints[i]["waypoint_index"]
            )
            sequence_order_ids = [orders[i - 1]["id"] for i in order_sequence]
            osrm = {"routes": trip["trips"]}
        else:
            ordered = nn_order(start, orders)
            sequence_order_ids = [o["id"] for o in ordered]
            coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
            osrm_try = await osrm_route(coords, alternatives=False)
            osrm = osrm_try if osrm_try else _fallback_route(coords, avoid_cbd=False, eco=False)

    route_json = osrm["routes"][0]
    geom = [[c[1], c[0]] for c in route_json["geometry"]["coordinates"]]
    # update order sequence
    for idx, oid in enumerate(sequence_order_ids, 1):
        await db.orders.update_one({"id": oid}, {"$set": {"sequence": idx}})

    rr = RouteRecord(
        driver_id=body.driver_id,
        mode=body.mode,
        waypoints=[list(start)] + [[orders[i]["lat"], orders[i]["lng"]] for i in range(len(orders))],
        ordered_order_ids=sequence_order_ids,
        distance_m=route_json["distance"],
        duration_s=route_json["duration"],
        geometry=geom,
    )
    # keep only latest per driver
    await db.routes.delete_many({"driver_id": body.driver_id})
    await db.routes.insert_one(rr.model_dump())
    return rr


@api.get("/routing/{driver_id}")
async def get_route(driver_id: str):
    r = await find_one("routes", {"driver_id": driver_id})
    if not r:
        raise HTTPException(404, "No route")
    return r


# ───────────────────────────── FR-18 Simulation helper ─────────────────────────────
class SimulateStepIn(BaseModel):
    step_m: float = 200.0


@api.post("/drivers/{did}/simulate-step")
async def simulate_step(did: str, body: SimulateStepIn):
    """Advance driver along their latest route geometry (for demo of FR-18)."""
    route = await find_one("routes", {"driver_id": did})
    if not route:
        raise HTTPException(404, "No route for driver")
    driver = await find_one("drivers", {"id": did})
    geom = route["geometry"]
    current = driver.get("location")
    if not current:
        new_loc = {"lat": geom[0][0], "lng": geom[0][1]}
        idx = 0
    else:
        # find closest point, then advance
        best_i = 0
        best_d = float("inf")
        for i, p in enumerate(geom):
            d = haversine((current["lat"], current["lng"]), (p[0], p[1]))
            if d < best_d:
                best_d = d
                best_i = i
        idx = best_i
        travelled = 0.0
        while idx < len(geom) - 1 and travelled < body.step_m:
            travelled += haversine((geom[idx][0], geom[idx][1]), (geom[idx + 1][0], geom[idx + 1][1]))
            idx += 1
        new_loc = {"lat": geom[idx][0], "lng": geom[idx][1]}
    loc = {"lat": new_loc["lat"], "lng": new_loc["lng"], "updated_at": now_iso()}
    await db.drivers.update_one({"id": did}, {"$set": {"location": loc, "status": "delivering"}})
    return {"location": loc, "progress_pct": round(100 * idx / max(1, len(geom) - 1), 1)}


# ───────────────────────────── FR-19 Shipper inbox ─────────────────────────────
@api.get("/shipper/{driver_id}/orders")
async def shipper_orders(driver_id: str):
    orders = await find_list("orders", {
        "driver_id": driver_id,
        "status": {"$in": ["assigned", "delivering"]},
    })
    orders.sort(key=lambda o: (o.get("sequence") or 9999))
    route = await find_one("routes", {"driver_id": driver_id})
    return {"orders": orders, "route": route}


# ───────────────────────────── LTA passthrough ─────────────────────────────
@api.get("/lta/incidents")
async def lta_incidents():
    return await fetch_lta("TrafficIncidents")


@api.get("/lta/speed-bands")
async def lta_speed_bands():
    data = await fetch_lta("v3/TrafficSpeedBands")
    # trim to ~800 items around SG + essential fields for map
    simplified = []
    for row in data[:800]:
        try:
            simplified.append({
                "LinkID": row.get("LinkID"),
                "RoadName": row.get("RoadName"),
                "SpeedBand": row.get("SpeedBand"),
                "StartLat": float(row["StartLat"]),
                "StartLon": float(row["StartLon"]),
                "EndLat": float(row["EndLat"]),
                "EndLon": float(row["EndLon"]),
            })
        except Exception:
            continue
    return simplified


@api.get("/lta/erp-rates")
async def lta_erp_rates():
    return await fetch_lta("ERPRates")


@api.get("/lta/taxi-availability")
async def lta_taxi():
    return await fetch_lta("Taxi-Availability")


# ───────────────────────────── Dashboard / Seed ─────────────────────────────
@api.get("/stats")
async def stats():
    counts = {
        "hub_managers": await db.hub_managers.count_documents({}),
        "drivers": await db.drivers.count_documents({}),
        "drivers_available": await db.drivers.count_documents({"status": "available"}),
        "drivers_delivering": await db.drivers.count_documents({"status": "delivering"}),
        "vehicles": await db.vehicles.count_documents({}),
        "vehicles_ev": await db.vehicles.count_documents({"fuel_type": "ev"}),
        "zones": await db.zones.count_documents({}),
        "orders_pending": await db.orders.count_documents({"status": "pending"}),
        "orders_assigned": await db.orders.count_documents({"status": "assigned"}),
        "orders_delivering": await db.orders.count_documents({"status": "delivering"}),
        "orders_delivered": await db.orders.count_documents({"status": "delivered"}),
        "orders_failed": await db.orders.count_documents({"status": "failed"}),
        "clusters": await db.clusters.count_documents({}),
    }
    return counts


@api.post("/seed")
async def seed_demo():
    # Clear
    for c in ["hub_managers", "drivers", "vehicles", "zones", "orders", "clusters", "routes"]:
        await db[c].delete_many({})

    # Hub managers
    hms = [
        HubManagerIn(name="Alicia Tan", phone="+6598000001", hub_name="Central Hub"),
        HubManagerIn(name="Rahul Menon", phone="+6598000002", hub_name="East Hub"),
    ]
    hm_ids = []
    for hm_in in hms:
        hm = HubManager(**hm_in.model_dump())
        await db.hub_managers.insert_one(hm.model_dump())
        hm_ids.append(hm.id)

    # Drivers
    driver_data = [
        ("Kumar Das", "+6591110001", "A"),
        ("Wei Ming Lee", "+6591110002", "B"),
        ("Siti Nurhaliza", "+6591110003", "C"),
        ("Arjun Pillai", "+6591110004", "B"),
        ("Chen Xin", "+6591110005", "A"),
        ("Dinesh Kumar", "+6591110006", "C"),
    ]
    driver_ids = []
    for name, phone, lic in driver_data:
        d = Driver(name=name, phone=phone, license_type=lic, hub_manager_id=hm_ids[0])
        await db.drivers.insert_one(d.model_dump())
        driver_ids.append(d.id)

    # Vehicles
    vehicles = [
        ("SGB 1001 A", "motorbike", "ev", 40),
        ("SGB 1002 B", "motorbike", "diesel", 40),
        ("SGV 2001 C", "van", "ev", 800),
        ("SGV 2002 D", "van", "diesel", 1000),
        ("SGB 1003 E", "motorbike", "ev", 40),
        ("SGV 2003 F", "van", "ev", 800),
    ]
    vehicle_ids = []
    for plate, vtype, fuel, cap in vehicles:
        v = Vehicle(plate=plate, type=vtype, fuel_type=fuel, capacity_kg=cap)
        await db.vehicles.insert_one(v.model_dump())
        vehicle_ids.append(v.id)

    # Assign each driver to a vehicle
    for did, vid in zip(driver_ids, vehicle_ids):
        await db.vehicles.update_one({"id": vid}, {"$set": {"assigned_driver_id": did}})
        await db.drivers.update_one({"id": did}, {"$set": {"vehicle_id": vid}})

    # Zones — 3 Singapore regions (approximate polygons)
    zones_data = [
        ("Central CBD", [
            [1.300, 103.830], [1.300, 103.870], [1.280, 103.870], [1.280, 103.830]
        ], "#ef4444"),
        ("East Coast", [
            [1.330, 103.900], [1.330, 103.960], [1.290, 103.960], [1.290, 103.900]
        ], "#0ea5a4"),
        ("North-West", [
            [1.400, 103.740], [1.400, 103.800], [1.360, 103.800], [1.360, 103.740]
        ], "#f59e0b"),
    ]
    zone_ids = []
    for name, poly, color in zones_data:
        z = Zone(name=name, polygon=poly, center=polygon_centroid(poly), color=color)
        await db.zones.insert_one(z.model_dump())
        zone_ids.append(z.id)

    # Assign drivers to zones (2 per zone)
    for i, did in enumerate(driver_ids):
        zid = zone_ids[i % len(zone_ids)]
        await db.zones.update_one({"id": zid}, {"$addToSet": {"driver_ids": did}})
        await db.drivers.update_one({"id": did}, {"$set": {"zone_id": zid}})

    # Orders across SG
    orders_data = [
        ("10 Bayfront Ave, Singapore", "018956", 1.2837, 103.8591, 3.2),
        ("2 Orchard Turn, Singapore", "238801", 1.3039, 103.8321, 1.5),
        ("1 Harbourfront Walk", "098585", 1.2652, 103.8220, 5.0),
        ("60 Airport Blvd", "819643", 1.3644, 103.9915, 2.8),
        ("18 Marina Gardens Dr", "018953", 1.2814, 103.8642, 4.2),
        ("9 Raffles Blvd", "039596", 1.2936, 103.8586, 1.9),
        ("1 Stadium Pl", "397628", 1.3029, 103.8740, 2.1),
        ("8 Sentosa Gateway", "098269", 1.2544, 103.8238, 3.7),
        ("1 Vista Exchange Grn", "138617", 1.3072, 103.7900, 6.0),
        ("21 Choa Chu Kang Ave 4", "689812", 1.3840, 103.7470, 2.6),
        ("30 Woodlands Ave 2", "738343", 1.4370, 103.7865, 4.5),
        ("50 Jurong Gateway Rd", "608549", 1.3331, 103.7426, 3.0),
        ("1 HarbourFront Pl", "098633", 1.2653, 103.8219, 2.2),
        ("83 Punggol Central", "828761", 1.4045, 103.9023, 1.8),
        ("1 Pasir Ris Close", "519599", 1.3732, 103.9497, 5.3),
    ]
    from datetime import timedelta
    base = datetime.now(timezone.utc) + timedelta(hours=6)
    for i, (addr, pc, lat, lng, wt) in enumerate(orders_data):
        count = i + 1
        o = Order(
            code=f"ORD-{count:05d}",
            address=addr, postal_code=pc, lat=lat, lng=lng,
            weight_kg=wt, required_by=(base + timedelta(hours=i)).isoformat()
        )
        await db.orders.insert_one(o.model_dump())

    return {
        "ok": True,
        "hub_managers": len(hm_ids),
        "drivers": len(driver_ids),
        "vehicles": len(vehicle_ids),
        "zones": len(zone_ids),
        "orders": len(orders_data),
    }


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
