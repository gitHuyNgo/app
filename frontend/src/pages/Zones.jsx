import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Modal, Badge } from "../components/UI";
import MapView from "../components/MapView";
import PolygonEditor from "../components/PolygonEditor";

export default function Zones() {
  const [zones, setZones] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", color: "#0d7c78", polygon: [] });
  const [assignOpen, setAssignOpen] = useState(null);
  const [assignDriverId, setAssignDriverId] = useState("");

  const load = async () => {
    const [z, d] = await Promise.all([http.get("/zones"), http.get("/drivers")]);
    setZones(z.data); setDrivers(d.data);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", color: "#0d7c78", polygon: [] }); setOpen(true); };
  const openEdit = (z) => { setEditing(z); setForm({ name: z.name, color: z.color || "#0d7c78", polygon: z.polygon }); setOpen(true); };

  const save = async () => {
    if (!form.name || form.polygon.length < 3) return;
    if (editing) await http.put(`/zones/${editing.id}`, { name: form.name, polygon: form.polygon, color: form.color });
    else await http.post("/zones", { name: form.name, polygon: form.polygon, color: form.color });
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
      <div className="page-subtitle">FR-09 · FR-10 · FR-11 — Trace zones on the map, assign drivers, visualize coverage</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-zone-btn" onClick={openNew}>+ Draw New Zone</button>
      </div>

      <div className="section">
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }} className="card-title">Zone Coverage</div>
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
                    <div className="muted" style={{ fontSize: 11 }}>
                      {z.polygon.length} vertices · center {z.center[0].toFixed(3)}, {z.center[1].toFixed(3)}
                    </div>
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
                    <button className="btn sm ghost" onClick={() => openEdit(z)} data-testid={`edit-zone-${z.id}`}>Edit</button>
                    <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(z)} data-testid={`del-zone-${z.id}`}>Delete</button>
                  </td>
                </tr>
              ))}
              {zones.length === 0 && <tr><td colSpan={3} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No zones. Draw your first one.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={open} title={editing ? `Edit ${editing.name}` : "Draw New Zone"} onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" disabled={!form.name || form.polygon.length < 3} onClick={save} data-testid="save-zone-btn">
            {editing ? "Save" : "Create"}
          </button>
        </>}>
        <div className="row">
          <div className="field"><label className="label">Zone name</label>
            <input className="input" data-testid="zone-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label className="label">Color</label>
            <input className="input" type="color" data-testid="zone-color" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} /></div>
        </div>
        <div className="field">
          <label className="label">Polygon — click the map to add vertices, drag to reshape</label>
          <PolygonEditor value={form.polygon} color={form.color} onChange={(p) => setForm(f => ({ ...f, polygon: p }))} height={380} />
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
