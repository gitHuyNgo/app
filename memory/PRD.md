# LionCity AI-Logistics — PRD

## Original Problem Statement
Build a workable web app implementing Functional Requirements FR-01 to FR-20 from
the project "Hệ thống Quản lý Hub và Điều phối Vận chuyển" (Hub & Delivery
Coordination System) — a centralised, AI-assisted last-mile delivery operations
platform for Singapore, using **LTA DataMall** as the live data source.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) at port 8001, `/api` prefix
- **Frontend**: React 19 + react-router + Tailwind + Leaflet (CartoDB light tiles)
- **Data**: MongoDB collections — `hub_managers`, `drivers`, `vehicles`, `zones`, `orders`, `clusters`, `routes`
- **External**:
  - LTA DataMall (`/api/lta/incidents`, `/speed-bands`, `/erp-rates`, `/taxi-availability`) — key in `/app/backend/.env`
  - OSRM public routing (attempted; unreachable from container → auto-fallback to pure-Python NN-TSP with CBD-bbox detour for Avoid-ERP mode)
- **No authentication** (per user choice) — role switched via top-bar dropdown (Admin / Hub Manager / Shipper)

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
