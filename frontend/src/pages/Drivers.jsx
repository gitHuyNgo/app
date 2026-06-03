import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Modal, Badge } from "../components/UI";

export default function Drivers() {
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [zones, setZones] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", license_type: "B", zone_id: "" });
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const [d, v, z] = await Promise.all([http.get("/drivers"), http.get("/vehicles"), http.get("/zones")]);
    setDrivers(d.data); setVehicles(v.data); setZones(z.data);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", phone: "", license_type: "B", zone_id: "" }); setOpen(true); setErr(""); };
  const openEdit = (d) => { setEditing(d); setForm({ name: d.name, phone: d.phone, license_type: d.license_type, zone_id: d.zone_id || "" }); setOpen(true); setErr(""); };

  const save = async () => {
    try {
      setErr("");
      const payload = { ...form, zone_id: form.zone_id || null };
      if (editing) await http.put(`/drivers/${editing.id}`, payload);
      else await http.post("/drivers", payload);
      setOpen(false); load();
    } catch (e) { setErr(e.response?.data?.detail || "Error"); }
  };
  const setStatus = async (d, status) => { await http.put(`/drivers/${d.id}/status`, { status }); load(); };
  const remove = async (id) => { if (!window.confirm("Delete this driver?")) return; await http.delete(`/drivers/${id}`); load(); };

  const vById = Object.fromEntries(vehicles.map(v => [v.id, v]));
  const zById = Object.fromEntries(zones.map(z => [z.id, z]));

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Drivers</div>
      <div className="page-subtitle">FR-03 · FR-04 · FR-05 — Manage drivers, their zone, fleet vehicle and status</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-driver-btn" onClick={openNew}>+ Add Driver</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl" data-testid="drivers-table">
          <thead><tr>
            <th>Name</th><th>Phone</th><th>License</th><th>Status</th><th>Assigned Fleet</th><th>Zone</th><th></th>
          </tr></thead>
          <tbody>
            {drivers.map(d => {
              const veh = d.vehicle_id ? vById[d.vehicle_id] : null;
              const zone = d.zone_id ? zById[d.zone_id] : null;
              return (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.name}</td>
                  <td className="muted">{d.phone}</td>
                  <td>{d.license_type}</td>
                  <td>
                    <select className="select" style={{ height: 28, padding: "0 8px", fontSize: 12 }}
                      data-testid={`driver-status-${d.id}`}
                      value={d.status} onChange={(e) => setStatus(d, e.target.value)}>
                      <option value="available">Available</option>
                      <option value="delivering">Delivering</option>
                      <option value="off_duty">Off-duty</option>
                    </select>
                  </td>
                  <td>
                    {veh ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 12.5 }}>{veh.plate}</span>
                        <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                          <span className="muted" style={{ fontSize: 11, textTransform: "capitalize" }}>{veh.type}</span>
                          <Badge tone={veh.fuel_type} >{veh.fuel_type.toUpperCase()}</Badge>
                          <span className="muted" style={{ fontSize: 11 }}>· {veh.capacity_kg} kg</span>
                        </div>
                      </div>
                    ) : <span className="muted">Unassigned</span>}
                  </td>
                  <td>
                    {zone ? (
                      <span className="chip" style={{ background: `${zone.color}22`, borderColor: zone.color }}>
                        <span style={{ width: 8, height: 8, background: zone.color, borderRadius: 2, display: "inline-block", marginRight: 4 }}></span>
                        {zone.name}
                      </span>
                    ) : <span className="muted">—</span>}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn sm ghost" onClick={() => openEdit(d)} data-testid={`edit-driver-${d.id}`}>Edit</button>
                    <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(d.id)} data-testid={`del-driver-${d.id}`}>Delete</button>
                  </td>
                </tr>
              );
            })}
            {drivers.length === 0 && <tr><td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No drivers.</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} title={editing ? "Edit Driver" : "New Driver"} onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={save} data-testid="save-driver-btn">{editing ? "Save" : "Create"}</button>
        </>}>
        <div className="row">
          <div className="field"><label className="label">Full name</label>
            <input className="input" data-testid="driver-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label className="label">Phone (unique)</label>
            <input className="input" data-testid="driver-phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
        </div>
        <div className="row">
          <div className="field"><label className="label">License Type</label>
            <select className="select" data-testid="driver-license" value={form.license_type} onChange={e => setForm({ ...form, license_type: e.target.value })}>
              <option value="A">A — Motorbike only</option>
              <option value="B">B — Motorbike or Van</option>
              <option value="C">C — Van / Truck only</option>
            </select></div>
          <div className="field"><label className="label">Operating Zone</label>
            <select className="select" data-testid="driver-zone" value={form.zone_id || ""} onChange={e => setForm({ ...form, zone_id: e.target.value })}>
              <option value="">— No zone (any) —</option>
              {zones.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
            </select></div>
        </div>
        <div className="muted" style={{ fontSize: 11.5 }}>
          Tip: license <b>B</b> is the most flexible — drivers can be matched to motorbikes <em>and</em> vans during auto-assignment.
        </div>
        {err && <div style={{ color: "#b91c1c", fontSize: 12 }}>{err}</div>}
      </Modal>
    </div>
  );
}
