import React, { useEffect, useState, useMemo } from "react";
import { http, fmtDate } from "../lib/api";
import MapView from "../components/MapView";
import { Badge } from "../components/UI";

export default function Overview() {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [zones, setZones] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [incidents, setIncidents] = useState([]);

  const load = async () => {
    const [s, o, d, z, h] = await Promise.all([
      http.get("/stats"), http.get("/orders"), http.get("/drivers"), http.get("/zones"), http.get("/hubs"),
    ]);
    setStats(s.data); setOrders(o.data); setDrivers(d.data); setZones(z.data); setHubs(h.data);
    try { const inc = await http.get("/lta/incidents"); setIncidents(inc.data); } catch { setIncidents([]); }
  };
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  const stat = (label, value, tone) => (
    <div className={`stat ${tone || ""}`} data-testid={`stat-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="label">{label}</div>
      <div className="value">{value ?? "—"}</div>
    </div>
  );

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Operations Overview</div>
      <div className="page-subtitle">Singapore-wide logistics control. Live traffic from LTA DataMall · {fmtDate(new Date().toISOString())}</div>

      <div className="stat-grid" style={{ marginBottom: 18 }}>
        {stat("Pending Orders", stats?.orders_pending, "red")}
        {stat("In Delivery", stats?.orders_delivering, "amber")}
        {stat("Delivered Today", stats?.orders_delivered, "emerald")}
        {stat("Drivers Available", stats?.drivers_available, "teal")}
        {stat("Active Zones", stats?.zones)}
        {stat("Hubs", hubs.length, "red")}
        {stat("EV Vehicles", `${stats?.vehicles_ev ?? 0}/${stats?.vehicles ?? 0}`, "teal")}
        {stat("Live Incidents", incidents.length, "red")}
      </div>

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
            <div className="card-title">Live Map — Orders, Drivers, Zones, Traffic Incidents</div>
            <div className="card-subtitle">Red dots: LTA incidents · Teal zones: delivery zones · Dark markers: driver GPS</div>
          </div>
          <div style={{ padding: 12 }}>
            <MapView height={560} orders={orders} drivers={drivers} zones={zones} hubs={hubs} incidents={incidents} />
            <div className="legend">
              <span><span className="sw" style={{ background: "#d2233c" }}></span>Hub / Incidents</span>
              <span><span className="sw" style={{ background: "#0d7c78" }}></span>Pending order</span>
              <span><span className="sw" style={{ background: "#2563eb" }}></span>Assigned order</span>
              <span><span className="sw" style={{ background: "#22c55e" }}></span>Delivered</span>
              <span><span className="sw" style={{ background: "#0f172a" }}></span>Driver GPS</span>
            </div>
          </div>
        </div>

        <div className="card" style={{ maxHeight: 660, overflow: "auto" }}>
          <div className="card-header">
            <div>
              <div className="card-title">Recent Traffic Incidents</div>
              <div className="card-subtitle">Source: LTA DataMall</div>
            </div>
            <Badge tone="failed">Live</Badge>
          </div>
          {incidents.length === 0 && <div className="empty">No active incidents reported.</div>}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {incidents.slice(0, 20).map((e, i) => (
              <div key={i} style={{ padding: "10px 12px", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12.5 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontWeight: 600 }}>{e.Type}</span>
                  <span style={{ color: "#64748b", fontSize: 11 }}>{e.Latitude?.toFixed(3)}, {e.Longitude?.toFixed(3)}</span>
                </div>
                <div style={{ color: "#334155" }}>{e.Message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
