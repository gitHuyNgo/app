# LionCity AI-Logistics — PRD

## Original Problem Statement
Build a workable web app implementing Functional Requirements FR-01 to FR-20 from
the project "Hệ thống Quản lý Hub và Điều phối Vận chuyển" (Hub & Delivery
Coordination System) — a centralised, AI-assisted last-mile delivery operations
platform for Singapore, using **LTA DataMall** as the live data source.

## Architecture
The backend follows a layered, FAANG-style structure under `backend/app/`:

```
backend/
├── server.py                # 47-line entrypoint: lifespan + CORS + include router
└── app/
    ├── __init__.py
    ├── config.py            # Frozen Settings dataclass loaded from .env
    ├── database.py          # Motor singleton + close_db()
    ├── logging.py           # Root logger configured once
    ├── utils.py             # now_iso, new_id, find_one, find_list, unique_phone
    ├── seed.py              # Deterministic demo dataset
    ├── models/              # Pydantic v2 models (one file per resource)
    │   ├── common.py        # MongoModel base with id + created_at
    │   ├── hub.py
    │   ├── hub_manager.py
    │   ├── driver.py
    │   ├── vehicle.py
    │   ├── zone.py
    │   ├── order.py
    │   ├── cluster.py
    │   └── route.py
    ├── services/            # Pure business logic — no FastAPI imports
    │   ├── geo.py           # haversine, CBD bbox, polygon centroid, interpolate
    │   ├── routing.py       # OSRM client + Python NN-TSP fallback
    │   ├── lta.py           # LTA DataMall paginated client
    │   ├── geocoding.py     # Nominatim wrapper (best-effort)
    │   ├── hubs.py          # get_active_hub(id) resolver
    │   ├── clustering.py    # Postal-sector clustering (FR-13)
    │   └── assignment.py    # Cluster → driver auto-assignment (FR-15)
    └── routers/             # FastAPI routers; one file per resource
        ├── __init__.py      # Aggregates everything under /api
        ├── meta.py          # /, /stats, /seed
        ├── hubs.py          # /hubs CRUD
        ├── hub_managers.py  # /hub-managers CRUD (FR-01..02)
        ├── drivers.py       # /drivers + /{id}/status, /{id}/location, /locations
        ├── vehicles.py      # /vehicles + /{id}/assign, /{id}/unassign
        ├── zones.py         # /zones + /{id}/(un)assign-driver
        ├── orders.py        # /orders + /cluster, /assign-auto, /assign-manual, /{id}/status
        ├── clusters.py      # /clusters (read-only)
        ├── routing.py       # /routing/plan, /routing/{driver_id}, /drivers/{id}/simulate-step
        ├── shipper.py       # /shipper/{driver_id}/orders (FR-19)
        └── lta.py           # /lta/* + /geocode
```

- **Frontend**: React 19 + react-router + Tailwind + Leaflet (CartoDB light tiles)
- **Data**: MongoDB collections — `hubs`, `hub_managers`, `drivers`, `vehicles`, `zones`, `orders`, `clusters`, `routes`
- **External**: LTA DataMall, OSRM (with Python NN-TSP fallback), Nominatim
- **No authentication** (per user choice) — role switched via top-bar dropdown

## User Personas
1. **Super Admin** — onboards Hub Managers, oversees fleet-wide KPIs.
2. **Hub Manager** — manages drivers, vehicles, zones, inbound warehouse orders, clustering, auto/manual dispatch, route planning.
3. **Shipper (Driver)** — sees assigned order list in optimal sequence, updates GPS, marks Delivered/Failed with reason.

