import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Modal, Badge } from "../components/UI";

export default function Drivers() {
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [zones, setZones] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", license_type: "B" });
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const [d, v, z] = await Promise.all([http.get("/drivers"), http.get("/vehicles"), http.get("/zones")]);
    setDrivers(d.data); setVehicles(v.data); setZones(z.data);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", phone: "", license_type: "B" }); setOpen(true); setErr(""); };
  const openEdit = (d) => { setEditing(d); setForm({ name: d.name, phone: d.phone, license_type: d.license_type }); setOpen(true); setErr(""); };

  const save = async () => {
    try {
      setErr("");
      if (editing) await http.put(`/drivers/${editing.id}`, form);
      else await http.post("/drivers", form);
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
      <div className="page-subtitle">FR-03 · FR-04 · FR-05 — Manage drivers, their status and assignments</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-driver-btn" onClick={openNew}>+ Add Driver</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl" data-testid="drivers-table">
          <thead><tr>
            <th>Name</th><th>Phone</th><th>License</th><th>Status</th><th>Vehicle</th><th>Zone</th><th></th>
          </tr></thead>
          <tbody>
            {drivers.map(d => (
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
                <td>{d.vehicle_id ? <span className="chip">{vById[d.vehicle_id]?.plate || d.vehicle_id.slice(0,6)}</span> : <span className="muted">—</span>}</td>
                <td>{d.zone_id ? <span className="chip">{zById[d.zone_id]?.name || "Zone"}</span> : <span className="muted">—</span>}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn sm ghost" onClick={() => openEdit(d)} data-testid={`edit-driver-${d.id}`}>Edit</button>
                  <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(d.id)} data-testid={`del-driver-${d.id}`}>Delete</button>
                </td>
              </tr>
            ))}
            {drivers.length === 0 && <tr><td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No drivers.</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} title={editing ? "Edit Driver" : "New Driver"} onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={save} data-testid="save-driver-btn">{editing ? "Save" : "Create"}</button>
        </>}>
        <div className="field"><label className="label">Full name</label>
          <input className="input" data-testid="driver-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
        <div className="field"><label className="label">Phone (unique)</label>
          <input className="input" data-testid="driver-phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
        <div className="field"><label className="label">License Type</label>
          <select className="select" data-testid="driver-license" value={form.license_type} onChange={e => setForm({ ...form, license_type: e.target.value })}>
            <option value="A">A — Motorbike</option>
            <option value="B">B — Car</option>
            <option value="C">C — Van / Truck</option>
          </select></div>
        {err && <div style={{ color: "#b91c1c", fontSize: 12 }}>{err}</div>}
      </Modal>
    </div>
  );
}
