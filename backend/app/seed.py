"""Deterministic demo dataset used to bootstrap a fresh database."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from app.database import db
from app.models.driver import Driver
from app.models.hub import Hub
from app.models.hub_manager import HubManager
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.zone import Zone
from app.services.geo import polygon_centroid

COLLECTIONS = ("hub_managers", "drivers", "vehicles", "zones", "orders", "clusters", "routes", "hubs")

HUBS: List[Tuple[str, str, float, float, bool]] = [
    ("Central Hub · Queenstown", "1 Tanglin Rd, Singapore 247905", 1.3053, 103.8198, True),
    ("East Hub · Tampines", "10 Tampines Central, Singapore 529538", 1.3540, 103.9430, False),
    ("West Hub · Jurong", "1 Jurong Gateway Rd, Singapore 608549", 1.3331, 103.7426, False),
]

HUB_MANAGERS: List[Tuple[str, str, str]] = [
    ("Alicia Tan", "+6598000001", "Central Hub"),
    ("Rahul Menon", "+6598000002", "East Hub"),
]

DRIVERS: List[Tuple[str, str, str]] = [
    ("Kumar Das", "+6591110001", "A"),
    ("Wei Ming Lee", "+6591110002", "B"),
    ("Siti Nurhaliza", "+6591110003", "C"),
    ("Arjun Pillai", "+6591110004", "B"),
    ("Chen Xin", "+6591110005", "A"),
    ("Dinesh Kumar", "+6591110006", "C"),
]

VEHICLES: List[Tuple[str, str, str, int]] = [
    ("SGB 1001 A", "motorbike", "ev", 40),
    ("SGB 1002 B", "motorbike", "diesel", 40),
    ("SGV 2001 C", "van", "ev", 800),
    ("SGV 2002 D", "van", "diesel", 1000),
    ("SGB 1003 E", "motorbike", "ev", 40),
    ("SGV 2003 F", "van", "ev", 800),
]

ZONES: List[Tuple[str, List[List[float]], str]] = [
    ("Central CBD", [[1.300, 103.830], [1.300, 103.870], [1.280, 103.870], [1.280, 103.830]], "#ef4444"),
    ("East Coast", [[1.330, 103.900], [1.330, 103.960], [1.290, 103.960], [1.290, 103.900]], "#0ea5a4"),
    ("North-West", [[1.400, 103.740], [1.400, 103.800], [1.360, 103.800], [1.360, 103.740]], "#f59e0b"),
]

ORDERS: List[Tuple[str, str, float, float, float]] = [
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


async def seed_demo() -> Dict[str, Any]:
    """Wipe and repopulate the database with deterministic demo data."""
    for collection in COLLECTIONS:
        await db[collection].delete_many({})

    hub_ids: List[str] = []
    for name, address, lat, lng, is_default in HUBS:
        hub = Hub(name=name, address=address, lat=lat, lng=lng, is_default=is_default)
        await db.hubs.insert_one(hub.model_dump())
        hub_ids.append(hub.id)

    hm_ids: List[str] = []
    for name, phone, hub_name in HUB_MANAGERS:
        hub_manager = HubManager(name=name, phone=phone, hub_name=hub_name)
        await db.hub_managers.insert_one(hub_manager.model_dump())
        hm_ids.append(hub_manager.id)

    driver_ids: List[str] = []
    for name, phone, license_type in DRIVERS:
        driver = Driver(name=name, phone=phone, license_type=license_type, hub_manager_id=hm_ids[0])
        await db.drivers.insert_one(driver.model_dump())
        driver_ids.append(driver.id)

    vehicle_ids: List[str] = []
    for plate, vehicle_type, fuel, capacity in VEHICLES:
        vehicle = Vehicle(plate=plate, type=vehicle_type, fuel_type=fuel, capacity_kg=capacity)
        await db.vehicles.insert_one(vehicle.model_dump())
        vehicle_ids.append(vehicle.id)

    for driver_id, vehicle_id in zip(driver_ids, vehicle_ids):
        await db.vehicles.update_one({"id": vehicle_id}, {"$set": {"assigned_driver_id": driver_id}})
        await db.drivers.update_one({"id": driver_id}, {"$set": {"vehicle_id": vehicle_id}})

    zone_ids: List[str] = []
    for name, polygon, color in ZONES:
        zone = Zone(name=name, polygon=polygon, center=polygon_centroid(polygon), color=color)
        await db.zones.insert_one(zone.model_dump())
        zone_ids.append(zone.id)

    for index, driver_id in enumerate(driver_ids):
        zone_id = zone_ids[index % len(zone_ids)]
        await db.zones.update_one({"id": zone_id}, {"$addToSet": {"driver_ids": driver_id}})
        await db.drivers.update_one({"id": driver_id}, {"$set": {"zone_id": zone_id}})

    base_time = datetime.now(timezone.utc) + timedelta(hours=6)
    for index, (address, postal, lat, lng, weight) in enumerate(ORDERS):
        order = Order(
            code=f"ORD-{index + 1:05d}",
            address=address,
            postal_code=postal,
            lat=lat,
            lng=lng,
            weight_kg=weight,
            required_by=(base_time + timedelta(hours=index)).isoformat(),
        )
        await db.orders.insert_one(order.model_dump())

    return {
        "ok": True,
        "hubs": len(hub_ids),
        "hub_managers": len(hm_ids),
        "drivers": len(driver_ids),
        "vehicles": len(vehicle_ids),
        "zones": len(zone_ids),
        "orders": len(ORDERS),
    }
