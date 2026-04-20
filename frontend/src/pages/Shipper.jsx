import React, { useEffect, useState } from "react";
import { http, fmtDate, fmtDist, fmtDur } from "../lib/api";
import MapView from "../components/MapView";
import { Badge, Modal } from "../components/UI";

export default function Shipper() {
  const [drivers, setDrivers] = useState([]);
  const [driverId, setDriverId] = useState("");
  const [payload, setPayload] = useState(null);
  const [orders, setOrders] = useState([]);
  const [busy, setBusy] = useState(false);
  const [failOpen, setFailOpen] = useState(null);
  const [failReason, setFailReason] = useState("");

  const load = async () => {
    const d = await http.get("/drivers");
    setDrivers(d.data);
    if (!driverId && d.data.length) setDriverId(d.data[0].id);
  };
  const loadOrders = async () => {
    if (!driverId) return;
    const r = await http.get(`/shipper/${driverId}/orders`);
    setPayload(r.data);
    const all = await http.get("/orders", { params: { driver_id: driverId } });
    setOrders(all.data);
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { loadOrders(); const t = setInterval(loadOrders, 5000); return () => clearInterval(t); }, [driverId]);

  const setStatus = async (status) => { await http.put(`/drivers/${driverId}/status`, { status }); load(); };
  const markDelivered = async (o) => { await http.put(`/orders/${o.id}/status`, { status: "delivered" }); loadOrders(); };
  const markFailed = async () => {
    await http.put(`/orders/${failOpen.id}/status`, { status: "failed", fail_reason: failReason });
    setFailOpen(null); setFailReason(""); loadOrders();
  };
  const simulate = async () => { setBusy(true); await http.post(`/drivers/${driverId}/simulate-step`, { step_m: 500 }); loadOrders(); load(); setBusy(false); };

  const driver = drivers.find(d => d.id === driverId);
  const activeOrders = payload?.orders || [];
  const done = orders.filter(o => ["delivered", "failed"].includes(o.status));

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Shipper Cockpit</div>
      <div className="page-subtitle">FR-05 · FR-14 · FR-18 · FR-19 · FR-20 — Driver's view of route, live location and delivery updates</div>

      <div className="toolbar">
        <select className="select" style={{ width: 240 }} data-testid="shipper-driver-select"
          value={driverId} onChange={e => setDriverId(e.target.value)}>
          {drivers.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        {driver && (
          <>
            <select className="select" style={{ width: 160 }} data-testid="shipper-status"
              value={driver.status} onChange={e => setStatus(e.target.value)}>
              <option value="available">Available</option>
              <option value="delivering">Delivering</option>
              <option value="off_duty">Off-duty</option>
            </select>
            <Badge tone={driver.status}>{driver.status}</Badge>
          </>
        )}
        <div style={{ flex: 1 }}></div>
        <button className="btn" disabled={!payload?.route || busy} onClick={simulate} data-testid="shipper-advance-btn">▶ Advance GPS 500m</button>
      </div>

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <MapView
            height={520}
            orders={activeOrders}
            drivers={driver && driver.location ? [driver] : []}
            routes={payload?.route ? [{ geometry: payload.route.geometry, color: "#0d7c78" }] : []}
          />
        </div>

        <div className="card" style={{ maxHeight: 620, overflow: "auto" }}>
          <div className="card-header">
            <div>
              <div className="card-title">My Delivery List</div>
              <div className="card-subtitle">{activeOrders.length} active · {done.length} completed</div>
            </div>
            {payload?.route && <Badge tone="assigned">{fmtDist(payload.route.distance_m)} · {fmtDur(payload.route.duration_s)}</Badge>}
          </div>

          {activeOrders.length === 0 && <div className="empty" data-testid="shipper-empty">No active deliveries. Ask your Hub Manager to assign a cluster.</div>}

          <ol style={{ padding: 0, margin: 0, listStyle: "none" }}>
            {activeOrders.map((o) => (
              <li key={o.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }} data-testid={`shipper-order-${o.id}`}>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#0d7c78", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12, flexShrink: 0 }}>
                    #{o.sequence || "·"}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{o.code}</div>
                    <div style={{ fontSize: 12.5, color: "#334155" }}>{o.address}</div>
                    <div style={{ fontSize: 11.5, color: "#64748b" }}>Postal {o.postal_code} · {o.weight_kg} kg · due {fmtDate(o.required_by)}</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="btn sm primary" data-testid={`deliver-${o.id}`} onClick={() => markDelivered(o)}>✓ Delivered</button>
                  <button className="btn sm danger" data-testid={`fail-${o.id}`} onClick={() => { setFailOpen(o); setFailReason(""); }}>✗ Failed</button>
                  <Badge tone={o.status}>{o.status}</Badge>
                </div>
              </li>
            ))}
          </ol>

          {done.length > 0 && (
            <>
              <div style={{ marginTop: 14, fontSize: 12, fontWeight: 600, color: "#475569" }}>Completed today</div>
              <ol style={{ padding: 0, margin: "8px 0 0 0", listStyle: "none" }}>
                {done.map(o => (
                  <li key={o.id} style={{ padding: "8px 0", borderBottom: "1px dashed var(--border)", fontSize: 12.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span><b>{o.code}</b> — <span className="muted">{o.address}</span></span>
                    <Badge tone={o.status}>{o.status}</Badge>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </div>

      <Modal open={!!failOpen} title={`Mark ${failOpen?.code} as failed`} onClose={() => setFailOpen(null)}
        footer={<>
          <button className="btn" onClick={() => setFailOpen(null)}>Cancel</button>
          <button className="btn danger" onClick={markFailed} data-testid="confirm-fail-btn">Confirm</button>
        </>}>
        <div className="field"><label className="label">Reason</label>
          <textarea className="textarea" data-testid="fail-reason" value={failReason} onChange={e => setFailReason(e.target.value)} placeholder="Recipient not home, damaged package, etc." /></div>
      </Modal>
    </div>
  );
}