## Implemented (Jan 2026)
- **FR-01 / FR-02** Hub Managers CRUD with phone uniqueness validation
- **FR-03 / FR-04 / FR-05** Drivers CRUD + status (available / delivering / off-duty)
- **FR-06 / FR-07 / FR-08** Vehicles CRUD (motorbike/van, EV/diesel), 1-driver-per-vehicle assignment
- **FR-09 / FR-10 / FR-11** Zone **interactive polygon drawing** (click-to-add vertices, drag-to-reshape, click-to-remove with draw-mode toggle) + driver-to-zone assignment + map visualization
- **FR-12** Warehouse entry (address, postal code, lat/lng, weight, required-by)
- **FR-13** Clustering by postal-code sector + configurable max-distance radius
- **FR-14** Order status lifecycle pending → assigned → delivering → delivered/failed
- **FR-15** Auto-assign: cluster → nearest available driver (by zone center, hub fallback)
- **FR-16** Manual assign: multi-select orders → pick driver
- **FR-17** Route planning with 3 modes (Time / Eco / Avoid-ERP) + **per-plan hub selector** (uses default hub if not specified)
- **FR-18** Real-time driver GPS update + simulate-step for demo; live on map every 5 s
- **FR-19** Shipper inbox `/api/shipper/{driver_id}/orders` with ordered sequence + route polyline
- **FR-20** Delivered/Failed update with optional proof_photo, proof_signature, fail_reason
- **Hubs (multi-location, Jan 2026)** full CRUD, pin by drag or map-click, address geocoding via OpenStreetMap Nominatim with graceful fallback, is_default flag enforced, shown on Overview map + used as routing origin
- **License-Vehicle Compatibility (Feb 2026)** UI filter + backend 400 enforcement on `POST /api/vehicles/{id}/assign` — matrix: motorbike→{A,B}, van→{B,C}
- **Hub-bound Hub Managers (Feb 2026)** `HubManager.hub_id` references real hub doc; create/edit modal uses dropdown sourced from `GET /api/hubs`; server resolves `hub_name` from the hub doc
- **Zone+Hub Clustering (Feb 2026)** rewrote `services/clustering.py`: orders bucketed by (zone, hub) via point-in-polygon; multi-zone overlap tie-broken by min hub distance; hub picked from hubs INSIDE the zone (falls back to nearest hub when no hub sits inside). Cluster carries `zone_id`, `zone_name`, `hub_id`, `hub_name`. Re-clustering preserves in-flight clusters.
- **Strict Zone-of-Working Assignment (Feb 2026)** `services/assignment.py` now hard-filters drivers by `driver.zone_id == cluster.zone_id` (alongside license + capacity).
- **Route Planning auto-hub (Feb 2026)** removed UI hub selector and `hub_id` from `RoutePlanIn`. `POST /api/routing/plan` derives the origin from the most common cluster the driver is currently working on.
- **Clustering UI (Feb 2026)** Orders → Clustering tab now lists per-order rows: Order Code | Address | Zone | Hub. Assignment tab shows Zone + Hub chips instead of cluster label.

## Frontend Pages (9)
1. Overview — KPIs including Hubs count, live Singapore map with hubs/zones/orders/drivers/incidents
2. Route Planning — driver + **hub** + mode selectors, route polyline, delivery sequence, traffic bands toggle
3. Orders & Dispatch — tabs: Inbound / Clustering / Assignment / Tracking
4. Drivers — CRUD + inline status
5. Fleet — Vehicles CRUD + assign/unassign driver
6. Zones — interactive polygon editor (Draw mode, Undo, Clear, vertex drag)
7. **Hubs — map-picker CRUD, geocode search, default-flag**
8. Hub Managers — CRUD
9. Shipper Cockpit — Delivered/Failed with reason

## Tests
- Backend: 29/29 pytest cases (`/app/backend/tests/backend_test.py`)
- Frontend: all 8 pages verified, role switcher, 4 Orders tabs, map rendering

## Next / Backlog
- P1: Split `server.py` (~1075 lines) into `routers/` per FR group for maintainability
- P1: Rich polygon drawing on the map (currently uses text/preset polygon input for Zones)
- P2: CSV export of daily deliveries; KPI history / charts (CO₂ saved, on-time rate)
- P2: Push-notifications / websockets for true real-time driver tracking (currently 5 s polling)
- P2: OAuth / JWT auth when multi-tenant needed
- P3: React-Native shipper mobile app (report originally specs RN)
- P3: ML-based cluster size optimisation and traffic-predictive routing

## Known behaviour
- OSRM public endpoint is unreachable from the container → routing transparently uses Python NN-TSP fallback (distance/duration/geometry still returned). Swap `OSRM_BASE_URL` in `/app/backend/.env` for a private OSRM to get true road geometry.
- LTA DataMall responses are served live, paginated with `$skip`, cached per request.
