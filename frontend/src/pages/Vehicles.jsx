import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Modal, Badge } from "../components/UI";

export default function Vehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [form, setForm] = useState({ plate: "", type: "van", fuel_type: "ev", capacity_kg: 500 });
  const [open, setOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(null); // vehicle
  const [assignDriverId, setAssignDriverId] = useState("");

  const load = async () => {
    const [v, d] = await Promise.all([http.get("/vehicles"), http.get("/drivers")]);
    setVehicles(v.data); setDrivers(d.data);
  };
  useEffect(() => { load(); }, []);

  const create = async () => { await http.post("/vehicles", form); setOpen(false); load(); };
  const remove = async (id) => { if (!window.confirm("Delete this vehicle?")) return; await http.delete(`/vehicles/${id}`); load(); };
  const assign = async () => { await http.post(`/vehicles/${assignOpen.id}/assign`, { driver_id: assignDriverId }); setAssignOpen(null); setAssignDriverId(""); load(); };
  const unassign = async (v) => { await http.post(`/vehicles/${v.id}/unassign`); load(); };

  const dById = Object.fromEntries(drivers.map(d => [d.id, d]));

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Fleet</div>
      <div className="page-subtitle">FR-06 · FR-07 · FR-08 — Vehicles and driver assignment</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-vehicle-btn" onClick={() => { setForm({ plate: "", type: "van", fuel_type: "ev", capacity_kg: 500 }); setOpen(true); }}>+ Add Vehicle</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl" data-testid="vehicles-table">
          <thead><tr><th>Plate</th><th>Type</th><th>Fuel</th><th>Capacity</th><th>Assigned driver</th><th></th></tr></thead>
          <tbody>
            {vehicles.map(v => (
              <tr key={v.id}>
                <td style={{ fontWeight: 600 }}>{v.plate}</td>
                <td style={{ textTransform: "capitalize" }}>{v.type}</td>
                <td><Badge tone={v.fuel_type}>{v.fuel_type.toUpperCase()}</Badge></td>
                <td>{v.capacity_kg} kg</td>
                <td>{v.assigned_driver_id ? <span className="chip">{dById[v.assigned_driver_id]?.name || "driver"}</span> : <span className="muted">—</span>}</td>
                <td style={{ textAlign: "right" }}>
                  {!v.assigned_driver_id
                    ? <button className="btn sm" onClick={() => { setAssignOpen(v); setAssignDriverId(""); }} data-testid={`assign-vehicle-${v.id}`}>Assign</button>
                    : <button className="btn sm ghost" onClick={() => unassign(v)} data-testid={`unassign-vehicle-${v.id}`}>Unassign</button>}
                  <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(v.id)} data-testid={`del-vehicle-${v.id}`}>Delete</button>
                </td>
              </tr>
            ))}
            {vehicles.length === 0 && <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No vehicles.</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} title="New Vehicle" onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={create} data-testid="save-vehicle-btn">Create</button>
        </>}>
        <div className="field"><label className="label">Plate</label>
          <input className="input" data-testid="veh-plate" value={form.plate} onChange={e => setForm({ ...form, plate: e.target.value })} /></div>
        <div className="row">
          <div className="field"><label className="label">Type</label>
            <select className="select" data-testid="veh-type" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
              <option value="motorbike">Motorbike</option>
              <option value="van">Van</option>
            </select></div>
          <div className="field"><label className="label">Fuel</label>
            <select className="select" data-testid="veh-fuel" value={form.fuel_type} onChange={e => setForm({ ...form, fuel_type: e.target.value })}>
              <option value="ev">EV</option>
              <option value="diesel">Diesel</option>
            </select></div>
        </div>
        <div className="field"><label className="label">Capacity (kg)</label>
          <input className="input" type="number" data-testid="veh-capacity" value={form.capacity_kg}
            onChange={e => setForm({ ...form, capacity_kg: parseFloat(e.target.value) || 0 })} /></div>
      </Modal>

      <Modal open={!!assignOpen} title={`Assign ${assignOpen?.plate || ""}`} onClose={() => setAssignOpen(null)}
        footer={<>
          <button className="btn" onClick={() => setAssignOpen(null)}>Cancel</button>
          <button className="btn primary" disabled={!assignDriverId} onClick={assign} data-testid="confirm-assign-vehicle-btn">Assign</button>
        </>}>
        <div className="field"><label className="label">Driver</label>
          <select className="select" data-testid="veh-assign-driver" value={assignDriverId} onChange={(e) => setAssignDriverId(e.target.value)}>
            <option value="">— select —</option>
            {drivers.map(d => <option key={d.id} value={d.id}>{d.name}{d.vehicle_id ? ` (re-assign from another vehicle)` : ""}</option>)}
          </select></div>
      </Modal>
    </div>
  );
}
