import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Modal, Badge } from "../components/UI";
import MapView from "../components/MapView";

const PRESETS = [
  { name: "Central CBD", color: "#ef4444", polygon: [[1.300,103.830],[1.300,103.870],[1.280,103.870],[1.280,103.830]] },
  { name: "East Coast", color: "#0ea5a4", polygon: [[1.330,103.900],[1.330,103.960],[1.290,103.960],[1.290,103.900]] },
  { name: "North-West", color: "#f59e0b", polygon: [[1.400,103.740],[1.400,103.800],[1.360,103.800],[1.360,103.740]] },
  { name: "Jurong", color: "#8b5cf6", polygon: [[1.345,103.720],[1.345,103.770],[1.320,103.770],[1.320,103.720]] },
  { name: "Punggol", color: "#0d7c78", polygon: [[1.415,103.890],[1.415,103.935],[1.390,103.935],[1.390,103.890]] },
];

export default function Zones() {
  const [zones, setZones] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", color: "#0d7c78", polygon: PRESETS[0].polygon });
  const [assignOpen, setAssignOpen] = useState(null);
  const [assignDriverId, setAssignDriverId] = useState("");

  const load = async () => {
    const [z, d] = await Promise.all([http.get("/zones"), http.get("/drivers")]);
    setZones(z.data); setDrivers(d.data);
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    await http.post("/zones", { name: form.name, polygon: form.polygon, color: form.color });
    setOpen(false); load();
  };
  const remove = async (z) => { if (!window.confirm(`Delete zone ${z.name}?`)) return; await http.delete(`/zones/${z.id}`); load(); };
  const assign = async () => {
    await http.post(`/zones/${assignOpen.id}/assign-driver`, { driver_id: assignDriverId });
    setAssignOpen(null); setAssignDriverId(""); load();
  };
  const unassign = async (zone, driverId) => {
    await http.post(`/zones/${zone.id}/unassign-driver`, { driver_id: driverId }); load();
  };

  const dById = Object.fromEntries(drivers.map(d => [d.id, d]));

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Zones</div>
      <div className="page-subtitle">FR-09 · FR-10 · FR-11 — Define delivery zones, assign drivers, visualize on map</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-zone-btn" onClick={() => { setForm({ name: "", color: "#0d7c78", polygon: PRESETS[0].polygon }); setOpen(true); }}>+ Add Zone</button>
      </div>

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }} className="card-title">Zone Map</div>
          <div style={{ padding: 12 }}>
            <MapView height={520} zones={zones} />
          </div>
        </div>

        <div className="card" style={{ padding: 0, maxHeight: 620, overflow: "auto" }}>
          <table className="tbl" data-testid="zones-table">
            <thead><tr><th>Zone</th><th>Drivers</th><th></th></tr></thead>
            <tbody>
              {zones.map(z => (
                <tr key={z.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 10, height: 10, background: z.color, borderRadius: 3 }}></span>
                      <b>{z.name}</b>
                    </div>
                    <div className="muted" style={{ fontSize: 11 }}>Center: {z.center[0].toFixed(3)}, {z.center[1].toFixed(3)}</div>
                  </td>
                  <td>
                    {z.driver_ids.length === 0 && <span className="muted">None</span>}
                    {z.driver_ids.map(did => (
                      <span className="chip" key={did}>
                        {dById[did]?.name || "driver"}
                        <button className="btn sm ghost" style={{ height: 18, padding: "0 4px", fontSize: 10 }}
                          onClick={() => unassign(z, did)} data-testid={`unassign-driver-${did}`}>×</button>
                      </span>
                    ))}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn sm" data-testid={`assign-zone-${z.id}`} onClick={() => { setAssignOpen(z); setAssignDriverId(""); }}>+ Driver</button>
                    <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(z)} data-testid={`del-zone-${z.id}`}>Delete</button>
                  </td>
                </tr>
              ))}
              {zones.length === 0 && <tr><td colSpan={3} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No zones.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={open} title="New Zone" onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" disabled={!form.name} onClick={create} data-testid="save-zone-btn">Create</button>
        </>}>
        <div className="field"><label className="label">Zone name</label>
          <input className="input" data-testid="zone-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
        <div className="row">
          <div className="field"><label className="label">Color</label>
            <input className="input" type="color" data-testid="zone-color" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} /></div>
          <div className="field"><label className="label">Preset shape</label>
            <select className="select" data-testid="zone-preset" onChange={e => {
              const p = PRESETS.find(x => x.name === e.target.value);
              if (p) setForm(f => ({ ...f, polygon: p.polygon, name: f.name || p.name, color: p.color }));
            }}>
              <option>— choose a preset polygon —</option>
              {PRESETS.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select></div>
        </div>
        <div className="field">
          <label className="label">Polygon (lat,lng; lat,lng; …)</label>
          <textarea className="textarea" data-testid="zone-polygon"
            value={form.polygon.map(p => p.join(",")).join("; ")}
            onChange={e => {
              const parsed = e.target.value.split(";").map(s => s.trim()).filter(Boolean).map(s => s.split(",").map(parseFloat));
              setForm({ ...form, polygon: parsed });
            }} />
        </div>
      </Modal>

      <Modal open={!!assignOpen} title={`Assign driver to ${assignOpen?.name || ""}`} onClose={() => setAssignOpen(null)}
        footer={<>
          <button className="btn" onClick={() => setAssignOpen(null)}>Cancel</button>
          <button className="btn primary" disabled={!assignDriverId} onClick={assign} data-testid="confirm-assign-zone-btn">Assign</button>
        </>}>
        <select className="select" data-testid="zone-assign-driver" value={assignDriverId} onChange={(e) => setAssignDriverId(e.target.value)}>
          <option value="">— select driver —</option>
          {drivers.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </Modal>
    </div>
  );
}
