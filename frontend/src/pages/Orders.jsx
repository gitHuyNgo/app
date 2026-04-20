import React, { useEffect, useState } from "react";
import { http, fmtDate } from "../lib/api";
import { Modal, Badge } from "../components/UI";
import MapView from "../components/MapView";

export default function Orders() {
  const [tab, setTab] = useState("inbound");
  const [orders, setOrders] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [form, setForm] = useState({ address: "", postal_code: "", lat: 1.305, lng: 103.83, weight_kg: 2.0, required_by: new Date(Date.now()+4*3600*1000).toISOString().slice(0,16) });
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState([]);
  const [manualDriver, setManualDriver] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const load = async () => {
    const [o, c, d] = await Promise.all([http.get("/orders"), http.get("/clusters"), http.get("/drivers")]);
    setOrders(o.data); setClusters(c.data); setDrivers(d.data);
  };
  useEffect(() => { load(); }, []);

  const addOrder = async () => {
    try {
      setBusy(true);
      await http.post("/orders", {
        ...form,
        lat: parseFloat(form.lat), lng: parseFloat(form.lng), weight_kg: parseFloat(form.weight_kg),
        required_by: new Date(form.required_by).toISOString(),
      });
      setOpen(false); setToast("Order added to warehouse"); load();
    } finally { setBusy(false); }
  };
  const doCluster = async () => {
    setBusy(true);
    const r = await http.post("/orders/cluster", { max_distance_m: 2500 });
    setToast(`Created ${r.data.count || 0} clusters`); await load(); setBusy(false);
  };
  const doAuto = async () => {
    setBusy(true);
    const r = await http.post("/orders/assign-auto");
    setToast(`Auto-assigned ${r.data.count || 0} clusters to drivers`); await load(); setBusy(false);
  };
  const doManual = async () => {
    if (!manualDriver || selected.length === 0) return;
    setBusy(true);
    await http.post("/orders/assign-manual", { driver_id: manualDriver, order_ids: selected });
    setToast(`Assigned ${selected.length} orders to driver`); setSelected([]); await load(); setBusy(false);
  };
  const updateStatus = async (o, status) => {
    await http.put(`/orders/${o.id}/status`, { status });
    load();
  };
  const remove = async (id) => { if (!window.confirm("Delete order?")) return; await http.delete(`/orders/${id}`); load(); };

  const dById = Object.fromEntries(drivers.map(d => [d.id, d]));
  const cById = Object.fromEntries(clusters.map(c => [c.id, c]));
  const pendingOrders = orders.filter(o => o.status === "pending");

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(""), 2500); return () => clearTimeout(t); } }, [toast]);

  const toggleSel = (id) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Orders & Dispatching</div>
      <div className="page-subtitle">FR-12 · FR-13 · FR-14 · FR-15 · FR-16 — Warehouse entry, clustering, assignment & status</div>

      <div className="tabs">
        <div className={`tab ${tab==='inbound'?'active':''}`} data-testid="tab-inbound" onClick={()=>setTab('inbound')}>Inbound Warehouse</div>
        <div className={`tab ${tab==='clustering'?'active':''}`} data-testid="tab-clustering" onClick={()=>setTab('clustering')}>Clustering</div>
        <div className={`tab ${tab==='assignment'?'active':''}`} data-testid="tab-assignment" onClick={()=>setTab('assignment')}>Assignment</div>
        <div className={`tab ${tab==='tracking'?'active':''}`} data-testid="tab-tracking" onClick={()=>setTab('tracking')}>Tracking</div>
      </div>

      {toast && <div className="card" style={{ background: "#ecfdf5", borderColor: "#a7f3d0", marginBottom: 12, fontSize: 13 }}>{toast}</div>}

      {tab === "inbound" && (
        <div>
          <div className="toolbar">
            <button className="btn primary" data-testid="add-order-btn" onClick={() => setOpen(true)}>+ Warehouse Entry</button>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="tbl" data-testid="orders-table">
              <thead><tr><th>Code</th><th>Address</th><th>Postal</th><th>Weight</th><th>Required by</th><th>Status</th><th>Driver</th><th></th></tr></thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td style={{ fontWeight: 600 }}>{o.code}</td>
                    <td>{o.address}</td>
                    <td>{o.postal_code}</td>
                    <td>{o.weight_kg} kg</td>
                    <td className="muted">{fmtDate(o.required_by)}</td>
                    <td><Badge tone={o.status}>{o.status}</Badge></td>
                    <td>{o.driver_id ? <span className="chip">{dById[o.driver_id]?.name || "driver"}</span> : <span className="muted">—</span>}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(o.id)} data-testid={`del-order-${o.id}`}>Delete</button>
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && <tr><td colSpan={8} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No orders yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "clustering" && (
        <div>
          <div className="toolbar">
            <button className="btn primary" data-testid="run-cluster-btn" disabled={busy} onClick={doCluster}>⚙ Run Clustering</button>
            <span className="muted" style={{ fontSize: 12 }}>Groups pending orders by postal-code sector + 2.5 km radius</span>
          </div>
          <div className="section">
            <div className="card" style={{ padding: 0 }}>
              <table className="tbl" data-testid="clusters-table">
                <thead><tr><th>Label</th><th>Orders</th><th>Centroid</th></tr></thead>
                <tbody>
                  {clusters.map(c => (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600 }}>{c.label}</td>
                      <td>{c.order_ids.length}</td>
                      <td className="muted">{c.centroid[0].toFixed(3)}, {c.centroid[1].toFixed(3)}</td>
                    </tr>
                  ))}
                  {clusters.length === 0 && <tr><td colSpan={3} style={{ padding: 20, textAlign: "center", color: "#64748b" }}>Run clustering to group pending orders.</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <MapView height={420} orders={orders.filter(o => o.status === 'pending')} />
            </div>
          </div>
        </div>
      )}

      {tab === "assignment" && (
        <div>
          <div className="toolbar">
            <button className="btn primary" data-testid="auto-assign-btn" disabled={busy || clusters.length === 0} onClick={doAuto}>⚡ Auto-Assign Clusters</button>
            <div style={{ flex: 1 }}></div>
            <span className="muted" style={{ fontSize: 12 }}>Manual:</span>
            <select className="select" style={{ width: 220 }} value={manualDriver} onChange={e => setManualDriver(e.target.value)} data-testid="manual-driver-select">
              <option value="">— choose driver —</option>
              {drivers.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <button className="btn" disabled={!manualDriver || selected.length === 0 || busy} onClick={doManual} data-testid="manual-assign-btn">Assign {selected.length || ""} selected</button>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="tbl" data-testid="assignment-table">
              <thead><tr>
                <th><input type="checkbox" data-testid="select-all-orders"
                  checked={selected.length === pendingOrders.length && pendingOrders.length > 0}
                  onChange={(e) => setSelected(e.target.checked ? pendingOrders.map(o => o.id) : [])} /></th>
                <th>Code</th><th>Address</th><th>Cluster</th><th>Driver</th><th>Status</th>
              </tr></thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td><input type="checkbox" data-testid={`select-order-${o.id}`}
                      disabled={o.status !== "pending"}
                      checked={selected.includes(o.id)} onChange={() => toggleSel(o.id)} /></td>
                    <td style={{ fontWeight: 600 }}>{o.code}</td>
                    <td>{o.address}</td>
                    <td>{o.cluster_id ? <span className="chip">{cById[o.cluster_id]?.label || o.cluster_id.slice(0,6)}</span> : <span className="muted">—</span>}</td>
                    <td>{o.driver_id ? <span className="chip">{dById[o.driver_id]?.name || "driver"}</span> : <span className="muted">—</span>}</td>
                    <td><Badge tone={o.status}>{o.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "tracking" && (
        <div className="section">
          <div className="card" style={{ padding: 0 }}>
            <table className="tbl" data-testid="tracking-table">
              <thead><tr><th>Code</th><th>Address</th><th>Status</th><th>Driver</th><th>Update</th></tr></thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td style={{ fontWeight: 600 }}>{o.code}</td>
                    <td>{o.address}</td>
                    <td><Badge tone={o.status}>{o.status}</Badge></td>
                    <td>{o.driver_id ? dById[o.driver_id]?.name : <span className="muted">—</span>}</td>
                    <td>
                      <select className="select" style={{ height: 28, padding: "0 6px", fontSize: 12 }}
                        value={o.status} data-testid={`status-${o.id}`}
                        onChange={(e) => updateStatus(o, e.target.value)}>
                        <option value="pending">pending</option>
                        <option value="assigned">assigned</option>
                        <option value="delivering">delivering</option>
                        <option value="delivered">delivered</option>
                        <option value="failed">failed</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <MapView height={520} orders={orders} />
          </div>
        </div>
      )}

      <Modal open={open} title="Warehouse Entry" onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={addOrder} disabled={busy || !form.address} data-testid="save-order-btn">Save</button>
        </>}>
        <div className="field"><label className="label">Delivery address</label>
          <input className="input" data-testid="order-address" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
        <div className="row">
          <div className="field"><label className="label">Postal code</label>
            <input className="input" data-testid="order-postal" value={form.postal_code} onChange={e => setForm({ ...form, postal_code: e.target.value })} /></div>
          <div className="field"><label className="label">Weight (kg)</label>
            <input className="input" type="number" step="0.1" data-testid="order-weight" value={form.weight_kg} onChange={e => setForm({ ...form, weight_kg: e.target.value })} /></div>
        </div>
        <div className="row">
          <div className="field"><label className="label">Latitude</label>
            <input className="input" data-testid="order-lat" value={form.lat} onChange={e => setForm({ ...form, lat: e.target.value })} /></div>
          <div className="field"><label className="label">Longitude</label>
            <input className="input" data-testid="order-lng" value={form.lng} onChange={e => setForm({ ...form, lng: e.target.value })} /></div>
        </div>
        <div className="field"><label className="label">Required by</label>
          <input className="input" type="datetime-local" data-testid="order-required" value={form.required_by} onChange={e => setForm({ ...form, required_by: e.target.value })} /></div>
      </Modal>
    </div>
  );
}
