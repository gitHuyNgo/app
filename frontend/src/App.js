import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Users, Truck, Map, Package, Route as RouteIcon, UserCircle2, RefreshCw, RadioTower, Warehouse,
} from "lucide-react";
import { http } from "./lib/api";
import Overview from "./pages/Overview";
import HubManagers from "./pages/HubManagers";
import Drivers from "./pages/Drivers";
import Vehicles from "./pages/Vehicles";
import Zones from "./pages/Zones";
import Orders from "./pages/Orders";
import Routing from "./pages/Routing";
import Shipper from "./pages/Shipper";
import Hubs from "./pages/Hubs";
import "./App.css";

const NAV = [
  { group: "Command", items: [
    { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
    { to: "/routing", label: "Route Planning", icon: RouteIcon },
  ]},
  { group: "Operations (Hub Manager)", items: [
    { to: "/orders", label: "Orders & Dispatch", icon: Package },
    { to: "/drivers", label: "Drivers", icon: Users },
    { to: "/vehicles", label: "Fleet", icon: Truck },
    { to: "/zones", label: "Zones", icon: Map },
    { to: "/hubs", label: "Hubs", icon: Warehouse },
  ]},
  { group: "Admin & Field", items: [
    { to: "/hub-managers", label: "Hub Managers", icon: UserCircle2 },
    { to: "/shipper", label: "Shipper Cockpit", icon: RadioTower },
  ]},
];

function Sidebar() {
  return (
    <aside className="lc-sidebar" data-testid="sidebar">
      <div className="lc-brand">
        <span className="dot"></span>
        <div>
          <div className="title sg-title">LionCity</div>
          <div className="subtitle">AI-Logistics · SG</div>
        </div>
      </div>
      {NAV.map(group => (
        <div key={group.group}>
          <div className="nav-group-label">{group.group}</div>
          {group.items.map(it => (
            <NavLink key={it.to} to={it.to} end={it.end}
              data-testid={`nav-${it.to.replace('/', '') || 'overview'}`}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <it.icon />
              <span>{it.label}</span>
            </NavLink>
          ))}
        </div>
      ))}
      <div style={{ marginTop: "auto", padding: "10px 8px", fontSize: 10.5, color: "#5c7879", letterSpacing: ".08em" }}>
        DATA · LTA DATAMALL
      </div>
    </aside>
  );
}

function TopBar() {
  const [role, setRole] = useState(() => localStorage.getItem("lc_role") || "admin");
  const [seeding, setSeeding] = useState(false);
  const location = useLocation();

  useEffect(() => { localStorage.setItem("lc_role", role); }, [role]);

  const reseed = async () => {
    if (!window.confirm("⚠️  This will WIPE all your data (hubs, drivers, vehicles, zones, orders) and replace it with the demo dataset. Continue?")) return;
    setSeeding(true);
    await http.post("/seed");
    setSeeding(false);
    window.location.reload();
  };

  const titleMap = {
    "/": "Operations Overview",
    "/hub-managers": "Hub Managers",
    "/drivers": "Drivers",
    "/vehicles": "Fleet",
    "/zones": "Zones",
    "/hubs": "Hubs",
    "/orders": "Orders & Dispatch",
    "/routing": "Route Planning",
    "/shipper": "Shipper Cockpit",
  };

  return (
    <header className="lc-topbar">
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ fontSize: 13, color: "#475569" }}>
          <span className="muted">Module /</span> <b style={{ color: "#0b1e24" }}>{titleMap[location.pathname] || "LionCity"}</b>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span className="lc-role-pill" data-testid="role-pill">
          Role:
          <select style={{ background: "transparent", border: 0, fontWeight: 600, color: "var(--teal-ink)", outline: "none" }}
            data-testid="role-switch" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="admin">Super Admin</option>
            <option value="hub_manager">Hub Manager</option>
            <option value="shipper">Shipper</option>
          </select>
        </span>
        <button className="btn" onClick={reseed} disabled={seeding} data-testid="reseed-btn" title="Wipe DB and load demo data">
          <RefreshCw size={14} /> {seeding ? "Seeding…" : "Reset to demo"}
        </button>
      </div>
    </header>
  );
}

function Shell() {
  const [empty, setEmpty] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const checkEmpty = async () => {
    try {
      const s = await http.get("/stats");
      const isEmpty = Object.values(s.data).every(v => v === 0);
      setEmpty(isEmpty);
    } catch {
      setEmpty(false);
    }
  };
  useEffect(() => { checkEmpty(); }, []);

  const loadDemo = async () => {
    setSeeding(true);
    try { await http.post("/seed"); window.location.reload(); }
    finally { setSeeding(false); }
  };

  return (
    <div className="lc-shell">
      <Sidebar />
      <div className="lc-main">
        <TopBar />
        <main className="lc-content">
          {empty && (
            <div className="card" data-testid="empty-db-banner" style={{ marginBottom: 18, borderColor: "#fde68a", background: "#fffbeb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Database is empty</div>
                  <div style={{ fontSize: 12.5, color: "#6b5b2c" }}>
                    Start by loading demo data or simply create your own hubs, drivers, vehicles, zones and orders — everything you create persists in MongoDB.
                  </div>
                </div>
                <button className="btn primary" onClick={loadDemo} disabled={seeding} data-testid="load-demo-btn">
                  {seeding ? "Loading…" : "Load demo data"}
                </button>
              </div>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/hub-managers" element={<HubManagers />} />
            <Route path="/drivers" element={<Drivers />} />
            <Route path="/vehicles" element={<Vehicles />} />
            <Route path="/zones" element={<Zones />} />
            <Route path="/hubs" element={<Hubs />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/routing" element={<Routing />} />
            <Route path="/shipper" element={<Shipper />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
