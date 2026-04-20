import React, { useEffect, useState } from "react";
import { http, fmtDate } from "../lib/api";
import { Modal, Badge } from "../components/UI";

export default function HubManagers() {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", hub_name: "", status: "available" });
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => { const r = await http.get("/hub-managers"); setRows(r.data); };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", phone: "", hub_name: "", status: "available" }); setOpen(true); setErr(""); };
  const openEdit = (hm) => { setEditing(hm); setForm({ name: hm.name, phone: hm.phone, hub_name: hm.hub_name || "", status: hm.status }); setOpen(true); setErr(""); };

  const save = async () => {
    try {
      setErr("");
      if (editing) await http.put(`/hub-managers/${editing.id}`, form);
      else await http.post("/hub-managers", form);
      setOpen(false); await load();
    } catch (e) { setErr(e.response?.data?.detail || "Error"); }
  };
  const remove = async (id) => { if (!window.confirm("Delete this hub manager?")) return; await http.delete(`/hub-managers/${id}`); load(); };

  return (
    <div>
      <div className="page-title"><span className="accent"></span>Hub Managers</div>
      <div className="page-subtitle">FR-01 · FR-02 — Manage hub managers and their operational status</div>

      <div className="toolbar">
        <button className="btn primary" data-testid="add-hub-manager-btn" onClick={openNew}>+ Add Hub Manager</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl" data-testid="hub-managers-table">
          <thead><tr><th>Name</th><th>Phone</th><th>Hub</th><th>Status</th><th>Created</th><th></th></tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id}>
                <td style={{ fontWeight: 500 }}>{r.name}</td>
                <td className="muted">{r.phone}</td>
                <td>{r.hub_name || "—"}</td>
                <td><Badge tone={r.status}>{r.status}</Badge></td>
                <td className="muted">{fmtDate(r.created_at)}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn sm ghost" onClick={() => openEdit(r)} data-testid={`edit-hm-${r.id}`}>Edit</button>
                  <button className="btn sm ghost" style={{ color: "#b91c1c" }} onClick={() => remove(r.id)} data-testid={`del-hm-${r.id}`}>Delete</button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No hub managers yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <Modal open={open} title={editing ? "Edit Hub Manager" : "New Hub Manager"} onClose={() => setOpen(false)}
        footer={<>
          <button className="btn" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn primary" onClick={save} data-testid="save-hm-btn">{editing ? "Save" : "Create"}</button>
        </>}>
        <div className="field"><label className="label">Full name</label>
          <input className="input" data-testid="hm-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
        <div className="field"><label className="label">Phone (unique)</label>
          <input className="input" data-testid="hm-phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
        <div className="field"><label className="label">Hub name</label>
          <input className="input" data-testid="hm-hub" value={form.hub_name} onChange={e => setForm({ ...form, hub_name: e.target.value })} /></div>
        <div className="field"><label className="label">Status</label>
          <select className="select" data-testid="hm-status" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
            <option value="available">Available</option>
            <option value="off_duty">Off-duty</option>
          </select></div>
        {err && <div style={{ color: "#b91c1c", fontSize: 12 }}>{err}</div>}
      </Modal>
    </div>
  );
}
