import React, { useEffect, useState } from "react";
import { http, fmtDist, fmtDur } from "../lib/api";
import MapView from "../components/MapView";
import { Badge } from "../components/UI";

const MODES = [
  { id: "time", label: "Time Priority", desc: "Fastest route" },
  { id: "eco", label: "Eco Mode", desc: "Minimize distance (EV-friendly)" },
  { id: "avoid_erp", label: "Avoid ERP", desc: "Route around CBD ERP zones" },
];

export default function Routing() {
  const [drivers, setDrivers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [driverId, setDriverId] = useState("");
  const [hubId, setHubId] = useState("");
  const [mode, setMode] = useState("time");
  const [route, setRoute] = useState(null);
  const [busy, setBusy] = useState(false);
  const [speedBands, setSpeedBands] = useState([]);
  const [showTraffic, setShowTraffic] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const [d, o, h] = await Promise.all([http.get("/drivers"), http.get("/orders"), http.get("/hubs")]);
    setDrivers(d.data); setOrders(o.data); setHubs(h.data);
    if (!hubId) {
      const def = h.data.find(x => x.is_default) || h.data[0];
      if (def) setHubId(def.id);
    }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    (async () => {
      if (driverId) {
        try { const r = await http.get(`/routing/${driverId}`); setRoute(r.data); } catch { setRoute(null); }
      }
    })();
  }, [driverId]);

  const plan = async () => {
    setBusy(true); setErr(""); setRoute(null);
    try {
      const r = await http.post("/routing/plan", { driver_id: driverId, mode, hub_id: hubId || undefined });
      setRoute(r.data); await load();
    } catch (e) { setErr(e.response?.data?.detail || "Error planning route"); }
    setBusy(false);
  };

  const simulate = async () => {
    await http.post(`/drivers/${driverId}/simulate-step`, { step_m: 400 });
    load();
  };

  const toggleTraffic = async () => {
    if (!showTraffic && speedBands.length === 0) {
      const r = await http.get("/lta/speed-bands");
      setSpeedBands(r.data);
    }
    setShowTraffic(v => !v);
  };

  const driverOrders = orders.filter(o => o.driver_id === driverId && ["assigned", "delivering"].includes(o.status));
  const ordersById = Object.fromEntries(orders.map(o => [o.id, o]));
  const driversWithOrders = drivers.filter(d => orders.some(o => o.driver_id === d.id && ["assigned","delivering"].includes(o.status)));
  const selectedDriver = drivers.find(d => d.id === driverId);

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Route Planning</div>
      <div className="page-subtitle">FR-17 · FR-18 · FR-19 — Optimal routing, live GPS and delivery sequence</div>

      <div className="toolbar">
        <select className="select" style={{ width: 240 }} data-testid="routing-driver"
          value={driverId} onChange={e => { setDriverId(e.target.value); setRoute(null); }}>
          <option value="">— choose driver with orders —</option>
          {driversWithOrders.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select className="select" style={{ width: 200 }} data-testid="routing-hub"
          value={hubId} onChange={e => setHubId(e.target.value)}>
          <option value="">Default hub</option>
          {hubs.map(h => <option key={h.id} value={h.id}>{h.name}{h.is_default ? " (default)" : ""}</option>)}
        </select>
        <select className="select" style={{ width: 180 }} data-testid="routing-mode" value={mode} onChange={e => setMode(e.target.value)}>
          {MODES.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
        <button className="btn primary" disabled={!driverId || busy || driverOrders.length === 0} onClick={plan} data-testid="plan-route-btn">
          {busy ? "Planning…" : "Plan Route"}
        </button>
        {route && <button className="btn" onClick={simulate} data-testid="simulate-step-btn">▶ Advance Driver 400 m</button>}
        <div style={{ flex: 1 }}></div>
        <button className="btn" onClick={toggleTraffic} data-testid="toggle-traffic-btn">{showTraffic ? "Hide" : "Show"} Live Traffic</button>
      </div>

      {err && <div className="card" style={{ marginBottom: 12, borderColor: "#fecaca", background: "#fef2f2", color: "#991b1b", fontSize: 13 }}>{err}</div>}

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <MapView
            height={560}
            orders={driverOrders.length ? driverOrders : orders}
            drivers={selectedDriver && selectedDriver.location ? [selectedDriver] : []}
            hubs={hubs}
            routes={route ? [{ geometry: route.geometry, color: mode === "eco" ? "#059669" : mode === "avoid_erp" ? "#d97706" : "#0d7c78" }] : []}
            speedBands={showTraffic ? speedBands : []}
          />
          {showTraffic && (
            <div className="legend" style={{ padding: "8px 12px" }}>
              Traffic:
              {[1,2,3,4,5,6,7,8].map(b => (
                <span key={b}><span className="sw" style={{ background: ["#b91c1c","#ef4444","#f97316","#f59e0b","#eab308","#84cc16","#22c55e","#16a34a"][b-1] }}></span>Band {b}</span>
              ))}
            </div>
          )}
        </div>

        <div className="card" style={{ maxHeight: 620, overflow: "auto" }}>
          <div className="card-header">
            <div>
              <div className="card-title">Delivery Sequence</div>
              <div className="card-subtitle">{MODES.find(m => m.id === mode)?.desc}</div>
            </div>
            {route && <Badge tone="assigned">{fmtDist(route.distance_m)} · {fmtDur(route.duration_s)}</Badge>}
          </div>

          {!route && <div className="empty">Select a driver with assigned orders and plan a route.</div>}
          {route && (
            <ol style={{ padding: 0, margin: 0, listStyle: "none" }}>
              {route.ordered_order_ids.map((oid, i) => {
                const o = ordersById[oid];
                if (!o) return null;
                return (
                  <li key={oid} style={{ display: "flex", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#0d7c78", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12, flexShrink: 0 }}>{i + 1}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{o.code}</div>
                      <div style={{ fontSize: 12, color: "#475569" }}>{o.address}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>Postal {o.postal_code} · {o.weight_kg} kg</div>
                    </div>
                    <Badge tone={o.status}>{o.status}</Badge>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
